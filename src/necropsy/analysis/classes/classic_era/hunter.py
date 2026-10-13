"""Classic Era Hunter forensics: shot cadence, Auto Shot cycle, weaving, pets and gear."""

from __future__ import annotations

import itertools
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import duckdb

from necropsy.analysis.classes import register
from necropsy.analysis.context import ParticipantFight, coverage, owned_pets
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceRef,
    complete_or_unknown,
    derived,
    inferred,
    observed,
    unknown,
)
from necropsy.analysis.generic import metrics
from necropsy.analysis.generic.environment import EnvironmentProfile, GearItem
from necropsy.rules import load_rules
from necropsy.snapshot.model import Direction

GAME = "classic_era"
HUNTER_CLASS_ID = 3
OPENER_LENGTH = 10
SLOT_MAIN_HAND, SLOT_OFF_HAND, SLOT_RANGED = 15, 16, 17
SLOT_TRINKETS = (12, 13)
RENATAKI = 19953
NO_UNIT_TARGET = -1
"""WCL's "Environment" placeholder target, e.g. for a trap placed on the ground."""

SHOT_KINDS = ("auto_shot", "aimed_shot", "multi_shot", "arcane_shot", "raptor_strike")
INSIDE_KINDS = ("aimed_shot", "multi_shot", "arcane_shot", "raptor_strike", "refocus")


@dataclass(frozen=True, slots=True)
class Cast:
    t_s: float
    timestamp: int
    kind: str
    event_uid: str
    copy_index: int
    target_id: int | None
    target_friendly: bool | None
    side_source: str | None
    """How the side was decided: event-flag, fight-friendly-list, fight-enemy-list, or
    no-unit-target for ground-placed casts such as traps."""


@dataclass(frozen=True, slots=True)
class CastStats:
    casts: Evidenced[tuple[Cast, ...]]
    per_minute: Evidenced[float]


@dataclass(frozen=True, slots=True)
class AutoInterval:
    index: int
    start: Cast
    end: Cast
    gap_s: float
    ranged_haste: Evidenced[bool]
    """Whether a ranged haste aura (Rapid Fire, Quick Shots, Berserking) overlapped."""
    inside: dict[str, tuple[float, ...]]
    """Special shots cast after the start Auto and up to the end Auto, by kind."""


@dataclass(frozen=True, slots=True)
class AutoGapSignal:
    """Advisory: Auto intervals unusually long for this fight (possible clipping or downtime)."""

    flagged: Evidenced[tuple[int, ...]]
    baseline_count: int
    median_gap_s: float | None
    threshold: float


@dataclass(frozen=True, slots=True)
class PetCategory:
    actor_id: int
    name: str
    game_id: int | None
    category: Evidenced[str]
    """hunter-pet, engineering, trap or other."""


@dataclass(frozen=True, slots=True)
class HunterPet:
    actor_id: int
    name: str
    family: Evidenced[str]
    family_candidates: tuple[str, ...]
    abilities: Evidenced[tuple[tuple[int, str], ...]]
    """(spell ID, ability name) of every ability the pet was seen using."""
    damage: Evidenced[int]
    dps: Evidenced[float]
    activity: Evidenced[metrics.ActivityWindow]
    deaths: metrics.DeathsFinding


@dataclass(frozen=True, slots=True)
class GearContext:
    """Equipment in the snapshot taken at the pull; swaps during the fight are not inferred."""

    ranged: Evidenced[GearItem]
    trinkets: Evidenced[tuple[GearItem, ...]]
    main_hand: Evidenced[GearItem]
    off_hand: Evidenced[GearItem]
    renataki_at_pull: Evidenced[bool]


@dataclass(frozen=True, slots=True)
class HunterAnalysis:
    participant: ParticipantFight
    shots: dict[str, CastStats]
    rapid_fire: CastStats
    refocus: CastStats
    hunters_mark: CastStats
    explosives: dict[str, CastStats]
    opener: Evidenced[tuple[Cast, ...]]
    quick_shots_procs: Evidenced[int]
    quick_shots_uptime_s: Evidenced[float]
    rapid_fire_uptime_s: Evidenced[float]
    friendly_crowd_control: Evidenced[tuple[Cast, ...]]
    auto_intervals: Evidenced[tuple[AutoInterval, ...]]
    auto_gap: AutoGapSignal
    raptor_damage: Evidenced[int]
    white_melee_swings: Evidenced[int]
    white_melee_damage: Evidenced[int]
    pets: tuple[PetCategory, ...]
    hunter_pets: tuple[HunterPet, ...]
    gear: GearContext


