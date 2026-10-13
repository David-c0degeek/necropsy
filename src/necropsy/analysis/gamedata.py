"""Static Classic Era knowledge from rule data: game client tables and cited encounter facts.

Nothing here is observed in a log. Item, set and enchant data come from the
game's own client tables (see rules/classic_era/game_data.yaml for the build);
encounter facts and ammunition advice cite the public page they were read from.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from typing import Any

from necropsy.rules import load_rules

GAME = "classic_era"
ARMOR_SLOTS = frozenset({"head", "shoulder", "chest", "waist", "legs", "feet", "wrist", "hands"})
"""Equipment slots that count as armor pieces of a set (not rings, trinkets or weapons)."""


@dataclass(frozen=True, slots=True)
class OnUse:
    """An item's use effect from the client's ItemEffect table."""

    spell: int
    cooldown_s: float
    category: int
    """Shared cooldown category; 0 when the item shares none."""
    category_cooldown_s: float
    """Lockout put on every other item of the same category; 0 or less when none."""


@dataclass(frozen=True, slots=True)
class GameItem:
    id: int
    name: str
    ranged_type: str | None = None
    uses_ammo: str | None = None
    ammo: str | None = None
    slot: str | None = None
    on_use: OnUse | None = None


@cache
def _data() -> dict[str, Any]:
    return dict(load_rules(GAME, "game_data"))


@cache
def items() -> dict[int, GameItem]:
    return {
        int(i["id"]): GameItem(
            int(i["id"]),
            str(i["name"]),
            i.get("ranged_type"),
            i.get("uses_ammo"),
            i.get("ammo"),
            i.get("slot"),
            None
            if not i.get("on_use")
            else OnUse(
                int(i["on_use"]["spell"]),
                int(i["on_use"]["cooldown_ms"]) / 1000,
                int(i["on_use"]["category"]),
                int(i["on_use"]["category_cooldown_ms"]) / 1000,
            ),
        )
        for i in _data()["items"]
    }


@cache
def enchant_names() -> dict[int, str]:
    return {int(e["id"]): str(e["name"]) for e in _data()["enchants"]}


@cache
def item_sets() -> tuple[tuple[int, str, frozenset[int]], ...]:
    return tuple(
        (int(s["id"]), str(s["name"]), frozenset(int(i) for i in s["items"]))
        for s in _data()["item_sets"]
    )


def source() -> dict[str, Any]:
    return dict(_data()["source"])


def set_pieces(item_ids: Iterable[int]) -> tuple[tuple[str, int], ...]:
    """Item sets worn with at least two pieces, by piece count (then name)."""
    worn = set(item_ids)
    counts: Counter[str] = Counter()
    for _set_id, name, members in item_sets():
        n = len(worn & members)
        if n >= 2:
            counts[name] = max(counts[name], n)
    return tuple(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


@dataclass(frozen=True, slots=True)
class SetArmor:
    """One worn item set: armor-slot pieces apart from its other members (rings etc.)."""

    set: str
    armor_pieces: int
    other_pieces: int
    other_slots: tuple[str, ...]
    """Slots of the worn non-armor members, e.g. ("finger",)."""


def set_armor(item_ids: Iterable[int]) -> tuple[SetArmor, ...]:
    """Worn sets with at least two pieces, splitting armor slots from other members.

    Same order as `set_pieces`; an item whose slot is not in the client data counts
    as an other piece with slot "unknown".
    """
    worn = set(item_ids)
    best: dict[str, SetArmor] = {}
    for _set_id, name, members in item_sets():
        hit = worn & members
        if len(hit) < 2:
            continue
        slots = [items()[i].slot if i in items() else None for i in sorted(hit)]
        armor = sum(1 for s in slots if s in ARMOR_SLOTS)
        others = tuple(sorted(s or "unknown" for s in slots if s not in ARMOR_SLOTS))
        found = SetArmor(name, armor, len(others), others)
        if name not in best or len(hit) > best[name].armor_pieces + best[name].other_pieces:
            best[name] = found
    return tuple(sorted(best.values(), key=lambda s: (-(s.armor_pieces + s.other_pieces), s.set)))


@dataclass(frozen=True, slots=True)
class AmmoAdvice:
    ranged_item: int | None
    ranged_type: str | None
    uses_ammo: str | None
    recommended_id: int | None
    recommended_name: str | None
    dps_bonus: float | None
    source: str | None
    rule: str
    reason: str | None = None


def ammo_advice(ranged_item: int | None) -> AmmoAdvice:
    """The recommended endgame ammunition for this ranged weapon's ammunition type."""
    rule = load_rules(GAME, "hunter")["ammunition_advice"]
    rule_id = str(rule["rule"])
    item = None if ranged_item is None else items().get(ranged_item)
    if item is None or item.uses_ammo is None:
        why = (
            "ranged weapon unknown"
            if ranged_item is None
            else "ammunition type of the ranged weapon unknown"
        )
        return AmmoAdvice(
            ranged_item,
            None if item is None else item.ranged_type,
            None,
            None,
            None,
            None,
            None,
            rule_id,
            why,
        )
    pick = rule.get(item.uses_ammo)
    if not pick:
        return AmmoAdvice(
            ranged_item,
            item.ranged_type,
            item.uses_ammo,
            None,
            None,
            None,
            None,
            rule_id,
            f"no advice for {item.uses_ammo}s",
        )
    return AmmoAdvice(
        ranged_item,
        item.ranged_type,
        item.uses_ammo,
        int(pick["id"]),
        str(pick["name"]),
        float(pick["dps_bonus"]),
        str(pick["source"]),
        rule_id,
    )


