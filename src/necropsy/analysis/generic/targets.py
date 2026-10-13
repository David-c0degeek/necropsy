"""Who the damage went to, and whether those targets belong to the encounter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage, owned_pets, pet_listing_known
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceRef,
    complete_or_unknown,
    unknown,
)
from necropsy.snapshot.model import Direction

NativeTarget = Callable[[int | None, str | None], bool]
"""(target game ID, target name) -> belongs to the encounter. Supplied by encounter rules."""


@dataclass(frozen=True, slots=True)
class TargetDamage:
    actor_id: int | None
    game_id: int | None
    name: str | None
    damage: int

    @property
    def classifiable(self) -> bool:
        """An encounter rule can only judge a target that is a listed actor with a game ID."""
        return self.actor_id is not None and self.game_id is not None


@dataclass(frozen=True, slots=True)
class TargetSplit:
    by_target: Evidenced[tuple[TargetDamage, ...]]
    native_damage: Evidenced[int]
    foreign_damage: Evidenced[int]
    unclassified: tuple[TargetDamage, ...] = ()
    """Damaged targets with no target ID, no actor record, or no game ID."""


def damage_by_target(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    actor_ids: list[int],
    is_native: NativeTarget | None,
) -> TargetSplit:
    rows = con.execute(
        """
        SELECT e.target_id, a.game_id, a.name, sum(coalesce(e.amount, 0)), count(*)
        FROM events e
        LEFT JOIN actors a ON a.report_code = e.report_code AND a.actor_id = e.target_id
        WHERE e.report_code = ? AND e.fight_id = ? AND e.type = 'damage'
          AND e.source_id IN (SELECT unnest(?::BIGINT[]))
        GROUP BY 1, 2, 3 ORDER BY 4 DESC, 1
        """,
        [pf.report_code, pf.fight_id, actor_ids],
    ).fetchall()
    ref = EvidenceRef(
        pf.report_code,
        pf.fight_id,
        actor_ids[0],
        "events",
        event_count=sum(int(r[4]) for r in rows),
        detail=f"damage by {actor_ids} grouped by target",
    )
    cov = [coverage(con, pf, a, Direction.SOURCE) for a in actor_ids]
    split = tuple(TargetDamage(r[0], r[1], r[2], int(r[3])) for r in rows)
    by_target = complete_or_unknown(split, cov, ref)
    if is_native is None or by_target.value is None:
        why = (
            "no encounter rule says which targets are native"
            if is_native is None
            else "damage by target unknown"
        )
        return TargetSplit(by_target, unknown(why, ref), unknown(why, ref))
    unclassified = tuple(t for t in split if not t.classifiable and t.damage)
    if unclassified:
        why = f"{len(unclassified)} damaged targets cannot be classified (no actor or game ID)"
        return TargetSplit(by_target, unknown(why, ref), unknown(why, ref), unclassified)
    native = sum(t.damage for t in split if is_native(t.game_id, t.name))
    foreign = sum(t.damage for t in split) - native
    return TargetSplit(
        by_target,
        complete_or_unknown(native, cov, ref),
        complete_or_unknown(foreign, cov, ref),
    )


ExcludedTarget = Callable[[int | None, str | None], bool]
"""(target game ID, target name) -> WCL ranking ignores damage to this target."""


@dataclass(frozen=True, slots=True)
class RankedTarget:
    """One damaged target and whether WCL's ranking counts its damage."""

    actor_id: int | None
    game_id: int | None
    name: str | None
    kind: str | None
    """Actor type from the report (`NPC`, `Player`, `Pet`, ...); None when unlisted."""
    damage: int
    category: str
    """`counted`, `excluded` (encounter rule), `own` (the Hunter or its pets), or
    `unclassifiable` (no target ID, or no game ID while encounter exclusions apply)."""


def _ranked_targets(
    rows: list[tuple[Any, ...]], own: set[int], excluded: ExcludedTarget | None
) -> tuple[RankedTarget, ...]:
    out = []
    for target_id, game_id, name, kind, damage, _count in rows:
        if target_id is None:
            category = "unclassifiable"
        elif int(target_id) in own:
            category = "own"
        elif excluded is not None and game_id is None:
            # Exclusions are decided by game ID; a display name alone cannot decide.
            category = "unclassifiable"
        elif excluded is not None and excluded(game_id, name):
            category = "excluded"
        else:
            category = "counted"
        out.append(RankedTarget(target_id, game_id, name, kind, int(damage), category))
    return tuple(
        sorted(out, key=lambda r: (-r.damage, r.actor_id if r.actor_id is not None else -1))
    )


