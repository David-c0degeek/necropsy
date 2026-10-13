"""Zone-wide summaries for the playbook's overview (rule set overview-v1).

Global setup aggregates the same-faction entries of every boss; corrections list,
per boss, what changes once other-faction entries are set aside. Counts always
come with how many entries were known, and names come from the game client data.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from necropsy.analysis import gamedata
from necropsy.analysis.benchmark import (
    BossData,
    Entry,
    PetFamilies,
    pet_families,
    split_by_faction,
    weave_adoption,
)
from necropsy.analysis.evidence import EvidenceLevel

RULE_SET = "overview-v1"
RANGED, HANDS = 17, 9


@dataclass(frozen=True, slots=True)
class Count:
    key: str
    count: int


@dataclass(frozen=True, slots=True)
class Tally:
    """How often each value appears among entries whose value is known."""

    counts: tuple[Count, ...]
    known: int
    unknown: int


def _tally(values: Iterable[str | None]) -> Tally:
    items = list(values)
    known = [v for v in items if v is not None]
    counter = Counter(known)
    return Tally(
        tuple(Count(k, n) for k, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))),
        len(known),
        len(items) - len(known),
    )


def _slot_item(e: Entry, slot: int) -> str | None:
    gear = e.profile.gear.value
    if gear is None:
        return None
    for g in gear:
        if g.slot == slot and g.item_id:
            found = gamedata.items().get(g.item_id)
            return found.name if found else f"item {g.item_id}"
    return None


def _ranged_enchant(e: Entry) -> str | None:
    gear = e.profile.gear.value
    if gear is None:
        return None
    for g in gear:
        if g.slot == RANGED:
            if not g.permanent_enchant:
                return "none"
            return gamedata.enchant_names().get(
                g.permanent_enchant, f"enchant {g.permanent_enchant}"
            )
    return None


def _sets(e: Entry) -> tuple[gamedata.SetArmor, ...] | None:
    gear = e.profile.gear.value
    return None if gear is None else gamedata.set_armor(g.item_id for g in gear if g.item_id)


def _armor(e: Entry) -> str | None:
    """Armor-slot pieces of the main worn set; rings and other members are not armor."""
    sets = _sets(e)
    if sets is None:
        return None
    return "no set" if not sets else f"{sets[0].armor_pieces}-piece {sets[0].set}"


def _set_extras(e: Entry) -> str | None:
    """Non-armor members worn with the main set (e.g. its ring), or "none"."""
    sets = _sets(e)
    if sets is None:
        return None
    if not sets or not sets[0].other_slots:
        return "none"
    return f"{sets[0].set}: " + ", ".join(sets[0].other_slots)


def _engineering(e: Entry) -> bool:
    return any(p.category.value == "engineering" for p in e.hunter.pets)


def _explosives(e: Entry) -> bool | None:
    casts = [s.casts.value for s in e.hunter.explosives.values()]
    if any(c is None for c in casts):
        return None
    return any(c for c in casts)


@dataclass(frozen=True, slots=True)
class BossRenataki:
    boss: str
    users: int
    known: int


@dataclass(frozen=True)
class GlobalSetup:
    entries: int
    talents: Tally
    darkmoon: Tally
    ranged_weapon: Tally
    ranged_enchant: Tally
    armor_pattern: Tally
    """Armor-slot pieces of each entry's main set (rings etc. not counted)."""
    set_extras: Tally
    """Non-armor members of the main set worn alongside it, by slot."""
    hands: Tally
    pet_families: PetFamilies
    engineering_pet_users: int
    explosive_users: Tally
    renataki_by_boss: tuple[BossRenataki, ...]
    pet_facts: gamedata.PetFacts
    """General pet knowledge (training budget, profiles, family modifiers); not logged."""
    subject_ammo: gamedata.AmmoAdvice
    faction: str | None
    faction_level: str


@dataclass(frozen=True, slots=True)
class Correction:
    boss: str
    rank_one_player: str | None
    rank_one_faction: str | None
    rank_one_race: str | None
    rank_one_race_proven: bool
    rank_one_windfury: str | None
    same_faction_weavers: tuple[tuple[str, int], ...]
    """(player, Raptor Strikes) for same-faction entries with at least one."""
    pure_ranged_reference: tuple[str, float | None] | None
    """Best-ranked same-faction entry with no Raptor Strike (player, ranked DPS)."""
    verdict_same_faction: str | None
    verdict_all_entries: str | None


