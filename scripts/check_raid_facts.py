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
    archive: VerifiedArchive,
    report: str,
    fight: int,
    actor: int,
    start: int,
    end: int,
    *,
    role: str = "player",
) -> list[dict[str, Any]]:
    if role not in {"player", "pet"}:
        raise ValueError("raw actor stream role must be player or pet")
    prefix = f"events/{report}/fight_{fight}/{role}_{actor}_"
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


def raw_summon_facts(
    archive: VerifiedArchive,
    report: str,
    fight: int,
    ability_ids: list[int],
    caster_game_ids: list[int],
    target_game_ids: list[int],
) -> dict[str, Any]:
    """Raw summon and damage-marker chronology; never reconstruct a living phase."""
    marker = archive.read_json("necropsy-snapshot.json")
    bundle = archive.read_json(f"reports/{report}/bundle.json")["reportData"]["report"]
    selected = next(f for f in bundle["fights"] if f["id"] == fight)
    zone = marker.get("zone")
    if not isinstance(zone, dict):
        raise ValueError("raw summon eligibility needs exact raid and partition metadata")
    eligibility: dict[str, Any] = {
        "encounter_id": selected.get("encounterID"),
        "revision": bundle.get("revision"),
        "zone_id": zone.get("id"),
        "partition": zone.get("partition"),
    }
    if any(type(value) is not int or value < 0 for value in eligibility.values()) or any(
        eligibility[key] < 1 for key in ("encounter_id", "zone_id", "partition")
    ):
        raise ValueError("raw summon eligibility identities must be exact integers")
    raw_encounter_facts(archive, report, selected, bundle)
    wanted_npcs = set(caster_game_ids) | set(target_game_ids)
    for entity in bundle["masterData"]["actors"]:
        if entity.get("gameID") in wanted_npcs and any(
            type(entity.get(key)) is not int or entity[key] < 1 for key in ("id", "gameID")
        ):
            raise ValueError("raw summon NPC catalog identities must be exact positive integers")
    for entity in selected.get("enemyNPCs", []):
        if entity.get("gameID") in wanted_npcs and any(
            type(entity.get(key)) is not int or entity[key] < 1
            for key in ("id", "gameID", "instanceCount")
        ):
            raise ValueError("raw summon NPC roster identities must be exact positive integers")
    rows, _ = _pages(
        archive,
        f"events/{report}/fight_{fight}/encounter",
        "all",
        selected["startTime"],
        selected["endTime"],
    )
    actors = {a["id"]: a for a in bundle["masterData"]["actors"]}
    targets = {
        actor
        for actor, data in actors.items()
        if data.get("type") == "NPC" and data.get("gameID") in target_game_ids
    }

    def ordered(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            events,
            key=lambda e: (e["timestamp"], json.dumps(e, sort_keys=True, separators=(",", ":"))),
        )

    summons = [e for e in rows if e["type"] == "summon" and e.get("abilityGameID") in ability_ids]
    damage = [e for e in rows if e["type"] == "damage" and e.get("targetID") in targets]
    lifecycles = [
        e for e in rows if e["type"] in {"death", "resurrect"} and e.get("targetID") in targets
    ]
    for event in [*summons, *damage, *lifecycles]:
        if (
            type(event.get("timestamp")) is not int
            or not selected["startTime"] <= event["timestamp"] <= selected["endTime"]
        ):
            raise ValueError("raw summon chronology timestamp is invalid")
        for key in ("targetID", "targetInstance"):
            if key in event and (type(event[key]) is not int or event[key] < 1):
                raise ValueError("raw summon recipient or instance identity is invalid")
        if event["type"] in {"summon", "damage"}:
            for key in ("sourceID", "sourceInstance", "abilityGameID"):
                if key in event and (type(event[key]) is not int or event[key] < 1):
                    raise ValueError("raw summon caster or ability identity is invalid")
        if event["type"] == "damage":
            for key in ("amount", "overkill"):
                if key not in event and key == "overkill":
                    continue
                value = event.get(key)
                if (
                    not isinstance(value, int | float)
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                    or (key == "amount" and value < 0)
                ):
                    raise ValueError("raw summon damage or overkill amount is invalid")
        if event["type"] == "death" and "feign" in event and type(event["feign"]) is not bool:
            raise ValueError("raw summon death flag is invalid")

    grouped: dict[tuple[int, int | None], list[dict[str, Any]]] = defaultdict(list)
    for event in damage:
        grouped[event["targetID"], event.get("targetInstance")].append(event)
    bounds = []
    for (actor, instance), hits in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1] or 0)
    ):
        markers = ordered([e for e in hits if e.get("overkill", 0) > 0])
        first = markers[0]["timestamp"] if markers else None
        bounds.append(
            {
                "actor": actor,
                "instance": instance,
                "first_last_damage_ms": [
                    min(e["timestamp"] for e in hits) - selected["startTime"],
                    max(e["timestamp"] for e in hits) - selected["startTime"],
                ],
                "positive_overkill": [
                    [
                        e["timestamp"] - selected["startTime"],
                        e.get("sourceID"),
                        e.get("abilityGameID"),
                        e["amount"],
                        e["overkill"],
                    ]
                    for e in markers
                ],
                "later_positive_damage_ms": sorted(
                    e["timestamp"] - selected["startTime"]
                    for e in hits
                    if first is not None and e["timestamp"] > first and e["amount"] > 0
                ),
            }
        )
    return {
        **eligibility,
        "duration_ms": selected["endTime"] - selected["startTime"],
        "caster_catalog": [a for a in actors.values() if a.get("gameID") in caster_game_ids],
        "target_catalog": [a for a in actors.values() if a.get("gameID") in target_game_ids],
        "caster_roster": [
            e for e in selected.get("enemyNPCs", []) if e.get("gameID") in caster_game_ids
        ],
        "target_roster": [
            e for e in selected.get("enemyNPCs", []) if e.get("gameID") in target_game_ids
        ],
        "summons": [
            [
                e["timestamp"] - selected["startTime"],
                e.get("sourceID"),
                e.get("sourceInstance"),
                e.get("targetID"),
                e.get("targetInstance"),
                e.get("abilityGameID"),
            ]
            for e in ordered(summons)
        ],
        "damage_by_instance": bounds,
        "lifecycles": [
            {
                "ms": e["timestamp"] - selected["startTime"],
                "kind": e["type"],
                "target": e.get("targetID"),
                "instance": e.get("targetInstance"),
                **({"feign": e["feign"]} if "feign" in e else {}),
            }
            for e in ordered(lifecycles)
        ],
    }


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


