"""Shared actor combat events and coverage-qualified totals, independent of class."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceRef,
    complete_or_unknown,
    observed,
    unknown,
)
from necropsy.snapshot.model import Direction


@dataclass(frozen=True, slots=True)
class CombatEvent:
    timestamp: int
    t_s: float
    kind: str
    source_id: int | None
    target_id: int | None
    ability_id: int | None
    name: str | None
    amount: int | None
    overheal: int | None
    uid: str
    copy: int
    raw: dict[str, Any]


def event_ref(pf: ParticipantFight, rows: list[CombatEvent], detail: str) -> EvidenceRef:
    return EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        pf.actor_id,
        [(r.uid, r.copy) for r in rows],
        detail=detail,
    )


def event_rows(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> list[CombatEvent]:
    rows = con.execute(
        """SELECT e.timestamp, e.type, e.source_id, e.target_id, e.ability_game_id,
                  a.name, e.amount, e.overheal, e.event_uid, e.copy_index, e.raw
           FROM events e LEFT JOIN abilities a
             ON a.report_code = e.report_code AND a.game_id = e.ability_game_id
           WHERE e.report_code = ? AND e.fight_id = ?
             AND (e.source_id = ? OR e.target_id = ?)
             AND e.timestamp BETWEEN ? AND ?
           ORDER BY e.timestamp, e.event_uid, e.copy_index""",
        [pf.report_code, pf.fight_id, pf.actor_id, pf.actor_id, pf.start_time, pf.end_time],
    ).fetchall()
    return [
        CombatEvent(
            int(ts),
            pf.relative_s(int(ts)),
            kind,
            source,
            target,
            ability,
            name,
            amount,
            overheal,
            uid,
            int(copy),
            json.loads(raw) if isinstance(raw, str) else raw,
        )
        for ts, kind, source, target, ability, name, amount, overheal, uid, copy, raw in rows
    ]


def event_totals(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    events: list[CombatEvent],
) -> tuple[dict[str, Evidenced[float]], Evidenced[dict[int, int]], Evidenced[dict[int, int]]]:
    source = coverage(con, pf, pf.actor_id, Direction.SOURCE)
    target = coverage(con, pf, pf.actor_id, Direction.TARGET)
    heals = [e for e in events if e.kind == "heal" and e.source_id == pf.actor_id]
    damage = [e for e in events if e.kind == "damage" and e.source_id == pf.actor_id]
    incoming = [e for e in events if e.kind == "damage" and e.target_id == pf.actor_id]
    support = [e for e in events if e.kind == "heal" and e.target_id == pf.actor_id]
    seconds = pf.duration_ms / 1000
    values: dict[str, Evidenced[float]] = {}
    for name, rows, cov in (
        ("damage", damage, source),
        ("effective_healing", heals, source),
        ("incoming_damage", incoming, target),
        ("healing_received", support, target),
    ):
        ref = event_ref(pf, rows, name)
        if any(e.amount is None for e in rows):
            values[name] = unknown(f"{name} has events without amount", ref)
        else:
            values[name] = complete_or_unknown(
                float(sum(e.amount or 0 for e in rows)),
                [cov],
                ref,
                note="sum of WCL event amount; effective amount excludes overheal",
            )
        total = values[name]
        values[f"{name}_per_second"] = (
            complete_or_unknown(total.value / seconds, [cov], *total.refs)
            if total.value is not None and seconds > 0
            else unknown(f"{name} rate unavailable")
        )
    ref = event_ref(pf, heals, "overhealing")
    # WCL heal payloads are sparse: absent overheal means zero. Explicit
    # null/malformed values remain unknown, as does incomplete source coverage.
    # See WoWAnalyzer's HealEvent and HealingDone._addHealing (optional field,
    # default 0): https://github.com/WoWAnalyzer/WoWAnalyzer/tree/midnight/src/parser
    overheals = [e.raw.get("overheal", 0) for e in heals]
    values["overhealing"] = (
        unknown("heal events contain null, malformed or negative overheal", ref)
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in overheals)
        else complete_or_unknown(
            float(sum(overheals)),
            [source],
            ref,
            rule_id="wcl-sparse-overheal-v1",
            note="WCL omits zero overheal; explicit null or invalid values remain unknown",
        )
    )
    effective, over = values["effective_healing"].value, values["overhealing"].value
    values["overhealing_pct"] = (
        complete_or_unknown(100 * over / (effective + over), [source], ref)
        if effective is not None and over is not None and effective + over > 0
        else unknown("no known nonzero total healing denominator", ref)
    )
    for field in ("absorbed", "blocked", "resisted", "mitigated", "unmitigatedAmount"):
        ref = event_ref(pf, incoming, f"incoming damage field {field}")
        readings = [e.raw.get(field) for e in incoming]
        values[f"incoming_{field}"] = (
            unknown(f"incoming events omit {field}; missing is not zero", ref)
            if any(type(v) not in (int, float) for v in readings)
            else complete_or_unknown(
                float(sum(v for v in readings if v is not None)), [target], ref
            )
        )

    def by_target(rows: list[CombatEvent], detail: str) -> Evidenced[dict[int, int]]:
        ref = event_ref(pf, rows, detail)
        if any(e.target_id is None or e.amount is None for e in rows):
            return unknown("target or amount missing from event", ref)
        grouped: dict[int, int] = defaultdict(int)
        for event in rows:
            assert event.target_id is not None and event.amount is not None
            grouped[event.target_id] += event.amount
        return complete_or_unknown(dict(grouped), [source], ref)

    return values, by_target(heals, "healing by target"), by_target(damage, "damage by target")


def actor_catalog(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, events: list[CombatEvent]
) -> Evidenced[dict[int, dict[str, Any]]]:
    actor_ids = sorted(
        {aid for e in events for aid in (e.source_id, e.target_id) if aid is not None and aid > 0}
    )
    actors = con.execute(
        """SELECT actor_id, name, type, sub_type, game_id FROM actors
           WHERE report_code = ? AND actor_id IN (SELECT unnest(?::BIGINT[]))""",
        [pf.report_code, actor_ids],
    ).fetchall()
    return observed(
        {
            int(aid): {"name": name, "type": kind, "sub_type": sub, "game_id": game_id}
            for aid, name, kind, sub, game_id in actors
        },
        EvidenceRef(pf.report_code, None, None, "actors", detail="report actor catalog"),
    )


def resource_readings(
    pf: ParticipantFight, events: list[CombatEvent]
) -> tuple[dict[str, Any], ...]:
    resources = []
    for event in events:
        raw = event.raw
        side = raw.get("resourceActor")
        if type(side) is not int:
            continue
        resource_actor = event.source_id if side == 1 else event.target_id if side == 2 else None
        if resource_actor != pf.actor_id:
            continue
        for resource in raw.get("classResources") or []:
            reading = (
                observed(resource, event_ref(pf, [event], "actor resource reading"))
                if type(resource.get("max")) in (int, float) and resource["max"] > 0
                else unknown(
                    "resource capacity is missing or zero; no usable resource reading",
                    event_ref(pf, [event], "resource payload"),
                )
            )
            resources.append(
                {
                    "t_s": event.t_s,
                    "reading": resource,
                    "evidence": reading,
                    "event_uid": event.uid,
                    "copy": event.copy,
                }
            )
    return tuple(resources)
