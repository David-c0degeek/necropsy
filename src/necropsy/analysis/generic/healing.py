"""Qualify source healing by recorded friendly roster and encounter boss identity."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import replace
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceRef,
    ScopedCoverageRef,
    complete_or_unknown,
    observed,
    unknown,
)
from necropsy.analysis.generic.combat import CombatEvent, event_ref
from necropsy.normalize.coverage import has_complete_encounter_event_set
from necropsy.snapshot.model import Direction


def recipient_groups(
    rows: list[CombatEvent], friendly: set[int], bosses: set[int]
) -> tuple[list[CombatEvent], list[CombatEvent], list[CombatEvent]]:
    """Partition qualified source effects without guessing unresolved recipients."""
    supported, hostile, unresolved = [], [], []
    for event in rows:
        raw_target = event.raw.get("targetID", event.target_id)
        if type(raw_target) is not int or raw_target != event.target_id:
            unresolved.append(event)
        elif event.target_id in friendly and event.target_id not in bosses:
            supported.append(event)
        elif event.target_id in bosses and event.target_id not in friendly:
            hostile.append(event)
        else:
            unresolved.append(event)
    return supported, hostile, unresolved


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
    absorbs = [e for e in events if e.kind == "absorbed" and e.source_id == pf.actor_id]
    supported, hostile, unresolved = recipient_groups(heals, friendly, bosses)
    shields, hostile_shields, unresolved_shields = recipient_groups(absorbs, friendly, bosses)
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

    def valid_sources(rows: list[CombatEvent]) -> bool:
        return all(
            type(e.raw.get("sourceID", e.source_id)) is int
            and e.raw.get("sourceID", e.source_id) == pf.actor_id
            for e in rows
        )

    def amount(
        name: str,
        rows: list[CombatEvent],
        uncertain: bool,
        relevant: list[CombatEvent],
    ) -> Evidenced[float]:
        refs = (event_ref(pf, relevant if uncertain else rows, name), roster_ref, boss_ref)
        if not valid_sources(relevant):
            return unknown("support source identity is malformed", *refs, coverage=cov)
        if uncertain:
            return unknown(
                "healing or absorption recipient is unresolved or conflicts with "
                "the friendly roster",
                *refs,
            )

        def valid_amount(e: CombatEvent) -> bool:
            raw_amount = e.raw.get("amount", e.amount)
            return (
                isinstance(raw_amount, int | float)
                and not isinstance(raw_amount, bool)
                and math.isfinite(raw_amount)
                and raw_amount >= 0
                and raw_amount == e.amount
            )

        if any(not valid_amount(e) for e in rows):
            return unknown("support event amount is missing, invalid or coerced", *refs)
        return complete_or_unknown(
            float(sum(e.amount or 0 for e in rows)),
            cov,
            *refs,
            rule_id="healing-recipients-v1",
            note=(
                "Source-owned absorbed event amount, separate from incoming damage mitigation. "
                if relevant is absorbs
                else "Heal event amount only; absorption events and overheal are separate. "
            )
            + "Recipient classification is not a WCL ranking reconciliation or quality score.",
        )

    for name, rows, uncertain, relevant in (
        ("raw_source_healing", heals, False, heals),
        ("effective_healing", supported, bool(unresolved), heals),
        ("healing_to_bosses", hostile, bool(unresolved), heals),
        ("unclassified_healing", unresolved, False, heals),
        ("raw_source_absorption", absorbs, False, absorbs),
        ("effective_absorption", shields, bool(unresolved_shields), absorbs),
        ("absorption_to_bosses", hostile_shields, bool(unresolved_shields), absorbs),
        ("unclassified_absorption", unresolved_shields, False, absorbs),
    ):
        value = amount(name, rows, uncertain, relevant)
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
    heal, absorb = result["effective_healing"], result["effective_absorption"]
    combined_refs = (*heal.refs, *absorb.refs)
    result["healing_and_absorption"] = (
        complete_or_unknown(
            heal.value + absorb.value,
            cov,
            *combined_refs,
            rule_id="friendly-healing-and-absorption-v1",
            note="Friendly actor healing plus credited absorption, excluding overheal. "
            "Pet/guardian contributions are not added. This is not a validated WCL HPS "
            "reconstruction or healing quality score.",
        )
        if heal.value is not None and absorb.value is not None
        else unknown("friendly healing or absorption is unresolved", *combined_refs, coverage=cov)
    )
    combined = result["healing_and_absorption"]
    result["healing_and_absorption_per_second"] = (
        complete_or_unknown(
            combined.value * 1000 / pf.duration_ms,
            cov,
            *combined.refs,
            rule_id="friendly-healing-and-absorption-v1",
        )
        if combined.value is not None and pf.duration_ms > 0
        else unknown("combined friendly support rate unavailable", *combined.refs, coverage=cov)
    )
    over = [e.raw.get("overheal", 0) for e in supported]
    refs = (
        event_ref(pf, heals if unresolved else supported, "friendly recipient overhealing"),
        roster_ref,
        boss_ref,
    )
    result["overhealing"] = (
        unknown("friendly healing source, recipients or overheal fields are unresolved", *refs)
        if not valid_sources(heals)
        or unresolved
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


ABSORPTION_RULE = "friendly-absorption-by-ability-v1"
ABSORPTION_LIMITATION = (
    "Recorded source-attributed absorption effects, separate from casts, healing quality, "
    "equipment causes and assignments. Self-protection and other credited abilities remain "
    "separate from Power Word: Shield. These are not prevented-damage, mana-efficiency or "
    "WCL ranking estimates."
)


def _absorption_roster(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, boss_game_ids: frozenset[int]
) -> tuple[set[int], set[int], dict[int, str | None]] | None:
    fights = con.execute(
        "SELECT encounter_id,start_time,end_time,friendly_players,friendly_pets FROM fights "
        "WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchall()
    if len(fights) != 1 or fights[0][:3] != (pf.encounter_id, pf.start_time, pf.end_time):
        return None
    rows = con.execute(
        "SELECT actor_id,type,sub_type,name,game_id FROM actors WHERE report_code=?",
        [pf.report_code],
    ).fetchall()
    catalog = {r[0]: r for r in rows}
    if len(catalog) != len(rows) or catalog.get(pf.actor_id, (None, None, None))[1:3] != (
        "Player",
        "Priest",
    ):
        return None
    players, pets = (json.loads(v) if isinstance(v, str) else v for v in fights[0][3:])
    if (
        not isinstance(players, list)
        or not players
        or any(type(p) is not int or p < 1 for p in players)
        or len(set(players)) != len(players)
        or pf.actor_id not in players
        or any(catalog.get(p, (None, None))[1] != "Player" for p in players)
        or not isinstance(pets, list)
    ):
        return None
    pet_ids: set[int] = set()
    for pet in pets:
        if (
            not isinstance(pet, dict)
            or type(pet.get("id")) is not int
            or pet["id"] < 1
            or pet["id"] in pet_ids
            or pet["id"] in players
            or catalog.get(pet["id"], (None, None))[1] != "Pet"
            or type(pet.get("gameID")) is not int
            or pet["gameID"] < 1
            or catalog[pet["id"]][4] != pet["gameID"]
            or (
                pet.get("petOwner") is not None
                and (type(pet["petOwner"]) is not int or pet["petOwner"] < 1)
            )
        ):
            return None
        pet_ids.add(pet["id"])
    return (
        set(players) | pet_ids,
        {a[0] for a in rows if a[1] == "NPC" and a[4] in boss_game_ids},
        {a[0]: a[3] for a in rows},
    )


def absorption_by_ability(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, boss_game_ids: frozenset[int]
) -> dict[str, Any]:
    """Reuse recipient classification after validating every possible owned effect."""
    source = coverage(con, pf, pf.actor_id, Direction.SOURCE)
    source_bindings = con.execute(
        "SELECT role,owner_actor_id FROM stream_coverage "
        "WHERE report_code=? AND fight_id=? AND actor_id=? AND direction='source'",
        [pf.report_code, pf.fight_id, pf.actor_id],
    ).fetchall()
    cov = [
        replace(source, trusted=source.trusted and source_bindings == [("player", None)]),
        ScopedCoverageRef(
            pf.report_code,
            pf.fight_id,
            None,
            "all",
            has_complete_encounter_event_set(con, pf.report_code, pf.fight_id),
            "encounter",
        ),
    ]
    refs = (
        EvidenceRef(
            pf.report_code,
            pf.fight_id,
            pf.actor_id,
            "actors",
            detail="unique Player/Priest owner and recipient catalog",
        ),
        EvidenceRef(
            pf.report_code,
            pf.fight_id,
            pf.actor_id,
            "fights",
            detail="selected friendly Player/Pet recipient bindings",
        ),
    )
    result: dict[str, Any] = {
        "rule": ABSORPTION_RULE,
        "limitation": ABSORPTION_LIMITATION,
        "abilities": [],
        "review": None,
    }
    from necropsy.analysis.encounters import duty

    if not duty.applies(con, pf):
        return result | {
            "absorption": unknown(
                "absorption breakdown is outside Era raid scope", *refs, coverage=cov
            )
        }
    roster = _absorption_roster(con, pf, boss_game_ids)
    if roster is None or not 0 <= pf.start_time < pf.end_time:
        return result | {
            "absorption": unknown(
                "absorption owner/recipient metadata is unresolved", *refs, coverage=cov
            )
        }
    friendly, bosses, actor_names = roster
    candidates = con.execute(
        "SELECT timestamp,type,source_id,target_id,ability_game_id,amount,raw,event_uid,copy_index "
        "FROM events WHERE report_code=? AND fight_id=? ORDER BY timestamp,event_uid,copy_index",
        [pf.report_code, pf.fight_id],
    ).fetchall()
    events = []
    unresolved = []
    seen: set[tuple[str, int]] = set()
    for ts, kind, source, target, spell, amount, payload, uid, copy in candidates:
        raw = json.loads(payload) if isinstance(payload, str) else payload
        if not isinstance(raw, dict):
            unresolved.append((uid, copy))
            continue
        if (isinstance(kind, str) and kind and raw.get("type") == kind and kind != "absorbed") or (
            type(raw.get("sourceID")) is int
            and raw["sourceID"] == source
            and source > 0
            and source != pf.actor_id
        ):
            continue
        valid = (
            kind == raw.get("type") == "absorbed"
            and type(raw.get("sourceID")) is int
            and raw["sourceID"] == source == pf.actor_id
            and type(raw.get("targetID")) is int
            and raw["targetID"] == target
            and target > 0
            and type(raw.get("abilityGameID")) is int
            and raw["abilityGameID"] == spell
            and spell > 0
            and type(raw.get("timestamp")) is int
            and raw["timestamp"] == ts
            and pf.start_time <= ts <= pf.end_time
            and ("fight" not in raw or (type(raw["fight"]) is int and raw["fight"] == pf.fight_id))
            and type(raw.get("amount")) in (int, float)
            and math.isfinite(raw["amount"])
            and raw["amount"] >= 0
            and raw["amount"] == amount
            and (uid, copy) not in seen
        )
        if not valid:
            unresolved.append((uid, copy))
            continue
        seen.add((uid, copy))
        events.append(
            CombatEvent(
                ts,
                pf.relative_s(ts),
                kind,
                source,
                target,
                spell,
                None,
                amount,
                None,
                uid,
                copy,
                raw,
            )
        )
    supported, _, uncertain_recipients = recipient_groups(events, friendly, bosses)
    unresolved.extend((e.uid, e.copy) for e in uncertain_recipients)
    unresolved_ref = EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        None,
        unresolved,
        detail="unresolved possible source-attributed absorption",
    )

    def metric(value: int | float, rows: list[CombatEvent], label: str) -> Evidenced[Any]:
        reference = event_ref(pf, rows, label)
        if unresolved:
            return unknown(
                "possible absorption rows or recipients are unresolved",
                unresolved_ref,
                reference,
                *refs,
                coverage=cov,
            )
        return complete_or_unknown(
            value, cov, reference, *refs, rule_id=ABSORPTION_RULE, note=ABSORPTION_LIMITATION
        )

    def details(rows: list[CombatEvent]) -> dict[str, Any]:
        return {
            "absorption": metric(sum(e.amount or 0 for e in rows), rows, "credited absorption"),
            "effects": metric(len(rows), rows, "absorption effect occurrences, not casts"),
            "observations": observed(
                [[e.timestamp - pf.start_time, e.target_id, e.amount] for e in rows],
                event_ref(pf, rows, "qualified positive absorption observations"),
                *refs,
            ),
        }

    names: dict[int, list[str | None]] = defaultdict(list)
    for spell, name in con.execute(
        "SELECT game_id,name FROM abilities WHERE report_code=?",
        [pf.report_code],
    ).fetchall():
        names[spell].append(name)
    by_ability: dict[int, list[CombatEvent]] = defaultdict(list)
    for event in supported:
        assert event.ability_id is not None
        by_ability[event.ability_id].append(event)
    for spell, rows in sorted(by_ability.items()):
        recipients = []
        for target in sorted({e.target_id for e in rows if e.target_id is not None}):
            matched = [e for e in rows if e.target_id == target]
            recipients.append(
                {"actor_id": target, "name": actor_names.get(target), **details(matched)}
            )
        result["abilities"].append(
            {
                "ability_id": spell,
                "name": names[spell][0] if len(names[spell]) == 1 else None,
                "recipients": recipients,
                **details(rows),
            }
        )
    result["absorption"] = metric(
        sum(e.amount or 0 for e in supported), supported, "friendly source-attributed absorption"
    )
    shields = [e for e in supported if e.ability_id == 10901 and (e.amount or 0) > 0]
    if shields:
        result["review"] = {
            "kind": "review-prompt",
            "text": "Review recorded Power Word: Shield absorption recipients separately from "
            "other credited absorption. Agree shield priorities with your tanks and "
            "healers before copying a reference cast mix.",
            "refs": (event_ref(pf, shields, "recorded Power Word: Shield absorption recipients"),),
            "limitation": ABSORPTION_LIMITATION,
        }
    return result