def _rules() -> dict[str, Any]:
    return load_rules(GAME, "hunter")


@dataclass(frozen=True, slots=True)
class FightSides:
    """Actor membership lists WCL gives for a fight."""

    friendly: frozenset[int]
    enemies: frozenset[int]


def _fight_sides(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> FightSides:
    row = con.execute(
        "SELECT friendly_players, friendly_pets, enemy_npcs FROM fights "
        "WHERE report_code = ? AND fight_id = ?",
        [pf.report_code, pf.fight_id],
    ).fetchone()
    players, pets, enemies = (
        ([], [], []) if row is None else (_as_list(row[0]), _as_list(row[1]), _as_list(row[2]))
    )
    friendly = {int(p) for p in players} | {
        int(p["id"]) for p in pets if isinstance(p, dict) and "id" in p
    }
    return FightSides(
        frozenset(friendly),
        frozenset(int(e["id"]) for e in enemies if isinstance(e, dict) and "id" in e),
    )


def _as_list(value: Any) -> list[Any]:
    parsed = json.loads(value) if isinstance(value, str) else value
    return parsed if isinstance(parsed, list) else []


def _side(
    flag: bool | None,
    target: int | None,
    owner: int | None,
    sides: FightSides,
    ground_placed: bool,
) -> tuple[bool | None, str | None]:
    """Rule target-side-v1: which side a cast's target is on, and how that is known.

    The event's own flag wins. Otherwise membership of the fight's friendly lists
    (players, pets) or enemy list decides, also for a pet through its owner.
    A ground-placed ability (a trap) aimed at WCL's Environment placeholder has no
    unit target. Anything else, including a missing target ID, is undecided
    (None); actor type alone never decides.
    """
    if flag is not None:
        return bool(flag), "event-flag"
    if ground_placed and target == NO_UNIT_TARGET:
        return None, "no-unit-target"
    if target is None:
        return None, None
    for actor in (target, owner):
        if actor is None:
            continue
        if actor in sides.friendly:
            return True, "fight-friendly-list"
        if actor in sides.enemies:
            return False, "fight-enemy-list"
    return None, None


def _casts(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    ids_by_kind: dict[str, list[int]],
    ground_placed: frozenset[int] = frozenset(),
) -> Evidenced[tuple[Cast, ...]]:
    kind_of = {spell: kind for kind, ids in ids_by_kind.items() for spell in ids}
    rows = con.execute(
        """
        SELECT e.timestamp, e.ability_game_id, e.event_uid, e.copy_index, e.target_id,
               e.target_is_friendly, a.pet_owner
        FROM events e
        LEFT JOIN actors a ON a.report_code = e.report_code AND a.actor_id = e.target_id
        WHERE e.report_code = ? AND e.fight_id = ? AND e.type = 'cast' AND e.source_id = ?
          AND e.ability_game_id IN (SELECT unnest(?::BIGINT[]))
        ORDER BY e.timestamp, e.event_uid, e.copy_index
        """,
        [pf.report_code, pf.fight_id, pf.actor_id, list(kind_of)],
    ).fetchall()
    sides = _fight_sides(con, pf)
    casts: list[Cast] = []
    for ts, ability, uid, copy, target, friendly, owner in rows:
        target_id = None if target is None else int(target)
        side, source = _side(
            friendly,
            target_id,
            None if owner is None else int(owner),
            sides,
            int(ability) in ground_placed,
        )
        casts.append(
            Cast(
                t_s=pf.relative_s(int(ts)),
                timestamp=int(ts),
                kind=kind_of[int(ability)],
                event_uid=uid,
                copy_index=int(copy),
                target_id=target_id,
                target_friendly=side,
                side_source=source,
            )
        )
    ref = EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        pf.actor_id,
        [(c.event_uid, c.copy_index) for c in casts],
        detail=f"casts of {sorted(ids_by_kind)}",
    )
    return complete_or_unknown(
        tuple(casts), [coverage(con, pf, pf.actor_id, Direction.SOURCE)], ref
    )


