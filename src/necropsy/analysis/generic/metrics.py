"""Generic fight metrics for one actor (a Hunter or one of its pets).

Whole-fight totals, counts, cadences and absences are COMPLETE claims: they
need trusted coverage of the stream they read, otherwise they are UNKNOWN.
Individual events found in an incomplete stream are still reported, as an
explicitly partial observation.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.evidence import (
    CoverageRef,
    Evidenced,
    EvidenceRef,
    complete_or_unknown,
    observed,
    unknown,
)
from necropsy.snapshot.model import Direction

DEATH_RECAP_WINDOW_MS = 5000
DEATH_RECAP_HITS = 3


@dataclass(frozen=True, slots=True)
class Hit:
    t_s: float
    source_id: int | None
    ability_id: int | None
    amount: int


@dataclass(frozen=True, slots=True)
class Death:
    t_s: float
    killer_id: int | None
    killing_ability_id: int | None
    recent_hits: tuple[Hit, ...]


@dataclass(frozen=True, slots=True)
class DeathsFinding:
    """`complete` is True when the list is every death; otherwise it is what was seen."""

    deaths: Evidenced[tuple[Death, ...]]
    complete: bool


@dataclass(frozen=True, slots=True)
class ActivityWindow:
    first_damage_s: float | None
    """Seconds after fight start of the first damage event, or None if none."""
    last_damage_before_end_s: float | None
    """Seconds between the last damage event and fight end, or None if none."""


def _rows(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any]) -> list[tuple[Any, ...]]:
    return con.execute(sql, params).fetchall()


def _ref(
    pf: ParticipantFight,
    actor_id: int,
    rows: Iterable[tuple[Any, ...]],
    uid_col: int,
    copy_col: int,
    detail: str,
) -> EvidenceRef:
    return EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        actor_id,
        [(r[uid_col], int(r[copy_col])) for r in rows],
        detail=detail,
    )


def _coverage(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, actor_ids: list[int], d: Direction
) -> list[CoverageRef]:
    return [coverage(con, pf, a, d) for a in actor_ids]


def damage_by_ability(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, actor_ids: list[int]
) -> Evidenced[dict[int, int]]:
    """Damage done (event `amount`) per ability by the given actors over the whole fight."""
    rows = _rows(
        con,
        """
        SELECT ability_game_id, coalesce(amount, 0), event_uid, copy_index FROM events
        WHERE report_code = ? AND fight_id = ? AND type = 'damage'
          AND source_id IN (SELECT unnest(?::BIGINT[]))
        """,
        [pf.report_code, pf.fight_id, actor_ids],
    )
    totals: dict[int, int] = defaultdict(int)
    for ability, amount, _uid, _copy in rows:
        totals[int(ability)] += int(amount)
    ref = _ref(pf, actor_ids[0], rows, 2, 3, f"damage events by {actor_ids}")
    return complete_or_unknown(
        dict(totals),
        _coverage(con, pf, actor_ids, Direction.SOURCE),
        ref,
        note="sum of damage event amounts",
    )


def cast_times(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, actor_id: int, ability_ids: list[int]
) -> Evidenced[tuple[float, ...]]:
    """Seconds after fight start of every cast of the given abilities."""
    rows = _rows(
        con,
        """
        SELECT timestamp, event_uid, copy_index FROM events
        WHERE report_code = ? AND fight_id = ? AND type = 'cast' AND source_id = ?
          AND ability_game_id IN (SELECT unnest(?::BIGINT[]))
        ORDER BY timestamp, event_uid, copy_index
        """,
        [pf.report_code, pf.fight_id, actor_id, ability_ids],
    )
    times = tuple(pf.relative_s(int(r[0])) for r in rows)
    ref = _ref(pf, actor_id, rows, 1, 2, f"casts of {ability_ids}")
    return complete_or_unknown(
        times,
        _coverage(con, pf, [actor_id], Direction.SOURCE),
        ref,
        params={"abilities": tuple(ability_ids)},
    )


def per_minute(casts: Evidenced[tuple[float, ...]], pf: ParticipantFight) -> Evidenced[float]:
    if casts.value is None:
        return unknown("cast list unknown", *casts.refs, coverage=casts.coverage)
    minutes = pf.duration_ms / 60000.0
    return complete_or_unknown(
        len(casts.value) / minutes,
        casts.coverage,
        *casts.refs,
        note="casts per minute of fight duration",
    )


_ON = frozenset({"applybuff", "applydebuff"})
_OFF = frozenset({"removebuff", "removedebuff"})
_SUSTAIN = frozenset(
    {
        "refreshbuff",
        "refreshdebuff",
        "applybuffstack",
        "removebuffstack",
        "applydebuffstack",
        "removedebuffstack",
    }
)
_AURA_SQL = f"""
    SELECT ability_game_id, timestamp, type, event_uid, copy_index FROM events
    WHERE report_code = ? AND fight_id = ? AND target_id = ?
      AND ability_game_id IN (SELECT unnest(?::BIGINT[]))
      AND type IN ({", ".join(f"'{k}'" for k in sorted(_ON | _OFF | _SUSTAIN))})
    ORDER BY timestamp, event_uid, copy_index
