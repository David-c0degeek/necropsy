"""Observed NPC aura windows, kept separate for each report actor and instance."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight
from necropsy.analysis.encounters import duty
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceRef,
    ScopedCoverageRef,
    complete_or_unknown,
    observed,
    unknown,
)
from necropsy.analysis.generic.metrics import observed_aura_windows
from necropsy.normalize.coverage import has_complete_encounter_coverage
from necropsy.raids import raid_for_encounter
from necropsy.rules import load_rules

BUFF_EVENTS = frozenset(
    {"applybuff", "removebuff", "refreshbuff", "applybuffstack", "removebuffstack"}
)
LIMITATION = (
    "Observed aura state for this target instance, not a global phase, attackability "
    "window or personal assignment. Initial state stays unknown until a definitive "
    "transition. Fight end censors active effects; no guide timer supplies a removal. "
    "These windows do not measure avoidability, lost throughput or quality."
)


@dataclass(frozen=True, slots=True)
class TargetAuraWindow:
    actor_id: int
    instance: int | None
    game_id: int
    name: str
    windows: Evidenced[tuple[tuple[float, float, bool | None], ...]]
    known_active_s: Evidenced[float]
    unknown_state_s: Evidenced[float]


@dataclass(frozen=True, slots=True)
class EncounterAura:
    rule: str
    label: str
    ability_id: int
    source: str
    retrieved: str
    applications: Evidenced[int]
    transitions: Evidenced[tuple[tuple[float, str, int, int | None], ...]]
    targets: tuple[TargetAuraWindow, ...]
    limitation: str = LIMITATION


def _identity(
    actors: dict[int, set[tuple[str | None, int | None, str | None]]],
    actor: int | None,
    wanted: tuple[int, ...],
) -> bool | None:
    identities = actors.get(actor) if actor is not None else None
    if not identities or len(identities) != 1:
        return None
    kind, game_id, _ = next(iter(identities))
    if kind is None:
        return None
    if kind != "NPC":
        return False
    return game_id in wanted if game_id is not None else None


def encounter_auras(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> tuple[EncounterAura, ...]:
    """Use only certified unrestricted encounter coverage for windows or absences."""
    if not duty.applies(con, pf):
        return ()
    raid = raid_for_encounter(pf.encounter_id)
    policies = (
        load_rules("classic_era", f"zones/{raid.slug}_guidance")
        .get("target_auras", {})
        .get(pf.encounter_id, ())
    )
    if not policies:
        return ()
    cov = ScopedCoverageRef(
        pf.report_code,
        pf.fight_id,
        None,
        "all",
        has_complete_encounter_coverage(con, pf.report_code, pf.fight_id),
        "encounter",
    )
    actors: dict[int, set[tuple[str | None, int | None, str | None]]] = defaultdict(set)
    for actor, kind, game_id, name in con.execute(
        "SELECT actor_id,type,game_id,name FROM actors WHERE report_code=?", [pf.report_code]
    ).fetchall():
        actors[actor].add((kind, game_id, name))
    rows = con.execute(
        """SELECT timestamp,type,source_id,target_id,ability_game_id,raw,event_uid,copy_index
           FROM events WHERE report_code=? AND fight_id=? AND timestamp BETWEEN ? AND ?
           ORDER BY timestamp,event_uid,copy_index""",
        [pf.report_code, pf.fight_id, pf.start_time, pf.end_time],
    ).fetchall()
    events = [
        (*row[:5], json.loads(row[5]) if isinstance(row[5], str) else row[5], *row[6:])
        for row in rows
    ]
    result = []
    for policy in policies:
        result.append(_aura(pf, policy, cov, actors, events))
    return tuple(result)


def _aura(
    pf: ParticipantFight,
    policy: dict[str, Any],
    cov: ScopedCoverageRef,
    actors: dict[int, set[tuple[str | None, int | None, str | None]]],
    events: list[tuple[Any, ...]],
) -> EncounterAura:
    rows = []
    unresolved = []
    for event in events:
        _ts, kind, caster, target, ability, raw, _uid, _copy = event
        if ability != policy["ability_id"] or kind not in BUFF_EVENTS:
            continue
        matches = (
            _identity(actors, caster, tuple(policy["caster_game_ids"])),
            _identity(actors, target, tuple(policy["target_game_ids"])),
        )
        if False in matches:
            continue
        instance = raw.get("targetInstance")
        if None in matches or (
            instance is not None and (type(instance) is not int or instance < 1)
        ):
            unresolved.append(event)
            continue
        rows.append(event)
    ref = EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        None,
        [(row[6], row[7]) for row in [*rows, *unresolved]],
        detail=f"{policy['label']} exact caster, recipient and instance transitions",
    )
    applications = (
        unknown(
            "some aura caster, recipient or instance identities are unresolved", ref, coverage=[cov]
        )
        if unresolved
        else complete_or_unknown(
            sum(row[1] == "applybuff" for row in rows), [cov], ref, rule_id=policy["rule"]
        )
    )
    transitions = tuple(
        (pf.relative_s(row[0]), row[1], row[3], row[5].get("targetInstance")) for row in rows
    )
    observed_transitions = (
        observed(transitions, ref, note="Positive observed transitions; scope may be incomplete.")
        if transitions
        else complete_or_unknown((), [cov], ref)
    )
    by_target: dict[tuple[int, int | None], list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_target[row[3], row[5].get("targetInstance")].append(row)
    targets = []
    for (actor, instance), target_rows in sorted(
        by_target.items(), key=lambda item: (item[0][0], item[0][1] or 0)
    ):
        _, game_id, name = next(iter(actors[actor]))
        assert game_id is not None
        target_ref = EvidenceRef.events(
            pf.report_code,
            pf.fight_id,
            actor,
            [(row[6], row[7]) for row in target_rows],
            detail=f"{policy['label']}, target instance {instance}",
        )
        resets = [
            row
            for row in events
            if row[1] in {"death", "resurrect"}
            and row[3] == actor
            and row[5].get("targetInstance") == instance
        ]
        segments = observed_aura_windows(
            pf.start_time,
            pf.end_time,
            [(row[0], row[1]) for row in target_rows]
            + [(row[0], "stateunknown") for row in resets],
        )
        # Repeated NPCs require a concrete instance. An unnumbered observation
        # remains visible but cannot be attached to any numbered unit's state.
        trustworthy = (
            cov.trusted
            and not unresolved
            and (instance is not None or not policy.get("require_instance", True))
        )
        if policy.get("require_instance", True) and any(
            row[3] == actor
            and (
                (row[1] in BUFF_EVENTS and row[4] == policy["ability_id"])
                or row[1] in {"death", "resurrect"}
            )
            and (type(row[5].get("targetInstance")) is not int or row[5]["targetInstance"] < 1)
            for row in events
        ):
            trustworthy = False
        reset_ref = EvidenceRef.events(
            pf.report_code,
            pf.fight_id,
            actor,
            [(row[6], row[7]) for row in resets],
            detail=f"lifecycle, target instance {instance}",
        )

        targets.append(
            TargetAuraWindow(
                actor,
                instance,
                game_id,
                name or str(actor),
                _measure(
                    tuple(
                        (pf.relative_s(lo), pf.relative_s(hi), state) for lo, hi, state in segments
                    ),
                    trustworthy,
                    cov,
                    (target_ref, reset_ref),
                    policy["rule"],
                ),
                _measure(
                    sum((hi - lo) / 1000 for lo, hi, state in segments if state is True),
                    trustworthy,
                    cov,
                    (target_ref, reset_ref),
                    policy["rule"],
                ),
                _measure(
                    sum((hi - lo) / 1000 for lo, hi, state in segments if state is None),
                    trustworthy,
                    cov,
                    (target_ref, reset_ref),
                    policy["rule"],
                ),
            )
        )
    return EncounterAura(
        policy["rule"],
        policy["label"],
        policy["ability_id"],
        policy["source"],
        policy["retrieved"],
        applications,
        observed_transitions,
        tuple(targets),
    )


def _measure[T](
    value: T,
    trustworthy: bool,
    cov: ScopedCoverageRef,
    refs: tuple[EvidenceRef, ...],
    rule: str,
) -> Evidenced[T]:
    if not trustworthy:
        return unknown(
            "aura windows require complete encounter coverage and unambiguous instances",
            *refs,
            coverage=[cov],
        )
    return complete_or_unknown(value, [cov], *refs, rule_id=rule)
