"""Direct boss melee pressure is context, not proof of an assigned tank job."""

from __future__ import annotations

from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.encounters import encounter_rules
from necropsy.analysis.evidence import Evidenced, complete_or_unknown, observed, unknown
from necropsy.analysis.generic import combat
from necropsy.raids import (
    ENCOUNTER_CONTEXT_PARTITIONS,
    ENCOUNTER_CONTEXT_ZONES,
    raid_for_encounter,
)
from necropsy.raids.naxxramas import RAID as NAXXRAMAS
from necropsy.snapshot.model import Direction
from necropsy.snapshot.v2 import FORMAT as V2_FORMAT


def applies(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> bool:
    """Keep the historical Naxx duty contract and seasonal rules separate.

    A Naxxramas capture gains duty context only when it carries whole-encounter
    scopes; its earlier actor-only captures keep their original behaviour.
    """
    meta = con.execute("SELECT zone_id, partition_id, format FROM snapshot_meta").fetchone()
    if meta is None:
        return False
    zone, partition, snapshot_format = meta
    return (
        zone in ENCOUNTER_CONTEXT_ZONES
        and partition in ENCOUNTER_CONTEXT_PARTITIONS
        and (zone != NAXXRAMAS.zone_id or snapshot_format == V2_FORMAT)
        and (raid_for_encounter(pf.encounter_id).zone_id == zone)
    )


def boss_melee(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, events: list[combat.CombatEvent]
) -> list[combat.CombatEvent]:
    rules = encounter_rules(
        "classic_era", raid_for_encounter(pf.encounter_id).slug, pf.encounter_id
    )
    bosses = {
        int(actor)
        for actor, game_id in con.execute(
            "SELECT actor_id, game_id FROM actors WHERE report_code=? AND type='NPC'",
            [pf.report_code],
        ).fetchall()
        if game_id is not None and rules.is_boss(int(game_id))
    }
    return [
        event
        for event in events
        if event.kind == "damage"
        and event.target_id == pf.actor_id
        and event.source_id in bosses
        and (event.name == "Melee" or event.raw.get("melee") is True)
    ]


def context(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> dict[str, Any]:
    events = boss_melee(con, pf, combat.event_rows(con, pf))
    ref = combat.event_ref(pf, events, "direct boss melee events against this actor")
    return {
        "player": pf.player,
        "report_code": pf.report_code,
        "fight_id": pf.fight_id,
        "actor_id": pf.actor_id,
        "melee_events": complete_or_unknown(
            len(events),
            [coverage(con, pf, pf.actor_id, Direction.TARGET)],
            ref,
            note="Direct boss melee event count; includes avoided or fully absorbed swings.",
        ),
        "observed_melee_times_s": observed([event.t_s for event in events], ref)
        if events
        else None,
        "limitation": "Boss melee pressure does not establish assigned tank duty, threat quality "
        "or a continuous tanking window. Confirm assignments before comparing throughput.",
    }


def guard_action_duty[T](
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    events: list[combat.CombatEvent],
    role: Evidenced[T],
    *,
    tank_actions: bool,
) -> Evidenced[T]:
    if not tank_actions and applies(con, pf):
        pressure = boss_melee(con, pf, events)
        if len(pressure) >= 3:
            return unknown(
                "Repeated boss melee pressure conflicts with a simple action-based duty; "
                "the narrow tank-cast list cannot resolve assignment.",
                combat.event_ref(pf, pressure, "boss melee pressure with unresolved duty"),
            )
    return role