@dataclass(frozen=True, slots=True)
class RapidFire:
    """Rapid Fire as the worn sets leave it (base values from the client data)."""

    duration_s: float
    cooldown_s: float
    ranged_haste_pct: float
    applied: tuple[str, ...]
    """Set bonuses applied, e.g. "Cryptstalker Armor (2): +4 s duration"."""
    known: bool
    """False when the gear is unknown: base values, set bonuses not checked."""
    rule: str
    source: str


def rapid_fire(worn: Iterable[int] | None) -> RapidFire:
    facts = load_rules(GAME, "hunter")["cooldown_facts"]
    rf = facts["rapid_fire"]
    duration, cooldown = float(rf["duration_s"]), float(rf["cooldown_s"])
    applied: list[str] = []
    if worn is not None:
        worn_ids = set(worn)
        members = {sid: m for sid, _name, m in item_sets()}
        for mod in rf.get("modifiers") or ():
            have = len(worn_ids & members.get(int(mod["set_id"]), frozenset()))
            if have >= int(mod["pieces"]):
                if "duration_s" in mod:
                    duration += float(mod["duration_s"])
                    applied.append(
                        f"{mod['set']} ({mod['pieces']}): +{mod['duration_s']} s duration"
                    )
                if "cooldown_s" in mod:
                    cooldown += float(mod["cooldown_s"])
                    applied.append(
                        f"{mod['set']} ({mod['pieces']}): {mod['cooldown_s']} s cooldown"
                    )
    return RapidFire(
        duration,
        cooldown,
        float(rf["ranged_haste_pct"]),
        tuple(applied),
        worn is not None,
        str(facts["rule"]),
        str(facts["source"]),
    )


@dataclass(frozen=True, slots=True)
class PetProfile:
    key: str
    label: str
    total_tp: int
    budget_tp: int
    fits: bool
    parts: tuple[tuple[str, int, int], ...]
    """(ability, rank, training points of that rank)."""


@dataclass(frozen=True, slots=True)
class FamilyModifier:
    family: str
    health: float
    armor: float
    damage: float


@dataclass(frozen=True)
class PetFacts:
    """General Hunter pet knowledge; never a claim about the subject's pet."""

    rule: str
    budget_tp: int
    budget_text: str
    cumulative_note: str
    frost_resistance: tuple[tuple[int, int, int, int], ...]
    """(rank, resistance, pet level, training points)."""
    profiles: tuple[PetProfile, ...]
    family_modifiers: tuple[FamilyModifier, ...]
    sources: dict[str, tuple[str, ...]]


