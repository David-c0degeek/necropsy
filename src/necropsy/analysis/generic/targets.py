"""Who the damage went to, and whether those targets belong to the encounter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
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


@dataclass(frozen=True, slots=True)
class TargetSplit:
    by_target: Evidenced[tuple[TargetDamage, ...]]
    native_damage: Evidenced[int]
    foreign_damage: Evidenced[int]


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
    native = sum(t.damage for t in split if is_native(t.game_id, t.name))
    foreign = sum(t.damage for t in split) - native
    return TargetSplit(
        by_target,
        complete_or_unknown(native, cov, ref),
        complete_or_unknown(foreign, cov, ref),
    )
