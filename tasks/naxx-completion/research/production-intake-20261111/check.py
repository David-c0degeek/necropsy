"""Strictly read the 2026-11-01..11 Naxx production archives, without network access.

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
  uv run python tasks/naxx-completion/research/production-intake-20261111/check.py
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
ARCHIVES = ROOT / "tests/golden/raids/raw/naxx-production-20261111"
QUEUE = ROOT / "tasks/capture-campaign/capture-queue.json"
QUEUE_SHA256 = "4f1a300a7b3ff61c7e6fbee8aef4a78a571da2c23ace5b74a8bb0a6efd603646"
ZONE, PARTITION = 2006, 1

# entry id -> (archive file name, pinned SHA-256 from the Tower sidecar)
PINS = {
    "naxxramas-druid-guardian-dps-horde": (
        "70621233-2006-20261101T123113.zip",
        "2fc02829c6013cb5bac380868754ee7689bc531819d85265d5f84f809bbea947",
    ),
    "naxxramas-druid-restoration-hps-alliance": (
        "60117765-2006-20261102T031646.zip",
        "5bb2468398c6b371d012ee717af46b5c52a4de0da78d7993f4b84dc2e8e50277",
    ),
    "naxxramas-druid-restoration-hps-horde": (
        "77577270-2006-20261103T040708.zip",
        "f2151316bf0531ee4187a54e5f234c18b29028f9418e3d7d513d83521c2a681d",
    ),
    "naxxramas-hunter-marksmanship-dps-alliance": (
        "75928820-2006-20261103T162831.zip",
        "98a2d5a39d3b85dfee8db0b777b1c74cbef11656138baa5b7b892302311050a1",
    ),
    "naxxramas-hunter-marksmanship-dps-horde": (
        "64181902-2006-20261104T151326.zip",
        "107c7bcb85e14bd9b69038141be282a8a5d8bc19e25b2d7f01609122d453349a",
    ),
    "naxxramas-mage-fire-dps-alliance": (
        "62428883-2006-20261104T171719.zip",
        "b887a4cf00d399171bf15023caae084a8eea139c3886ec76e4fbb29c3c3ab370",
    ),
    "naxxramas-mage-fire-dps-horde": (
        "62508348-2006-20261104T223319.zip",
        "b61a8d4304e0e0b546a6cf8ff045c5fe9c807a91d8a1e93f287f54760302546d",
    ),
    "naxxramas-mage-frost-dps-alliance": (
        "96494133-2006-20261105T033802.zip",
        "6c0c59209ab15336d31b0f5e38e56873b050d9be0d4546bc4cde16039bb1fb71",
    ),
    "naxxramas-mage-frost-dps-horde": (
        "83910414-2006-20261105T054215.zip",
        "3ad2f7dba9a65ac121ccfd7b140d1d31e8c22574197285bb0f32d4a6fd222ac0",
    ),
    "naxxramas-paladin-holy-hps-alliance": (
        "77152471-2006-20261105T150116.zip",
        "566899fe83351370211b425ae94f48a0d367fbb9ecd0d26ca7d870df76838618",
    ),
    "naxxramas-paladin-protection-dps-alliance": (
        "67666001-2006-20261105T232014.zip",
        "b768ff71aa948c5091eb22eafbc8baa9e3a36165c0304d39d9d48b113ec1b591",
    ),
    "naxxramas-paladin-retribution-dps-alliance": (
        "76716431-2006-20261106T042624.zip",
        "3b64e402362774511ae10a81c176e4cacf9aae04b62778dab30dd26a38c67585",
    ),
    "naxxramas-priest-holy-hps-alliance": (
        "77573659-2006-20261106T154918.zip",
        "d292ee0e8a3db304a504e98ecc0528b70e43446dd74548afaf5788d8af9d8139",
    ),
    "naxxramas-priest-holy-hps-horde": (
        "77516109-2006-20261107T143644.zip",
        "6261e9d695747c333065fa0655f610a7b7bd0be5015f47f70395edf7e7789eca",
    ),
    "naxxramas-priest-shadow-dps-alliance": (
        "77122652-2006-20261107T163813.zip",
        "85f096bcc2951498da23e9d8e3297387fc1bd899217ec963867b977459298585",
    ),
    "naxxramas-priest-shadow-dps-horde": (
        "66195792-2006-20261108T070712.zip",
        "05aa6d44d37a8dcbf6a64ccc17060b81f0d42f4abaa4c69a8eba453510c3f6de",
    ),
    "naxxramas-rogue-assassination-dps-alliance": (
        "77022735-2006-20261108T142205.zip",
        "f677e3ee78aeefc0ffe92aba276c7110707df719c2a3d05585a4aa47aa2abbb6",
    ),
    "naxxramas-rogue-assassination-dps-horde": (
        "62246596-2006-20261108T183110.zip",
        "fe4586f7b35248d9aac33bd34fee7bae7499e57c9f39a27cd524ff3fd2cd9078",
    ),
    "naxxramas-shaman-elemental-dps-horde": (
        "80764809-2006-20261109T140845.zip",
        "750c3d91e175728e632f7b185f8cf3e078ad780c9fb94f7a0e43f0777e97f9d2",
    ),
    "naxxramas-shaman-enhancement-dps-horde": (
        "74643978-2006-20261109T142333.zip",
        "c794197d7cce61dd8817f1b85be4eb6a570c9880b9765922743b50586dc4592d",
    ),
    "naxxramas-shaman-restoration-hps-horde": (
        "62259058-2006-20261109T151537.zip",
        "d6828c7a2256d1cbc284cd828a839d24c088cd11a5429aedc125819e2836756a",
    ),
    "naxxramas-warlock-destruction-dps-alliance": (
        "77751784-2006-20261109T171544.zip",
        "44aa5ecd2af4f99afc994efb5cc9832d2dc9026370c15b908a5d1f0924f71068",
    ),
    "naxxramas-warlock-destruction-dps-horde": (
        "64322945-2006-20261110T064311.zip",
        "62ee186326d8affa4f56d5e53616640e38e5f8fc87ffae5396d0806bb576684d",
    ),
    "naxxramas-warrior-fury-dps-alliance": (
        "76296293-2006-20261110T135634.zip",
        "e563a99f200c4df744213a18292b941ad51c418c9efadc420f7df7b691ab3457",
    ),
    "naxxramas-warrior-fury-dps-horde": (
        "75322236-2006-20261110T150026.zip",
        "3750625e922916fb4f3a6cf7243311216149d77b3b09eeebffcdcd43558f76dd",
    ),
    "naxxramas-warrior-protection-dps-alliance": (
        "75466963-2006-20261111T134356.zip",
        "fb12765c9b6fd67e8cb252b09df71668d12ee793cb22bd20be4afcf2d86b1442",
    ),
    "naxxramas-warrior-protection-dps-horde": (
        "61334639-2006-20261111T164838.zip",
        "21e6e2cd5b1414f44b76357454889f90a030870bde28d1a9fbbf9ab20c46e1f9",
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
            "archive": f"tests/golden/raids/raw/naxx-production-20261111/{name}",
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
