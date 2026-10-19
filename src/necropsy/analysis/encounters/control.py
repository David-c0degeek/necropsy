"""Source-owned control applications, with NPC instances retained as evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, cast

import duckdb

from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.encounters import duty
from necropsy.analysis.evidence import (
    CoverageRef,
    Evidenced,
    EvidenceRef,
    ScopedCoverageRef,
    complete_or_unknown,
    observed,
    unknown,
)
from necropsy.analysis.generic import combat
from necropsy.normalize.coverage import has_complete_encounter_event_set
from necropsy.raids import raid_for_encounter
from necropsy.rules import load_rules
from necropsy.snapshot.model import Direction

LIMITATION = (
    "Recorded control applications, separate from casts. NPC actor and instance identity "
    "are retained where recorded. Actor-source coverage does not establish full add control "
    "uptime, break causes, assigned targets or available opportunities. A zero count is "
    "not a failed duty or a utility score. Complete counts require trusted player SOURCE "
    "and encounter event-set proof; qualified recorded applications remain visible when "
    "the count is unknown."
)
REVIEW_LIMITATION = (
    "A recorded application is not an assignment, maintained uptime or proof that control "
    "was needed. Agree add control and backup coverage with your raid."
)


CURSE_LIMITATION = (
    "Counts only Curse of Recklessness, Curse of the Elements and Curse of Shadow; other "
    "curses are outside this count. Recorded curse applications, separate from casts. "
    "Applications are not uptime, "
    "assignment or proof of raid benefit; curse choice is assigned by the raid, and another "
    "Warlock's curse is not yours. A zero count is not a failed duty. Complete counts require "
    "trusted player SOURCE and encounter event-set proof; qualified recorded applications "
    "remain visible when the count is unknown."
)
CURSE_REVIEW_LIMITATION = (
    "A recorded curse application is not an assignment, uptime or a recommendation to change "
    "curses. Agree curse assignments with your raid."
)


@dataclass(frozen=True, slots=True)
class _Kind:
    section: str
    noun: str
    limitation: str
    review_limitation: str
    instance_required: bool
    advice: str


CONTROL = _Kind(
    "control",
    "control",
    LIMITATION,
    REVIEW_LIMITATION,
    True,
    "Confirm whether you should maintain control on this add and who provides backup when it "
    "ends before copying a damage reference opener.",
)
CURSES = _Kind(
    "curses",
    "curse",
    CURSE_LIMITATION,
    CURSE_REVIEW_LIMITATION,
    False,
    "Confirm which curse your raid assigned you before copying a reference curse choice.",
)


@dataclass(frozen=True, slots=True)
class ControlApplications:
    rule: str
    label: str
    source: str
    retrieved: str
    applications: Evidenced[int]
    observations: Evidenced[tuple[tuple[float, int, int | None, int], ...]]
    limitation: str = LIMITATION
    review: tuple[dict[str, Any], ...] = ()


def _decoded(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _context(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, class_name: str
) -> tuple[dict[int, tuple[Any, ...]], list[dict[str, Any]]] | None:
    """Unique fight, catalog, Player source and typed enemy roster, or None."""
    fights = con.execute(
        "SELECT encounter_id,start_time,end_time,friendly_players,enemy_npcs FROM fights "
        "WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchall()
    if (
        len(fights) != 1
        or any(type(v) is not int for v in fights[0][:3])
        or fights[0][:3] != (pf.encounter_id, pf.start_time, pf.end_time)
        or not 0 <= pf.start_time < pf.end_time
    ):
        return None
    actors = con.execute(
        "SELECT actor_id,type,sub_type,game_id,name FROM actors WHERE report_code=?",
        [pf.report_code],
    ).fetchall()
    catalog = {a[0]: a for a in actors}
    if (
        len(catalog) != len(actors)
        or any(type(a[0]) is not int for a in actors)
        or catalog.get(pf.actor_id, (None, None, None))[1:3] != ("Player", class_name)
    ):
        return None
    players, enemies = map(_decoded, fights[0][3:])
    if (
        not isinstance(players, list)
        or any(type(p) is not int or p < 1 for p in players)
        or len(set(players)) != len(players)
        or pf.actor_id not in players
        or not isinstance(enemies, list)
    ):
        return None
    seen: set[int] = set()
    for enemy in enemies:
        if (
            not isinstance(enemy, dict)
            or type(enemy.get("id")) is not int
            or enemy["id"] < 1
            or enemy["id"] in seen
            or enemy["id"] in players
            or type(enemy.get("gameID")) is not int
            or enemy["gameID"] < 1
            or catalog.get(enemy["id"], (None, None))[1] != "NPC"
            or catalog[enemy["id"]][3] != enemy["gameID"]
            or type(enemy.get("instanceCount")) is not int
            or enemy["instanceCount"] < 1
        ):
            return None
        seen.add(enemy["id"])
    return catalog, enemies


def applications(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> tuple[ControlApplications, ...]:
    return _applications(con, pf, CONTROL)


def curse_applications(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> tuple[ControlApplications, ...]:
    """Owned curse applications under the same occurrence, roster and coverage proofs."""
    return _applications(con, pf, CURSES)


def _applications(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, kind_: _Kind
) -> tuple[ControlApplications, ...]:
    noun = kind_.noun
    if not duty.applies(con, pf):
        return ()
    meta = con.execute("SELECT subject_class_id FROM snapshot_meta").fetchone()
    policies = (
        load_rules("classic_era", f"zones/{raid_for_encounter(pf.encounter_id).slug}_guidance")
        .get(kind_.section, {})
        .get(pf.encounter_id, ())
    )
    policies = [p for p in policies if meta and meta[0] in p["classes"]]
    if not policies:
        return ()
    assert meta is not None
    source = coverage(con, pf, pf.actor_id, Direction.SOURCE)
    bindings = con.execute(
        "SELECT role,owner_actor_id FROM stream_coverage "
        "WHERE report_code=? AND fight_id=? AND actor_id=? AND direction='source'",
        [pf.report_code, pf.fight_id, pf.actor_id],
    ).fetchall()
    cov: list[CoverageRef] = [
        replace(source, trusted=source.trusted and bindings == [("player", None)]),
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
            detail=f"unique Player class source and {noun} NPC identity",
        ),
        EvidenceRef(
            pf.report_code,
            pf.fight_id,
            None,
            "fights",
            detail="selected friendly Player and enemy NPC/instanceCount roster",
        ),
    )
    context = _context(con, pf, CLASS_NAMES.get(meta[0], ""))
    rows = (
        con.execute(
            "SELECT timestamp,type,source_id,target_id,target_instance,ability_game_id,raw,"
            "event_uid,copy_index FROM events WHERE report_code=? AND fight_id=? "
            "ORDER BY timestamp,event_uid,copy_index",
            [pf.report_code, pf.fight_id],
        ).fetchall()
        if context is not None
        else []
    )
    names: dict[int, list[Any]] = {}
    for spell, name in con.execute(
        "SELECT game_id,name FROM abilities WHERE report_code=?", [pf.report_code]
    ).fetchall():
        names.setdefault(spell, []).append(name)
    result = []
    for policy in policies:
        if context is None:
            withheld: Evidenced[Any] = unknown(
                f"{noun} source, fight or enemy roster binding is unresolved", *refs, coverage=cov
            )
            result.append(
                ControlApplications(
                    policy["rule"],
                    policy["label"],
                    policy["source"],
                    policy["retrieved"],
                    withheld,
                    withheld,
                    kind_.limitation,
                )
            )
            continue
        catalog, enemies = context
        spells = set(policy["ability_ids"])
        games = set(policy["target_game_ids"])
        targets = {e["id"]: e["instanceCount"] for e in enemies if e["gameID"] in games}
        # A relevant catalog NPC without a selected roster binding cannot certify a zero,
        # even while another bound control target remains.
        unbound = sorted(a for a, row in catalog.items() if row[1] == "NPC" and row[3] in games)
        unbound = [a for a in unbound if a not in targets]
        if not targets:
            withheld = unknown(
                f"selected enemy roster has no {noun} target binding", *refs, coverage=cov
            )
            result.append(
                ControlApplications(
                    policy["rule"],
                    policy["label"],
                    policy["source"],
                    policy["retrieved"],
                    withheld,
                    withheld,
                    kind_.limitation,
                )
            )
            continue
        qualified: list[combat.CombatEvent] = []
        unresolved: list[tuple[Any, Any]] = []
        seen: set[tuple[Any, Any]] = set()
        for ts, kind, src, target, instance, spell, payload, uid, copy in rows:
            raw = _decoded(payload)
            # No SQL pruning: an unresolved possible application cannot vanish into zero.
            if not isinstance(raw, dict):
                unresolved.append((uid, copy))
                continue
            if isinstance(kind, str) and kind and raw.get("type") == kind != "applydebuff":
                continue
            if (
                type(raw.get("sourceID")) is int
                and raw["sourceID"] == src
                and src > 0
                and src != pf.actor_id
            ):
                continue
            if (
                kind == raw.get("type") == "applydebuff"
                and type(raw.get("abilityGameID")) is int
                and raw["abilityGameID"] == spell
                and spell > 0
                and spell not in spells
            ):
                continue
            recipient = catalog.get(target) if type(target) is int else None
            if (
                kind == raw.get("type") == "applydebuff"
                and type(raw.get("targetID")) is int
                and raw["targetID"] == target
                and recipient is not None
                and (
                    recipient[1] in {"Player", "Pet"}
                    or (
                        recipient[1] == "NPC"
                        and type(recipient[3]) is int
                        and recipient[3] > 0
                        and recipient[3] not in games
                    )
                )
            ):
                continue
            valid = (
                kind == raw.get("type") == "applydebuff"
                and all(
                    type(raw.get(key)) is int and raw[key] == value and value > 0
                    for key, value in (
                        ("sourceID", src),
                        ("targetID", target),
                        ("abilityGameID", spell),
                    )
                )
                and src == pf.actor_id
                and spell in spells
                and type(raw.get("timestamp")) is int
                and raw["timestamp"] == ts
                and pf.start_time <= ts <= pf.end_time
                and (
                    "fight" not in raw
                    or (type(raw["fight"]) is int and raw["fight"] == pf.fight_id)
                )
                and (
                    (raw.get("targetInstance") is None and instance is None)
                    or (
                        type(raw.get("targetInstance")) is int
                        and raw["targetInstance"] == instance
                        and instance > 0
                    )
                )
                and recipient is not None
                and recipient[1] == "NPC"
                and recipient[3] in games
                and target in targets
                and (instance is None or instance <= targets[target])
                and (uid, copy) not in seen
            )
            if not valid:
                unresolved.append((uid, copy))
                continue
            seen.add((uid, copy))
            qualified.append(
                combat.CombatEvent(
                    ts,
                    pf.relative_s(ts),
                    kind,
                    src,
                    target,
                    spell,
                    None,
                    None,
                    None,
                    uid,
                    copy,
                    raw,
                )
            )
        reference = combat.event_ref(pf, qualified, f"source-owned {noun} applications")
        ambiguity = EvidenceRef.events(
            pf.report_code,
            pf.fight_id,
            None,
            unresolved,
            detail=f"unresolved possible {noun} applications",
        )
        reason = f"possible {noun} rows, recipients or instances are unresolved"
        if unbound:
            reason = f"a relevant {noun} NPC lacks a selected enemy roster binding"
        count = (
            unknown(reason, ambiguity, reference, *refs, coverage=cov)
            if unresolved or unbound
            else complete_or_unknown(
                len(qualified), cov, reference, *refs, rule_id=policy["rule"], note=kind_.limitation
            )
        )
        values = tuple(
            (e.t_s, cast(int, e.target_id), _decoded_instance(e.raw), cast(int, e.ability_id))
            for e in qualified
        )
        observations = (
            observed(values, reference, *refs)
            if qualified
            else unknown(reason, ambiguity, *refs, coverage=cov)
            if unresolved or unbound
            else complete_or_unknown((), cov, reference, *refs)
        )
        review = []
        prompted: set[tuple[int, int, int | None]] = set()
        for event in qualified:
            instance_id = _decoded_instance(event.raw)
            key = (
                0 if kind_.instance_required else cast(int, event.ability_id),
                cast(int, event.target_id),
                instance_id,
            )
            # One prompt per add instance; the observation timeline keeps reapplications.
            if (instance_id is None and kind_.instance_required) or key in prompted:
                continue
            prompted.add(key)
            spell_names = names.get(event.ability_id or 0, [])
            spell_name = spell_names[0] if len(spell_names) == 1 and spell_names[0] else None
            target_name = catalog[cast(int, event.target_id)][4] or "NPC"
            review.append(
                {
                    "kind": "review-prompt",
                    "text": f"Recorded {spell_name or f'ability {event.ability_id}'} on "
                    f"{target_name} {event.target_id}, "
                    + ("instance unrecorded" if instance_id is None else f"instance {instance_id}")
                    + f", at {event.t_s:.2f}s. {kind_.advice}",
                    "target_actor_id": event.target_id,
                    "target_instance": instance_id,
                    "elapsed_s": event.t_s,
                    "ability_id": event.ability_id,
                    "refs": (
                        combat.event_ref(pf, [event], f"recorded owned {noun} application"),
                        *refs,
                    ),
                    "limitation": kind_.review_limitation,
                }
            )
        result.append(
            ControlApplications(
                policy["rule"],
                policy["label"],
                policy["source"],
                policy["retrieved"],
                count,
                observations,
                kind_.limitation,
                tuple(review),
            )
        )
    return tuple(result)


def _decoded_instance(raw: dict[str, Any]) -> int | None:
    value = raw.get("targetInstance")
    return value if type(value) is int else None
