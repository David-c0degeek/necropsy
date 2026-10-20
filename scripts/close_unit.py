"""Write and register the closures of one capture unit from a reviewed spec.

Usage: uv run python scripts/close_unit.py closures SPEC --commit REV [--replace]
       (commit the closure files)
       uv run python scripts/close_unit.py register SPEC
       uv run python scripts/close_unit.py rehash PATH   (a shared ledger changed)

A unit spec (JSON) holds what its cells share once and what differs per cell:

    {"unit": "mc/6/Holy/hps/Alliance",
     "archive": {"path": ..., "report": ...},
     "evidence_files": [paths pinned in every closure],
     "source_review": path, "evidence_pinning": text,
     "shared": {"fields": {...}, "limitations": [...]},
     "cells": {CELL_ID: {"fight": N, "actor": N, "report": code?, "archive": path?,
                         "source_review": path?,
                         "fields": {...}, "limitations": [...],
                         "references": {DIMENSION: [[path, locator], ...]},
                         "coverage_note": text, "matrix_note": text}
               | {"open": reason}}}

A cell's own "report" and "archive" replace the unit's: one capture holds
fights from many reports, and a cell's registered source can be another archive.
`closures` merges the shared and per-cell
fields (nested objects merge, a cell's value replaces any other), appends the
cell's limitations to the shared ones,
writes tests/golden/raids/closures/<raid>-<encounter>-<class>-<category>-<metric>-
<faction>.json and pins it to REV with closure_pins. A cell marked `open` gets no
closure and is reported, so a unit can close only some of its cells. Every
evidence file must already be committed at REV.

`register`, run once the closures are committed, first checks every closed cell:
its closure is committed and unchanged at HEAD, its pins verify, and its cell,
archive, report, fight and actor are the registered real actor source; every extra
reference is a HEAD blob the checkout still matches. Only then does it set each
closed cell COMPLETE
in coverage.json with references to its closure fields plus the spec's extra
references, and updates its matrix row. Both steps are mechanical: COMPLETE
still needs each dimension's reviewed evidence and applicability, which is the
review of the spec, the receipts and these files, never this script.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # run as a script: make the sibling tools importable
    sys.path.insert(0, str(ROOT))

from scripts import closure_pins  # noqa: E402

CLOSURES = "tests/golden/raids/closures"
COVERAGE = "tests/golden/raids/coverage.json"
MATRIX = "tasks/raid-completion/coverage-matrix.csv"
FIELDS = (
    "implementation",
    "mechanics_and_guidance",
    "synthetic_behavior",
    "real_actor_source",
    "independent_facts",
    "ranking_reconciliation",
    "render_review",
)
SHARED_LEDGER = re.compile(r"tests/golden/raids/[a-z0-9-]+-source-review\.json")
MATRIX_KEY = ("raid", "encounter_id", "class_id", "category", "metric", "faction")


def merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = merge(base[key], value) if key in base else copy.deepcopy(value)
        return merged
    return copy.deepcopy(override)


def closure_path(cell_id: str) -> str:
    raid, encounter, class_id, category, metric, faction = cell_id.split("/")
    name = "-".join((raid, encounter, class_id, category, metric, faction)).lower()
    return f"{CLOSURES}/{name}.json"


def matrix_rows(root: Path) -> tuple[list[list[str]], str]:
    raw = (root / MATRIX).read_bytes().decode("utf-8")
    return list(csv.reader(io.StringIO(raw))), ("\r\n" if "\r\n" in raw else "\n")


def matrix_row(rows: list[list[str]], cell_id: str) -> list[str]:
    raid, encounter, class_id, category, metric, faction = cell_id.split("/")
    head = rows[0]
    want = dict(
        zip(MATRIX_KEY, (raid, encounter, class_id, category, metric, faction), strict=True)
    )
    hits = [
        row
        for row in rows[1:]
        if all(row[head.index(k)] == v for k, v in want.items())
        and row[head.index("variant")] == "standard"
    ]
    if len(hits) != 1:
        raise ValueError(f"{cell_id}: {len(hits)} matrix rows")
    return hits[0]


def build(spec: dict[str, Any], cell_id: str, matrix: str) -> dict[str, Any]:
    cell = spec["cells"][cell_id]
    shared = spec.get("shared") or {}
    fields = merge(shared.get("fields") or {}, cell.get("fields") or {})
    missing = [f for f in FIELDS if f not in fields]
    if missing:
        raise ValueError(f"{cell_id}: closure fields missing {', '.join(missing)}")
    return {
        "version": 1,
        "cell_id": cell_id,
        "matrix_row": matrix,
        "commit": "",
        "archive": {
            "path": cell.get("archive") or spec["archive"]["path"],
            "sha256": "",
            "report": cell.get("report") or spec["archive"]["report"],
            "fight": cell["fight"],
            "actor": cell["actor"],
        },
        "evidence_files_at_closure": {path: "" for path in spec["evidence_files"]},
        "fields": {f: fields[f] for f in FIELDS},
        "limitations": [*(shared.get("limitations") or ()), *(cell.get("limitations") or ())],
        "evidence_pinning": spec["evidence_pinning"],
        "source_review": {
            "path": cell.get("source_review") or spec["source_review"],
            "sha256": "",
        },
    }


def closures(spec: dict[str, Any], rev: str, replace: bool, root: Path = ROOT) -> int:
    rows, _ = matrix_rows(root)
    written, opened = [], []
    for cell_id, cell in spec["cells"].items():
        if "open" in cell:
            opened.append(f"{cell_id}: open ({cell['open']})")
            continue
        target = root / closure_path(cell_id)
        if target.exists() and not replace:
            raise ValueError(f"{target.relative_to(root)} exists; pass --replace")
        line = io.StringIO()
        csv.writer(line, lineterminator="").writerow(matrix_row(rows, cell_id))
        draft = build(spec, cell_id, line.getvalue())
        # Pin a separate draft and replace the target only once that succeeded, so a
        # failure never changes or removes an existing closure.
        staging = target.with_name(f".{target.stem}.draft.json")
        staging.write_bytes((json.dumps(draft, indent=2, ensure_ascii=False) + "\n").encode())
        try:
            pinned, _ = closure_pins.pin_closure(root, staging.relative_to(root), rev)
            staging.write_bytes((json.dumps(pinned, indent=2, ensure_ascii=False) + "\n").encode())
            staging.replace(target)
        finally:
            staging.unlink(missing_ok=True)
        written.append(f"{target.relative_to(root).as_posix()} pinned to {pinned['commit'][:12]}")
    for line_ in [*written, *opened]:
        print(line_)
    return 0


def _committed(root: Path, path: str) -> bytes:
    """HEAD's blob for PATH, which the checkout must still match."""
    done = subprocess.run(
        ["git", "cat-file", "blob", f"HEAD:{path}"], cwd=root, capture_output=True, check=False
    )
    if done.returncode:
        raise ValueError(f"{path} is not committed at HEAD")
    if not (root / path).is_file() or (root / path).read_bytes() != done.stdout:
        raise ValueError(f"{path} differs from its HEAD blob")
    return done.stdout