def ground_placed_ids(entries: list[dict[str, Any]]) -> frozenset[int]:
    return frozenset(int(e["spell"]) for e in entries if e.get("ground_placed"))


def spell_groups(entries: list[dict[str, Any]]) -> dict[str, list[int]]:
    """Rule entries {spell, name} grouped by name; several IDs may share a name."""
    groups: dict[str, list[int]] = defaultdict(list)
    for entry in entries:
        groups[str(entry["name"])].append(int(entry["spell"]))
    return dict(groups)


def _stats(casts: Evidenced[tuple[Cast, ...]], kind: str, pf: ParticipantFight) -> CastStats:
    if casts.value is None:
        gone: Evidenced[tuple[Cast, ...]] = unknown(
            casts.note or "casts unknown", *casts.refs, coverage=casts.coverage
        )
        return CastStats(gone, unknown("casts unknown", *casts.refs, coverage=casts.coverage))
    mine = tuple(c for c in casts.value if c.kind == kind)
    ref = EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        pf.actor_id,
        [(c.event_uid, c.copy_index) for c in mine],
        detail=kind,
    )
    selected = complete_or_unknown(mine, casts.coverage, ref)
    minutes = pf.duration_ms / 60000.0
    return CastStats(selected, complete_or_unknown(len(mine) / minutes, casts.coverage, ref))


def _id_lists(entries: list[Any]) -> list[int]:
    return [int(e["spell"]) if isinstance(e, dict) else int(e) for e in entries]


def _overlaps(intervals: tuple[tuple[int, int], ...], start: int, end: int) -> bool:
    return any(lo < end and hi > start for lo, hi in intervals)


def _auto_intervals(
    casts: Evidenced[tuple[Cast, ...]],
    haste: Evidenced[tuple[tuple[int, int], ...]],
    pf: ParticipantFight,
) -> Evidenced[tuple[AutoInterval, ...]]:
    if casts.value is None:
        return unknown("casts unknown", *casts.refs, coverage=casts.coverage)
    autos = [c for c in casts.value if c.kind == "auto_shot"]
    specials = [c for c in casts.value if c.kind in INSIDE_KINDS]
    result: list[AutoInterval] = []
    for i, (start, end) in enumerate(itertools.pairwise(autos), start=1):
        inside: dict[str, list[float]] = defaultdict(list)
        for s in specials:
            if start.timestamp < s.timestamp <= end.timestamp:
                inside[s.kind].append(s.t_s)
        haste_ref = EvidenceRef.events(
            pf.report_code,
            pf.fight_id,
            pf.actor_id,
            [(start.event_uid, start.copy_index), (end.event_uid, end.copy_index)],
            detail="auto interval",
        )
        overlap: Evidenced[bool] = (
            unknown("ranged haste aura state unknown", haste_ref, coverage=haste.coverage)
            if haste.value is None
            else complete_or_unknown(
                _overlaps(haste.value, start.timestamp, end.timestamp), haste.coverage, haste_ref
            )
        )
        result.append(
            AutoInterval(
                index=i,
                start=start,
                end=end,
                gap_s=(end.timestamp - start.timestamp) / 1000.0,
                ranged_haste=overlap,
                inside={k: tuple(v) for k, v in inside.items()},
            )
        )
    return complete_or_unknown(tuple(result), casts.coverage, *casts.refs)


def _auto_gap(
    intervals: Evidenced[tuple[AutoInterval, ...]], pf: ParticipantFight
) -> AutoGapSignal:
    rule = _rules()["auto_gap"]
    threshold = float(rule["threshold"])
    if intervals.value is None:
        return AutoGapSignal(unknown("auto intervals unknown", *intervals.refs), 0, None, threshold)
    baseline = [iv for iv in intervals.value if iv.ranged_haste.value is False and not iv.inside]
    if len(baseline) < int(rule["min_baseline"]):
        return AutoGapSignal(
            unknown(
                f"only {len(baseline)} clean Auto intervals to compare against", *intervals.refs
            ),
            len(baseline),
            None,
            threshold,
        )
    median = statistics.median(iv.gap_s for iv in baseline)
    flagged = tuple(iv.index for iv in baseline if iv.gap_s > threshold * median)
    ref = EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        pf.actor_id,
        [(iv.end.event_uid, iv.end.copy_index) for iv in baseline if iv.index in flagged],
        detail="unusually long clean Auto intervals",
    )
    return AutoGapSignal(
        inferred(
            flagged,
            ref,
            *intervals.refs,
            rule_id=str(rule["rule"]),
            params={
                "threshold": threshold,
                "median_gap_s": median,
                "baseline_count": len(baseline),
            },
            note="advisory: possible clipping, movement or downtime; not a diagnosed clip",
        ),
        len(baseline),
        median,
        threshold,
    )


