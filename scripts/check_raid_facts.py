"""Independent raw actor arithmetic; never calls an analyzer or normalizer.

    uv run python scripts/check_raid_facts.py tests/golden/raids/facts.json

Frozen expectations must be reviewed from raw evidence before registering them.
This command checks expectations; it cannot generate or refresh them.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest


def _events(archive: VerifiedArchive, report: str, fight: int, actor: int) -> list[dict[str, Any]]:
    prefix = f"events/{report}/fight_{fight}/player_{actor}_"
    streams: dict[str, Counter[str]] = defaultdict(Counter)
    events: dict[str, dict[str, Any]] = {}
    terminal: dict[str, bool] = {}
    for name in sorted(archive.names()):
        if not name.startswith(prefix) or not any(s in name for s in ("/source_", "/target_")):
            continue
        page = archive.read_json(name)
        stream = name.rsplit("_", 1)[0]
        if "nextPageTimestamp" not in page:
            raise ValueError("raw page does not establish stream completion")
        terminal[stream] = page["nextPageTimestamp"] is None
        for event in page["data"]:
            identity = json.dumps(event, sort_keys=True, separators=(",", ":"))
            events[identity] = event
            streams[stream][identity] += 1
    if {s.rsplit("/", 1)[-1] for s in terminal} != {"source", "target"}:
        raise ValueError("both raw actor stream directions are required")
    if not all(terminal.values()):
        raise ValueError("raw actor stream is incomplete")
    # A self heal occurs in both directions. Union by maximum multiplicity,
    # retaining identical legitimate events repeated within either stream.
    occurrences: Counter[str] = Counter()
    for counts in streams.values():
        occurrences |= counts
    return [events[key] for key, count in occurrences.items() for _ in range(count)]


def raw_actor_facts(
    archive: VerifiedArchive, report: str, fight: int, actor: int
) -> dict[str, Any]:
    bundle = archive.read_json(f"reports/{report}/bundle.json")["reportData"]["report"]
    f = next(f for f in bundle["fights"] if f["id"] == fight)
    a = next(a for a in bundle["masterData"]["actors"] if a["id"] == actor)
    events = _events(archive, report, fight, actor)
    if not events:
        raise ValueError("no usable raw actor events")
    outgoing = [e for e in events if e.get("sourceID") == actor]
    incoming = [e for e in events if e.get("targetID") == actor]
    totals = {
        "damage": sum(e.get("amount", 0) for e in outgoing if e["type"] == "damage"),
        "effective_healing": sum(e.get("amount", 0) for e in outgoing if e["type"] == "heal"),
        "absorbed_amount": sum(e.get("amount", 0) for e in outgoing if e["type"] == "absorbed"),
        "incoming_damage": sum(e.get("amount", 0) for e in incoming if e["type"] == "damage"),
    }
    casts: dict[str, list[int]] = defaultdict(list)
    targets: Counter[str] = Counter()
    for e in outgoing:
        ability = e.get("abilityGameID")
        if ability is None and isinstance(e.get("ability"), dict):
            ability = e["ability"].get("guid")
        if e["type"] == "cast":
            casts[str(ability)].append(e["timestamp"] - f["startTime"])
        if e["type"] == "damage":
            targets[str(e.get("targetID"))] += e.get("amount", 0)
    return {
        "encounter_id": f["encounterID"],
        "revision": bundle["revision"],
        "duration_ms": f["endTime"] - f["startTime"],
        "actor_class": a["subType"],
        "actor_game_id": a.get("gameID"),
        "totals": totals,
        "casts_ms": {key: sorted(value) for key, value in sorted(casts.items())},
        "damage_by_actor": dict(sorted(targets.items())),
        "target_game_ids": {
            str(a["id"]): a.get("gameID")
            for a in bundle["masterData"]["actors"]
            if str(a["id"]) in targets
        },
        "pet_ownership": {
            str(p["id"]): {
                "game_id": p.get("gameID"),
                "fight_owner": p.get("petOwner"),
                "master_owner": next(
                    (
                        a.get("petOwner")
                        for a in bundle["masterData"]["actors"]
                        if a["id"] == p["id"]
                    ),
                    None,
                ),
            }
            for p in f.get("friendlyPets") or []
        },
    }


def check_register(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not data.get("cases"):
        raise ValueError("a fact register needs version 1 and nonempty reviewed cases")
    problems = []
    for case in data["cases"]:
        if not case.get("review_basis"):
            problems.append(f"{case['id']}: missing independent review basis")
        archive_path = path.parent / case["archive"]
        entries = load_entries_manifest(path.parent / case["entries"])
        with VerifiedArchive(
            archive_path, expected_sha256=case["sha256"], entries=entries
        ) as archive:
            actual = raw_actor_facts(archive, case["report"], case["fight"], case["actor"])
        expected = case["expected"]
        if set(expected) != set(actual):
            problems.append(f"{case['id']}: expected fact dimensions differ from raw checker")
        for field in expected:
            if expected[field] != actual.get(field):
                problems.append(f"{case['id']}: {field} differs from frozen raw expectation")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("register", type=Path)
    args = parser.parse_args()
    problems = check_register(args.register)
    print(json.dumps({"problems": problems}, indent=2))
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