def raw_control_facts(
    archive: VerifiedArchive,
    report: str,
    fight: int,
    ability_ids: list[int],
    target_game_ids: list[int],
    *,
    aura_kind: str = "debuff",
) -> dict[str, Any]:
    """Raw scoped aura transitions and identity bindings, never analyzer windows."""
    if type(aura_kind) is not str or aura_kind not in {"buff", "debuff"}:
        raise ValueError("raw aura facts require an explicit buff/debuff kind")
    bundle = archive.read_json(f"reports/{report}/bundle.json")["reportData"]["report"]
    selected = next(f for f in bundle["fights"] if f["id"] == fight)
    raw_encounter_facts(archive, report, selected, bundle)  # exact raw scope/page proofs
    rows, _ = _pages(
        archive,
        f"events/{report}/fight_{fight}/encounter",
        "all",
        selected["startTime"],
        selected["endTime"],
    )
    actors = {a["id"]: a for a in bundle["masterData"]["actors"]}

    def identity(actor: int | None) -> dict[str, Any]:
        if actor is not None and (type(actor) is not int or actor < 1):
            raise ValueError("raw control actor identity is invalid")
        return {
            k: v
            for k, v in actors.get(actor, {}).items()
            if k in {"id", "type", "subType", "name", "gameID"}
        }

    ordered = sorted(
        rows, key=lambda e: (e["timestamp"], json.dumps(e, sort_keys=True, separators=(",", ":")))
    )
    observations = [
        {
            "ms": e["timestamp"] - selected["startTime"],
            "kind": e["type"],
            "spell": e.get("abilityGameID"),
            "caster": identity(e.get("sourceID")),
            "target": identity(e.get("targetID")),
            "instance": e.get("targetInstance"),
        }
        for e in ordered
        if e.get("abilityGameID") in ability_ids
        and e["type"]
        in {
            f"apply{aura_kind}",
            f"remove{aura_kind}",
            f"refresh{aura_kind}",
            f"apply{aura_kind}stack",
            f"remove{aura_kind}stack",
        }
    ]
    native = {
        a["id"]
        for a in actors.values()
        if a.get("type") == "NPC" and a.get("gameID") in target_game_ids
    }
    return {
        "duration_ms": selected["endTime"] - selected["startTime"],
        "observations": observations,
        "lifecycles": [
            [
                e["timestamp"] - selected["startTime"],
                e["type"],
                e.get("targetID"),
                e.get("targetInstance"),
            ]
            for e in ordered
            if e["type"] in {"death", "resurrect"} and e.get("targetID") in native
        ],
    }