def _melee(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> tuple[Evidenced[int], Evidenced[int], Evidenced[int]]:
    rules = _rules()
    raptor_ids = [int(x) for x in rules["shots"]["raptor_strike"]]
    melee_ids = [int(x) for x in rules["melee_swing_abilities"]]
    by_ability = metrics.damage_by_ability(con, pf, [pf.actor_id])
    rows = con.execute(
        """
        SELECT count(*) FROM events WHERE report_code = ? AND fight_id = ? AND type = 'damage'
          AND source_id = ? AND ability_game_id IN (SELECT unnest(?::BIGINT[]))
        """,
        [pf.report_code, pf.fight_id, pf.actor_id, melee_ids],
    ).fetchone()
    if by_ability.value is None or rows is None:
        why = "damage events incomplete"
        return (unknown(why, *by_ability.refs, coverage=by_ability.coverage),) * 3
    raptor = sum(v for k, v in by_ability.value.items() if k in raptor_ids)
    white = sum(v for k, v in by_ability.value.items() if k in melee_ids)
    return (
        complete_or_unknown(raptor, by_ability.coverage, *by_ability.refs),
        complete_or_unknown(int(rows[0]), by_ability.coverage, *by_ability.refs),
        complete_or_unknown(white, by_ability.coverage, *by_ability.refs),
    )


def _pet_abilities(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, pet_id: int
) -> list[tuple[int, str, str, int]]:
    return con.execute(
        """
        SELECT DISTINCT e.ability_game_id, coalesce(a.name, ''), min(e.event_uid),
               min(e.copy_index)
        FROM events e
        LEFT JOIN abilities a ON a.report_code = e.report_code AND a.game_id = e.ability_game_id
        WHERE e.report_code = ? AND e.fight_id = ? AND e.source_id = ?
          AND e.type IN ('cast', 'damage')
        GROUP BY 1, 2 ORDER BY 1
        """,
        [pf.report_code, pf.fight_id, pet_id],
    ).fetchall()


def classify_pets(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> tuple[PetCategory, ...]:
    rules = _rules()
    by_game_id = {int(e["game_id"]): e for e in rules["non_hunter_pets"]}
    hunter_pet_abilities = (
        set(rules["pet_family_abilities"])
        | set(rules["hunter_pet_only_abilities"])
        | set(rules.get("pet_ability_aliases") or {})
    )
    result: list[PetCategory] = []
    for pet in owned_pets(con, pf):
        ref_actor = EvidenceRef(pf.report_code, None, pet.actor_id, "actors", detail="game_id")
        if pet.game_id is not None and pet.game_id in by_game_id:
            entry = by_game_id[pet.game_id]
            category: Evidenced[str] = derived(
                str(entry["category"]),
                ref_actor,
                rule_id="non-hunter-pet-gameid-v1",
                params={"game_id": pet.game_id},
            )
        else:
            used = _pet_abilities(con, pf, pet.actor_id)
            evidence = [
                (uid, int(copy)) for spell, name, uid, copy in used if name in hunter_pet_abilities
            ]
            if evidence:
                ref = EvidenceRef.events(
                    pf.report_code,
                    pf.fight_id,
                    pet.actor_id,
                    evidence,
                    detail="hunter-pet abilities",
                )
                category = inferred("hunter-pet", ref, rule_id="hunter-pet-ability-v1")
            else:
                cov = [coverage(con, pf, pet.actor_id, Direction.SOURCE)]
                category = unknown(
                    "no hunter-pet ability seen and no rule for its game ID",
                    ref_actor,
                    coverage=cov,
                )
        result.append(PetCategory(pet.actor_id, pet.name, pet.game_id, category))
    return tuple(result)


def _hunter_pet(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, pet: PetCategory
) -> HunterPet:
    families_by_ability: dict[str, list[str]] = _rules()["pet_family_abilities"]
    aliases: dict[str, str] = _rules().get("pet_ability_aliases") or {}
    raw = _pet_abilities(con, pf, pet.actor_id)
    used = [(spell, aliases.get(name, name), uid, copy) for spell, name, uid, copy in raw]
    ref = EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        pet.actor_id,
        [(uid, int(copy)) for _s, _n, uid, copy in used],
        detail="abilities used",
    )
    abilities = observed(tuple((int(s), n) for s, n, _u, _c in raw), ref)
    restricted = sorted({n for _s, n, _u, _c in used if n in families_by_ability})
    candidates: set[str] | None = None
    for name in restricted:
        fams = set(families_by_ability[name])
        candidates = fams if candidates is None else candidates & fams
    cand = tuple(sorted(candidates or ()))
    if len(cand) == 1:
        family: Evidenced[str] = inferred(
            cand[0], ref, rule_id="pet-family-abilities-v1", params={"abilities": tuple(restricted)}
        )
    else:
        family = unknown(
            "abilities do not identify a single family"
            if restricted
            else "no family-restricted ability seen",
            ref,
        )
    damage_by = metrics.damage_by_ability(con, pf, [pet.actor_id])
    if damage_by.value is None:
        damage: Evidenced[int] = unknown(
            "pet damage incomplete", *damage_by.refs, coverage=damage_by.coverage
        )
        dps: Evidenced[float] = unknown(
            "pet damage incomplete", *damage_by.refs, coverage=damage_by.coverage
        )
    else:
        total = sum(damage_by.value.values())
        damage = complete_or_unknown(total, damage_by.coverage, *damage_by.refs)
        dps = complete_or_unknown(
            total / (pf.duration_ms / 1000.0), damage_by.coverage, *damage_by.refs
        )
    return HunterPet(
        actor_id=pet.actor_id,
        name=pet.name,
        family=family,
        family_candidates=cand,
        abilities=abilities,
        damage=damage,
        dps=dps,
        activity=metrics.activity_window(con, pf, pet.actor_id),
        deaths=metrics.deaths(con, pf, pet.actor_id),
    )


def _gear_context(profile: EnvironmentProfile) -> GearContext:
    gear = profile.gear
    if gear.value is None:
        gone_item: Evidenced[GearItem] = unknown("gear unknown", *gear.refs)
        return GearContext(
            gone_item,
            unknown("gear unknown", *gear.refs),
            gone_item,
            gone_item,
            unknown("gear unknown", *gear.refs),
        )
    slots = {g.slot: g for g in gear.value}

    def slot(n: int) -> Evidenced[GearItem]:
        item = slots.get(n)
        return observed(item, *gear.refs) if item else unknown(f"slot {n} not recorded", *gear.refs)

    trinkets = tuple(slots[n] for n in SLOT_TRINKETS if n in slots)
    both_recorded = len(trinkets) == len(SLOT_TRINKETS)
    has_renataki = any(t.item_id == RENATAKI for t in trinkets)
    pull_note = "snapshot at the pull; trinket swaps are not tracked"
    return GearContext(
        ranged=slot(SLOT_RANGED),
        trinkets=observed(trinkets, *gear.refs)
        if both_recorded
        else unknown("trinket slots not both recorded", *gear.refs),
        main_hand=slot(SLOT_MAIN_HAND),
        off_hand=slot(SLOT_OFF_HAND),
        renataki_at_pull=observed(has_renataki, *gear.refs, note=pull_note)
        if both_recorded or has_renataki
        else unknown("trinket slots not both recorded", *gear.refs),
    )


def _starting_aura_ids(profile: EnvironmentProfile) -> frozenset[int] | None:
    auras = profile.starting_auras.value
    return None if auras is None else frozenset(a.ability_id for a in auras)


class HunterClassicEra:
    game = GAME
    class_id = HUNTER_CLASS_ID
    name = "Hunter"

    def analyze(
        self, con: duckdb.DuckDBPyConnection, pf: ParticipantFight, profile: EnvironmentProfile
    ) -> HunterAnalysis:
        rules = _rules()
        ids: dict[str, list[int]] = {k: [int(x) for x in v] for k, v in rules["shots"].items()}
        ids.update({k: [int(x) for x in v] for k, v in rules["cooldowns"].items()})
        explosives = spell_groups(rules["explosives"])
        crowd_control = spell_groups(rules["crowd_control"])
        casts = _casts(
            con,
            pf,
            {
                **ids,
                **{f"explosive:{k}": v for k, v in explosives.items()},
                **{f"cc:{k}": v for k, v in crowd_control.items()},
            },
            ground_placed_ids(rules["crowd_control"]),
        )
        at_start = _starting_aura_ids(profile)
        haste_ids = _id_lists(rules["ranged_haste_auras"])
        haste = metrics.aura_intervals(con, pf, pf.actor_id, haste_ids, at_start)
        intervals = _auto_intervals(casts, haste, pf)
        opener_kinds = {*SHOT_KINDS, "rapid_fire", "refocus"}
        if casts.value is None:
            opener: Evidenced[tuple[Cast, ...]] = unknown(
                "casts unknown", *casts.refs, coverage=casts.coverage
            )
            friendly: Evidenced[tuple[Cast, ...]] = unknown(
                "casts unknown", *casts.refs, coverage=casts.coverage
            )
        else:
            opener = complete_or_unknown(
                tuple(c for c in casts.value if c.kind in opener_kinds)[:OPENER_LENGTH],
                casts.coverage,
                *casts.refs,
            )
            cc_casts = tuple(c for c in casts.value if c.kind.startswith("cc:"))
            on_friends = tuple(c for c in cc_casts if c.target_friendly is True)
            undecided = sum(
                1 for c in cc_casts if c.target_friendly is None and c.side_source is None
            )
            friendly = (
                observed(
                    on_friends,
                    *casts.refs,
                    note=f"partial: {undecided} crowd-control casts on targets of unknown side",
                )
                if undecided
                else complete_or_unknown(on_friends, casts.coverage, *casts.refs)
            )
        quick_ids = [int(x) for x in rules["auras"]["quick_shots"]]
        procs = con.execute(
            """
            SELECT event_uid, copy_index FROM events
            WHERE report_code = ? AND fight_id = ? AND type = 'applybuff' AND target_id = ?
              AND ability_game_id IN (SELECT unnest(?::BIGINT[]))
            """,
            [pf.report_code, pf.fight_id, pf.actor_id, quick_ids],
        ).fetchall()
        procs_ref = EvidenceRef.events(
            pf.report_code,
            pf.fight_id,
            pf.actor_id,
            [(u, int(c)) for u, c in procs],
            detail="Quick Shots",
        )
        raptor, swings, white = _melee(con, pf)
        pets = classify_pets(con, pf)
        return HunterAnalysis(
            participant=pf,
            shots={k: _stats(casts, k, pf) for k in SHOT_KINDS},
            rapid_fire=_stats(casts, "rapid_fire", pf),
            refocus=_stats(casts, "refocus", pf),
            hunters_mark=_stats(casts, "hunters_mark", pf),
            explosives={k: _stats(casts, f"explosive:{k}", pf) for k in explosives},
            opener=opener,
            quick_shots_procs=complete_or_unknown(
                len(procs), [coverage(con, pf, pf.actor_id, Direction.TARGET)], procs_ref
            ),
            quick_shots_uptime_s=metrics.aura_uptime(con, pf, pf.actor_id, quick_ids, at_start),
            rapid_fire_uptime_s=metrics.aura_uptime(
                con, pf, pf.actor_id, [int(x) for x in rules["auras"]["rapid_fire"]], at_start
            ),
            friendly_crowd_control=friendly,
            auto_intervals=intervals,
            auto_gap=_auto_gap(intervals, pf),
            raptor_damage=raptor,
            white_melee_swings=swings,
            white_melee_damage=white,
            pets=pets,
            hunter_pets=tuple(
                _hunter_pet(con, pf, p) for p in pets if p.category.value == "hunter-pet"
            ),
            gear=_gear_context(profile),
        )


HUNTER = register(HunterClassicEra())
