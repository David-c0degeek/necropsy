"""Observed NPC aura windows, kept separate for each report actor and instance."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import duckdb

from necropsy.analysis.class_catalog import CLASS_NAMES
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
from necropsy.analysis.generic.lifecycle import real_death
from necropsy.analysis.generic.metrics import observed_aura_windows
from necropsy.analysis.generic.npcs import identity as _identity
from necropsy.analysis.generic.npcs import singletons as _singleton_npcs
from necropsy.normalize.coverage import has_complete_encounter_coverage
from necropsy.raids import raid_for_encounter
from necropsy.rules import load_rules

BUFF_EVENTS = frozenset(
    {"applybuff", "removebuff", "refreshbuff", "applybuffstack", "removebuffstack"}
)
DEBUFF_EVENTS = frozenset(
    {"applydebuff", "removedebuff", "refreshdebuff", "applydebuffstack", "removedebuffstack"}
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
    classes: dict[int, set[tuple[str | None, str | None]]] = defaultdict(set)
    for actor, kind, game_id, name, subtype in con.execute(
        "SELECT actor_id,type,game_id,name,sub_type FROM actors WHERE report_code=?",
        [pf.report_code],
    ).fetchall():
        actors[actor].add((kind, game_id, name))
        classes[actor].add((kind, subtype))
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
    events = [row for row in events if row[1] != "death" or real_death(row[5]) is not False]
    result = []
    singletons = (
        _singleton_npcs(con, pf, actors)
        if any(policy.get("require_instance") is False for policy in policies)
        else set()
    )
    for policy in policies:
        result.append(_aura(pf, policy, cov, actors, events, classes, singletons))
    return tuple(result)


def _aura(
    pf: ParticipantFight,
    policy: dict[str, Any],
    cov: ScopedCoverageRef,
    actors: dict[int, set[tuple[str | None, int | None, str | None]]],
    events: list[tuple[Any, ...]],
    classes: dict[int, set[tuple[str | None, str | None]]],
    singletons: set[int],
) -> EncounterAura:
    aura_kind = policy.get("aura_kind", "buff")
    if aura_kind not in {"buff", "debuff"}:
        raise ValueError("unsupported target aura kind")
    event_kinds = DEBUFF_EVENTS if aura_kind == "debuff" else BUFF_EVENTS
    if ("caster_classes" in policy) == ("caster_game_ids" in policy):
        raise ValueError("target aura requires exactly one caster identity policy")
    wanted_classes = policy.get("caster_classes")
    if wanted_classes is not None and (
        not wanted_classes or any(name not in CLASS_NAMES.values() for name in wanted_classes)
    ):
        raise ValueError("target aura caster classes must be known game classes")

    def caster_identity(actor: int | None) -> bool | None:
        if wanted_classes is None:
            return _identity(actors, actor, tuple(policy["caster_game_ids"]))
        identities = classes.get(actor) if actor is not None else None
        catalog = actors.get(actor) if actor is not None else None
        if not identities or len(identities) != 1 or not catalog or len(catalog) != 1:
            return None
        kind, subtype = next(iter(identities))
        if kind is None:
            return None
        if kind != "Player":
            return False
        return subtype in wanted_classes if subtype in CLASS_NAMES.values() else None

    rows = []
    unresolved = []
    for event in events:
        _ts, kind, caster, target, ability, raw, _uid, _copy = event
        if ability != policy["ability_id"] or kind not in event_kinds:
            continue
        raw_identity_valid = all(
            key not in raw or (type(raw[key]) is int and raw[key] > 0 and raw[key] == value)
            for key, value in (
                ("sourceID", caster),
                ("targetID", target),
                ("abilityGameID", ability),
            )
        )
        if not raw_identity_valid:
            unresolved.append(event)
            continue
        matches = (
            caster_identity(caster),
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
            sum(row[1] == f"apply{aura_kind}" for row in rows), [cov], ref, rule_id=policy["rule"]
        )
    )
    transitions = tuple(
        (pf.relative_s(row[0]), row[1], row[3], row[5].get("targetInstance")) for row in rows
    )
    observed_transitions = (
        observed(transitions, ref, note="Positive observed transitions; scope may be incomplete.")
        if transitions
        else unknown("some aura identities are unresolved", ref, coverage=[cov])
        if unresolved
        else complete_or_unknown((), [cov], ref)
    )
    by_target: dict[tuple[int, int | None], list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_target[row[3], row[5].get("targetInstance")].append(row)
    target_actors = {actor for actor, _instance in by_target}
    unresolved_lifecycles = [
        row
        for row in events
        if row[1] in {"death", "resurrect"}
        and (
            row[3] is None
            or (row[1] == "death" and row[3] in target_actors and real_death(row[5]) is None)
            or (
                "targetID" in row[5]
                and (
                    type(row[5]["targetID"]) is not int
                    or row[5]["targetID"] < 1
                    or row[5]["targetID"] != row[3]
                )
            )
        )
    ]
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
            and (
                instance is not None
                or (policy.get("require_instance") is False and actor in singletons)
            )
            and not unresolved_lifecycles
        )
        if policy.get("require_instance", True) and any(
            row[3] == actor
            and (
                (row[1] in event_kinds and row[4] == policy["ability_id"])
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

        state_refs: tuple[EvidenceRef, ...] = (target_ref, reset_ref)
        if instance is None and policy.get("require_instance") is False:
            state_refs += (
                EvidenceRef(
                    pf.report_code,
                    pf.fight_id,
                    actor,
                    "fights",
                    detail="enemyNPCs exact actor/game ID binding and singleton instanceCount",
                ),
            )
        if unresolved_lifecycles:
            state_refs += (
                EvidenceRef.events(
                    pf.report_code,
                    pf.fight_id,
                    None,
                    [(row[6], row[7]) for row in unresolved_lifecycles],
                    detail="lifecycle rows with unresolved recipient identities",
                ),
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
                    state_refs,
                    policy["rule"],
                ),
                _measure(
                    sum((hi - lo) / 1000 for lo, hi, state in segments if state is True),
                    trustworthy,
                    cov,
                    state_refs,
                    policy["rule"],
                ),
                _measure(
                    sum((hi - lo) / 1000 for lo, hi, state in segments if state is None),
                    trustworthy,
                    cov,
                    state_refs,
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
