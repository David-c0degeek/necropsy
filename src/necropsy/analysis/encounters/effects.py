"""Observed actor debuff exposure; never a guide-timed boss phase or opportunity."""

from __future__ import annotations

import json
from dataclasses import dataclass

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.encounters import duty
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceRef,
    complete_or_unknown,
    observed,
    unknown,
)
from necropsy.analysis.generic import combat, metrics
from necropsy.raids import raid_for_encounter
from necropsy.rules import load_rules
from necropsy.snapshot.model import Direction

LIMITATION = (
    "Actor debuff exposure, not a boss phase or lost damage opportunity. State before the "
    "first recorded transition remains unknown. These observations do not establish "
    "assignment, avoidability, dispel opportunity or fault."
)
AURA_EVENTS = frozenset(
    {
        "applydebuff",
        "removedebuff",
        "refreshdebuff",
        "applydebuffstack",
        "removedebuffstack",
    }
)


@dataclass(frozen=True, slots=True)
class EffectExposure:
    rule: str
    label: str
    source: str
    retrieved: str
    ability_ids: tuple[int, ...]
    windows: Evidenced[tuple[tuple[float, float, bool | None], ...]]
    known_affected_s: Evidenced[float]
    unknown_state_s: Evidenced[float]
    transitions: Evidenced[tuple[tuple[float, str, int], ...]]
    limitation: str = LIMITATION


@dataclass(frozen=True, slots=True)
class MechanicRemoval:
    rule: str
    label: str
    source: str
    retrieved: str
    removed_ability_ids: tuple[int, ...]
    removals: Evidenced[int]
    observations: Evidenced[tuple[tuple[float, int | None, int | None, int], ...]]
    is_buff: bool = False
    target_game_ids: tuple[int, ...] = ()
    removing_ability_ids: tuple[int, ...] = ()
    applicable_classes: tuple[int, ...] = ()
    limitation: str = (
        "Recorded successful mechanic removals by this actor, separate from cast counts. "
        "They do not establish assignment, available dispel opportunities, reaction time "
        "or lost throughput. Missing opportunity evidence cannot support a utility score."
    )