def _ref(root: Path, path: str, locator: str) -> dict[str, str]:
    blob = _committed(root, path)
    return {"path": path, "sha256": hashlib.sha256(blob).hexdigest(), "locator": locator}


def _checked_closure(root: Path, cell_id: str, record: dict[str, Any]) -> str:
    """A committed, unchanged closure whose pins verify and whose cell and actor
    source are the registered ones."""
    path = closure_path(cell_id)
    closure = json.loads(_committed(root, path))
    problems, _ = closure_pins.verify_closure(root, Path(path))
    if problems:
        raise ValueError(f"{path}: {'; '.join(problems)}")
    source = record.get("real_actor_source")
    if not source:
        raise ValueError(f"{cell_id}: no registered real actor source")
    archive = closure["archive"]
    expected = (
        cell_id,
        source["archive"]["path"],
        source["archive"]["sha256"],
        source["report"],
        source["fight"],
        source["actor"],
    )
    found = (
        closure.get("cell_id"),
        archive["path"],
        archive["sha256"],
        archive["report"],
        archive["fight"],
        archive["actor"],
    )
    if found != expected:
        raise ValueError(f"{path}: cell or actor source differs from the registered source")
    return path


def register(spec: dict[str, Any], root: Path = ROOT) -> int:
    coverage = json.loads((root / COVERAGE).read_text(encoding="utf-8"))
    records = {r["cell_id"]: r for r in coverage["records"]}
    rows, newline = matrix_rows(root)
    head = rows[0]
    # Every check runs before either register changes.
    for cell_id, cell in spec["cells"].items():
        if "open" in cell:
            continue
        record = records.get(cell_id)
        if record is None:
            raise ValueError(f"{cell_id}: no registered real actor source")
        closure = _checked_closure(root, cell_id, record)
        extra = cell.get("references") or {}
        references: dict[str, list[dict[str, str]]] = {}
        for dimension in (
            "implementation",
            "mechanics_and_guidance",
            "synthetic_behavior",
            "independent_facts",
            "ranking_reconciliation",
            "render_review",
        ):
            refs = [_ref(root, p, loc) for p, loc in extra.get(dimension, ())]
            if dimension not in ("independent_facts", "ranking_reconciliation") or not refs:
                refs.insert(0, _ref(root, closure, f"fields.{dimension}"))
            elif dimension == "ranking_reconciliation":
                refs.append(_ref(root, closure, f"fields.{dimension}"))
            references[dimension] = refs
        record.update(status="COMPLETE", references=references, note=cell["coverage_note"])
        row = matrix_row(rows, cell_id)
        ranking = next(iter(extra.get("ranking_reconciliation", ())), None)
        facts = references["independent_facts"][0]
        values = {
            "implementation": f"{closure}#fields.implementation",
            "real_actor_source": f"{COVERAGE}#{cell_id}",
            "independent_facts": f"{facts['path']}#{facts['locator']}",
            "mechanics_and_guidance": f"{closure}#fields.mechanics_and_guidance",
            "synthetic_behavior": f"{closure}#fields.synthetic_behavior",
            "ranking_reconciliation": f"{ranking[0]}#{ranking[1]}"
            if ranking
            else f"{closure}#fields.ranking_reconciliation",
            "render_review": f"{closure}#fields.render_review",
            "status": "COMPLETE",
            "notes": cell["matrix_note"],
        }
        for column, value in values.items():
            row[head.index(column)] = value
        print(f"{cell_id}: COMPLETE")
    (root / COVERAGE).write_bytes(
        (json.dumps(coverage, indent=2, ensure_ascii=False) + "\n").encode()
    )
    out = io.StringIO()
    csv.writer(out, lineterminator=newline).writerows(rows)
    (root / MATRIX).write_bytes(out.getvalue().encode("utf-8"))
    return 0


