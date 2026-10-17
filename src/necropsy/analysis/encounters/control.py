"""Source-owned control applications, with NPC instances retained as evidence."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.encounters import duty
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceRef,
    complete_or_unknown,
    observed,
    unknown,
)
from necropsy.analysis.generic import combat
from necropsy.raids import raid_for_encounter
from necropsy.rules import load_rules
from necropsy.snapshot.model import Direction


@dataclass(frozen=True, slots=True)
class ControlApplications:
    rule: str
    label: str
    source: str
    retrieved: str
    applications: Evidenced[int]
    observations: Evidenced[tuple[tuple[float, int, int | None, int], ...]]
    limitation: str = (
        "Recorded control applications, separate from casts. NPC actor and instance identity "
        "are retained where recorded. Actor-source coverage does not establish full add control "
        "uptime, break causes, assigned targets or available opportunities. A zero count is "
        "not a failed duty or a utility score."
    )


def applications(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> tuple[ControlApplications, ...]:
    if not duty.applies(con, pf):
        return ()
    meta = con.execute("SELECT subject_class_id FROM snapshot_meta").fetchone()
    policies = (
        load_rules("classic_era", f"zones/{raid_for_encounter(pf.encounter_id).slug}_guidance")
        .get("control", {})
        .get(pf.encounter_id, ())
    )
    policies = [p for p in policies if meta and meta[0] in p["classes"]]
    if not policies:
        return ()
    identities: dict[int, set[tuple[str | None, int | None]]] = {}
    for actor, kind, game in con.execute(
        "SELECT actor_id,type,game_id FROM actors WHERE report_code=?", [pf.report_code]
    ).fetchall():
        identities.setdefault(actor, set()).add((kind, game))
    events = combat.event_rows(con, pf)
    result = []
    for policy in policies:
        rows, unresolved = [], []
        for event in events:
            if event.kind != "applydebuff" or event.source_id != pf.actor_id:
                continue
            ability = (
                event.ability_id in policy["ability_ids"] if event.ability_id is not None else None
            )
            candidates = identities.get(event.target_id) if event.target_id is not None else None
            identity = next(iter(candidates)) if candidates and len(candidates) == 1 else None
            target = (
                None
                if identity is None or identity[0] is None
                else False
                if identity[0] != "NPC"
                else identity[1] in policy["target_game_ids"]
                if identity[1] is not None
                else None
            )
            if ability is False or target is False:
                continue
            if ability is None or target is None:
                unresolved.append(event)
            else:
                rows.append(event)
        refs = (
            combat.event_ref(pf, rows, "source-owned control applications"),
            EvidenceRef(pf.report_code, pf.fight_id, None, "actors", detail="control NPC identity"),
        )
        ambiguity = combat.event_ref(pf, unresolved, "unresolved control recipient identity")
        count = (
            unknown(
                "required control ability or recipient identity is unresolved", *refs, ambiguity
            )
            if unresolved
            else complete_or_unknown(
                len(rows),
                [coverage(con, pf, pf.actor_id, Direction.SOURCE)],
                *refs,
                rule_id=policy["rule"],
            )
        )
        values = tuple(
            (
                e.t_s,
                int(e.target_id),
                e.raw.get("targetInstance") if type(e.raw.get("targetInstance")) is int else None,
                int(e.ability_id),
            )
            for e in rows
            if e.target_id is not None and e.ability_id is not None
        )
        observations = (
            observed(values, *refs)
            if rows
            else unknown(
                "required control ability or recipient identity is unresolved", *refs, ambiguity
            )
            if unresolved
            else complete_or_unknown((), [coverage(con, pf, pf.actor_id, Direction.SOURCE)], *refs)
        )
        result.append(
            ControlApplications(
                policy["rule"],
                policy["label"],
                policy["source"],
                policy["retrieved"],
                count,
                observations,
            )
        )
    return tuple(result)
