"""Generic fight metrics for one player or pet actor.

Whole-fight totals, counts, cadences and absences are COMPLETE claims: they
need trusted coverage of the stream they read, otherwise they are UNKNOWN.
Individual events found in an incomplete stream are still reported, as an
explicitly partial observation.
"""

from __future__ import annotations

import itertools
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
        ORDER BY timestamp, event_uid, copy_index
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


def ability_counts(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
) -> Evidenced[dict[str, int]]:
    """All recorded actor casts, including spells, melee skills, shots and items.

    Uses normalized event occurrences, so repeated page copies are not new uses.
    A missing action means zero only with trusted actor source coverage.
    """
    rows = _rows(
        con,
        """
        SELECT a.name, e.ability_game_id, e.event_uid, e.copy_index FROM events e
        LEFT JOIN abilities a ON a.report_code=e.report_code AND a.game_id=e.ability_game_id
        WHERE e.report_code=? AND e.fight_id=? AND e.source_id=? AND e.type='cast'
        ORDER BY e.timestamp, e.event_uid, e.copy_index
    """,
        [pf.report_code, pf.fight_id, pf.actor_id],
    )
    counts: dict[str, int] = defaultdict(int)
    for name, ability, _, _ in rows:
        counts[name or f"Ability {ability} (name unknown)"] += 1
    return complete_or_unknown(
        dict(sorted(counts.items())),
        _coverage(con, pf, [pf.actor_id], Direction.SOURCE),
        _ref(pf, pf.actor_id, rows, 2, 3, "actor ability-use counts"),
        note="Recorded cast events; excludes passive damage ticks, "
        "swings without cast events and pet actions.",
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


def _merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def aura_intervals(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    actor_id: int,
    aura_ids: list[int],
    active_at_start: frozenset[int] | None,
) -> Evidenced[tuple[tuple[int, int], ...]]:
    """Merged (start, end) timestamps when at least one of the auras was on the actor.

    `active_at_start` is the set of auras present at the pull (from the starting
    aura snapshot), or None when that snapshot is missing. Each aura is tracked
    separately and the intervals are merged. An aura whose state cannot be
    settled — no starting snapshot and no events, or a refresh/stack event while
    it should be off — makes the result UNKNOWN. Intervals are clipped to the fight.
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
        tuple(_merge(intervals)), cov, ref, params={"auras": tuple(aura_ids)}
    )


def observed_aura_windows(
    start_time: int,
    end_time: int,
    events: Iterable[tuple[int, str]],
    initial_state: bool | None = None,
) -> list[tuple[int, int, bool | None]]:
    """Three-state intervals for one exact entity and aura; never guess initial state.

    Callers establish identity, lifetime and coverage. Conflicting simultaneous
    transitions and lifecycle resets remain unknown, independent of hash order.
    A sustain while definitively inactive invalidates the preceding interval.
    """
    state = initial_state
    since = start_time
    result = []
    relevant = sorted((ts, kind) for ts, kind in events if start_time <= ts <= end_time)
    for ts, group in itertools.groupby(relevant, key=lambda event: event[0]):
        kinds = {kind for _, kind in group}
        previous = state
        if "stateunknown" in kinds or (kinds & _OFF and kinds & (_ON | _SUSTAIN)):
            state = None
        elif kinds & _ON:
            state = True
        elif kinds & _OFF:
            state = False
        elif state is False:
            previous, state = None, None
        if since < ts:
            result.append((since, ts, previous))
        since = ts
    if since < end_time:
        result.append((since, end_time, state))
    return result


def aura_states(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    actor_id: int,
    aura_ids: list[int],
    active_at_start: frozenset[int] | None,
    *,
    observed_only: bool = False,
    event_kinds: frozenset[str] | None = None,
) -> Evidenced[tuple[tuple[int, int, bool | None], ...]]:
    """Union of active, inactive and uncertain windows, without guessing missing state.

    A known active member proves the union active even if another is uncertain.
    A definitive apply/remove event settles subsequent state. Contradictory
    refreshes invalidate the preceding segment and remain uncertain until a
    definitive transition. Existing whole-fight uptime calculations stay separate.
    `observed_only` keeps missing initial state unknown, ignores out-of-fight
    transitions and leaves simultaneous contradictory transitions unresolved.
    """
    rows = _rows(con, _AURA_SQL, [pf.report_code, pf.fight_id, actor_id, aura_ids])
    if event_kinds is not None:
        rows = [row for row in rows if row[2] in event_kinds]
    if observed_only:
        rows = [row for row in rows if pf.start_time <= row[1] <= pf.end_time]
        resets = _rows(
            con,
            "SELECT NULL, timestamp, 'stateunknown', event_uid, copy_index FROM events "
            "WHERE report_code=? AND fight_id=? AND target_id=? "
            "AND type IN ('death', 'resurrect') AND timestamp BETWEEN ? AND ?",
            [pf.report_code, pf.fight_id, actor_id, pf.start_time, pf.end_time],
        )
        rows = sorted([*rows, *resets], key=lambda row: (row[1], row[3], row[4]))
    cov = [coverage(con, pf, actor_id, Direction.TARGET)]
    ref = _ref(pf, actor_id, rows, 3, 4, f"three-state aura windows {aura_ids}")
    timelines = []
    for aura in aura_ids:
        events = [
            (int(ts), kind)
            for ability, ts, kind, _, _ in rows
            if ability == aura or kind == "stateunknown"
        ]
        state: bool | None = (
            aura in active_at_start
            if active_at_start is not None
            else events[0][1] not in _ON
            if events and not observed_only
            else None
        )
        start = pf.start_time
        segments = []
        if observed_only:
            segments = observed_aura_windows(pf.start_time, pf.end_time, events, state)
        else:
            for ts, kind in events:
                ts = min(max(ts, pf.start_time), pf.end_time)
                previous = state
                if kind == "ambiguous":
                    state = None
                elif kind in _ON:
                    state = True
                elif kind in _OFF:
                    state = False
                elif state is False:
                    previous, state = None, None
                if start < ts:
                    segments.append((start, ts, previous))
                start = ts
            if start < pf.end_time:
                segments.append((start, pf.end_time, state))
        timelines.append(segments)
    boundaries = sorted(
        {pf.start_time, pf.end_time}
        | {t for segments in timelines for lo, hi, _ in segments for t in (lo, hi)}
    )
    result = []
    for lo, hi in itertools.pairwise(boundaries):
        states = [state for segments in timelines for a, b, state in segments if a <= lo < b]
        union = True if True in states else None if None in states else False
        result.append((lo, hi, union))
    return complete_or_unknown(
        tuple(result),
        cov,
        ref,
        rule_id="aura-observed-windows-v1" if observed_only else "aura-state-windows-v1",
    )


def aura_uptime(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    actor_id: int,
    aura_ids: list[int],
    active_at_start: frozenset[int] | None,
) -> Evidenced[float]:
    """Seconds during which at least one of the auras was on the actor (see aura_intervals)."""
    intervals = aura_intervals(con, pf, actor_id, aura_ids, active_at_start)
    if intervals.value is None:
        return unknown(
            intervals.note or "aura intervals unknown", *intervals.refs, coverage=intervals.coverage
        )
    total = sum(end - start for start, end in intervals.value)
    return complete_or_unknown(
        total / 1000.0, intervals.coverage, *intervals.refs, params={"auras": tuple(aura_ids)}
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