def raw_actor_effect_facts(
    archive: VerifiedArchive, report: str, fight: int, actor: int, ability_ids: list[int]
) -> dict[str, Any]:
    """Project raw actor-recipient transitions; never compute expected aura windows."""
    bundle = archive.read_json(f"reports/{report}/bundle.json")["reportData"]["report"]
    selected = next(f for f in bundle["fights"] if f["id"] == fight)
    identities = [a for a in bundle["masterData"]["actors"] if a["id"] == actor]
    if len(identities) != 1 or identities[0].get("type") != "Player":
        raise ValueError("actor effect facts need one explicit Player identity")
    rows = _events(archive, report, fight, actor, selected["startTime"], selected["endTime"])
    ordered = sorted(
        rows, key=lambda e: (e["timestamp"], json.dumps(e, sort_keys=True, separators=(",", ":")))
    )
    transitions = []
    lifecycles = []
    death_feign_flags = []
    for row in ordered:
        kind = row["type"]
        aura = (
            kind
            in {
                "applydebuff",
                "removedebuff",
                "refreshdebuff",
                "applydebuffstack",
                "removedebuffstack",
            }
            and row.get("abilityGameID") in ability_ids
        )
        lifecycle = kind in {"death", "resurrect"}
        if not aura and not lifecycle:
            continue
        target = row.get("targetID")
        if type(target) is not int or target < 1:
            raise ValueError("raw actor effect recipient is unresolved")
        if aura and type(row.get("abilityGameID")) is not int:
            raise ValueError("raw actor effect spell is unresolved")
        if target != actor:
            continue
        ms = row["timestamp"] - selected["startTime"]
        if lifecycle:
            lifecycles.append([ms, kind])
            if kind == "death" and "feign" in row:
                if type(row["feign"]) is not bool:
                    raise ValueError("raw death feign flag is unresolved")
                death_feign_flags.append([ms, row["feign"]])
        else:
            transitions.append([ms, kind, row["abilityGameID"]])
    result: dict[str, Any] = {
        "duration_ms": selected["endTime"] - selected["startTime"],
        "actor_class": identities[0].get("subType"),
        "transitions": transitions,
        "lifecycles": lifecycles,
    }
    if death_feign_flags:
        result["death_feign_flags"] = death_feign_flags
    return result