def rehash(path: str, root: Path = ROOT) -> int:
    """Point every coverage reference to PATH at its committed HEAD blob.

    A shared ledger (a boss-major source review, for example) can grow after
    earlier cells registered it; their references then name an older hash. The
    file must be committed and unchanged; closures keep their own commit pins.
    Only shared source ledgers qualify: a closure or any other evidence file
    carries identity that only a full registration may check.
    """
    if not SHARED_LEDGER.fullmatch(path):
        raise ValueError(f"{path} is not a shared source ledger; register its cells instead")
    blob = _committed(root, path)
    digest = hashlib.sha256(blob).hexdigest()
    coverage = json.loads((root / COVERAGE).read_text(encoding="utf-8"))
    changed = 0
    for record in coverage["records"]:
        for refs in record.get("references", {}).values():
            for ref in refs:
                if ref["path"] == path and ref["sha256"] != digest:
                    ref["sha256"] = digest
                    changed += 1
    (root / COVERAGE).write_bytes(
        (json.dumps(coverage, indent=2, ensure_ascii=False) + "\n").encode()
    )
    print(f"{path}: {changed} reference(s) now name {digest[:12]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("closures", help="write and pin every closed cell's closure")
    write.add_argument("spec", type=Path)
    write.add_argument("--commit", required=True)
    write.add_argument("--replace", action="store_true")
    reg = sub.add_parser("register", help="register committed closures as COMPLETE")
    reg.add_argument("spec", type=Path)
    again = sub.add_parser("rehash", help="re-point coverage references to a committed file")
    again.add_argument("path")
    args = parser.parse_args(argv)
    if args.command == "rehash":
        try:
            return rehash(args.path)
        except (ValueError, OSError) as error:
            print(f"refused: {error}", file=sys.stderr)
            return 2
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    try:
        if args.command == "closures":
            return closures(spec, args.commit, args.replace)
        return register(spec)
    except (ValueError, KeyError, OSError, closure_pins.PinError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
