"""Separate owned-unit support from actor throughput and ranking scores."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import replace
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight, Pet, coverage
from necropsy.analysis.evidence import (
    EvidenceRef,
    ScopedCoverageRef,
    complete_or_unknown,
    unknown,
)
from necropsy.analysis.generic import combat, healing
from necropsy.normalize.coverage import has_complete_encounter_event_set
from necropsy.snapshot.model import Direction

LIMITATION = (
    "Separate owned-unit contributions over the whole fight, excluding overheal. "
    "These are not added to actor support or WCL scores. An incomplete listing "
    "cannot establish all-summon totals, usage, assignments or healing quality."
)
FIELDS = ("healing", "absorption", "combined_per_second")


def _decoded(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def support(
    con: duckdb.DuckDBPyConnection,
    owner: ParticipantFight,
    pet: Pet,
    boss_game_ids: frozenset[int],
) -> dict[str, Any]:
    """Certify an individual unit only, including under an incomplete owner listing."""
    pf = replace(owner, actor_id=pet.actor_id)
    refs = (
        EvidenceRef(
            owner.report_code,
            owner.fight_id,
            owner.actor_id,
            "actors",
            detail=f"owner Player and Pet {pet.actor_id} master ownership",
        ),
        EvidenceRef(
            owner.report_code,
            owner.fight_id,
            pet.actor_id,
            "fights",
            detail="selected friendlyPlayers/friendlyPets ownership and game ID",
        ),
        EvidenceRef(
            owner.report_code,
            owner.fight_id,
            pet.actor_id,
            "stream_coverage",
            detail=f"pet source stream owner {owner.actor_id}",
        ),
    )
    covs = [
        coverage(con, pf, pet.actor_id, Direction.SOURCE),
        ScopedCoverageRef(
            owner.report_code,
            owner.fight_id,
            None,
            "all",
            has_complete_encounter_event_set(con, owner.report_code, owner.fight_id),
            "encounter",
        ),
    ]
    result: dict[str, Any] = {
        "rule": "owned-summon-friendly-support-v1",
        "owner_actor_id": owner.actor_id,
        "game_id": pet.game_id,
        "limitation": LIMITATION,
    }

    def withheld(reason: str, event_refs: tuple[EvidenceRef, ...] = ()) -> dict[str, Any]:
        return result | {key: unknown(reason, *event_refs, *refs, coverage=covs) for key in FIELDS}

    if not _ownership(con, owner, pet):
        return withheld("owned-unit metadata is missing, conflicting or malformed")
    if not all(c.trusted for c in covs):
        return withheld("owned-unit source or encounter event-set coverage is incomplete")
    full = con.execute(
        "SELECT timestamp,type,source_id,target_id,ability_game_id,amount,raw,event_uid,copy_index "
        "FROM events WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchall()
    occurrences: list[tuple[str, int]] = []
    for ts, kind, source, target, spell, amount, raw, uid, copy in full:
        raw = _decoded(raw)
        if not isinstance(raw, dict):
            return withheld("event payload is malformed")
        # Only consistent, typed unrelated rows may be excluded. Neither side
        # retaining an identity/type must not hide an unresolved support event.
        if (
            isinstance(kind, str)
            and kind
            and raw.get("type") == kind
            and kind not in ("heal", "absorbed")
        ) or (
            type(raw.get("sourceID")) is int
            and type(source) is int
            and raw["sourceID"] == source
            and source > 0
            and source != pet.actor_id
        ):
            continue
        # Inspect possible raw OR normalized ownership before any time/type exclusion.
        valid = (
            type(raw.get("sourceID")) is int
            and raw["sourceID"] == source == pet.actor_id
            and type(raw.get("targetID")) is int
            and raw["targetID"] == target
            and target > 0
            and type(raw.get("timestamp")) is int
            and raw["timestamp"] == ts
            and pf.start_time <= ts <= pf.end_time
            and raw.get("type") == kind
            and kind in {"heal", "absorbed"}
            and type(raw.get("abilityGameID")) is int
            and raw["abilityGameID"] == spell
            and spell > 0
            and ("fight" not in raw or (type(raw["fight"]) is int and raw["fight"] == pf.fight_id))
            and type(raw.get("amount")) in (int, float)
            and math.isfinite(raw["amount"])
            and raw["amount"] >= 0
            and raw["amount"] == amount
        )
        if not valid:
            event_ref = EvidenceRef.events(
                pf.report_code,
                pf.fight_id,
                None,
                [(uid, copy)],
                detail="unresolved owned-unit support candidate",
            )
            return withheld(
                "owned-unit support event identity, time or amount is invalid", (event_ref,)
            )
        occurrences.append((uid, copy))
    events = combat.event_rows(con, pf)
    projected = [
        (e.uid, e.copy)
        for e in events
        if e.source_id == pet.actor_id and e.kind in ("heal", "absorbed")
    ]
    if Counter(projected) != Counter(occurrences):
        return withheld("owned-unit support projection changed event occurrence multiplicity")
    totals, _, _ = combat.event_totals(con, pf, events)
    qualified = healing.recipient_metrics(con, pf, events, boss_game_ids, totals)
    for key, metric in zip(
        FIELDS,
        ("effective_healing", "effective_absorption", "healing_and_absorption_per_second"),
        strict=True,
    ):
        value = qualified[metric]
        result[key] = (
            complete_or_unknown(
                value.value, covs, *value.refs, *refs, rule_id=result["rule"], note=LIMITATION
            )
            if value.value is not None
            else unknown(
                value.note or "owned-unit recipients are unresolved",
                *value.refs,
                *refs,
                coverage=covs,
            )
        )
    return result


def _ownership(con: duckdb.DuckDBPyConnection, pf: ParticipantFight, pet: Pet) -> bool:
    actors = con.execute(
        "SELECT actor_id,type,game_id,pet_owner FROM actors WHERE report_code=?",
        [pf.report_code],
    ).fetchall()
    catalog = {a[0]: a for a in actors}
    if len(catalog) != len(actors) or pet.actor_id == pf.actor_id:
        return False
    owner, unit = catalog.get(pf.actor_id), catalog.get(pet.actor_id)
    if (
        owner is None
        or owner[1] != "Player"
        or unit is None
        or unit[1] != "Pet"
        or unit[3] != pf.actor_id
        or type(pet.game_id) is not int
        or pet.game_id < 1
        or unit[2] != pet.game_id
    ):
        return False
    rows = con.execute(
        "SELECT friendly_players,friendly_pets FROM fights WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchall()
    if len(rows) != 1:
        return False
    players, pets = map(_decoded, rows[0])
    if (
        not isinstance(players, list)
        or not players
        or pf.actor_id not in players
        or any(
            type(p) is not int or p < 1 or catalog.get(p, (None, None))[1] != "Player"
            for p in players
        )
        or len(set(players)) != len(players)
        or not isinstance(pets, list)
    ):
        return False
    ids: set[int] = set()
    binding = None
    for p in pets:
        if (
            not isinstance(p, dict)
            or type(p.get("id")) is not int
            or p["id"] < 1
            or p["id"] in ids
            or p["id"] in players
            or catalog.get(p["id"], (None, None))[1] != "Pet"
        ):
            return False
        ids.add(p["id"])
        if p["id"] == pet.actor_id:
            binding = p
    if (
        binding is None
        or type(binding.get("petOwner")) is not int
        or binding["petOwner"] != pf.actor_id
        or type(binding.get("gameID")) is not int
        or binding["gameID"] != pet.game_id
    ):
        return False
    streams = con.execute(
        "SELECT role,owner_actor_id FROM stream_coverage WHERE report_code=? AND fight_id=? "
        "AND actor_id=? AND direction='source'",
        [pf.report_code, pf.fight_id, pet.actor_id],
    ).fetchall()
    return streams == [("pet", pf.actor_id)]