def raw_owned_pet_facts(
    archive: VerifiedArchive, report: str, fight: int, owner: int
) -> dict[str, Any]:
    """Project raw owner/listing/catalog bindings and exact pet event arithmetic."""
    bundle = archive.read_json(f"reports/{report}/bundle.json")["reportData"]["report"]
    selected = next(f for f in bundle["fights"] if f["id"] == fight)
    actors = {a["id"]: a for a in bundle["masterData"]["actors"]}
    if len(actors) != len(bundle["masterData"]["actors"]):
        raise ValueError("raw pet catalog identities are ambiguous")
    identity = actors.get(owner, {})
    if type(identity.get("id")) is not int or identity.get("type") != "Player":
        raise ValueError("raw pet owner identity is unresolved")
    prefix = f"events/{report}/fight_{fight}/player_{owner}_"
    listings = [
        name
        for name in archive.names()
        if name.startswith(prefix) and name.endswith(("/pets.json", "/confirmed_pets.json"))
    ]
    if len(listings) != 1:
        raise ValueError("owned pet facts need one unambiguous raw listing")
    listing = listings[0]
    pets = archive.read_json(listing)
    if (
        not isinstance(pets, list)
        or any(not isinstance(p, dict) or type(p.get("id")) is not int or p["id"] < 1 for p in pets)
        or len({p["id"] for p in pets}) != len(pets)
    ):
        raise ValueError("raw pet listing identities are invalid")
    result = []
    for pet in pets:
        actor = pet["id"]
        bindings = [p for p in selected.get("friendlyPets") or [] if p["id"] == actor]
        if len(bindings) != 1:
            raise ValueError("raw pet needs one exact friendly fight binding")
        catalog = actors.get(actor, {})
        required_owners = [pet.get("petOwner"), bindings[0].get("petOwner")]
        master_owner = catalog.get("petOwner")
        if (
            actor == owner
            or type(catalog.get("id")) is not int
            or catalog.get("type") != "Pet"
            or any(type(value) is not int or value != owner for value in required_owners)
            or (
                master_owner is not None
                and (type(master_owner) is not int or master_owner != owner)
            )
        ):
            raise ValueError("raw owned pet bindings are unresolved or disagree")
        rows = _events(
            archive,
            report,
            fight,
            actor,
            selected["startTime"],
            selected["endTime"],
            role="pet",
        )
        outgoing = [e for e in rows if e.get("sourceID") == actor]
        incoming = [e for e in rows if e.get("targetID") == actor]
        for event in outgoing + incoming:
            if event["type"] not in {"damage", "heal", "absorbed"}:
                continue
            values = [event.get("amount")]
            if event["type"] == "damage":
                values.append(event.get("absorbed", 0))
            if any(
                not isinstance(value, int | float)
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value < 0
                for value in values
            ):
                raise ValueError("raw pet amount is missing or invalid")
        damage = [e for e in outgoing if e["type"] == "damage"]
        targets: Counter[str] = Counter()
        casts: dict[str, list[int]] = defaultdict(list)
        for event in damage:
            targets[str(event.get("targetID"))] += event["amount"]
        for event in outgoing:
            if event["type"] == "cast":
                casts[str(event.get("abilityGameID"))].append(
                    event["timestamp"] - selected["startTime"]
                )
        result.append(
            {
                "actor": actor,
                "catalog": {
                    k: v
                    for k, v in actors.get(actor, {}).items()
                    if k in {"id", "name", "type", "subType", "gameID", "petOwner"}
                },
                "listing_binding": {k: pet.get(k) for k in ("id", "gameID", "petOwner")},
                "fight_binding": {
                    k: bindings[0].get(k) for k in ("id", "gameID", "instanceCount", "petOwner")
                },
                "totals": {
                    "damage": sum(e["amount"] for e in damage),
                    "damage_absorbed": sum(e.get("absorbed", 0) for e in damage),
                    "effective_healing": sum(e["amount"] for e in outgoing if e["type"] == "heal"),
                    "absorbed_amount": sum(
                        e["amount"] for e in outgoing if e["type"] == "absorbed"
                    ),
                    "incoming_damage": sum(e["amount"] for e in incoming if e["type"] == "damage"),
                },
                "damage_by_actor": dict(sorted(targets.items())),
                "target_game_ids": {
                    str(a["id"]): a.get("gameID")
                    for a in bundle["masterData"]["actors"]
                    if str(a["id"]) in targets
                },
                "casts_ms": {k: sorted(v) for k, v in sorted(casts.items())},
                "deaths_ms": sorted(
                    e["timestamp"] - selected["startTime"] for e in incoming if e["type"] == "death"
                ),
                "resurrections_ms": sorted(
                    e["timestamp"] - selected["startTime"]
                    for e in incoming
                    if e["type"] == "resurrect"
                ),
                "damage_bounds_ms": None
                if not damage
                else [
                    min(e["timestamp"] for e in damage) - selected["startTime"],
                    max(e["timestamp"] for e in damage) - selected["startTime"],
                ],
            }
        )
    return {
        "duration_ms": selected["endTime"] - selected["startTime"],
        "owner_class": actors.get(owner, {}).get("subType"),
        "owner_identity": {
            k: v
            for k, v in actors.get(owner, {}).items()
            if k in {"id", "type", "subType", "name", "gameID"}
        },
        "listing_member": listing,
        "listing_complete": listing.endswith("/pets.json"),
        "pets": result,
        "unattributed_friendly_pets": [
            {
                "actor": p["id"],
                "game_id": p.get("gameID"),
                "fight_owner": p.get("petOwner"),
                "master_owner": actors.get(p["id"], {}).get("petOwner"),
            }
            for p in selected.get("friendlyPets") or []
            if type(p.get("petOwner")) is not int or p["petOwner"] < 1
        ],
    }


