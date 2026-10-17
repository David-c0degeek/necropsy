"""Qualify source healing by recorded friendly roster and encounter boss identity."""

from __future__ import annotations

import json
import math
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.evidence import Evidenced, EvidenceRef, complete_or_unknown, unknown
from necropsy.analysis.generic.combat import CombatEvent, event_ref
from necropsy.snapshot.model import Direction


def recipient_metrics(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    events: list[CombatEvent],
    boss_game_ids: frozenset[int],
    raw_metrics: dict[str, Evidenced[float]],
) -> dict[str, Evidenced[float]]:
    """Keep raw sums; unknown targets cannot supply a friendly-healing zero."""
    row = con.execute(
        "SELECT friendly_players, friendly_pets FROM fights WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchone()

    def decoded(value: Any) -> Any:
        return json.loads(value) if isinstance(value, str) else value

    players, pets = (decoded(v) for v in row) if row else (None, None)
    friendly = {pf.actor_id}
    if isinstance(players, list):
        friendly.update(p for p in players if type(p) is int)
    if isinstance(pets, list):
        friendly.update(p["id"] for p in pets if isinstance(p, dict) and type(p.get("id")) is int)
    bosses = {
        actor
        for actor, game_id in con.execute(
            "SELECT actor_id, game_id FROM actors WHERE report_code=? AND type='NPC'",
            [pf.report_code],
        ).fetchall()
        if game_id in boss_game_ids
    }
    heals = [e for e in events if e.kind == "heal" and e.source_id == pf.actor_id]
    supported, hostile, unresolved = [], [], []
    for event in heals:
        if event.target_id in friendly and event.target_id not in bosses:
            supported.append(event)
        elif event.target_id in bosses and event.target_id not in friendly:
            hostile.append(event)
        else:
            unresolved.append(event)
    cov = [coverage(con, pf, pf.actor_id, Direction.SOURCE)]
    roster_ref = EvidenceRef(
        pf.report_code,
        pf.fight_id,
        pf.actor_id,
        "fights",
        detail="friendlyPlayers/friendlyPets recipient roster",
    )
    boss_ref = EvidenceRef(
        pf.report_code,
        pf.fight_id,
        None,
        "actors",
        detail=f"NPC game IDs in encounter boss policy {sorted(boss_game_ids)}",
    )
    result = {
        **raw_metrics,
        "raw_source_healing": raw_metrics["effective_healing"],
        "raw_source_healing_per_second": raw_metrics["effective_healing_per_second"],
    }

    def amount(name: str, rows: list[CombatEvent], uncertain: bool) -> Evidenced[float]:
        refs = (event_ref(pf, heals if uncertain else rows, name), roster_ref, boss_ref)
        if uncertain:
            return unknown(
                "healing recipient is unresolved or conflicts with the friendly roster", *refs
            )
        if any(e.amount is None or e.amount < 0 for e in rows):
            return unknown("healing event amount is missing or negative", *refs)
        return complete_or_unknown(
            float(sum(e.amount or 0 for e in rows)),
            cov,
            *refs,
            rule_id="healing-recipients-v1",
            note="Heal event amount only; absorption events and overheal are separate. "
            "Recipient classification is not a WCL ranking reconciliation or quality score.",
        )

    for name, rows, uncertain in (
        ("effective_healing", supported, bool(unresolved)),
        ("healing_to_bosses", hostile, bool(unresolved)),
        ("unclassified_healing", unresolved, False),
    ):
        value = amount(name, rows, uncertain)
        result[name] = value
        result[f"{name}_per_second"] = (
            complete_or_unknown(
                value.value * 1000 / pf.duration_ms,
                cov,
                *value.refs,
                rule_id="healing-recipients-v1",
            )
            if value.value is not None and pf.duration_ms > 0
            else unknown("recipient-qualified healing rate unavailable", *value.refs)
        )
    over = [e.raw.get("overheal", 0) for e in supported]
    refs = (
        event_ref(pf, heals if unresolved else supported, "friendly recipient overhealing"),
        roster_ref,
        boss_ref,
    )
    result["overhealing"] = (
        unknown("friendly healing recipients or overheal fields are unresolved", *refs)
        if unresolved
        or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in over)
        else complete_or_unknown(float(sum(over)), cov, *refs, rule_id="healing-recipients-v1")
    )
    effective, overheal = result["effective_healing"].value, result["overhealing"].value
    result["overhealing_pct"] = (
        complete_or_unknown(
            100 * overheal / (effective + overheal), cov, *refs, rule_id="healing-recipients-v1"
        )
        if effective is not None and overheal is not None and effective + overheal > 0
        else unknown("no known nonzero friendly healing denominator", *refs)
    )
    return result
