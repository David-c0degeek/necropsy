"""Strictly read the 2026-10-27..31 Naxx production archives, without network access.

Every archive is opened against its pinned SHA-256 and entries manifest, every
member is read back through that manifest, and the strict v1/v3 reader must
report no unplaced content. The marker subject must match its queue entry in the
pinned production queue, with the production zone, partition and user endpoint.
Every expected stream is read; statuses are tallied per role and direction.
Per boss, the receipt keeps cohort size, usable deep comparisons, the coverage
flags and the coverage reasons that make the archive partial.

This classifies source evidence only. It registers no actor, admits no
comparison and changes no cell status.

Usage:
  uv run python tasks/naxx-completion/research/production-intake-20261031/check.py
  uv run python ... check.py --out FRESH   # write a new receipt; never overwrites
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from necropsy.snapshot.archive import (  # noqa: E402
    VerifiedArchive,
    load_entries_manifest,
    sha256_file,
)
from necropsy.snapshot.v1 import MARKER, open_snapshot  # noqa: E402
from necropsy.snapshot.v3 import ENCOUNTER_FORMATS  # noqa: E402
from scripts.capture_runner import load_queue  # noqa: E402

HERE = Path(__file__).resolve().parent
RECEIPT = HERE / "receipt.json"
ARCHIVES = ROOT / "tests/golden/raids/raw/naxx-production-20261031"
QUEUE = ROOT / "tasks/naxx-completion/capture-queue.json"
QUEUE_SHA256 = "888b8d8d0355e985c7d8017f61b3dd864af56fd58d3701771647ce4eb9fc8552"
ZONE, PARTITION = 2006, 1

# entry id -> (archive file name, pinned SHA-256 from the Tower sidecar)
PINS = {
    "naxxramas-druid-balance-dps-horde": (
        "64347501-2006-20261027T093033.zip",
        "7021b6a180220f5933e700ec5121db16441526d5004d88679d6bf48e98718ab2",
    ),
    "naxxramas-druid-balance-hps-alliance": (
        "65603754-2006-20261027T195031.zip",
        "f439dc7db47a18dcda8d5db7264be0990cd042124900315b93fff583bf2220be",
    ),
    "naxxramas-druid-balance-hps-horde": (
        "76376122-2006-20261028T163059.zip",
        "392bf13fb1350ae468253631895b9be591d46516a40d020a00dcaa568fa1ef4f",
    ),
    "naxxramas-druid-feral-dps-alliance": (
        "75650895-2006-20261029T065847.zip",
        "be76c08559f11ed91b648a7a3aa88970647c7a333552356b6e84049511578633",
    ),
    "naxxramas-druid-feral-dps-horde": (
        "77548335-2006-20261030T095117.zip",
        "4e39a080967408826e0ac36826f90cfb9094230407a7e5b4c5f437c8c7b7a82e",
    ),
    "naxxramas-druid-guardian-dps-alliance": (
        "83306366-2006-20261031T073441.zip",
        "d6ecd3846ba9a27641ce80eb801006d630432348fd0283594d2f805dda7dcb55",
    ),
}


def require(condition: bool, message: str) -> None:
    """Keep every verification guard active under python -O/PYTHONOPTIMIZE."""
    if not condition:
        raise AssertionError(message)


def read_archive(entry: Any, name: str, digest: str) -> dict[str, Any]:
    path = ARCHIVES / name
    entries = path.with_suffix(".entries")
    with VerifiedArchive(
        path, expected_sha256=digest, entries=load_entries_manifest(entries)
    ) as archive:
        members = archive.names()
        for member in members:
            archive.read_bytes(member)  # every member against the manifest
        reader = open_snapshot(archive)
        descriptor = reader.descriptor()
        require(descriptor.format in ENCOUNTER_FORMATS, f"{name}: not an encounter snapshot")
        require(not reader.issues(), f"{name}: unplaced content {reader.issues()}")
        marker = archive.read_json(MARKER)
        subject = marker["subject"]
        expected = {
            "class_id": entry.class_id,
            "faction": entry.faction,
            "ranking_category": entry.category,
            "ranking_metric": entry.metric,
        }
        require(
            all(subject.get(k) == v for k, v in expected.items()),
            f"{name}: subject differs from queue entry {entry.entry_id}",
        )
        identity = "/".join(
            str(subject.get(k, "")).lower().replace(" ", "-") for k in ("region", "server", "name")
        )
        forms = {f"/character/{identity}?", f"/character/id/{subject['id']}?"}
        require(
            any(form in c.lower() for c in entry.candidates for form in forms),
            f"{name}: subject {identity} is not a queue candidate",
        )
        require(
            descriptor.zone.id == ZONE
            and descriptor.zone.partition == PARTITION
            and marker["endpoint"] == "user",
            f"{name}: zone, partition or endpoint differs from production",
        )
        streams: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
        for ref in reader.expected_streams():
            result = reader.read_stream(ref)
            streams[f"{ref.role.value}/{ref.direction.value}"][result.status.value] += 1
        bosses = []
        for boss in marker["bosses"]:
            coverage = boss["coverage"]
            bosses.append(
                {
                    "encounter_id": boss["encounter_id"],
                    "boss": boss["boss"],
                    "attempted": boss["attempted"],
                    "subject_status": (boss.get("subject") or {}).get("status"),
                    "cohort": len(boss.get("cohort") or []),
                    "usable_deep": coverage.get("usable_deep"),
                    "target": coverage.get("target"),
                    "complete": coverage.get("complete"),
                    "below_minimum": coverage.get("below_minimum"),
                    "dropped": len(boss.get("dropped") or []),
                    "selection_stop": (boss.get("selection") or {}).get("stop"),
                    "reasons": coverage.get("reasons", []),
                }
            )
        bosses.sort(key=lambda b: b["encounter_id"])
        return {
            "entry": entry.entry_id,
            "archive": f"tests/golden/raids/raw/naxx-production-20261031/{name}",
            "sha256": archive.sha256,
            "entries_sha256": sha256_file(entries),
            "members": len(members),
            "format": descriptor.format,
            "kind": marker["kind"],
            "subject": {k: subject.get(k) for k in ("id", "name", "server", "faction")},
            "top_n": marker["top_n"],
            "cohort_mode": marker["cohort"],
            "stopped": marker["stopped"],
            "fights": len(descriptor.fights),
            "participants": sum(len(f.participants) for f in descriptor.fights),
            "streams": {k: dict(sorted(v.items())) for k, v in sorted(streams.items())},
            "bosses": bosses,
            "complete_bosses": sum(1 for b in bosses if b["complete"]),
            "below_minimum_bosses": sum(1 for b in bosses if b["below_minimum"]),
        }


def build() -> dict[str, Any]:
    queue_sha, queue = load_queue(QUEUE)
    require(queue_sha == QUEUE_SHA256, "production queue changed")
    by_id = {e.entry_id: e for e in queue}
    archives = [read_archive(by_id[eid], name, digest) for eid, (name, digest) in PINS.items()]
    return {
        "kind": "Naxx production archive intake; source classification only",
        "queue_sha256": queue_sha,
        "checker_sha256": sha256_file(Path(__file__)),
        "archives": archives,
        "limits": [
            "No actor is registered, no comparison admitted, no cell status changed.",
            "Archive bytes are pinned; a clean checkout needs them restored first.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, help="write a fresh receipt; refuses to overwrite")
    args = parser.parse_args(argv)
    result = build()
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print(f"wrote {args.out}")
        return 0
    stored = json.loads(RECEIPT.read_text(encoding="utf-8"))
    stored.pop("checker_sha256", None)
    fresh = dict(result)
    fresh.pop("checker_sha256", None)
    require(stored == fresh, "replay differs from the committed receipt")
    print(f"replay matches receipt: {len(result['archives'])} archives")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
