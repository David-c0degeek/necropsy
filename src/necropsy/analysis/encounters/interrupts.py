"""Raid-roster interruption observations, separate from personal utility."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight
from necropsy.analysis.encounters import duty
from necropsy.analysis.evidence import (
    EvidenceRef,
    ScopedCoverageRef,
    complete_or_unknown,
    observed,
    unknown,
)
from necropsy.normalize.coverage import has_complete_encounter_event_set

RULE = "raid-shaman-dark-mending-interrupts-v1"
CLASSES = frozenset(
    {"Warrior", "Paladin", "Hunter", "Rogue", "Priest", "Shaman", "Mage", "Warlock", "Druid"}
)
LIMITATION = (
    "Raid-member observations, not credited to the selected player or ranking category. "
    "These effects establish no assignment, available opportunities, missed interrupts, "
    "reaction time, saved healing or quality grade. Target instances are retained where recorded."
)


def _decoded(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def contexts(
    con: duckdb.DuckDBPyConnection, participants: Iterable[ParticipantFight]
) -> list[dict[str, Any]]:
    """One context per report/fight, including subjects excluded from comparisons."""
    if con.execute("SELECT subject_class_id FROM snapshot_meta").fetchall() != [(9,)]:
        return []
    groups: dict[tuple[str, int], list[ParticipantFight]] = defaultdict(list)
    for pf in participants:
        if pf.encounter_id == 50669 and duty.applies(con, pf):
            groups[pf.report_code, pf.fight_id].append(pf)
    return [_context(con, group) for _, group in sorted(groups.items())]


def _context(
    con: duckdb.DuckDBPyConnection, participants: list[ParticipantFight]
) -> dict[str, Any]:
    pf = participants[0]
    cov = ScopedCoverageRef(
        pf.report_code,
        pf.fight_id,
        None,
        "all",
        has_complete_encounter_event_set(con, pf.report_code, pf.fight_id),
        "encounter",
    )
    refs = (
        EvidenceRef(
            pf.report_code,
            pf.fight_id,
            None,
            "actors",
            detail="unique Player class bindings and NPC11662 identity",
        ),
        EvidenceRef(
            pf.report_code,
            pf.fight_id,
            None,
            "fights",
            detail="selected friendly raid roster and NPC11662 instance roster",
        ),
        EvidenceRef(pf.report_code, pf.fight_id, None, "reports", detail="report revision"),
    )
    result: dict[str, Any] = {
        "rule": RULE,
        "report_code": pf.report_code,
        "fight_id": pf.fight_id,
        "encounter_id": pf.encounter_id,
        "scope": "friendly-raid-roster",
        "limitation": LIMITATION,
        "observations": [],
    }

    def withheld(reason: str) -> dict[str, Any]:
        return result | {"interrupts": unknown(reason, *refs, coverage=[cov])}

    fights = con.execute(
        "SELECT encounter_id,start_time,end_time,friendly_players,enemy_npcs FROM fights "
        "WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchall()
    revisions = con.execute(
        "SELECT revision FROM reports WHERE report_code=?", [pf.report_code]
    ).fetchall()
    if (
        len(fights) != 1
        or len(revisions) != 1
        or type(revisions[0][0]) is not int
        or revisions[0][0] < 0
        or any((p.encounter_id, p.start_time, p.end_time) != fights[0][:3] for p in participants)
        or any(type(v) is not int for v in fights[0][:3])
        or not 0 <= pf.start_time < pf.end_time
    ):
        return withheld("raid interruption fight/revision context is conflicting or invalid")
    result["revision"] = revisions[0][0]
    actors = con.execute(
        "SELECT actor_id,type,sub_type,game_id,name FROM actors WHERE report_code=?",
        [pf.report_code],
    ).fetchall()
    catalog = {a[0]: a for a in actors}
    if len(catalog) != len(actors) or any(type(a[0]) is not int for a in actors):
        return withheld("raid interruption catalog identities are ambiguous")
    players, enemies = map(_decoded, fights[0][3:])
    if (
        not isinstance(players, list)
        or not players
        or any(type(p) is not int or p < 1 for p in players)
        or len(set(players)) != len(players)
        or any(
            catalog.get(p, (None, None, None))[1:3] not in {("Player", c) for c in CLASSES}
            for p in players
        )
        or any(
            p.actor_id not in players or catalog[p.actor_id][2] != "Shaman" for p in participants
        )
        or not isinstance(enemies, list)
        or not enemies
    ):
        return withheld("raid interruption roster/class eligibility is unresolved")
    targets: dict[int, int] = {}
    seen: set[int] = set()
    for enemy in enemies:
        if (
            not isinstance(enemy, dict)
            or type(enemy.get("id")) is not int
            or enemy["id"] < 1
            or enemy["id"] in seen
            or enemy["id"] in players
            or type(enemy.get("gameID")) is not int
            or enemy["gameID"] < 1
            or catalog.get(enemy["id"], (None, None))[1] != "NPC"
            or catalog[enemy["id"]][3] != enemy["gameID"]
            or type(enemy.get("instanceCount")) is not int
            or enemy["instanceCount"] < 1
        ):
            return withheld("raid interruption target NPC/instance binding is unresolved")
        seen.add(enemy["id"])
        if enemy["gameID"] == 11662:
            targets[enemy["id"]] = enemy["instanceCount"]
    if not targets:
        return withheld("raid interruption eligible Flamewaker Priest roster is absent")
    rows = con.execute(
        "SELECT timestamp,type,source_id,target_id,ability_game_id,extra_ability_game_id,"
        "target_instance,raw,event_uid,copy_index FROM events WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchall()
    unresolved = False
    unresolved_occurrences = []
    occurrences = []
    for ts, kind, source, target, spell, stopped, instance, payload, uid, copy in rows:
        raw = _decoded(payload)
        # No source/type/time SQL filter: unresolved rows cannot disappear into zero.
        if not isinstance(raw, dict):
            unresolved = True
            unresolved_occurrences.append((uid, copy))
            continue
        if isinstance(kind, str) and kind and raw.get("type") == kind and kind != "interrupt":
            continue
        valid = (
            kind == raw.get("type") == "interrupt"
            and all(
                type(raw.get(key)) is int and raw[key] == value and value > 0
                for key, value in (
                    ("sourceID", source),
                    ("targetID", target),
                    ("abilityGameID", spell),
                    ("extraAbilityGameID", stopped),
                )
            )
            and type(raw.get("timestamp")) is int
            and raw["timestamp"] == ts
            and pf.start_time <= ts <= pf.end_time
            and ("fight" not in raw or (type(raw["fight"]) is int and raw["fight"] == pf.fight_id))
            and (
                (raw.get("targetInstance") is None and instance is None)
                or (
                    type(raw.get("targetInstance")) is int
                    and raw["targetInstance"] == instance
                    and instance > 0
                )
            )
        )
        if not valid:
            unresolved = True
            unresolved_occurrences.append((uid, copy))
            continue
        caster, recipient = catalog.get(source), catalog.get(target)
        if (
            caster is None
            or recipient is None
            or caster[1] not in {"Player", "NPC", "Pet"}
            or (caster[1] == "Player" and caster[2] not in CLASSES)
            or recipient[1] not in {"Player", "NPC", "Pet"}
            or (recipient[1] == "NPC" and (type(recipient[3]) is not int or recipient[3] < 1))
            or (target in targets and instance is not None and instance > targets[target])
        ):
            unresolved = True
            unresolved_occurrences.append((uid, copy))
            continue
        if (
            caster[1:3] == ("Player", "Shaman")
            and source in players
            and stopped == 19775
            and recipient[1] == "NPC"
            and recipient[3] == 11662
            and target not in targets
        ):
            unresolved = True
            unresolved_occurrences.append((uid, copy))
            continue
        if (
            caster[1:3] != ("Player", "Shaman")
            or source not in players
            or target not in targets
            or stopped != 19775
        ):
            continue
        ref = EvidenceRef.events(
            pf.report_code,
            pf.fight_id,
            source,
            [(uid, copy)],
            detail="raid-roster Shaman interrupted Dark Mending",
        )
        occurrences.append((uid, copy))
        result["observations"].append(
            observed(
                {
                    "source_actor_id": source,
                    "source_name": caster[4],
                    "source_class": caster[2],
                    "target_actor_id": target,
                    "target_game_id": 11662,
                    "target_instance": instance,
                    "elapsed_ms": ts - pf.start_time,
                    "interrupt_ability_id": spell,
                    "stopped_ability_id": stopped,
                },
                ref,
                *refs,
            )
        )
    result["observations"].sort(key=lambda o: (o.value["elapsed_ms"], o.value["source_actor_id"]))
    event_ref = EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        None,
        occurrences,
        detail="qualified raid-roster interruption effects",
    )
    result["interrupts"] = (
        unknown(
            "possible interruption rows have unresolved identity, type, time or metadata",
            EvidenceRef.events(
                pf.report_code,
                pf.fight_id,
                None,
                unresolved_occurrences,
                detail="unresolved possible raid interruption occurrences",
            ),
            event_ref,
            *refs,
            coverage=[cov],
        )
        if unresolved
        else complete_or_unknown(
            len(occurrences), [cov], event_ref, *refs, rule_id=RULE, note=LIMITATION
        )
    )
    return result