"""  # noqa: S608 - the IN list is fixed event-type names, never input


def _union_ms(intervals: list[tuple[int, int]]) -> int:
    total = 0
    current: tuple[int, int] | None = None
    for start, end in sorted(intervals):
        if current is None or start > current[1]:
            if current is not None:
                total += current[1] - current[0]
            current = (start, end)
        else:
            current = (current[0], max(current[1], end))
    if current is not None:
        total += current[1] - current[0]
    return total


def aura_uptime(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    actor_id: int,
    aura_ids: list[int],
    active_at_start: frozenset[int] | None,
) -> Evidenced[float]:
    """Seconds during which at least one of the auras was on the actor, clipped to the fight.

    `active_at_start` is the set of auras present at the pull (from the starting
    aura snapshot), or None when that snapshot is missing. Each aura is tracked
    separately and the intervals are merged. An aura whose state cannot be
    settled — no starting snapshot and no events, or a refresh/stack event while
    it should be off — makes the result UNKNOWN.
    """
    rows = _rows(con, _AURA_SQL, [pf.report_code, pf.fight_id, actor_id, aura_ids])
    cov = [coverage(con, pf, actor_id, Direction.TARGET)]
    ref = _ref(pf, actor_id, rows, 3, 4, f"aura events {aura_ids}")
    if not cov[0].trusted:
        return unknown("target stream incomplete or untrustworthy", ref, coverage=cov)
    by_aura: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for ability, ts, kind, _uid, _copy in rows:
        by_aura[int(ability)].append((min(max(int(ts), pf.start_time), pf.end_time), kind))
    intervals: list[tuple[int, int]] = []
    for aura in aura_ids:
        events = by_aura.get(aura, [])
        if active_at_start is not None:
            on = aura in active_at_start
        elif events:
            on = events[0][1] not in _ON
        else:
            return unknown(f"state of aura {aura} at fight start is unknown", ref, coverage=cov)
        since: int | None = pf.start_time if on else None
        for ts, kind in events:
            if kind in _ON and since is None:
                since = ts
            elif kind in _OFF and since is not None:
                intervals.append((since, ts))
                since = None
            elif kind in _SUSTAIN and since is None:
                return unknown(
                    f"aura {aura} refreshed or stacked while it should be off", ref, coverage=cov
                )
        if since is not None:
            intervals.append((since, pf.end_time))
    return complete_or_unknown(
        _union_ms(intervals) / 1000.0, cov, ref, params={"auras": tuple(aura_ids)}
    )


def deaths(con: duckdb.DuckDBPyConnection, pf: ParticipantFight, actor_id: int) -> DeathsFinding:
    rows = _rows(
        con,
        """
        SELECT timestamp, killer_id, killing_ability_game_id, event_uid, copy_index FROM events
        WHERE report_code = ? AND fight_id = ? AND type = 'death' AND target_id = ?
        ORDER BY timestamp, event_uid, copy_index
        """,
        [pf.report_code, pf.fight_id, actor_id],
    )
    found: list[Death] = []
    for ts, killer, ability, _uid, _copy in rows:
        hits = _rows(
            con,
            """
            SELECT timestamp, source_id, ability_game_id, coalesce(amount, 0) FROM events
            WHERE report_code = ? AND fight_id = ? AND type = 'damage' AND target_id = ?
              AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp DESC, event_uid, copy_index LIMIT ?
            """,
            [
                pf.report_code,
                pf.fight_id,
                actor_id,
                int(ts) - DEATH_RECAP_WINDOW_MS,
                int(ts),
                DEATH_RECAP_HITS,
            ],
        )
        found.append(
            Death(
                t_s=pf.relative_s(int(ts)),
                killer_id=killer,
                killing_ability_id=ability,
                recent_hits=tuple(
                    Hit(pf.relative_s(int(h[0])), h[1], h[2], int(h[3])) for h in reversed(hits)
                ),
            )
        )
    ref = _ref(pf, actor_id, rows, 3, 4, "death events")
    cov = [coverage(con, pf, actor_id, Direction.TARGET)]
    if cov[0].trusted:
        return DeathsFinding(complete_or_unknown(tuple(found), cov, ref), complete=True)
    if found:
        return DeathsFinding(
            observed(tuple(found), ref, note="partial: the target stream is incomplete"),
            complete=False,
        )
    return DeathsFinding(
        unknown("target stream incomplete or untrustworthy", ref, coverage=cov), complete=False
    )


def activity_window(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, actor_id: int
) -> Evidenced[ActivityWindow]:
    rows = _rows(
        con,
        """
        SELECT min(timestamp), max(timestamp), count(*) FROM events
        WHERE report_code = ? AND fight_id = ? AND type = 'damage' AND source_id = ?
        """,
        [pf.report_code, pf.fight_id, actor_id],
    )
    first, last, count = rows[0]
    ref = EvidenceRef(
        pf.report_code,
        pf.fight_id,
        actor_id,
        "events",
        event_count=int(count),
        detail="first and last damage event",
    )
    window = ActivityWindow(
        first_damage_s=None if first is None else pf.relative_s(int(first)),
        last_damage_before_end_s=None if last is None else (pf.end_time - int(last)) / 1000.0,
    )
    return complete_or_unknown(window, [coverage(con, pf, actor_id, Direction.SOURCE)], ref)
