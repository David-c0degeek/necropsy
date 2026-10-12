"""Developer tooling for the frozen Haplina golden fixture.

Not part of the shipped CLI. Commands:

  entries <archive> <out>          Write an entries manifest (sha256, size, origin, name)
                                   for every member of a trusted archive.
  subset <archive> <entries> <out-zip> <out-entries>
                                   Build the deterministic fast-test subset from the
                                   full export, verifying every source member.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from necropsy.snapshot.archive import (
    EntryDigest,
    EntryOrigin,
    VerifiedArchive,
    format_entries_manifest,
    load_entries_manifest,
    sha256_file,
)

SUBSET_DESCRIPTOR = "subset.json"
SUBSET_KIND = "necropsy.fixture-subset"
SUBSET_FORMAT_VERSION = 1
_FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)
_UNIX_CREATE_SYSTEM = 3
_FILE_MODE = 0o644 << 16


@dataclass(frozen=True)
class BossRule:
    boss: str
    all_participants: bool


# Fast-test scope: every recorded Patchwerk fight (weave, Windfury, Renataki,
# pet benchmarks) plus Haplina and rank 1 on the encounters with known
# forensic findings (Grobbulus pet death, Gothik foreign trash, KT raid utility).
SUBSET_RULES = (
    BossRule("Patchwerk", all_participants=True),
    BossRule("Grobbulus", all_participants=False),
    BossRule("Gothik the Harvester", all_participants=False),
    BossRule("Kel'Thuzad", all_participants=False),
)


def _wanted(rule: BossRule, participant: dict[str, Any]) -> bool:
    if rule.all_participants:
        return True
    return participant["kind"] == "you" or participant.get("leaderboardPosition") == 1


def select_subset(selection: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = {r.boss: r for r in SUBSET_RULES}
    chosen: list[dict[str, Any]] = []
    for fight in selection:
        keep = [
            {
                "kind": p["kind"],
                "player": p["player"],
                "boss": p["boss"],
                "leaderboardPosition": p.get("leaderboardPosition"),
            }
            for p in fight["participants"]
            if p["boss"] in rules and _wanted(rules[p["boss"]], p)
        ]
        if keep:
            chosen.append(
                {"reportID": fight["reportID"], "fightID": fight["fightID"], "participants": keep}
            )
    return sorted(chosen, key=lambda f: (f["reportID"], f["fightID"]))


def _boss_slugs(names: list[str], bosses: set[str]) -> set[str]:
    slugs: set[str] = set()
    for name in names:
        if name.startswith(("leaderboards/", "user_rankings/")):
            stem = name.split("/", 1)[1].removesuffix(".json")
            if stem.split("_", 1)[1] in bosses:
                slugs.add(name)
    return slugs


def subset_members(names: list[str], fights: list[dict[str, Any]]) -> list[str]:
    reports = {f["reportID"] for f in fights}
    fight_dirs = {f"events/{f['reportID']}/fight_{f['fightID']}/" for f in fights}
    bosses = {p["boss"] for f in fights for p in f["participants"]}
    keep = {"profile.json", "manifest.json", "selection.json"}
    keep |= _boss_slugs(names, bosses)
    for name in names:
        parts = name.split("/")
        if parts[0] == "reports" and parts[1] in reports:
            keep.add(name)
        if parts[0] == "events" and any(name.startswith(d) for d in fight_dirs):
            keep.add(name)
    missing_dirs = [d for d in fight_dirs if not any(n.startswith(d) for n in keep)]
    if missing_dirs:
        raise SystemExit(f"selected fights without event members: {sorted(missing_dirs)}")
    return sorted(keep)


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=_FIXED_DATE_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = _UNIX_CREATE_SYSTEM
    info.external_attr = _FILE_MODE
    return info


def build_subset(archive_path: Path, entries_path: Path, out_zip: Path, out_entries: Path) -> None:
    entries = load_entries_manifest(entries_path)
    with VerifiedArchive(archive_path, entries=entries) as archive:
        selection = archive.read_json("selection.json")
        fights = select_subset(selection)
        members = subset_members(archive.names(), fights)
        descriptor = {
            "kind": SUBSET_KIND,
            "formatVersion": SUBSET_FORMAT_VERSION,
            "source": {
                "archive": archive_path.name,
                "sha256": archive.sha256,
                "entriesManifestSha256": sha256_file(entries_path),
                "fightCount": len(selection),
            },
            "fights": fights,
            "excludedFightCount": len(selection) - len(fights),
            "note": (
                "Defines the subset scope. selection.json and manifest.json are the "
                "unmodified full-export originals and do not describe this subset."
            ),
        }
        descriptor_bytes = (json.dumps(descriptor, indent=2, ensure_ascii=False) + "\n").encode()
        digests: list[EntryDigest] = []
        out_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_zip, "w", compresslevel=9) as out:
            for name in sorted([*members, SUBSET_DESCRIPTOR]):
                if name == SUBSET_DESCRIPTOR:
                    data, origin = descriptor_bytes, EntryOrigin.GENERATED
                else:
                    data, origin = archive.read_bytes(name), EntryOrigin.SOURCE
                out.writestr(_zip_info(name), data)
                digests.append(
                    EntryDigest(name, len(data), hashlib.sha256(data).hexdigest(), origin)
                )
    out_entries.write_text(format_entries_manifest(digests), encoding="utf-8", newline="\n")


def write_entries(archive_path: Path, out: Path) -> None:
    with VerifiedArchive(archive_path) as archive:
        text = format_entries_manifest(archive.iter_digests(EntryOrigin.SOURCE))
    out.write_text(text, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    entries = sub.add_parser("entries")
    entries.add_argument("archive", type=Path)
    entries.add_argument("out", type=Path)
    subset = sub.add_parser("subset")
    subset.add_argument("archive", type=Path)
    subset.add_argument("entries", type=Path)
    subset.add_argument("out_zip", type=Path)
    subset.add_argument("out_entries", type=Path)
    args = parser.parse_args(argv)
    if args.command == "entries":
        write_entries(args.archive, args.out)
    else:
        build_subset(args.archive, args.entries, args.out_zip, args.out_entries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