def check_register(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not data.get("cases"):
        raise ValueError("a fact register needs version 1 and nonempty reviewed cases")
    kind = data.get("kind", "actor")
    if kind not in {
        "actor",
        "healing-recipients",
        "npc-controls",
        "npc-auras",
        "actor-effects",
        "owned-pets",
        "npc-summons",
    }:
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
            if kind == "npc-summons":
                selectors = [
                    case.get(key) for key in ("ability_ids", "caster_game_ids", "target_game_ids")
                ]
                if any(
                    not isinstance(values, list)
                    or not values
                    or any(type(value) is not int or value < 1 for value in values)
                    or len(set(values)) != len(values)
                    for values in selectors
                ):
                    raise ValueError(
                        "raw summon facts need unique positive ability/caster/target IDs"
                    )
                actual = raw_summon_facts(
                    archive,
                    case["report"],
                    case["fight"],
                    case["ability_ids"],
                    case["caster_game_ids"],
                    case["target_game_ids"],
                )
            elif kind == "owned-pets":
                if type(case.get("actor")) is not int or case["actor"] < 1:
                    raise ValueError("owned pet facts require a positive owner actor")
                actual = raw_owned_pet_facts(archive, case["report"], case["fight"], case["actor"])
            elif kind == "actor-effects":
                abilities = case.get("ability_ids")
                if (
                    not isinstance(abilities, list)
                    or not abilities
                    or any(type(i) is not int or i < 1 for i in abilities)
                    or len(set(abilities)) != len(abilities)
                    or type(case.get("actor")) is not int
                    or case["actor"] < 1
                ):
                    raise ValueError(
                        "actor effect facts need a positive actor and unique spell IDs"
                    )
                actual = raw_actor_effect_facts(
                    archive, case["report"], case["fight"], case["actor"], abilities
                )
            elif kind in {"npc-controls", "npc-auras"}:
                abilities, targets = case.get("ability_ids"), case.get("target_game_ids")
                if any(
                    not isinstance(ids, list)
                    or not ids
                    or any(type(i) is not int or i < 1 for i in ids)
                    or len(set(ids)) != len(ids)
                    for ids in (abilities, targets)
                ):
                    raise ValueError("control facts need explicit unique spell and NPC IDs")
                actual = raw_control_facts(
                    archive,
                    case["report"],
                    case["fight"],
                    abilities,
                    targets,
                    aura_kind=case.get("aura_kind", "") if kind == "npc-auras" else "debuff",
                )
                if kind == "npc-auras":
                    bundle = archive.read_json(f"reports/{case['report']}/bundle.json")[
                        "reportData"
                    ]["report"]
                    fight = next(f for f in bundle["fights"] if f["id"] == case["fight"])
                    actual["target_roster"] = [
                        {key: row.get(key) for key in ("id", "gameID", "instanceCount")}
                        for row in fight.get("enemyNPCs") or []
                        if row.get("gameID") in targets
                    ]
            elif kind == "healing-recipients":
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
