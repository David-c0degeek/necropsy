"""Per-instance summon and overkill event bounds, never physical opportunity."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, TypeGuard

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
from necropsy.analysis.generic import npcs
from necropsy.analysis.generic.lifecycle import real_death
from necropsy.normalize.coverage import has_complete_encounter_event_set
from necropsy.raids import raid_for_encounter
from necropsy.rules import load_rules

LIMITATION = (
    "Elapsed time between recorded summon and positive-overkill events for this exact "
    "NPC instance; it does not establish lifetime, continuous attackability, range, "
    "assignment or damage opportunity. Groups can overlap. Missing or conflicting "
    "endpoints stay unknown; fight end and later summon casts do not supply an endpoint."
)


@dataclass(frozen=True, slots=True)
class SummonBound:
    actor_id: int
    instance: int
    game_id: int
    name: str
    summoned_s: Evidenced[float]
    first_positive_overkill_s: Evidenced[float]
    elapsed_to_overkill_s: Evidenced[float]


@dataclass(frozen=True, slots=True)
class EncounterSummons:
    rule: str
    label: str
    ability_id: int
    source: str
    retrieved: str
    summons: Evidenced[int]
    transitions: Evidenced[tuple[tuple[float, int, int, int], ...]]
    targets: tuple[SummonBound, ...]
    limitation: str = LIMITATION


@dataclass(frozen=True, slots=True)
class _Event:
    timestamp: int
    kind: str
    source: int | None
    target: int | None
    ability: int | None
    raw: dict[str, Any] | None
    uid: str
    copy: int


def _valid(event: _Event, *, source: bool = False, ability: bool = False) -> bool:
    raw = event.raw
    if raw is None:
        return False
    if "type" in raw and raw["type"] != event.kind:
        return False
    if "timestamp" in raw and (
        type(raw["timestamp"]) is not int or raw["timestamp"] != event.timestamp
    ):
        return False
    fields = [("targetID", event.target)]
    if source:
        fields.append(("sourceID", event.source))
    if ability:
        fields.append(("abilityGameID", event.ability))
    return all(
        key not in raw or (type(raw[key]) is int and raw[key] > 0 and raw[key] == value)
        for key, value in fields
    )


def _number(value: Any) -> TypeGuard[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def summon_observations(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> tuple[EncounterSummons, ...]:
    if not duty.applies(con, pf):
        return ()
    raid = raid_for_encounter(pf.encounter_id)
    policies = (
        load_rules("classic_era", f"zones/{raid.slug}_guidance")
        .get("summons", {})
        .get(pf.encounter_id, ())
    )
    if not policies:
        return ()
    cov = ScopedCoverageRef(
        pf.report_code,
        pf.fight_id,
        None,
        "all",
        has_complete_encounter_event_set(con, pf.report_code, pf.fight_id),
        "encounter",
    )
    actors: npcs.Catalog = defaultdict(set)
    for actor, kind, game_id, name in con.execute(
        "SELECT actor_id,type,game_id,name FROM actors WHERE report_code=?", [pf.report_code]
    ).fetchall():
        actors[actor].add((kind, game_id, name))
    counts = npcs.cardinalities(con, pf, actors)
    events = []
    for row in con.execute(
        """SELECT timestamp,type,source_id,target_id,ability_game_id,raw,event_uid,copy_index
           FROM events WHERE report_code=? AND fight_id=? AND timestamp BETWEEN ? AND ?
           AND type IN ('summon','damage','death','resurrect')
           ORDER BY timestamp,event_uid,copy_index""",
        [pf.report_code, pf.fight_id, pf.start_time, pf.end_time],
    ).fetchall():
        raw = json.loads(row[5]) if isinstance(row[5], str) else row[5]
        events.append(
            _Event(
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                raw if isinstance(raw, dict) else None,
                row[6],
                row[7],
            )
        )
    roster = npcs.fight_roster(con, pf) or []
    return tuple(_policy(pf, policy, cov, actors, counts, roster, events) for policy in policies)


def _policy(
    pf: ParticipantFight,
    policy: dict[str, Any],
    cov: ScopedCoverageRef,
    actors: npcs.Catalog,
    counts: dict[int, int],
    roster: list[dict[str, Any]],
    events: list[_Event],
) -> EncounterSummons:
    spawns: dict[tuple[int, int], list[_Event]] = defaultdict(list)
    hits: dict[tuple[int, int], list[_Event]] = defaultdict(list)
    resets: dict[tuple[int, int], list[_Event]] = defaultdict(list)
    unresolved_spawns = []
    unresolved_bounds = []
    casters, recipients = tuple(policy["caster_game_ids"]), tuple(policy["target_game_ids"])
    declared_casters = {
        row["id"]
        for row in roster
        if type(row.get("id")) is int
        and type(row.get("gameID")) is int
        and row["gameID"] in casters
    }
    declared_targets = {
        row["id"]
        for row in roster
        if type(row.get("id")) is int
        and type(row.get("gameID")) is int
        and row["gameID"] in recipients
    }
    for event in events:
        raw = event.raw or {}
        if event.kind == "summon":
            if (
                event.ability != policy["ability_id"]
                and raw.get("abilityGameID") != policy["ability_id"]
            ):
                continue
            if not _valid(event, source=True, ability=True):
                unresolved_spawns.append(event)
                continue
            matches = (
                npcs.identity(actors, event.source, casters),
                npcs.identity(actors, event.target, recipients),
            )
            if (matches[0] is False and event.source in declared_casters) or (
                matches[1] is False and event.target in declared_targets
            ):
                unresolved_spawns.append(event)
                continue
            if False in matches:
                continue
            instance = raw.get("targetInstance")
            source_instance = raw.get("sourceInstance")
            if (
                None in matches
                or counts.get(event.source or -1) != 1
                or (
                    source_instance is not None
                    and (type(source_instance) is not int or source_instance != 1)
                )
                or type(instance) is not int
                or instance < 1
                or instance > counts.get(event.target or -1, 0)
            ):
                unresolved_spawns.append(event)
                continue
            assert event.target is not None
            spawns[event.target, instance].append(event)
            continue
        # Both representations must establish an unrelated recipient before a
        # malformed chronology can be ignored. A conflicting or missing raw
        # identity can still refer to a policy target and remains unresolved.
        if (
            type(raw.get("targetID")) is int
            and raw["targetID"] > 0
            and raw["targetID"] == event.target
            and npcs.identity(actors, event.target, recipients) is False
            and event.target not in declared_targets
        ):
            continue
        if not _valid(event):
            unresolved_bounds.append(event)
            continue
        target_matches = npcs.identity(actors, event.target, recipients)
        if target_matches is False and event.target in declared_targets:
            unresolved_bounds.append(event)
            continue
        if target_matches is False:
            continue
        instance = raw.get("targetInstance")
        if (
            target_matches is None
            or type(instance) is not int
            or instance < 1
            or instance > counts.get(event.target or -1, 0)
        ):
            unresolved_bounds.append(event)
            continue
        assert event.target is not None
        key = (event.target, instance)
        if event.kind == "damage":
            amount, overkill = raw.get("amount"), raw.get("overkill", 0)
            if (
                not _number(amount)
                or amount < 0
                or not _number(overkill)
                or (overkill > 0 and amount <= 0)
            ):
                resets[key].append(event)
            else:
                hits[key].append(event)
        elif event.kind == "resurrect" or real_death(event.raw) is not False:
            resets[key].append(event)

    all_spawns = sorted(
        [event for group in spawns.values() for event in group],
        key=lambda event: (event.timestamp, event.uid, event.copy),
    )
    ref = EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        None,
        [(e.uid, e.copy) for e in [*all_spawns, *unresolved_spawns]],
        detail=f"{policy['label']} exact caster, recipient and numbered-instance summons",
    )
    count = (
        unknown("some summon identities or cardinalities are unresolved", ref, coverage=[cov])
        if unresolved_spawns
        else complete_or_unknown(len(all_spawns), [cov], ref, rule_id=policy["rule"])
    )
    transitions = tuple(
        (pf.relative_s(e.timestamp), e.source, e.target, e.raw["targetInstance"])
        for e in all_spawns
        if e.source is not None and e.target is not None and e.raw is not None
    )
    positive = (
        observed(transitions, ref, note="Positive observed summons; scope may be incomplete.")
        if transitions
        else unknown("some summon identities are unresolved", ref, coverage=[cov])
        if unresolved_spawns
        else complete_or_unknown((), [cov], ref)
    )
    targets = []
    for (actor, instance), starts in sorted(spawns.items()):
        markers = [e for e in hits[actor, instance] if (e.raw or {}).get("overkill", 0) > 0]
        first = min((e.timestamp for e in markers), default=None)
        start = starts[0].timestamp if len(starts) == 1 else None
        contradiction = any(
            (start is not None and e.timestamp < start)
            or (first is not None and e.timestamp > first and (e.raw or {}).get("amount", 0) > 0)
            for e in hits[actor, instance]
        )
        boundary_ref = EvidenceRef.events(
            pf.report_code,
            pf.fight_id,
            None,
            [
                (e.uid, e.copy)
                for e in [
                    *starts,
                    *markers,
                    *resets[actor, instance],
                    *unresolved_spawns,
                    *unresolved_bounds,
                    *(hits[actor, instance] if contradiction else []),
                ]
            ],
            detail=f"{policy['label']} NPC {actor} instance {instance} observed event bounds",
        )
        roster_ref = EvidenceRef(
            pf.report_code,
            pf.fight_id,
            None,
            "exact fight enemyNPCs cardinality and report NPC identity",
        )
        uncertain = bool(unresolved_spawns or unresolved_bounds or resets[actor, instance])
        summoned = (
            unknown("summon start is ambiguous", boundary_ref, roster_ref, coverage=[cov])
            if start is None or unresolved_spawns
            else complete_or_unknown(
                pf.relative_s(start), [cov], boundary_ref, roster_ref, rule_id=policy["rule"]
            )
        )
        valid = (
            start is not None
            and first is not None
            and first > start
            and not uncertain
            and not contradiction
        )
        endpoint = (
            complete_or_unknown(
                pf.relative_s(first), [cov], boundary_ref, roster_ref, rule_id=policy["rule"]
            )
            if valid and first is not None
            else unknown(
                "a unique consistent overkill event bound is unavailable",
                boundary_ref,
                roster_ref,
                coverage=[cov],
            )
        )
        elapsed = (
            complete_or_unknown(
                (first - start) / 1000, [cov], boundary_ref, roster_ref, rule_id=policy["rule"]
            )
            if valid and start is not None and first is not None
            else unknown(
                "no certified summon-to-overkill elapsed bound",
                boundary_ref,
                roster_ref,
                coverage=[cov],
            )
        )
        _kind, game_id, name = next(iter(actors[actor]))
        assert game_id is not None
        targets.append(
            SummonBound(
                actor, instance, game_id, name or "Unknown NPC", summoned, endpoint, elapsed
            )
        )
    return EncounterSummons(
        policy["rule"],
        policy["label"],
        policy["ability_id"],
        policy["source"],
        policy["retrieved"],
        count,
        positive,
        tuple(targets),
    )
