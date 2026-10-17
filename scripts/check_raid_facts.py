"""Independent raw actor arithmetic; never calls an analyzer or normalizer.

    uv run python scripts/check_raid_facts.py tests/golden/raids/facts.json

Frozen expectations must be reviewed from raw evidence before registering them.
This command checks expectations; it cannot generate or refresh them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest


def _pages(
    archive: VerifiedArchive, prefix: str, direction: str, start: int, end: int
) -> tuple[list[dict[str, Any]], list[str]]:
    names = sorted(n for n in archive.names() if n.startswith(f"{prefix}/{direction}_"))
    if not names or names != [
        f"{prefix}/{direction}_{i:03d}.json" for i in range(1, len(names) + 1)
    ]:
        raise ValueError("raw stream pages are missing or non-contiguous")
    events = []
    cursor: int | float = start
    for index, name in enumerate(names):
        page = archive.read_json(name)
        if not isinstance(page, dict) or "nextPageTimestamp" not in page:
            raise ValueError("raw stream does not establish completion")
        data = page.get("data")
        if not isinstance(data, list) or not all(isinstance(e, dict) for e in data):
            raise ValueError("raw stream data is malformed")
        events.extend(data)
        following = page["nextPageTimestamp"]
        if following is None:
            if index != len(names) - 1:
                raise ValueError("raw stream has pages after its terminal page")
        elif (
            type(following) not in (int, float)
            or not math.isfinite(following)
            or not cursor < following <= end
            or index == len(names) - 1
        ):
            raise ValueError("raw stream has an invalid or unterminated cursor")
        else:
            cursor = following
    return events, names


def _events(
    archive: VerifiedArchive, report: str, fight: int, actor: int, start: int, end: int
) -> list[dict[str, Any]]:
    prefix = f"events/{report}/fight_{fight}/player_{actor}_"
    streams: dict[str, Counter[str]] = defaultdict(Counter)
    events: dict[str, dict[str, Any]] = {}
    folders = {
        n.rsplit("/", 1)[0]
        for n in archive.names()
        if n.startswith(prefix) and any(s in n for s in ("/source_", "/target_"))
    }
    if len(folders) != 1:
        raise ValueError("both raw directions require one unambiguous actor stream folder")
    folder = folders.pop()
    for stream in ("source", "target"):
        rows, _ = _pages(archive, folder, stream, start, end)
        for event in rows:
            identity = json.dumps(event, sort_keys=True, separators=(",", ":"))
            events[identity] = event
            streams[stream][identity] += 1
    # A self heal occurs in both directions. Union by maximum multiplicity,
    # retaining identical legitimate events repeated within either stream.
    occurrences: Counter[str] = Counter()
    for counts in streams.values():
        occurrences |= counts
    return [events[key] for key, count in occurrences.items() for _ in range(count)]


def raw_actor_facts(
    archive: VerifiedArchive,
    report: str,
    fight: int,
    actor: int,
    *,
    encounter_context: bool = False,
    encounter_aura_ids: tuple[int, ...] = (),
) -> dict[str, Any]:
    bundle = archive.read_json(f"reports/{report}/bundle.json")["reportData"]["report"]
    f = next(f for f in bundle["fights"] if f["id"] == fight)
    a = next(a for a in bundle["masterData"]["actors"] if a["id"] == actor)
    events = _events(archive, report, fight, actor, f["startTime"], f["endTime"])
    if not events:
        raise ValueError("no usable raw actor events")
    outgoing = [e for e in events if e.get("sourceID") == actor]
    incoming = [e for e in events if e.get("targetID") == actor]
    for event in outgoing + incoming:
        if event["type"] not in ("damage", "heal", "absorbed"):
            continue
        amount = event.get("amount")
        if (
            not isinstance(amount, int | float)
            or isinstance(amount, bool)
            or not math.isfinite(amount)
            or amount < 0
        ):
            raise ValueError("raw amount missing or invalid; cannot establish an exact total")
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
    result = {
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
    if encounter_context:
        result["encounter_context"] = raw_encounter_facts(
            archive, report, f, bundle, aura_ids=encounter_aura_ids
        )
    return result


def raw_encounter_facts(
    archive: VerifiedArchive,
    report: str,
    fight: dict[str, Any],
    bundle: dict[str, Any],
    *,
    aura_ids: tuple[int, ...] = (),
) -> dict[str, Any]:
    """Independent scoped observations, without reconstructing ranking or assigning duties."""
    marker = archive.read_json("necropsy-snapshot.json")
    if type(marker.get("formatVersion")) is not int or marker["formatVersion"] != 2:
        raise ValueError("encounter facts require explicit live format2")
    streams = {}
    for role, direction in (("encounter", "all"), ("critical", "critical")):
        proofs = [
            p
            for p in marker["encounter_streams"]
            if (p["report"], p["fight"], p["role"]) == (report, fight["id"], role)
        ]
        if len(proofs) != 1:
            raise ValueError("encounter stream needs one exact scope proof")
        proof = proofs[0]
        expected = dict(
            site="vanilla.warcraftlogs.com",
            code=report,
            revision=bundle["revision"],
            fight=fight["id"],
            actor_id=None,
            role=role,
            direction="all",
            start_time=float(fight["startTime"]),
            end_time=float(fight["endTime"]),
            data_type="All",
            limit=10000,
            include_resources=True,
            translate=True,
            query_version=1,
            endpoint=marker["endpoint"],
        )
        if role == "critical":
            expected["filter_expression"] = 'type = "damage" AND isCritical = true'
        if (
            proof["actor_id"] is not None
            or proof["direction"] != "all"
            or json.dumps(proof["identity"], sort_keys=True) != json.dumps(expected, sort_keys=True)
        ):
            raise ValueError("encounter scope identity differs from its exact raw request")
        rows, names = _pages(
            archive,
            f"events/{report}/fight_{fight['id']}/encounter",
            direction,
            fight["startTime"],
            fight["endTime"],
        )
        if [hashlib.sha256(archive.read_bytes(n)).hexdigest() for n in names] != proof["pages"]:
            raise ValueError("encounter page proofs differ from raw bytes")
        streams[role] = rows
    all_events, critical = streams["encounter"], streams["critical"]

    def canon(event: dict[str, Any]) -> str:
        return json.dumps(event, sort_keys=True, separators=(",", ":"))

    if any(e.get("type") != "damage" for e in critical) or Counter(map(canon, critical)) - Counter(
        map(canon, all_events)
    ):
        raise ValueError("critical raw events are not an exact damage subset")
    actors = {a["id"]: a for a in bundle["masterData"]["actors"]}
    if len(actors) != len(bundle["masterData"]["actors"]):
        raise ValueError("encounter facts require unambiguous raw actor identities")
    schools = {a["gameID"]: a.get("type") for a in bundle["masterData"].get("abilities", [])}
    fire: dict[str, set[int]] = defaultdict(set)
    unknown_schools = set()
    unknown_sources = set()
    for event in critical:
        actor = actors.get(event.get("sourceID"), {})
        if actor.get("type") not in {"Player", "NPC", "Pet"} or (
            actor.get("type") == "Player" and not actor.get("subType")
        ):
            unknown_sources.add(str(event.get("sourceID")))
        if actor.get("type") != "Player" or actor.get("subType") != "Mage":
            continue
        ability = event.get("abilityGameID")
        school = schools.get(ability)
        if type(school) is str and school.isdigit():
            school = int(school)
        if type(school) is not int:
            unknown_schools.add(str(ability))
        elif school & 4:
            fire[str(event.get("targetID"))].add(event["sourceID"])
    ignite: dict[str, int | float] = defaultdict(int)
    for event in all_events:
        if event.get("type") == "damage" and event.get("abilityGameID") == 12654:
            amount = event.get("amount")
            if (
                not isinstance(amount, int | float)
                or isinstance(amount, bool)
                or not math.isfinite(amount)
                or amount < 0
            ):
                raise ValueError("raw Ignite amount is missing or invalid")
            ignite[f"{event.get('sourceID')}/{event.get('targetID')}"] += amount

    def observations(kinds: set[str], ability: int | None = None) -> list[list[Any]]:
        return [
            [
                e["timestamp"] - fight["startTime"],
                e["type"],
                e.get("sourceID"),
                e.get("targetID"),
                e.get("targetInstance"),
                e.get("abilityGameID"),
                e.get("extraAbilityGameID"),
            ]
            for e in sorted(all_events, key=lambda e: (e["timestamp"], canon(e)))
            if e.get("type") in kinds and (ability is None or e.get("abilityGameID") == ability)
        ]

    result = {
        "events": len(all_events),
        "critical_events": len(critical),
        "critical_hit_types": dict(
            sorted(Counter(str(e.get("hitType")) for e in critical).items())
        ),
        "fire_critical_mages_by_target": {k: sorted(v) for k, v in sorted(fire.items())},
        "unclassified_mage_critical_abilities": sorted(unknown_schools),
        "unclassified_critical_sources": sorted(unknown_sources),
        "ignite_by_source_target": dict(sorted(ignite.items())),
        "mind_control_transitions": observations(
            {"applydebuff", "removedebuff", "refreshdebuff"}, 20604
        ),
        "deaths": observations({"death"}),
        "interrupts": observations({"interrupt"}),
    }
    if aura_ids:
        result["aura_transitions"] = {
            str(ability): observations(
                {"applybuff", "removebuff", "refreshbuff", "applybuffstack", "removebuffstack"},
                ability,
            )
            for ability in aura_ids
        }
    return result


def raw_healing_facts(
    archive: VerifiedArchive, report: str, fight: int, actor: int, boss_game_ids: list[int]
) -> dict[str, Any]:
    """Independent recipient arithmetic over the raw maximum-multiplicity union."""
    bundle = archive.read_json(f"reports/{report}/bundle.json")["reportData"]["report"]
    f = next(f for f in bundle["fights"] if f["id"] == fight)
    rows = _events(archive, report, fight, actor, f["startTime"], f["endTime"])
    friends = {actor, *(f.get("friendlyPlayers") or [])}
    friends.update(p["id"] for p in f.get("friendlyPets") or [])
    bosses = {
        a["id"]
        for a in bundle["masterData"]["actors"]
        if a.get("type") == "NPC" and a.get("gameID") in boss_game_ids
    }
    totals: dict[str, int | float] = defaultdict(int)
    uncertain = set()
    for row in rows:
        if row.get("sourceID") != actor or row.get("type") not in {"heal", "absorbed"}:
            continue
        if type(row.get("sourceID")) is not int:
            raise ValueError("raw healing/absorption source identity is invalid")
        value = row.get("amount")
        if (
            not isinstance(value, int | float)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("raw healing/absorption amount is missing or invalid")
        kind = "healing" if row["type"] == "heal" else "absorption"
        target = row.get("targetID")
        membership = (
            type(target) is int and target in friends,
            type(target) is int and target in bosses,
        )
        group = {(True, False): "friendly", (False, True): "boss"}.get(membership, "unclassified")
        totals[f"{group}_{kind}"] += value
        totals[f"raw_{kind}"] += value
        if group == "unclassified":
            uncertain.add(kind)
    result: dict[str, Any] = {}
    for kind in ("healing", "absorption"):
        for group in ("friendly", "boss", "unclassified", "raw"):
            key = f"{group}_{kind}"
            result[key] = (
                None if kind in uncertain and group in {"friendly", "boss"} else totals[key]
            )
    result["friendly_healing_and_absorption"] = (
        None if uncertain else totals["friendly_healing"] + totals["friendly_absorption"]
    )
    result["duration_ms"] = f["endTime"] - f["startTime"]
    return result


def check_register(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not data.get("cases"):
        raise ValueError("a fact register needs version 1 and nonempty reviewed cases")
    kind = data.get("kind", "actor")
    if kind not in {"actor", "healing-recipients"}:
        raise ValueError("unsupported independent fact register kind")
    problems = []
    ids = [case["id"] for case in data["cases"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate independent fact case IDs")
    for case in data["cases"]:
        if type(case.get("encounter_context", False)) is not bool:
            raise ValueError("encounter context selection must be boolean")
        aura_ids = case.get("encounter_aura_ids", [])
        if (
            not isinstance(aura_ids, list)
            or any(type(a) is not int or a < 1 for a in aura_ids)
            or len(set(aura_ids)) != len(aura_ids)
            or (aura_ids and not case.get("encounter_context"))
        ):
            raise ValueError("encounter aura selection needs unique positive IDs and context")
        if not case.get("review_basis"):
            problems.append(f"{case['id']}: missing independent review basis")
        archive_path = path.parent / case["archive"]
        entries = load_entries_manifest(path.parent / case["entries"])
        with VerifiedArchive(
            archive_path, expected_sha256=case["sha256"], entries=entries
        ) as archive:
            if kind == "healing-recipients":
                boss_ids = case.get("boss_game_ids")
                if (
                    not isinstance(boss_ids, list)
                    or not boss_ids
                    or any(type(i) is not int or i < 1 for i in boss_ids)
                    or len(set(boss_ids)) != len(boss_ids)
                ):
                    raise ValueError("recipient facts need explicit unique boss NPC IDs")
                actual = raw_healing_facts(
                    archive, case["report"], case["fight"], case["actor"], boss_ids
                )
            else:
                actual = raw_actor_facts(
                    archive,
                    case["report"],
                    case["fight"],
                    case["actor"],
                    encounter_context=case.get("encounter_context", False),
                    encounter_aura_ids=tuple(aura_ids),
                )
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
