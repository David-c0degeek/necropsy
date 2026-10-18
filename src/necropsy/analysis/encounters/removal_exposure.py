"""Explicit aura endpoints alongside owned removals, without reaction grading."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from itertools import groupby
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.encounters.effects import AURA_EVENTS, EffectExposure, MechanicRemoval
from necropsy.analysis.evidence import Evidenced, ScopedCoverageRef, complete_or_unknown
from necropsy.analysis.generic import combat
from necropsy.analysis.generic.lifecycle import real_death
from necropsy.normalize.coverage import has_complete_encounter_event_set
from necropsy.raids import raid_for_encounter
from necropsy.rules import load_rules
from necropsy.snapshot.model import Direction


@dataclass(frozen=True, slots=True)
class RemovalExposure:
    rule: str
    label: str
    ability_id: int
    recipient: int
    source: str
    retrieved: str
    # Relative integer milliseconds: application, removal, elapsed, removing spell.
    intervals_ms: Evidenced[tuple[tuple[int, int, int, int], ...]]
    coordination: str
    limitation: str = (
        "Recorded exposure ending alongside an owned self-dispel. Same-timestamp events "
        "are unordered; this pairing does not establish causation, reaction quality, "
        "saved mana or damage, assignment or available dispel opportunities."
    )


def correlations(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    exposures: tuple[EffectExposure, ...],
    removals: tuple[MechanicRemoval, ...],
) -> tuple[RemovalExposure, ...]:
    """Withhold pairs on incomplete streams or ambiguous raw state transitions."""
    policies = (
        load_rules("classic_era", f"zones/{raid_for_encounter(pf.encounter_id).slug}_guidance")
        .get("removals", {})
        .get(pf.encounter_id, ())
    )
    enabled = {p["rule"]: p for p in policies if p.get("correlate_self_exposure") is True}
    eligible = [r for r in removals if r.rule in enabled and r.removals.value is not None]
    if not eligible:
        return ()
    covs = [coverage(con, pf, pf.actor_id, d) for d in (Direction.SOURCE, Direction.TARGET)]
    covs.append(
        ScopedCoverageRef(
            pf.report_code,
            pf.fight_id,
            None,
            "all",
            has_complete_encounter_event_set(con, pf.report_code, pf.fight_id),
            "encounter",
        )
    )
    if not all(c.trusted for c in covs):
        return ()
    events = combat.event_rows(con, pf)
    full = con.execute(
        "SELECT timestamp,type,target_id,ability_game_id,raw FROM events "
        "WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchall()
    result = []
    for removal in eligible:
        for ability in removal.removed_ability_ids:
            if not any(
                ability in effect.ability_ids and effect.windows.value is not None
                for effect in exposures
            ) or not _valid_aura_rows(full, pf, ability):
                continue
            timeline = [
                event
                for event in events
                if event.target_id == pf.actor_id
                and (
                    (event.kind in AURA_EVENTS and event.ability_id == ability)
                    or event.kind == "resurrect"
                    or (event.kind == "death" and real_death(event.raw) is not False)
                )
            ]
            effects: dict[int, list[combat.CombatEvent]] = defaultdict(list)
            for event in events:
                if (
                    event.kind == "dispel"
                    and event.source_id == pf.actor_id
                    and event.target_id == pf.actor_id
                    and event.ability_id in removal.removing_ability_ids
                    and type(event.raw.get("extraAbilityGameID")) is int
                    and event.raw["extraAbilityGameID"] == ability
                    and event.raw.get("isBuff") is False
                ):
                    effects[event.timestamp].append(event)
            pending = None
            intervals = []
            refs = []
            ambiguous = False
            for timestamp, grouped in groupby(
                sorted(timeline, key=lambda e: e.timestamp), key=lambda e: e.timestamp
            ):
                group = list(grouped)
                if len(group) != 1:
                    ambiguous = True
                    break
                event = group[0]
                if event.kind == "applydebuff":
                    # A repeated application makes this state segment ambiguous.
                    if pending is None:
                        pending = event
                    else:
                        ambiguous = True
                        break
                elif event.kind == "removedebuff":
                    matching = effects.get(timestamp, [])
                    if pending is not None and pending.timestamp < timestamp and len(matching) == 1:
                        removing_spell = matching[0].ability_id
                        assert removing_spell is not None
                        intervals.append(
                            (
                                pending.timestamp - pf.start_time,
                                timestamp - pf.start_time,
                                timestamp - pending.timestamp,
                                removing_spell,
                            )
                        )
                        refs.extend([pending, event, matching[0]])
                    pending = None
                else:
                    if event.kind in AURA_EVENTS:
                        ambiguous = True
                        break
                    pending = None
            if intervals and not ambiguous:
                policy = enabled[removal.rule]
                result.append(
                    RemovalExposure(
                        removal.rule,
                        removal.label,
                        ability,
                        pf.actor_id,
                        removal.source,
                        removal.retrieved,
                        complete_or_unknown(
                            tuple(intervals),
                            covs,
                            combat.event_ref(
                                pf, refs, "aura endpoints alongside owned self-dispel"
                            ),
                            rule_id="explicit-self-removal-exposure-v1",
                        ),
                        str(policy["coordination"]),
                    )
                )
    return tuple(result)


def _valid_aura_rows(rows: list[tuple[Any, ...]], pf: ParticipantFight, ability: int) -> bool:
    """Check possible raw recipients/spells before normalized exclusions hide conflicts."""
    for timestamp, kind, target, spell, payload in rows:
        raw = json.loads(payload) if isinstance(payload, str) else payload
        if not isinstance(raw, dict):
            if target in {None, pf.actor_id} and (
                kind in AURA_EVENTS | {"death", "resurrect", None}
            ):
                return False
            continue
        raw_target = raw.get("targetID", target)
        possible_target = (
            type(target) is not int
            or target < 1
            or target == pf.actor_id
            or type(raw_target) is not int
            or raw_target < 1
            or raw_target == pf.actor_id
        )
        raw_kind = raw.get("type")
        possible_kind = (
            kind in AURA_EVENTS | {"death", "resurrect", None}
            or (type(raw_kind) is str and raw_kind in AURA_EVENTS | {"death", "resurrect"})
            or ("type" in raw and type(raw_kind) is not str)
        )
        possible_spell = (
            kind in {"death", "resurrect", None}
            or (type(raw_kind) is str and raw_kind in {"death", "resurrect"})
            or spell in {None, ability}
            or raw.get("abilityGameID") == ability
            or ("abilityGameID" in raw and type(raw["abilityGameID"]) is not int)
        )
        if not (possible_target and possible_kind and possible_spell):
            continue
        if (
            type(timestamp) is not int
            or not pf.start_time <= timestamp <= pf.end_time
            or type(target) is not int
            or target != pf.actor_id
            or kind not in AURA_EVENTS | {"death", "resurrect"}
            or any(
                key in raw and (type(raw[key]) is not typ or raw[key] != value)
                for key, typ, value in [
                    ("timestamp", int, timestamp),
                    ("type", str, kind),
                    ("targetID", int, target),
                    ("fight", int, pf.fight_id),
                ]
            )
            or (
                kind in AURA_EVENTS
                and (
                    type(spell) is not int
                    or spell != ability
                    or (
                        "abilityGameID" in raw
                        and (type(raw["abilityGameID"]) is not int or raw["abilityGameID"] != spell)
                    )
                )
            )
            or (kind == "death" and real_death(raw) is None)
        ):
            return False
    return True
