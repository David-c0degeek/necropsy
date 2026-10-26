"""Rewrite the registered v2 measurement archive as v3 and compare its analysis.

Offline only. Every actor target stream becomes a derived stream: its page members
are the fight's encounter-All page bytes (identical already, see the 2026-10-26
capture-cost receipt), its identity becomes null and it gains the derivation
record, and its entries become GENERATED. Nothing else changes. The new code must
accept the v3 copy, and its analysis.json and pages must equal the v2 archive's
after the whitelisted provenance differences below. Check mode (the default)
compares with the committed receipt; ``--out FRESH`` writes a new one and
refuses to overwrite.
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import (
    EntryOrigin,
    VerifiedArchive,
    format_entries_manifest,
    load_entries_manifest,
)
from necropsy.snapshot.v1 import MARKER, open_snapshot

ROOT = Path(__file__).resolve().parents[4]
SOURCE = (
    ROOT / "tests/golden/raids/raw/naxx-balance-v2-measurement/77619978-2006-20261023T152230.zip"
)
SOURCE_SHA256 = "caa199389d11dab0d3c0678d086a352fb679d3e3cd133e62f2da0ecfef86dcb5"
RECEIPT = Path(__file__).with_name("receipt.json")
RULE = "target-equals-encounter-all-v1"
# The only fields allowed to differ between the v2 and v3 analyses: the archive's
# own digest and format, which honestly describe a different file.
WHITELIST = ("snapshot.archive_sha256", "snapshot.format")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def convert(work):
    require(sha256(SOURCE.read_bytes()) == SOURCE_SHA256, "source archive changed")
    entries = load_entries_manifest(SOURCE.with_suffix(".entries"))
    with zipfile.ZipFile(SOURCE) as z:
        members = {n: z.read(n) for n in z.namelist()}
    marker = json.loads(members[MARKER])
    parents = {
        (p["report"], p["fight"]): p
        for p in marker["encounter_streams"]
        if p["role"] == "encounter"
    }
    converted = 0
    for stream in marker["streams"]:
        if stream["direction"] != "target":
            continue
        parent = parents[(stream["report"], stream["fight"])]
        require(stream["pages"] == parent["pages"], "target pages are not the All pages")
        prefix = f"events/{stream['report']}/fight_{stream['fight']}/"
        folder = next(
            n.rsplit("/", 1)[0]
            for n in members
            if n.startswith(f"{prefix}{stream['role']}_{stream['actor_id']}_") and "/target_" in n
        )
        for n in range(1, len(parent["pages"]) + 1):
            mine = f"{folder}/target_{n:03d}.json"
            require(
                members[mine] == members[f"{prefix}encounter/all_{n:03d}.json"],
                "page bytes",
            )
            entries[mine] = entries[mine].__class__(
                mine, entries[mine].size, entries[mine].sha256, EntryOrigin.GENERATED
            )
        stream["identity"], stream["meta"] = None, {}
        stream["derivation"] = {
            "rule": RULE,
            "parent": parent["identity"],
            "parent_pages": parent["pages"],
        }
        converted += 1
    marker["formatVersion"] = 3
    members[MARKER] = json.dumps(marker, ensure_ascii=False).encode()
    entries[MARKER] = entries[MARKER].__class__(
        MARKER, len(members[MARKER]), sha256(members[MARKER]), entries[MARKER].origin
    )
    target = work / "77619978-2006-v3.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(members):
            z.writestr(name, members[name])
    target.with_suffix(".entries").write_text(
        format_entries_manifest(entries.values()), encoding="utf-8"
    )
    return target, converted


def analyse(archive, work, label):
    out = work / label
    run_offline(archive, out, db=work / f"{label}.duckdb")
    return {p.name: p.read_bytes() for p in sorted(out.iterdir()) if p.suffix in {".json", ".html"}}


def masked(document):
    """The whitelisted values, and the document with exactly those values replaced."""
    copy = json.loads(json.dumps(document))
    values = {}
    for path in WHITELIST:
        *parents, leaf = path.split(".")
        node = copy
        for key in parents:
            require(isinstance(node, dict) and key in node, f"{path} is missing")
            node = node[key]
        require(isinstance(node, dict) and leaf in node, f"{path} is missing")
        values[path], node[leaf] = node[leaf], f"<{path}>"
    return values, copy


def equal_outside_whitelist(left, right):
    """Exact structural equality (types, nulls, empty containers) after masking."""
    _, a = masked(left)
    _, b = masked(right)
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True) and a == b


def self_test():
    """The guard must see a missing null, a removed empty container and a changed value."""
    base = {"snapshot": {"archive_sha256": "a", "format": "f"}, "x": None, "y": [], "z": {}}
    require(equal_outside_whitelist(base, json.loads(json.dumps(base))), "self-test: equal")
    require(
        equal_outside_whitelist(base, {**base, "snapshot": {"archive_sha256": "b", "format": "g"}}),
        "self-test: whitelisted values",
    )
    for planted in (
        {k: v for k, v in base.items() if k != "x"},
        {k: v for k, v in base.items() if k != "y"},
        {k: v for k, v in base.items() if k != "z"},
        {**base, "x": 0},
        {**base, "y": {}},
    ):
        require(not equal_outside_whitelist(base, planted), f"self-test missed {planted}")


def flatten(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from flatten(v, f"{path}.{k}" if path else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from flatten(v, f"{path}[{i}]")
    else:
        yield path, value


def compare():
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        v3, converted = convert(work)
        with VerifiedArchive(v3, entries=load_entries_manifest(v3.with_suffix(".entries"))) as a:
            reader = open_snapshot(a)
            require(reader.issues() == [], "v3 copy has issues")
            fmt = reader.descriptor().format
        before = analyse(SOURCE, work, "v2")
        after = analyse(v3, work, "v3")
        require(set(before) == set(after), "different output files")
        self_test()
        left_doc = json.loads(before["analysis.json"])
        right_doc = json.loads(after["analysis.json"])
        require(
            equal_outside_whitelist(left_doc, right_doc),
            "analysis differs beyond the whitelisted provenance fields",
        )
        old, _ = masked(left_doc)
        new, _ = masked(right_doc)
        differing = [k for k in WHITELIST if old[k] != new[k]]
        left = dict(flatten(left_doc))
        pages = {}
        # Pages show the analysis digest (full and 12-hex) and the archive digest (12-hex);
        # both follow from the whitelisted fields, so exactly those labels are substituted.
        labels = {
            side: [
                (sha256(outputs["analysis.json"]), "<analysis.json sha256>"),
                (sha256(outputs["analysis.json"])[:12], "<analysis.json sha256[:12]>"),
                (str(values["snapshot.archive_sha256"]), "<archive sha256>"),
                (str(values["snapshot.archive_sha256"])[:12], "<archive sha256[:12]>"),
                (str(values["snapshot.format"]), "<snapshot format>"),
            ]
            for side, outputs, values in (("v2", before, old), ("v3", after, new))
        }
        for name in sorted(n for n in before if n.endswith(".html")):
            texts = {"v2": before[name].decode(), "v3": after[name].decode()}
            counts = {}
            for side in texts:
                for value, label in labels[side]:
                    counts.setdefault(label, {})[side] = texts[side].count(value)
                    texts[side] = texts[side].replace(value, label)
            require(texts["v2"] == texts["v3"], f"{name} differs beyond the whitelisted labels")
            pages[name] = {
                "v2_sha256": sha256(before[name]),
                "v3_sha256": sha256(after[name]),
                "equal_after_label_substitution": True,
                "label_occurrences": counts,
            }
        return {
            "kind": "Offline v2-to-v3 rewrite and analysis comparison; no capture or WCL call",
            "source": {"path": SOURCE.relative_to(ROOT).as_posix(), "sha256": SOURCE_SHA256},
            "derived_streams": converted,
            "v3_reader_format": fmt,
            "analysis_whitelist": list(WHITELIST),
            "analysis_differences": {k: {"v2": old.get(k), "v3": new.get(k)} for k in differing},
            "analysis_leaf_paths_counted": len(left),
            "pages": pages,
            "limits": [
                "The v3 copy's archive digest is environment-independent only up to zip "
                "compression; the receipt therefore records the analysis differences by path "
                "and value only for the v2 side, with the v3 digest checked as a sha256 shape.",
            ],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = compare()
    v3_digest = result["analysis_differences"].get("snapshot.archive_sha256", {}).get("v3")
    require(
        isinstance(v3_digest, str) and re.fullmatch(r"[0-9a-f]{64}", v3_digest) is not None,
        "v3 digest",
    )
    result["analysis_differences"]["snapshot.archive_sha256"]["v3"] = "<sha256 of the v3 copy>"
    for page in result["pages"].values():
        page["v3_sha256"] = "<depends on the v3 copy digest>"
    result["script_sha256"] = sha256(Path(__file__).read_bytes())
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    else:
        require(RECEIPT.read_bytes() == text.encode("utf-8"), "receipt differs from a fresh run")
    sys.stdout.reconfigure(encoding="utf-8")
    print("WROTE" if args.out else "PASS")


if __name__ == "__main__":
    main()
