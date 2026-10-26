"""Verify a produced capture's selected fight, independently of runner exit status.

Supply the archive's recorded SHA-256, entries manifest, exact staged queue and
entry, resolved subject id and selected report/fight/encounter. This verifies
archive integrity and complete v2 scopes; it does not certify domain findings
or full-raid completion. The receipt records interpreter and input digests.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from necropsy import __version__  # noqa: E402
from necropsy.raids import RAIDS  # noqa: E402
from necropsy.snapshot.archive import (  # noqa: E402
    ArchiveError,
    VerifiedArchive,
    load_entries_manifest,
    sha256_file,
)
from necropsy.snapshot.model import ActorRole, SnapshotError, StreamStatus  # noqa: E402
from necropsy.snapshot.v1 import MARKER, open_snapshot  # noqa: E402
from necropsy.snapshot.v3 import ENCOUNTER_FORMATS  # noqa: E402
from scripts.capture_runner import Entry, QueueError, load_queue  # noqa: E402


def verify_capture(
    archive_path: Path,
    digest: str,
    entries: Path,
    entry: Entry,
    *,
    subject_id: int,
    report: str,
    fight: int,
    encounter: int,
) -> dict[str, Any]:
    raid = next((r for r in RAIDS if r.slug == entry.raid), None)
    if raid is None:
        raise ValueError("queue entry has an unsupported raid")
    with VerifiedArchive(
        archive_path, expected_sha256=digest, entries=load_entries_manifest(entries)
    ) as archive:
        for member in archive.names():
            archive.read_bytes(member)  # Check every member against the supplied manifest.
        reader = open_snapshot(archive)
        descriptor = reader.descriptor()
        if descriptor.format not in ENCOUNTER_FORMATS or reader.issues():
            raise ValueError(
                "capture must be a recognized encounter snapshot without unplaced content"
            )
        marker = archive.read_json(MARKER)
        subject = marker["subject"]
        expected = {
            "id": subject_id,
            "class_id": entry.class_id,
            "faction": entry.faction,
            "ranking_category": entry.category,
            "ranking_metric": entry.metric,
        }
        if any(subject.get(k) != v for k, v in expected.items()):
            raise ValueError(
                "capture subject differs from the expected entry and resolved identity"
            )
        if (
            descriptor.zone.id != raid.zone_id
            or descriptor.zone.partition != entry.partition
            or marker["endpoint"] != "user"
        ):
            raise ValueError(
                "capture zone, partition or endpoint differs from the production entry"
            )
        selected = [f for f in descriptor.fights if (f.report_code, f.fight_id) == (report, fight)]
        if len(selected) != 1 or not any(
            p.encounter_id == encounter for p in selected[0].participants
        ):
            raise ValueError("expected report, fight and encounter are not selected")
        refs = [
            r for r in reader.expected_streams() if (r.report_code, r.fight_id) == (report, fight)
        ]
        if not {ActorRole.ENCOUNTER, ActorRole.CRITICAL} <= {r.role for r in refs}:
            raise ValueError("selected fight lacks encounter or critical scope")
        streams = []
        for ref in refs:
            result = reader.read_stream(ref)
            if result.status is not StreamStatus.COMPLETE:
                raise ValueError(f"selected fight has incomplete {ref.role}/{ref.direction} scope")
            streams.append(
                {
                    "role": ref.role.value,
                    "direction": ref.direction.value,
                    "actor_id": ref.actor_id,
                    "pages": result.pages,
                    "events": len(result.events),
                }
            )
        return {
            "status": "verified",
            "scope": "selected fight only; not full-raid or domain acceptance",
            "checked_at": datetime.now(UTC).isoformat(),
            "python": platform.python_version(),
            "necropsy_version": __version__,
            "verifier_sha256": sha256_file(Path(__file__)),
            "archive_sha256": archive.sha256,
            "entries_sha256": sha256_file(entries),
            "entry": entry.label(),
            "subject_id": subject_id,
            "report": report,
            "fight": fight,
            "encounter": encounter,
            "streams": streams,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--subject-id", type=int, required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--fight", type=int, required=True)
    parser.add_argument("--encounter", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True, help="fresh receipt file")
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise ValueError("receipt already exists; choose a fresh output file")
        pin, entries = load_queue(args.queue)
        matches = [e for e in entries if e.entry_id == args.entry]
        if len(matches) != 1:
            raise ValueError("queue does not contain the expected entry")
        receipt = verify_capture(
            args.archive,
            args.sha256,
            args.entries,
            matches[0],
            subject_id=args.subject_id,
            report=args.report,
            fight=args.fight,
            encounter=args.encounter,
        )
        receipt["queue_sha256"] = pin
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    except (ArchiveError, SnapshotError, QueueError, OSError, ValueError) as error:
        print(f"capture verification refused: {error}", file=sys.stderr)
        return 2
    print(f"verified v2 fight {args.report}/{args.fight}; receipt {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