@dataclass(frozen=True)
class Overview:
    rule_set: str
    recorded_entries: int
    by_faction: tuple[Count, ...]
    inferred_faction_entries: int
    setup: GlobalSetup
    corrections: tuple[Correction, ...]


def _raptors(e: Entry) -> int | None:
    casts = e.hunter.shots["raptor_strike"].casts.value
    return None if casts is None else len(casts)


def build(bosses: list[BossData]) -> Overview:
    pool: list[Entry] = []
    everyone: list[Entry] = []
    renataki = []
    corrections = []
    for boss in bosses:
        everyone.extend(boss.cohort)
        split = split_by_faction(boss)
        same = () if split is None else split.same_faction
        pool.extend(same)
        worn = [e.hunter.gear.renataki_at_pull.value for e in same]
        renataki.append(
            BossRenataki(
                boss.boss, sum(1 for w in worn if w), sum(1 for w in worn if w is not None)
            )
        )
        rank_one = next((e for e in boss.cohort if e.participant.leaderboard_position == 1), None)
        weavers = tuple((e.participant.player, r) for e in same if (r := _raptors(e)))
        ranged_only = [e for e in same if _raptors(e) == 0]
        best = min(
            ranged_only, key=lambda e: e.participant.leaderboard_position or 99, default=None
        )
        corrections.append(
            Correction(
                boss.boss,
                None if rank_one is None else rank_one.participant.player,
                None
                if rank_one is None or rank_one.profile.faction.value is None
                else str(rank_one.profile.faction.value.value),
                None if rank_one is None else rank_one.profile.race.race.value,
                rank_one is not None and rank_one.profile.race.race.level is EvidenceLevel.OBSERVED,
                None if rank_one is None else str(rank_one.profile.windfury.status.value),
                weavers,
                None
                if best is None
                else (
                    best.participant.player,
                    None if best.ranked_dps is None else round(best.ranked_dps, 2),
                ),
                weave_adoption(same).boss.verdict.value if same else None,
                weave_adoption(boss.cohort).boss.verdict.value if boss.cohort else None,
            )
        )
    by = Counter(
        "unknown" if e.profile.faction.value is None else str(e.profile.faction.value.value)
        for e in everyone
    )
    subjects = [b.subject for b in bosses if b.subject is not None]
    factions = {s.profile.faction.value for s in subjects if s.profile.faction.value is not None}
    faction = None if len(factions) != 1 else next(iter(factions))
    levels = {s.profile.faction.level for s in subjects if s.profile.faction.value is not None}
    ranged = subjects[0].hunter.gear.ranged.value if subjects else None
    setup = GlobalSetup(
        entries=len(pool),
        talents=_tally(e.profile.talents.value for e in pool),
        darkmoon=_tally(e.profile.darkmoon_faire.value for e in pool),
        ranged_weapon=_tally(_slot_item(e, RANGED) for e in pool),
        ranged_enchant=_tally(_ranged_enchant(e) for e in pool),
        armor_pattern=_tally(_armor(e) for e in pool),
        set_extras=_tally(_set_extras(e) for e in pool),
        hands=_tally(_slot_item(e, HANDS) for e in pool),
        pet_families=pet_families(pool),
        engineering_pet_users=sum(1 for e in pool if _engineering(e)),
        explosive_users=_tally(
            None if (x := _explosives(e)) is None else ("used" if x else "not used") for e in pool
        ),
        renataki_by_boss=tuple(renataki),
        pet_facts=gamedata.pet_facts(),
        subject_ammo=gamedata.ammo_advice(None if ranged is None else ranged.item_id or None),
        faction=None if faction is None else str(faction.value),
        faction_level="unknown"
        if faction is None
        else ("inferred" if EvidenceLevel.INFERRED in levels else "observed"),
    )
    return Overview(
        RULE_SET,
        len(everyone),
        tuple(Count(k, n) for k, n in sorted(by.items())),
        sum(1 for e in everyone if e.profile.faction.level is EvidenceLevel.INFERRED),
        setup,
        tuple(corrections),
    )


__all__ = ["Overview", "build"]
