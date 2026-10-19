"""Recorded encounter-wide mechanic presence for labelling fight comparisons.

A count is known only under a certified complete encounter event set; otherwise
it stays unknown. Presence or absence describes the recorded fight, not why a
mechanic did or did not occur, and never grades either fight.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import duckdb

from necropsy.analysis.context import ParticipantFight
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceRef,
    ScopedCoverageRef,
    complete_or_unknown,
    observed,
    unknown,
)
from necropsy.normalize.coverage import has_complete_encounter_event_set
from necropsy.raids import raid_for_encounter
from necropsy.rules import load_rules


@dataclass(frozen=True, slots=True)
class MechanicPresence:
    rule: str
    label: str
    ability_id: int
    event_type: str
    applications: Evidenced[int]
    source: str
    retrieved: str


def mechanic_presence(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> tuple[MechanicPresence, ...]:
    raid = raid_for_encounter(pf.encounter_id)
    policies = (
        load_rules("classic_era", f"zones/{raid.slug}_guidance")
        .get("mechanic_presence", {})
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
    actors = {
        actor: (kind, game_id)
        for actor, kind, game_id in con.execute(
            "SELECT actor_id,type,game_id FROM actors WHERE report_code=?", [pf.report_code]
        ).fetchall()
    }
    result = []
    for policy in policies:
        wanted = {int(g) for g in policy["caster_game_ids"]}
        rows = con.execute(
            """SELECT source_id,raw,event_uid,copy_index FROM events
               WHERE report_code=? AND fight_id=? AND type=? AND ability_game_id=?
                 AND timestamp BETWEEN ? AND ?
               ORDER BY timestamp,event_uid,copy_index""",
            [
                pf.report_code,
                pf.fight_id,
                policy["event_type"],
                int(policy["ability_id"]),
                pf.start_time,
                pf.end_time,
            ],
        ).fetchall()
        matched = []
        unresolved = []
        for source, raw, uid, copy in rows:
            # Only a consistent source bound to a cataloged actor classifies the
            # event; the spell ID alone never makes it the boss's.
            kind, game_id = actors.get(source, (None, None))
            raw_source = (json.loads(raw) if isinstance(raw, str) else raw).get("sourceID")
            if (
                source is None
                or raw_source != source
                or kind is None
                or (kind == "NPC" and game_id is None)
            ):
                unresolved.append((uid, copy))
            elif kind == "NPC" and game_id in wanted:
                matched.append((uid, copy))
        ref = EvidenceRef.events(
            pf.report_code,
            pf.fight_id,
            None,
            matched + unresolved,
            detail=f"{policy['label']} {policy['event_type']} events from the boss",
        )
        result.append(
            MechanicPresence(
                policy["rule"],
                policy["label"],
                int(policy["ability_id"]),
                policy["event_type"],
                unknown(
                    f"{len(unresolved)} {policy['label']} event(s) have no consistent "
                    "cataloged caster",
                    ref,
                    coverage=[cov],
                )
                if unresolved
                else complete_or_unknown(len(matched), [cov], ref, rule_id=policy["rule"]),
                policy["source"],
                policy["retrieved"],
            )
        )
    return tuple(result)


DEMAND = {"healer": "healing demand", "dps": "damage opportunities", "tank": "incoming damage"}


def _join(labels: list[str]) -> str:
    return labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + f" or {labels[-1]}"


def reference_statement(
    yours_s: float,
    reference_s: float,
    reference: tuple[MechanicPresence, ...],
    role: str,
) -> str:
    """Duration and recorded-mechanic context; never a cause or a verdict."""
    parts = [f"Reference fight: {reference_s:.2f}s; your fight: {yours_s:.2f}s."]
    absent = [m.label for m in reference if m.applications.value == 0]
    unmeasured = [m.label for m in reference if m.applications.value is None]
    if absent:
        parts.append(f"This reference records no {_join(absent)} transitions.")
    if unmeasured:
        parts.append(f"{_join(unmeasured)} transitions are unmeasured for this reference.")
    quality = "better healing" if role == "healer" else "better play"
    parts.append(
        f"Different durations and observed mechanics can change {DEMAND[role]}; these "
        f"whole-fight comparisons do not establish {quality} or matching assignments."
    )
    return " ".join(parts)


def other_enemies(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, boss_game_ids: frozenset[int]
) -> Evidenced[tuple[str, ...]]:
    """Recorded non-boss enemies in the fight roster; their role in the fight is unknown."""
    row = con.execute(
        "SELECT enemy_npcs FROM fights WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchone()
    ref = EvidenceRef(pf.report_code, pf.fight_id, None, "fights", detail="fight enemy roster")
    roster = None if row is None or row[0] is None else row[0]
    if isinstance(roster, str):
        roster = json.loads(roster)
    if not isinstance(roster, list) or not roster:
        return unknown("the fight records no enemy roster", ref)
    names = dict(
        con.execute(
            "SELECT actor_id,name FROM actors WHERE report_code=?", [pf.report_code]
        ).fetchall()
    )
    others = []
    for npc in roster:
        if npc.get("gameID") in boss_game_ids:
            continue
        name = names.get(npc.get("id"))
        if name is None:
            return unknown("an enemy roster entry has no catalog name", ref)
        others.append(name)
    return observed(tuple(sorted(set(others))), ref)