def _rank_tp(data: dict[str, Any], ability: str, rank: int) -> int:
    if ability in data["passive_ranks"]:
        for row in data["passive_ranks"][ability]:
            if int(row["rank"]) == rank:
                return int(row["tp"])
        raise KeyError(f"{ability} rank {rank} not in pet facts")
    active = data["active_ranks"][ability]
    if active["rank"] is not None and int(active["rank"]) != rank:
        raise KeyError(f"{ability} rank {rank}: only rank {active['rank']} is listed")
    return int(active["tp"])


@cache
def pet_facts() -> PetFacts:
    data = load_rules(GAME, "hunter")["pet_facts"]
    tp = data["training_points"]
    budget = int(tp["max"])
    profiles = []
    for prof in data["profiles"]:
        parts = tuple(
            (ability, int(rank), _rank_tp(data, ability, int(rank)))
            for ability, rank in prof["ranks"].items()
        )
        total = sum(p[2] for p in parts)
        profiles.append(
            PetProfile(str(prof["key"]), str(prof["label"]), total, budget, total <= budget, parts)
        )
    return PetFacts(
        str(data["rule"]),
        budget,
        str(tp["budget"]),
        " ".join(str(tp["note"]).split()),
        tuple(
            (int(r["rank"]), int(r["resistance"]), int(r["pet_level"]), int(r["tp"]))
            for r in data["passive_ranks"]["frost_resistance"]
        ),
        tuple(profiles),
        tuple(
            FamilyModifier(str(f), float(m["health"]), float(m["armor"]), float(m["damage"]))
            for f, m in data["family_modifiers"].items()
        ),
        {
            "training_points": tuple(str(s) for s in tp["sources"]),
            "passive_ranks": (str(data["passive_ranks_source"]),),
            "active_ranks": (str(data["active_ranks_source"]),),
            "family_modifiers": (str(data["family_modifiers_source"]),),
        },
    )


@dataclass(frozen=True, slots=True)
class Timing:
    key: str
    text: str
    at_s: float | None = None
    every_s: float | None = None
    after_s: float | None = None
    duration_s: float | None = None
    at_health_pct: float | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class EncounterFacts:
    encounter_id: int
    creature_type: str | None
    source: str | None
    note: str | None
    timings: tuple[Timing, ...]
    rule: str
    retrieved: str
    type_source: str | None = None
    """Page the creature type was read from, when it is not `source`."""


@cache
def encounter_facts(zone: str, encounter_id: int) -> EncounterFacts | None:
    data = load_rules(GAME, f"zones/{zone}_facts")
    for e in data["encounters"]:
        if int(e["id"]) == encounter_id:
            return EncounterFacts(
                encounter_id,
                e.get("creature_type"),
                e.get("source"),
                e.get("note"),
                tuple(
                    Timing(**{k: v for k, v in t.items() if k in Timing.__slots__})
                    for t in e.get("timings") or ()
                ),
                str(data["rule"]),
                str(data["retrieved"]),
                e.get("type_source"),
            )
    return None


@dataclass(frozen=True, slots=True)
class TypeBonus:
    item_id: int
    name: str
    effect: str
    applies: bool | None
    """None when the boss's creature type is not known."""
    source: str


def creature_type_bonuses(zone: str, encounter_id: int) -> tuple[TypeBonus, ...]:
    facts = encounter_facts(zone, encounter_id)
    creature = None if facts is None else facts.creature_type
    out = []
    for i in load_rules(GAME, f"zones/{zone}_facts").get("creature_type_items") or ():
        applies = None if creature is None else creature in i["applies_to"]
        out.append(
            TypeBonus(int(i["id"]), str(i["name"]), str(i["effect"]), applies, str(i["source"]))
        )
    return tuple(out)


__all__ = [
    "AmmoAdvice",
    "EncounterFacts",
    "FamilyModifier",
    "GameItem",
    "OnUse",
    "PetFacts",
    "PetProfile",
    "RapidFire",
    "SetArmor",
    "TypeBonus",
    "ammo_advice",
    "creature_type_bonuses",
    "enchant_names",
    "encounter_facts",
    "item_sets",
    "items",
    "pet_facts",
    "rapid_fire",
    "set_armor",
    "set_pieces",
    "source",
]