@dataclass(frozen=True, slots=True)
class RankingDamage:
    """Damage by a Hunter and every actor exported as its pet, split by what counts."""

    raw: Evidenced[int]
    """All damage events, any target."""
    external: Evidenced[int]
    """Damage to anything except the Hunter itself and its own pet-linked actors."""
    ranked: Evidenced[int]
    """External damage minus targets the encounter rule excludes from WCL rankings."""
    actor_ids: tuple[int, ...]
    by_target: Evidenced[tuple[RankedTarget, ...]]
    """Every damaged target with its ranking category."""


def ranking_damage(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    excluded: ExcludedTarget | None,
    exclusion_rule: str | None,
) -> RankingDamage:
    """Damage as WCL ranks it: Hunter + pet-linked actors, minus damage to themselves.

    Rule `external-damage-v1`, checked against the fixture: WCL's ranked amount
    leaves out self-damage (Goblin Sapper Charge, Dense Dynamite) but counts damage
    to other players, e.g. mind-controlled raid members, and to every NPC. With
    no encounter exclusions it reproduces 64 of the 75 top-five Naxxramas
    rankings exactly; the rest are bosses whose adds WCL leaves out, which the
    encounter rule supplies through `excluded`. A missing pet listing makes every
    total UNKNOWN, because pet damage could not be attributed.
    """
    pets = [p.actor_id for p in owned_pets(con, pf)]
    actor_ids = [pf.actor_id, *pets]
    rows = con.execute(
        """
        SELECT e.target_id, a.game_id, a.name, a.type, sum(coalesce(e.amount, 0)), count(*)
        FROM events e
        LEFT JOIN actors a ON a.report_code = e.report_code AND a.actor_id = e.target_id
        WHERE e.report_code = ? AND e.fight_id = ? AND e.type = 'damage'
          AND e.source_id IN (SELECT unnest(?::BIGINT[]))
        GROUP BY 1, 2, 3, 4
        """,
        [pf.report_code, pf.fight_id, actor_ids],
    ).fetchall()
    ref = EvidenceRef(
        pf.report_code,
        pf.fight_id,
        pf.actor_id,
        "events",
        event_count=sum(int(r[5]) for r in rows),
        detail=f"damage by Hunter and pet-linked actors {actor_ids}",
    )
    cov = [coverage(con, pf, a, Direction.SOURCE) for a in actor_ids]
    if not pet_listing_known(con, pf):
        why = "the Hunter's pet listing is missing, so pet damage cannot be attributed"
        gone: Evidenced[int] = unknown(why, ref, coverage=cov)
        return RankingDamage(gone, gone, gone, tuple(actor_ids), unknown(why, ref, coverage=cov))
    own = set(actor_ids)
    by_target = complete_or_unknown(
        _ranked_targets(rows, own, excluded),
        cov,
        ref,
        rule_id="external-damage-v1",
        params={"encounter_exclusions": exclusion_rule or "none"},
    )
    raw = sum(int(r[4]) for r in rows)
    raw_e = complete_or_unknown(raw, cov, ref)
    rule = "external-damage-v1"
    no_target = [r for r in rows if r[0] is None]
    if no_target:
        events = sum(int(r[5]) for r in no_target)
        amount = sum(int(r[4]) for r in no_target)
        why = f"{events} damage events ({amount} damage) have no target ID; they may be self-damage"
        return RankingDamage(
            raw_e,
            unknown(why, ref, coverage=cov),
            unknown(why, ref, coverage=cov),
            tuple(actor_ids),
            by_target,
        )
    external_rows = [r for r in rows if int(r[0]) not in own]
    external = sum(int(r[4]) for r in external_rows)
    external_e = complete_or_unknown(external, cov, ref, rule_id=rule)
    unlisted = [r for r in external_rows if r[1] is None]
    if excluded is not None and unlisted:
        why = (
            f"{sum(int(r[5]) for r in unlisted)} damage events went to targets with no game ID "
            "(missing from the actor list or unidentified), "
            "so the encounter exclusions cannot be applied"
        )
        return RankingDamage(
            raw_e, external_e, unknown(why, ref, coverage=cov), tuple(actor_ids), by_target
        )
    ranked_total = external - sum(
        int(r[4]) for r in external_rows if excluded is not None and excluded(r[1], r[2])
    )
    return RankingDamage(
        raw_e,
        external_e,
        complete_or_unknown(
            ranked_total,
            cov,
            ref,
            rule_id=rule,
            params={"encounter_exclusions": exclusion_rule or "none"},
        ),
        tuple(actor_ids),
        by_target,
    )
