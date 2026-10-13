"""Structured per-boss playbook decisions (rule set playbook-v1).

These are the facts and named decisions behind the playbook's Benchmark
context, Loadout plan, Execution plan, Do not and Raid ask sections. They are
data, not prose: the renderer words them. Every list names the entries it was
built from, and anything that is not known stays None with a reason. Same-faction
entries drive advice; other-faction entries appear only as context (for example
the melee package that is not a fair benchmark).
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from necropsy.analysis import gamedata, guidance
from necropsy.analysis.benchmark import Baseline, BossData, Entry, RaidSpeed, hunter_pet_dps
from necropsy.analysis.encounters.findings import RaidUtility, TargetIntegrity
from necropsy.analysis.evidence import EvidenceLevel, WindfuryStatus
from necropsy.rules import load_rules

RULE_SET = "playbook-v1"
ZONE = "naxxramas"


def _cfg() -> dict[str, Any]:
    return dict(load_rules("classic_era", "benchmarks")["playbook"])


# -- small per-entry readers ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Who:
    player: str
    leaderboard_position: int | None
    faction: str | None
    ranked_dps: float | None


def who(e: Entry) -> Who:
    faction = e.profile.faction.value
    return Who(
        e.participant.player,
        e.participant.leaderboard_position,
        None if faction is None else str(faction.value),
        None if e.ranked_dps is None else round(e.ranked_dps, 2),
    )


def _item(value: Any) -> int | None:
    return None if value is None else int(value.item_id) or None


def _weapons(e: Entry) -> tuple[int | None, int | None, int | None] | None:
    g = e.hunter.gear
    if g.ranged.value is None or g.main_hand.value is None or g.off_hand.value is None:
        return None
    return (_item(g.main_hand.value), _item(g.off_hand.value), _item(g.ranged.value))


def _trinkets(e: Entry) -> tuple[int, ...] | None:
    value = e.hunter.gear.trinkets.value
    if value is None:
        return None
    return tuple(sorted(i.item_id for i in value if i.item_id))


def _count(evidence: Any) -> int | None:
    value = evidence.value
    return None if value is None else len(value)


def _first_t(evidence: Any) -> float | None:
    value = evidence.value
    if value is None or not value:
        return None
    return float(value[0].t_s)


MIN_KNOWN = 3


@dataclass(frozen=True, slots=True)
class Aggregate:
    """A cohort statistic with its sample and how far it can be trusted."""

    value: float | None
    level: str
    """`derived`, `inferred` (inferred cohort membership) or `unknown`."""
    n_values: int
    """Entries that contributed a value (for timings: entries that cast it)."""
    n_without: int
    """Entries known not to have a value (for timings: known, never cast)."""
    n_unknown: int
    """Entries whose input is unknown."""
    reason: str | None = None


def aggregate(
    values: Iterable[float | _NoValue | None], inferred_membership: bool, how: str = "median"
) -> Aggregate:
    """Median of the known values; needs MIN_KNOWN of them, else unknown with a reason.

    `NO_VALUE` marks an entry known to have no value (e.g. never cast the spell),
    which is not a timing and is counted separately from unknown inputs.
    """
    items = list(values)
    known = [float(v) for v in items if isinstance(v, (int, float))]
    without = sum(1 for v in items if v is NO_VALUE)
    missing = len(items) - len(known) - without
    if len(known) < MIN_KNOWN:
        return Aggregate(
            None,
            "unknown",
            len(known),
            without,
            missing,
            f"{len(known)} of {len(known) + without} known entries cast it "
            f"(need {MIN_KNOWN} timings)"
            if without
            else f"only {len(known)} known values (need {MIN_KNOWN})",
        )
    if how == "min":
        value = min(known)
    elif how == "max":
        value = max(known)
    else:
        value = float(statistics.median(known))
    level = "inferred" if inferred_membership else "derived"
    reason = "comparison group rests on an inferred faction" if inferred_membership else None
    return Aggregate(round(value, 4), level, len(known), without, missing, reason)


class _NoValue:
    def __repr__(self) -> str:
        return "NO_VALUE"


NO_VALUE = _NoValue()


# -- decisions --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WeaponSet:
    main_hand: int | None
    off_hand: int | None
    ranged: int | None
    entries: tuple[Who, ...]
    raptor_users: int
    """How many of these entries cast at least one Raptor Strike."""


@dataclass(frozen=True, slots=True)
class MeleePackage:
    """An other-faction entry whose melee output rests on things this character lacks."""

    entry: Who
    race: str | None
    race_proven: bool
    windfury_status: str
    windfury_procs: int | None
    white_swings: int | None
    white_damage: int | None
    white_dps: float | None
    windfury_matched_damage: int | None
    """Damage of the swings uniquely matched to Windfury procs (rule-based matching)."""
    windfury_matched_level: str
    """`inferred` when matched, else `unknown`: matching is inference, not proof of
    the damage Windfury caused, and not a bound on it."""
    raptor_casts: int | None
    weapons: tuple[int | None, int | None, int | None] | None


@dataclass(frozen=True, slots=True)
class TrinketPair:
    items: tuple[int, ...]
    entries: tuple[Who, ...]


@dataclass(frozen=True, slots=True)
class PetPlan:
    subject_pet: str | None
    subject_family: str | None
    subject_family_level: str
    subject_dps: float | None
    subject_stopped_early_s: float | None
    subject_died_at_s: float | None
    no_hunter_pet: bool | None
    """True when it is known that no Hunter pet took part; None when not known."""
    same_faction_median_dps: Aggregate
    same_faction_dps_min: Aggregate
    same_faction_dps_max: Aggregate


@dataclass(frozen=True, slots=True)
class WeaveEntry:
    entry: Who
    raptors_total: int | None
    raptors_on_boss: int | None
    raptors_on_others: int | None
    windfury_status: str


@dataclass(frozen=True, slots=True)
class WeavingPlan:
    boss_verdict: str | None
    non_boss_verdict: str | None
    same_faction: tuple[WeaveEntry, ...]
    other_faction_heavy: tuple[WeaveEntry, ...]
    """Other-faction entries with five or more Raptor Strikes (context only)."""
    subject: WeaveEntry | None


@dataclass(frozen=True, slots=True)
class TimedEntry:
    entry: Who
    first_s: float | None
    used: bool | None = None
    """False when the casts are complete and empty (a proven non-use); None when
    the casts are unknown, so `first_s` None alone never means "not cast"."""


@dataclass(frozen=True, slots=True)
class OpenerPlan:
    subject_sequence: tuple[tuple[float, str], ...] | None
    comparator_sequence: tuple[tuple[float, str], ...] | None
    subject_first_aimed_s: float | None
    comparator_first_aimed_s: float | None
    same_faction_first_aimed_s: Aggregate
    renataki_users: int
    renataki_known: int
    weave_on_boss: str | None


@dataclass(frozen=True, slots=True)
class CooldownPlan:
    subject_first_s: float | None
    subject_used: bool | None
    """None when the casts are unknown; False when known and none was cast."""
    rank_one: TimedEntry | None
    same_faction_first_s: Aggregate
    overall_first_s: Aggregate
    """Every recorded entry of any faction; context only."""


@dataclass(frozen=True, slots=True)
class DoNot:
    kind: str
    """`other-faction-melee-package`, `idle-pet`, `long-auto-gaps` or `padded-comparison`."""
    details: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RaidAsk:
    kind: str
    """`raid-speed`, `already-faster-than-rank-one`, `raid-utility`, `padding-strategy`."""
    details: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class BenchmarkContext:
    by_faction: Mapping[str, int]
    inferred_faction_entries: int
    same_faction_entries: int
    comparator: Who | None
    overall_top: Who | None
    membership_level: str
    small_sample: bool


@dataclass(frozen=True, slots=True)
class TypeBonusUse:
    item_id: int
    name: str
    effect: str
    applies_to_boss: bool | None
    source: str
    subject_wears: bool | None
    same_faction_wearers: int
    same_faction_known: int


@dataclass(frozen=True)
class StaticFacts:
    """Cited game knowledge for this boss (rules, not observations)."""

    encounter: gamedata.EncounterFacts | None
    ammo: gamedata.AmmoAdvice
    type_bonuses: tuple[TypeBonusUse, ...]
    guidance: guidance.Guidance | None = None
    """General advice from cited facts, with snapshot conditions (never observations)."""


@dataclass(frozen=True)
class BossPlaybook:
    rule_set: str
    context: BenchmarkContext
    weapons: tuple[WeaponSet, ...]
    subject_weapons: tuple[int | None, int | None, int | None] | None
    melee_packages: tuple[MeleePackage, ...]
    trinket_pairs: tuple[TrinketPair, ...]
    subject_trinkets: tuple[int, ...] | None
    pet: PetPlan
    weaving: WeavingPlan
    opener: OpenerPlan
    rapid_fire: CooldownPlan
    refocus: CooldownPlan
    do_not: tuple[DoNot, ...]
    raid_asks: tuple[RaidAsk, ...]
    static: StaticFacts | None = None
    limitations: tuple[str, ...] = field(default=())


def _weave_entry(e: Entry) -> WeaveEntry:
    roles = e.raptor_roles.value
    return WeaveEntry(
        who(e),
        _count(e.hunter.shots["raptor_strike"].casts),
        None if roles is None else roles.boss,
        None if roles is None else roles.non_boss,
        str(e.profile.windfury.status.value),
    )


def _melee_package(e: Entry, min_swings: int) -> MeleePackage | None:
    wf = e.profile.windfury
    swings = e.hunter.white_melee_swings.value
    confirmed = wf.status is WindfuryStatus.CONFIRMED
    if not confirmed and (swings is None or swings < min_swings):
        return None
    damage = e.hunter.white_melee_damage.value
    seconds = e.participant.duration_ms / 1000.0
    race = e.profile.race
    return MeleePackage(
        who(e),
        race.race.value,
        race.race.level is EvidenceLevel.OBSERVED,
        str(wf.status.value),
        wf.procs.value,
        swings,
        damage,
        None if damage is None or seconds <= 0 else round(damage / seconds, 2),
        wf.attributed_damage.value,
        str(wf.attributed_damage.level.value),
        _count(e.hunter.shots["raptor_strike"].casts),
        _weapons(e),
    )


def _cooldown(
    subject: Entry,
    same: tuple[Entry, ...],
    overall: tuple[Entry, ...],
    rank_one: Entry | None,
    key: str,
    inferred_membership: bool = False,
) -> CooldownPlan:
    def stats(e: Entry) -> Any:
        return e.hunter.rapid_fire if key == "rapid_fire" else e.hunter.refocus

    def timing(e: Entry) -> float | _NoValue | None:
        value = stats(e).casts.value
        if value is None:
            return None
        return NO_VALUE if not value else float(value[0].t_s)

    casts = stats(subject).casts
    return CooldownPlan(
        subject_first_s=_first_t(casts),
        subject_used=None if casts.value is None else bool(casts.value),
        rank_one=None
        if rank_one is None
        else TimedEntry(
            who(rank_one),
            _first_t(stats(rank_one).casts),
            None if stats(rank_one).casts.value is None else bool(stats(rank_one).casts.value),
        ),
        same_faction_first_s=aggregate((timing(e) for e in same), inferred_membership),
        overall_first_s=aggregate((timing(e) for e in overall), False),
    )


def _sequence(e: Entry, limit: int) -> tuple[tuple[float, str], ...] | None:
    opener = e.hunter.opener.value
    if opener is None:
        return None
    return tuple((round(c.t_s, 2), str(c.kind)) for c in opener[:limit])


def build(
    boss: BossData,
    same: tuple[Entry, ...],
    other: tuple[Entry, ...],
    base: Baseline,
    comparator: Entry | None,
    speed: RaidSpeed | None,
    utility: RaidUtility | None,
    integrity: TargetIntegrity | None,
    cohort_foreign_median: float | None,
) -> BossPlaybook | None:
    subject = boss.subject
    if subject is None:
        return None
    cfg = _cfg()
    overall = boss.cohort
    rank_one = next((e for e in overall if e.participant.leaderboard_position == 1), None)
    limitations: list[str] = []

    # Benchmark context
    by: dict[str, int] = {}
    inferred_n = 0
    for e in overall:
        key = "unknown" if e.profile.faction.value is None else str(e.profile.faction.value.value)
        by[key] = by.get(key, 0) + 1
        inferred_n += e.profile.faction.level is EvidenceLevel.INFERRED
    context = BenchmarkContext(
        dict(sorted(by.items())),
        inferred_n,
        len(same),
        None if comparator is None else who(comparator),
        None if rank_one is None else who(rank_one),
        str(base.membership.level.value),
        len(same) < 3,
    )

    # Weapons: same-faction sets, plus other-faction melee packages as context
    sets: dict[tuple[int | None, int | None, int | None], list[Entry]] = {}
    unknown_weapons = 0
    for e in same:
        w = _weapons(e)
        if w is None:
            unknown_weapons += 1
            continue
        sets.setdefault(w, []).append(e)
    weapon_sets = tuple(
        WeaponSet(
            *w,
            tuple(who(e) for e in entries),
            sum(1 for e in entries if (_count(e.hunter.shots["raptor_strike"].casts) or 0) > 0),
        )
        for w, entries in sorted(sets.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))
    )
    if unknown_weapons:
        limitations.append(f"{unknown_weapons} same-faction entries have unrecorded weapons")
    packages = tuple(
        p for p in (_melee_package(e, int(cfg["melee_package_min_swings"])) for e in other) if p
    )

    # Trinkets
    pairs: dict[tuple[int, ...], list[Entry]] = {}
    for e in same:
        t = _trinkets(e)
        if t is not None:
            pairs.setdefault(t, []).append(e)
    trinket_pairs = tuple(
        TrinketPair(items, tuple(who(e) for e in entries))
        for items, entries in sorted(pairs.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    )
    renataki = [e.hunter.gear.renataki_at_pull.value for e in same]

    # Pet
    pet = subject.hunter.hunter_pets[0] if len(subject.hunter.hunter_pets) == 1 else None
    no_pet: bool | None
    if not subject.pets_listed or any(p.category.value is None for p in subject.hunter.pets):
        no_pet = None
    else:
        no_pet = not subject.hunter.hunter_pets
    weak = base.membership.level is not EvidenceLevel.DERIVED
    same_dps = [hunter_pet_dps(e).value for e in same]
    deaths = None if pet is None else pet.deaths.deaths.value
    activity = None if pet is None else pet.activity.value
    pet_plan = PetPlan(
        subject_pet=None if pet is None else pet.name,
        subject_family=None if pet is None else pet.family.value,
        subject_family_level="unknown" if pet is None else str(pet.family.level.value),
        subject_dps=None if pet is None else pet.dps.value,
        subject_stopped_early_s=None if activity is None else activity.last_damage_before_end_s,
        subject_died_at_s=None if not deaths else round(deaths[0].t_s, 2),
        no_hunter_pet=no_pet,
        same_faction_median_dps=aggregate(same_dps, weak),
        same_faction_dps_min=aggregate(same_dps, weak, "min"),
        same_faction_dps_max=aggregate(same_dps, weak, "max"),
    )

    # Weaving
    weaving = WeavingPlan(
        boss_verdict=base.weave.boss.verdict.value,
        non_boss_verdict=base.weave.non_boss.verdict.value,
        same_faction=tuple(_weave_entry(e) for e in same),
        other_faction_heavy=tuple(
            _weave_entry(e)
            for e in other
            if (_count(e.hunter.shots["raptor_strike"].casts) or 0) >= int(cfg["heavy_raptors"])
        ),
        subject=_weave_entry(subject),
    )

    # Execution
    limit = int(cfg["opener_casts"])

    def first_aimed(e: Entry) -> float | _NoValue | None:
        value = e.hunter.shots["aimed_shot"].casts.value
        if value is None:
            return None
        return NO_VALUE if not value else float(value[0].t_s)

    opener = OpenerPlan(
        subject_sequence=_sequence(subject, limit),
        comparator_sequence=None if comparator is None else _sequence(comparator, limit),
        subject_first_aimed_s=_first_t(subject.hunter.shots["aimed_shot"].casts),
        comparator_first_aimed_s=None
        if comparator is None
        else _first_t(comparator.hunter.shots["aimed_shot"].casts),
        same_faction_first_aimed_s=aggregate((first_aimed(e) for e in same), weak),
        renataki_users=sum(1 for r in renataki if r),
        renataki_known=sum(1 for r in renataki if r is not None),
        weave_on_boss=base.weave.boss.verdict.value,
    )
    rapid_fire = _cooldown(subject, same, overall, rank_one, "rapid_fire", weak)
    refocus = _cooldown(subject, same, overall, rank_one, "refocus", weak)

    # Do not
    do_not: list[DoNot] = [DoNot("other-faction-melee-package", {"package": p}) for p in packages]
    if pet is not None and deaths:
        do_not.append(DoNot("idle-pet", {"reason": "died", "at_s": round(deaths[0].t_s, 2)}))
    elif (
        activity is not None
        and activity.last_damage_before_end_s is not None
        and activity.last_damage_before_end_s > float(cfg["pet_stop_early_s"])
    ):
        do_not.append(
            DoNot(
                "idle-pet",
                {"reason": "stopped-early", "seconds": activity.last_damage_before_end_s},
            )
        )
    flagged = subject.hunter.auto_gap.flagged.value
    if flagged:
        do_not.append(DoNot("long-auto-gaps", {"count": len(flagged), "advisory": True}))
    if cohort_foreign_median is not None and cohort_foreign_median >= float(
        cfg["padding_share_pct"]
    ):
        do_not.append(
            DoNot(
                "padded-comparison",
                {
                    "cohort_median_foreign_share_pct": round(cohort_foreign_median, 2),
                    "level": "inferred" if weak else "derived",
                },
            )
        )

    # Raid ask
    asks: list[RaidAsk] = []
    mine = subject.participant.duration_ms / 1000.0
    if speed is not None and speed.flagged:
        used = speed.vs_median if speed.basis == "median" else speed.vs_fastest
        asks.append(
            RaidAsk(
                "raid-speed",
                {
                    "basis": speed.basis,
                    "your_kill_s": round(mine, 2),
                    "reference": None if used is None else used.reference,
                    "reference_s": None if used is None else used.reference_s.value,
                    "ratio": None if used is None else used.ratio.value,
                    "level": None if used is None else str(used.ratio.level.value),
                },
            )
        )
    if rank_one is not None and mine <= rank_one.participant.duration_ms / 1000.0:
        asks.append(
            RaidAsk(
                "already-faster-than-rank-one",
                {
                    "your_kill_s": round(mine, 2),
                    "rank_one_kill_s": rank_one.participant.duration_ms / 1000.0,
                },
            )
        )
    if utility is not None and utility.friendly_casts.value:
        asks.append(
            RaidAsk(
                "raid-utility", {"friendly_crowd_control_casts": len(utility.friendly_casts.value)}
            )
        )
    if any(d.kind == "padded-comparison" for d in do_not) and integrity is not None:
        asks.append(
            RaidAsk(
                "padding-strategy",
                {
                    "your_foreign_share_pct": integrity.foreign_share_pct.value,
                    "cohort_median_foreign_share_pct": cohort_foreign_median,
                    "level": "inferred" if weak else "derived",
                },
            )
        )
    if base.membership.level is not EvidenceLevel.DERIVED:
        limitations.append("same-faction membership rests on an inferred faction")
    return BossPlaybook(
        RULE_SET,
        context,
        weapon_sets,
        _weapons(subject),
        packages,
        trinket_pairs,
        _trinkets(subject),
        pet_plan,
        weaving,
        opener,
        rapid_fire,
        refocus,
        tuple(do_not),
        tuple(asks),
        _static(boss, subject, same, weak),
        tuple(limitations),
    )


def _wears(e: Entry, item_id: int) -> bool | None:
    gear = e.profile.gear.value
    return None if gear is None else any(g.item_id == item_id for g in gear)


def _static(
    boss: BossData, subject: Entry, same: tuple[Entry, ...], inferred_membership: bool = False
) -> StaticFacts:
    ranged = subject.hunter.gear.ranged.value
    uses = []
    for bonus in gamedata.creature_type_bonuses(ZONE, boss.encounter_id):
        worn = [_wears(e, bonus.item_id) for e in same]
        uses.append(
            TypeBonusUse(
                bonus.item_id,
                bonus.name,
                bonus.effect,
                bonus.applies,
                bonus.source,
                _wears(subject, bonus.item_id),
                sum(1 for w in worn if w),
                sum(1 for w in worn if w is not None),
            )
        )
    return StaticFacts(
        gamedata.encounter_facts(ZONE, boss.encounter_id),
        gamedata.ammo_advice(None if ranged is None else ranged.item_id or None),
        tuple(uses),
        guidance.build(ZONE, boss, subject, same, inferred_membership),
    )


__all__ = ["RULE_SET", "BossPlaybook", "build"]