def mechanic_removals(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> tuple[MechanicRemoval, ...]:
    if not duty.applies(con, pf):
        return ()
    raid = raid_for_encounter(pf.encounter_id)
    policies = (
        load_rules("classic_era", f"zones/{raid.slug}_guidance")
        .get("removals", {})
        .get(pf.encounter_id, ())
    )
    if not policies:
        return ()
    meta = con.execute("SELECT subject_class_id FROM snapshot_meta").fetchone()
    class_id = meta[0] if meta else None
    policies = [
        policy for policy in policies if "classes" not in policy or class_id in policy["classes"]
    ]
    if not policies:
        return ()
    events = combat.event_rows(con, pf)
    result = []
    actors: dict[int, set[tuple[str | None, int | None]]] = {}
    for actor, kind, game_id in con.execute(
        "SELECT actor_id, type, game_id FROM actors WHERE report_code=?", [pf.report_code]
    ).fetchall():
        actors.setdefault(actor, set()).add((kind, game_id))
    for policy in policies:
        ids = tuple(int(ability) for ability in policy["removed_ability_ids"])
        wanted_buff = policy.get("is_buff", False)
        if type(wanted_buff) is not bool:
            raise ValueError("removal policy needs a boolean buff/debuff selector")
        targets = tuple(int(target) for target in policy.get("target_game_ids", ()))
        abilities = tuple(int(ability) for ability in policy.get("removing_ability_ids", ()))
        rows, unresolved = [], []
        for event in events:
            if event.kind != "dispel" or event.source_id != pf.actor_id:
                continue
            extra = event.raw.get("extraAbilityGameID")
            buff = event.raw.get("isBuff")
            matches: list[bool | None] = [
                extra in ids if type(extra) is int else None,
                buff == wanted_buff if type(buff) is bool else None,
            ]
            if targets:
                identities = actors.get(event.target_id) if event.target_id is not None else None
                target = next(iter(identities)) if identities and len(identities) == 1 else None
                if target is None or target[0] is None:
                    matches.append(None)
                elif target[0] != "NPC":
                    matches.append(False)
                else:
                    matches.append(target[1] in targets if target[1] is not None else None)
            if abilities:
                matches.append(
                    event.ability_id in abilities if event.ability_id is not None else None
                )
            if False in matches:
                continue
            if None in matches:
                unresolved.append(event)
            else:
                rows.append(event)
        ref = combat.event_ref(pf, rows, f"successful mechanic removals {ids}")
        refs = (
            ref,
            *(
                (
                    EvidenceRef(
                        pf.report_code,
                        pf.fight_id,
                        None,
                        "actors",
                        detail=f"removal recipients with NPC game IDs {targets}",
                    ),
                )
                if targets
                else ()
            ),
        )
        ambiguous_ref = combat.event_ref(pf, unresolved, "unresolved dispel metadata")
        count = (
            unknown(
                "source dispel events omit required mechanic/target/ability metadata",
                *refs,
                ambiguous_ref,
            )
            if unresolved
            else complete_or_unknown(
                len(rows),
                [coverage(con, pf, pf.actor_id, Direction.SOURCE)],
                *refs,
                rule_id=policy["rule"],
                note="Source-owned dispel effects, not cast or opportunity count.",
            )
        )
        values = tuple(
            (event.t_s, event.target_id, event.ability_id, int(event.raw["extraAbilityGameID"]))
            for event in rows
        )
        observations = (
            observed(values, *refs)
            if rows
            else unknown("dispel metadata cannot establish absence", *refs, ambiguous_ref)
            if unresolved
            else complete_or_unknown(
                (),
                [coverage(con, pf, pf.actor_id, Direction.SOURCE)],
                *refs,
                note="No matching removal effects in the complete actor-source stream.",
            )
        )
        result.append(
            MechanicRemoval(
                policy["rule"],
                policy["label"],
                policy["source"],
                policy["retrieved"],
                ids,
                count,
                observations,
                is_buff=wanted_buff,
                target_game_ids=targets,
                removing_ability_ids=abilities,
                applicable_classes=tuple(policy.get("classes", ())),
            )
        )
    return tuple(result)


def _effect_identity_matches(raw: object, target: int | None, ability: int | None) -> bool:
    if not isinstance(raw, dict) or type(target) is not int or target < 1:
        return False
    return all(
        key not in raw or (type(raw[key]) is int and raw[key] > 0 and raw[key] == normalized)
        for key, normalized in (("targetID", target), ("abilityGameID", ability))
    )


def _unresolved_effect_identity(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, ids: tuple[int, ...]
) -> EvidenceRef | None:
    rows = con.execute(
        """SELECT type,target_id,ability_game_id,raw,event_uid,copy_index FROM events
           WHERE report_code=? AND fight_id=? AND timestamp BETWEEN ? AND ?
             AND ((ability_game_id IN (SELECT unnest(?::BIGINT[]))
                   AND type IN (SELECT unnest(?::VARCHAR[])))
                  OR type IN ('death','resurrect'))""",
        [pf.report_code, pf.fight_id, pf.start_time, pf.end_time, ids, sorted(AURA_EVENTS)],
    ).fetchall()
    unresolved = []
    for kind, target, ability, raw, uid, copy in rows:
        raw = json.loads(raw) if isinstance(raw, str) else raw
        if kind in {"death", "resurrect"} and isinstance(raw, dict):
            raw = {k: v for k, v in raw.items() if k != "abilityGameID"}
        if not isinstance(raw, dict) or not _effect_identity_matches(raw, target, ability):
            unresolved.append((uid, copy))
    return (
        EvidenceRef.events(
            pf.report_code,
            pf.fight_id,
            None,
            unresolved,
            detail="Unresolved actor-effect recipient or spell identity",
        )
        if unresolved
        else None
    )


def actor_effects(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> tuple[EffectExposure, ...]:
    if not duty.applies(con, pf):
        return ()
    raid = raid_for_encounter(pf.encounter_id)
    policies = (
        load_rules("classic_era", f"zones/{raid.slug}_guidance")
        .get("effects", {})
        .get(pf.encounter_id, ())
    )
    if not policies:
        return ()
    meta = con.execute("SELECT subject_class_id FROM snapshot_meta").fetchone()
    class_id = meta[0] if meta else None
    policies = [
        policy for policy in policies if "classes" not in policy or class_id in policy["classes"]
    ]
    events = combat.event_rows(con, pf)
    result = []
    for policy in policies:
        ids = tuple(int(ability) for ability in policy["ability_ids"])
        unresolved = _unresolved_effect_identity(con, pf, ids)
        states = (
            unknown(
                "actor-effect identity is unresolved",
                unresolved,
                coverage=[coverage(con, pf, pf.actor_id, Direction.TARGET)],
            )
            if unresolved is not None
            else metrics.aura_states(
                con, pf, pf.actor_id, list(ids), None, observed_only=True, event_kinds=AURA_EVENTS
            )
        )
        rows = [
            e
            for e in events
            if e.target_id == pf.actor_id
            and e.kind in AURA_EVENTS
            and e.ability_id in ids
            and _effect_identity_matches(e.raw, e.target_id, e.ability_id)
        ]
        ref = combat.event_ref(pf, rows, f"actor debuff transitions {ids}")
        transitions = (
            unknown("actor-effect identity is unresolved", unresolved)
            if unresolved
            else (
                observed(
                    tuple(
                        (e.t_s, e.kind, int(e.ability_id)) for e in rows if e.ability_id is not None
                    ),
                    ref,
                )
                if rows
                else complete_or_unknown(
                    (),
                    [coverage(con, pf, pf.actor_id, Direction.TARGET)],
                    ref,
                    note="No transitions in the complete target stream; initial state is unknown.",
                )
            )
        )
        windows: Evidenced[tuple[tuple[float, float, bool | None], ...]]
        affected: Evidenced[float]
        uncertain: Evidenced[float]
        if states.value is None:
            windows = unknown(
                states.note or "debuff windows require complete actor-target coverage",
                *states.refs,
                coverage=states.coverage,
            )
            affected = unknown(
                "known debuff duration unavailable", *states.refs, coverage=states.coverage
            )
            uncertain = unknown(
                "unknown-state duration unavailable", *states.refs, coverage=states.coverage
            )
        else:
            windows = complete_or_unknown(
                tuple(
                    (pf.relative_s(lo), pf.relative_s(hi), state) for lo, hi, state in states.value
                ),
                states.coverage,
                *states.refs,
                rule_id=policy["rule"],
            )
            affected = complete_or_unknown(
                sum((hi - lo) / 1000 for lo, hi, state in states.value if state is True),
                states.coverage,
                *states.refs,
                rule_id=policy["rule"],
            )
            uncertain = complete_or_unknown(
                sum((hi - lo) / 1000 for lo, hi, state in states.value if state is None),
                states.coverage,
                *states.refs,
                rule_id=policy["rule"],
            )
        result.append(
            EffectExposure(
                policy["rule"],
                policy["label"],
                policy["source"],
                policy["retrieved"],
                ids,
                windows,
                affected,
                uncertain,
                transitions,
            )
        )
    return tuple(result)
