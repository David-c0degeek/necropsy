"""Encounter-specific findings built from the generic and Hunter analyses."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from necropsy.analysis.classes.classic_era.hunter import Cast, HunterAnalysis
from necropsy.analysis.context import ParticipantFight
from necropsy.analysis.encounters import EncounterRules
from necropsy.analysis.evidence import Evidenced, complete_or_unknown, unknown
from necropsy.analysis.generic import targets


@dataclass(frozen=True, slots=True)
class TargetIntegrity:
    """Damage to the encounter's own units vs foreign units (e.g. trash pulled in)."""

    native: Evidenced[int]
    foreign: Evidenced[int]
    foreign_share_pct: Evidenced[float]
    foreign_targets: tuple[tuple[str, int], ...]
    unclassified_targets: tuple[tuple[str, int], ...]
    """Damaged targets no rule can judge; while any exist the split is UNKNOWN."""
    actors: str
    """'hunter' (the Hunter's own damage) or 'hunter+pets'."""


def target_integrity(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    rules: EncounterRules,
    actor_ids: list[int],
    actors_label: str,
) -> TargetIntegrity | None:
    """None when the encounter has no native-target rule."""
    if rules.native_game_ids is None:
        return None
    split = targets.damage_by_target(con, pf, actor_ids, rules.is_native)
    foreign_targets: tuple[tuple[str, int], ...] = ()
    if split.by_target.value is not None:
        foreign_targets = tuple(
            (t.name or f"actor {t.actor_id}", t.damage)
            for t in split.by_target.value
            if t.classifiable and not rules.is_native(t.game_id, t.name) and t.damage
        )
    unclassified = tuple(
        (t.name or ("no target" if t.actor_id is None else f"actor {t.actor_id}"), t.damage)
        for t in split.unclassified
    )
    if split.native_damage.value is None or split.foreign_damage.value is None:
        share: Evidenced[float] = unknown("target split unknown", *split.native_damage.refs)
    else:
        total = split.native_damage.value + split.foreign_damage.value
        share = complete_or_unknown(
            100.0 * split.foreign_damage.value / total if total else 0.0,
            split.native_damage.coverage,
            *split.native_damage.refs,
            rule_id="native-targets",
            params={"encounter": rules.name},
        )
    return TargetIntegrity(
        split.native_damage,
        split.foreign_damage,
        share,
        foreign_targets,
        unclassified,
        actors_label,
    )


@dataclass(frozen=True, slots=True)
class RaidUtility:
    """Crowd control the Hunter spent on raid members, and the Aimed gap it sits in."""

    friendly_casts: Evidenced[tuple[Cast, ...]]
    longest_aimed_gap_s: Evidenced[tuple[float, float]]
    """(start, end) seconds of the longest gap between Aimed Shots, if known."""
    utility_inside_gap: bool | None


def raid_utility(hunter: HunterAnalysis) -> RaidUtility:
    aimed = hunter.shots["aimed_shot"].casts
    if aimed.value is None or len(aimed.value) < 2:
        gap: Evidenced[tuple[float, float]] = unknown(
            "fewer than two known Aimed Shots", *aimed.refs, coverage=aimed.coverage
        )
    else:
        start, end = max(
            ((a.t_s, b.t_s) for a, b in zip(aimed.value, aimed.value[1:], strict=False)),
            key=lambda pair: pair[1] - pair[0],
        )
        gap = complete_or_unknown((start, end), aimed.coverage, *aimed.refs)
    inside: bool | None = None
    if gap.value is not None and hunter.friendly_crowd_control.value is not None:
        lo, hi = gap.value
        inside = any(lo < c.t_s < hi for c in hunter.friendly_crowd_control.value)
    return RaidUtility(hunter.friendly_crowd_control, gap, inside)
