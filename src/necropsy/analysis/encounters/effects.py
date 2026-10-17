"""Observed actor debuff exposure; never a guide-timed boss phase or opportunity."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.encounters import duty
from necropsy.analysis.evidence import Evidenced, complete_or_unknown, observed, unknown
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
    limitation: str = (
        "Recorded successful debuff removals by this actor, separate from cast counts. "
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
    events = combat.event_rows(con, pf)
    result = []
    for policy in policies:
        ids = tuple(int(ability) for ability in policy["removed_ability_ids"])
        rows = [
            event
            for event in events
            if event.kind == "dispel"
            and event.source_id == pf.actor_id
            and event.raw.get("isBuff") is False
            and type(event.raw.get("extraAbilityGameID")) is int
            and event.raw["extraAbilityGameID"] in ids
        ]
        unresolved = [
            event
            for event in events
            if event.kind == "dispel"
            and event.source_id == pf.actor_id
            and event.raw.get("isBuff") is not True
            and (
                type(event.raw.get("extraAbilityGameID")) is not int
                or (event.raw["extraAbilityGameID"] in ids and event.raw.get("isBuff") is not False)
            )
        ]
        ref = combat.event_ref(pf, rows, f"successful mechanic removals {ids}")
        ambiguous_ref = combat.event_ref(pf, unresolved, "unresolved dispel metadata")
        count = (
            unknown("source dispel events omit usable debuff/mechanic metadata", ref, ambiguous_ref)
            if unresolved
            else complete_or_unknown(
                len(rows),
                [coverage(con, pf, pf.actor_id, Direction.SOURCE)],
                ref,
                rule_id=policy["rule"],
                note="Source-owned dispel effects, not cast or opportunity count.",
            )
        )
        values = tuple(
            (event.t_s, event.target_id, event.ability_id, int(event.raw["extraAbilityGameID"]))
            for event in rows
        )
        observations = (
            observed(values, ref)
            if rows
            else unknown("dispel metadata cannot establish absence", ambiguous_ref)
            if unresolved
            else complete_or_unknown(
                (),
                [coverage(con, pf, pf.actor_id, Direction.SOURCE)],
                ref,
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
            )
        )
    return tuple(result)


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
    events = combat.event_rows(con, pf)
    result = []
    for policy in policies:
        ids = tuple(int(ability) for ability in policy["ability_ids"])
        states = metrics.aura_states(
            con, pf, pf.actor_id, list(ids), None, observed_only=True, event_kinds=AURA_EVENTS
        )
        rows = [
            e
            for e in events
            if e.target_id == pf.actor_id and e.kind in AURA_EVENTS and e.ability_id in ids
        ]
        ref = combat.event_ref(pf, rows, f"actor debuff transitions {ids}")
        transitions = (
            observed(
                tuple((e.t_s, e.kind, int(e.ability_id)) for e in rows if e.ability_id is not None),
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
        windows: Evidenced[tuple[tuple[float, float, bool | None], ...]]
        affected: Evidenced[float]
        uncertain: Evidenced[float]
        if states.value is None:
            windows = unknown("debuff windows require complete actor-target coverage", *states.refs)
            affected = unknown("known debuff duration unavailable", *states.refs)
            uncertain = unknown("unknown-state duration unavailable", *states.refs)
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
