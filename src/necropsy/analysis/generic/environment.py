"""Per-fight environment and bias profile: what shaped a parse besides execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceRef,
    Faction,
    RaceStatus,
    WindfuryStatus,
    complete_or_unknown,
    derived,
    inferred,
    observed,
    unknown,
)
from necropsy.analysis.taxonomy import point_totals, talent_points
from necropsy.rules import load_rules
from necropsy.snapshot.model import Direction
from necropsy.wcl.combatant import auras_at_start
from necropsy.wcl.combatant import snapshot as context_snapshot

GAME = "classic_era"


@dataclass(frozen=True, slots=True)
class RaceFinding:
    race: Evidenced[str]
    status: RaceStatus


@dataclass(frozen=True, slots=True)
class WindfuryFinding:
    status: WindfuryStatus
    status_evidence: Evidenced[WindfuryStatus]
    procs: Evidenced[int]
    extra_attacks: Evidenced[int]
    matched_procs: int
    ambiguous_procs: int
    unmatched_procs: int
    attributed_damage: Evidenced[int]
    """Inferred damage among uniquely matched candidate swings; never the true WF total."""


@dataclass(frozen=True, slots=True)
class GearItem:
    slot: int
    item_id: int
    permanent_enchant: int | None
    temporary_enchant: int | None


@dataclass(frozen=True, slots=True)
class Aura:
    ability_id: int
    name: str | None


@dataclass(frozen=True, slots=True)
class EnvironmentProfile:
    participant: ParticipantFight
    faction: Evidenced[Faction]
    race: RaceFinding
    talents: Evidenced[str]
    starting_auras: Evidenced[tuple[Aura, ...]]
    world_buffs: Evidenced[tuple[str, ...]]
    darkmoon_faire: Evidenced[str]
    windfury: WindfuryFinding
    kill_duration_ms: Evidenced[int]
    gear: Evidenced[tuple[GearItem, ...]]


def _rows(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any]) -> list[tuple[Any, ...]]:
    return con.execute(sql, params).fetchall()


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _combatant_rows(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> list[tuple[Any, ...]]:
    return _rows(
        con,
        """
        SELECT faction, talent_points, auras, gear, event_uid FROM combatant_info
        WHERE report_code = ? AND fight_id = ? AND actor_id = ? ORDER BY timestamp, event_uid
        """,
        [pf.report_code, pf.fight_id, pf.actor_id],
    )


def _combatant_ref(pf: ParticipantFight, uid: str) -> EvidenceRef:
    return EvidenceRef.events(
        pf.report_code, pf.fight_id, pf.actor_id, [(uid, 0)], detail="combatantinfo"
    )


def faction(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> Evidenced[Faction]:
    """Faction from every direct field; any disagreement or unreadable code is UNKNOWN.

    The raid-class inference runs only when no direct field exists at all.
    """
    names = {int(k): v for k, v in load_rules(GAME, "externals")["factions"].items()}
    readings: list[tuple[int, EvidenceRef]] = []
    for code, _talents, _auras, _gear, uid in _combatant_rows(con, pf):
        if code is not None:
            readings.append((int(code), _combatant_ref(pf, uid)))
    for (code,) in _rows(
        con,
        "SELECT faction_id FROM player_details WHERE report_code = ? AND actor_id = ? "
        "AND faction_id IS NOT NULL",
        [pf.report_code, pf.actor_id],
    ):
        ref = EvidenceRef(
            pf.report_code, None, pf.actor_id, "player_details", detail="combatantInfo.factionID"
        )
        readings.append((int(code), ref))
    if not readings:
        return _raid_class_faction(con, pf)
    refs = tuple(ref for _, ref in readings)
    unreadable = sorted({c for c, _ in readings if c not in names})
    if unreadable:
        return unknown(f"unrecognised faction codes {unreadable}", *refs)
    values = {Faction(names[c]) for c, _ in readings}
    if len(values) > 1:
        return unknown(f"faction fields disagree: {sorted(values)}", *refs)
    return observed(values.pop(), *refs)


def _raid_class_faction(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> Evidenced[Faction]:
    rule = load_rules(GAME, "externals")["raid_class_faction"]
    classes = {
        str(r[0])
        for r in _rows(
            con,
            "SELECT DISTINCT sub_type FROM actors WHERE report_code = ? AND type = 'Player' "
            "AND sub_type IN ('Paladin', 'Shaman')",
            [pf.report_code],
        )
    }
    if len(classes) != 1:
        return unknown("no faction field, and the raid's class mix does not settle it")
    cls = classes.pop()
    ref = EvidenceRef(
        pf.report_code,
        None,
        None,
        "actors",
        detail=f"report players include {cls} and not the other faction's class",
    )
    return inferred(Faction(rule[cls]), ref, rule_id=str(rule["rule"]), params={"class": cls})


def race(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> RaceFinding:
    racials = {int(r["spell"]): r["race"] for r in load_rules(GAME, "racials")["racials"]}
    rows = _rows(
        con,
        """
        SELECT ability_game_id, event_uid, copy_index FROM events
        WHERE report_code = ? AND fight_id = ? AND type = 'cast' AND source_id = ?
          AND ability_game_id IN (SELECT unnest(?::BIGINT[]))
        ORDER BY timestamp, event_uid, copy_index
        """,
        [pf.report_code, pf.fight_id, pf.actor_id, list(racials)],
    )
    races = {racials[int(r[0])] for r in rows}
    if len(races) != 1:
        note = (
            "no racial ability cast; race is not inferred from faction or class"
            if not races
            else f"conflicting racial casts: {sorted(races)}"
        )
        return RaceFinding(unknown(note), RaceStatus.UNKNOWN)
    ref = EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        pf.actor_id,
        [(r[1], r[2]) for r in rows],
        detail="racial ability cast",
    )
    return RaceFinding(observed(races.pop(), ref), RaceStatus.RACIAL_EVENT_CONFIRMED)


def talents(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> Evidenced[str]:
    rows = [(t, uid) for _f, t, _a, _g, uid in _combatant_rows(con, pf) if t is not None]
    values = {t for t, _ in rows}
    refs = [_combatant_ref(pf, uid) for _, uid in rows[:1]]
    if any(point_totals(value) is None for value in values):
        return unknown("combatant talent totals are malformed", *refs)
    for raw, uid in _rows(
        con,
        "SELECT talents, event_uid FROM combatant_info "
        "WHERE report_code=? AND fight_id=? AND actor_id=?",
        [pf.report_code, pf.fight_id, pf.actor_id],
    ):
        raw = _json(raw)
        if raw is not None and raw != [] and talent_points(raw, "id") is None:
            return unknown("combatant talent metadata is malformed", *refs, _combatant_ref(pf, uid))
    for raw, source in _context_rows(con, pf):
        event = context_snapshot(_json(raw))
        trees = None if event is None else event.get("talents")
        points = talent_points(trees, "id")
        if trees is not None and trees != [] and points is None:
            return unknown("combatant context talent metadata is malformed", *refs)
        if points is not None:
            values.add(points)
            refs.append(
                EvidenceRef(
                    pf.report_code,
                    pf.fight_id,
                    pf.actor_id,
                    "combatant_context",
                    detail=source + "; raw combatant snapshot talents",
                )
            )
    metadata = con.execute(
        """SELECT combatant_info, source, sha256 FROM fight_player_details
           WHERE report_code = ? AND fight_id = ? AND actor_id = ?""",
        [pf.report_code, pf.fight_id, pf.actor_id],
    ).fetchall()
    for info, source, digest in metadata:
        trees = (_json(info) or {}).get("talents")
        if trees is None or trees == []:
            continue
        points = talent_points(trees, "guid")
        if points is None:
            return unknown("fight-scoped talent metadata is malformed", *refs)
        values.add(points)
        refs.append(
            EvidenceRef(
                pf.report_code,
                pf.fight_id,
                pf.actor_id,
                "fight_player_details",
                detail=f"{source}; report SHA-256 {digest}; combatantInfo.talents tree points",
            )
        )
    if len(values) != 1:
        return unknown(
            "no talent data" if not values else f"conflicting talents {sorted(values)}", *refs
        )
    return observed(values.pop(), *refs)


def starting_auras(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> Evidenced[tuple[Aura, ...]]:
    rows = [(a, uid) for _f, _t, a, _g, uid in _combatant_rows(con, pf) if a is not None]
    if not rows:
        contexts = []
        refs = []
        for raw, source in _context_rows(con, pf):
            parsed_context = auras_at_start(_json(raw))
            if parsed_context is None:
                return unknown("combatant prelude aura state could not be reconstructed")
            contexts.append(tuple(Aura(ability, name) for ability, name in parsed_context))
            refs.append(
                EvidenceRef(
                    pf.report_code,
                    pf.fight_id,
                    pf.actor_id,
                    "combatant_context",
                    detail=source + "; snapshot and prelude buff changes",
                )
            )
        if contexts:
            if any(v != contexts[0] for v in contexts):
                return unknown("combatant contexts disagree on starting auras", *refs)
            return derived(
                contexts[0],
                *refs,
                rule_id="combatant-prelude-auras-v1",
                note=(
                    "Reconstructed at ranked combat start from the earlier snapshot "
                    "and intervening buff events."
                ),
            )
        return unknown("no combatantinfo auras for this fight")
    auras, uid = rows[0]
    parsed = tuple(
        Aura(int(a["ability"]), a.get("name")) for a in _json(auras) or [] if "ability" in a
    )
    return observed(parsed, _combatant_ref(pf, uid))


def _context_rows(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> list[tuple[Any, ...]]:
    return con.execute(
        """SELECT raw, source FROM combatant_context
           WHERE report_code=? AND fight_id=? AND actor_id=?""",
        [pf.report_code, pf.fight_id, pf.actor_id],
    ).fetchall()


def _named_subset(
    auras: Evidenced[tuple[Aura, ...]], table: list[dict[str, Any]]
) -> Evidenced[tuple[str, ...]]:
    if auras.value is None:
        return unknown("starting auras unknown", *auras.refs)
    ids = {int(e["spell"]): e["name"] for e in table}
    names = tuple(sorted({ids[a.ability_id] for a in auras.value if a.ability_id in ids}))
    return observed(names, *auras.refs)


def world_buffs(auras: Evidenced[tuple[Aura, ...]]) -> Evidenced[tuple[str, ...]]:
    return _named_subset(auras, load_rules(GAME, "externals")["world_buffs"])


def darkmoon_faire(auras: Evidenced[tuple[Aura, ...]]) -> Evidenced[str]:
    found = _named_subset(auras, load_rules(GAME, "externals")["darkmoon_faire"])
    if found.value is None:
        return unknown("starting auras unknown", *found.refs)
    if len(found.value) > 1:
        return unknown(f"several Darkmoon Faire fortunes: {found.value}", *found.refs)
    return observed(found.value[0] if found.value else "none", *found.refs)


def windfury(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> WindfuryFinding:
    rules = load_rules(GAME, "externals")
    wf_ids = [int(e["spell"]) for e in rules["windfury"]["extra_attack_abilities"]]
    window = int(rules["windfury"]["attribution"]["window_ms"])
    rule_id = str(rules["windfury"]["attribution"]["rule"])
    melee = [int(x) for x in rules["melee_swing_abilities"]]
    cov = [coverage(con, pf, pf.actor_id, Direction.SOURCE)]
    procs = _rows(
        con,
        """
        SELECT timestamp, coalesce(extra_attacks, 1), event_uid, copy_index FROM events
        WHERE report_code = ? AND fight_id = ? AND type = 'extraattacks' AND source_id = ?
          AND ability_game_id IN (SELECT unnest(?::BIGINT[]))
        ORDER BY timestamp, event_uid, copy_index
        """,
        [pf.report_code, pf.fight_id, pf.actor_id, wf_ids],
    )
    proc_ref = EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        pf.actor_id,
        [(p[2], p[3]) for p in procs],
        detail="windfury extraattacks",
    )
    status_evidence: Evidenced[WindfuryStatus] = (
        observed(WindfuryStatus.CONFIRMED, proc_ref)
        if procs
        else complete_or_unknown(WindfuryStatus.NOT_OBSERVED, cov, proc_ref)
    )
    status = status_evidence.value or WindfuryStatus.UNKNOWN
    count_proc = complete_or_unknown(len(procs), cov, proc_ref)
    count_extra = complete_or_unknown(sum(int(p[1]) for p in procs), cov, proc_ref)
    swings = _rows(
        con,
        """
        SELECT timestamp, coalesce(amount, 0), event_uid, copy_index FROM events
        WHERE report_code = ? AND fight_id = ? AND type = 'damage' AND source_id = ?
          AND ability_game_id IN (SELECT unnest(?::BIGINT[]))
        ORDER BY timestamp, event_uid, copy_index
        """,
        [pf.report_code, pf.fight_id, pf.actor_id, melee],
    )
    matched, ambiguous, unmatched, damage, used = _attribute(procs, swings, window)
    params = {"window_ms": window, "melee_abilities": tuple(melee)}
    if not cov[0].trusted:
        attributed: Evidenced[int] = unknown(
            "source stream incomplete or untrustworthy", proc_ref, coverage=cov
        )
    elif not procs:
        attributed = complete_or_unknown(
            0,
            cov,
            proc_ref,
            rule_id="windfury-no-procs-v1",
            note=(
                "No Windfury procs observed; no proc damage to attribute. "
                "This does not prove totem availability."
            ),
        )
    elif matched == 0:
        attributed = unknown("no Windfury proc has a unique candidate swing", proc_ref)
    else:
        swing_ref = EvidenceRef.events(
            pf.report_code,
            pf.fight_id,
            pf.actor_id,
            used,
            detail="uniquely matched candidate swings",
        )
        attributed = inferred(
            damage,
            proc_ref,
            swing_ref,
            rule_id=rule_id,
            params=params,
            note="damage among uniquely matched candidate swings only; "
            "the true total Windfury damage is unknown",
        )
    return WindfuryFinding(
        status, status_evidence, count_proc, count_extra, matched, ambiguous, unmatched, attributed
    )


def _attribute(
    procs: list[tuple[Any, ...]], swings: list[tuple[Any, ...]], window_ms: int
) -> tuple[int, int, int, int, list[tuple[str, int]]]:
    """Rule wf-unique-swing-v1. A swing counts for a proc only if it lies in no other proc's
    window and the proc's window holds exactly as many swings as the proc's extra attacks."""
    windows = [(int(p[0]), int(p[0]) + window_ms) for p in procs]
    owners: list[list[int]] = [
        [i for i, (lo, hi) in enumerate(windows) if lo <= int(s[0]) <= hi] for s in swings
    ]
    matched = ambiguous = unmatched = damage = 0
    used: list[tuple[str, int]] = []
    for i, proc in enumerate(procs):
        candidates = [j for j, o in enumerate(owners) if i in o]
        shared = any(len(owners[j]) > 1 for j in candidates)
        wanted = int(proc[1])
        if shared or len(candidates) > wanted:
            ambiguous += 1
        elif len(candidates) < wanted:
            unmatched += 1
        else:
            matched += 1
            damage += sum(int(swings[j][1]) for j in candidates)
            used.extend((swings[j][2], int(swings[j][3])) for j in candidates)
    return matched, ambiguous, unmatched, damage, used


def kill_duration(pf: ParticipantFight) -> Evidenced[int]:
    ref = EvidenceRef(pf.report_code, pf.fight_id, None, "fights", detail="endTime - startTime")
    return derived(pf.duration_ms, ref)


def gear(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> Evidenced[tuple[GearItem, ...]]:
    candidates: list[tuple[Any, EvidenceRef]] = [
        (g, _combatant_ref(pf, uid)) for _f, _t, _a, g, uid in _combatant_rows(con, pf) if g
    ]
    if not candidates:
        rows = _rows(
            con,
            "SELECT combatant_info FROM player_details WHERE report_code = ? AND actor_id = ?",
            [pf.report_code, pf.actor_id],
        )
        for (info,) in rows:
            items = (_json(info) or {}).get("gear")
            if items:
                candidates.append(
                    (
                        items,
                        EvidenceRef(
                            pf.report_code, None, pf.actor_id, "player_details", detail="gear"
                        ),
                    )
                )
    if not candidates:
        return unknown("no gear data")
    items, ref = candidates[0]
    parsed = tuple(
        GearItem(slot, int(item["id"]), item.get("permanentEnchant"), item.get("temporaryEnchant"))
        for slot, item in enumerate(_json(items))
        if isinstance(item, dict) and item.get("id") is not None
    )
    return observed(parsed, ref)


def environment_profile(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> EnvironmentProfile:
    auras = starting_auras(con, pf)
    return EnvironmentProfile(
        participant=pf,
        faction=faction(con, pf),
        race=race(con, pf),
        talents=talents(con, pf),
        starting_auras=auras,
        world_buffs=world_buffs(auras),
        darkmoon_faire=darkmoon_faire(auras),
        windfury=windfury(con, pf),
        kill_duration_ms=kill_duration(pf),
        gear=gear(con, pf),
    )
