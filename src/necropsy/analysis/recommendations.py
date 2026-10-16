"""Structured recommendations (rule set recommendations-v1).

Each recommendation states an observed gap against a named benchmark view, the
evidence it rests on, and who can act on it. It never estimates a DPS gain.
Severity and confidence are a heuristic evidence-quality tiering, not
calibrated probabilities: confidence drops with INFERRED inputs, partial
observations and small samples. A rule whose inputs are unknown emits nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from necropsy.analysis.benchmark import (
    Baseline,
    BossData,
    CohortSplit,
    Entry,
    Median,
    RaidSpeed,
    hunter_pet_roster_known,
)
from necropsy.analysis.encounters.findings import RaidUtility, TargetIntegrity
from necropsy.analysis.evidence import Evidenced, EvidenceLevel
from necropsy.rules import load_rules


class Controllability(StrEnum):
    PLAYER = "player"
    GEAR_BUILD = "gear-build"
    PET = "pet"
    RAID_ASSIGNMENT = "raid-assignment"
    RAID_SPEED_ENVIRONMENT = "raid-speed-environment"
    FACTION_RACIAL_EXTERNAL = "faction-racial-external"
    RNG_LOW_CONFIDENCE = "rng-low-confidence"


class Tier(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class Recommendation:
    rule: str
    boss: str
    category: str
    controllability: Controllability
    severity: Tier
    confidence: Tier
    finding: str
    recommendation: str
    observed: dict[str, Any]
    benchmark: dict[str, Any]
    evidence: tuple[str, ...]
    """Paths into the same analysis.json that support this recommendation."""
    limitations: tuple[str, ...] = field(default=())


def _cfg() -> dict[str, Any]:
    return dict(load_rules("classic_era", "benchmarks")["recommendations"])


def _confidence(inputs: list[Evidenced[Any]], n_known: int, partial: bool = False) -> Tier:
    if partial or n_known < 3 or any(i.level is EvidenceLevel.UNKNOWN for i in inputs):
        return Tier.LOW
    if any(i.level is EvidenceLevel.INFERRED for i in inputs) or n_known < 4:
        return Tier.MEDIUM
    return Tier.HIGH


def _bench(view: str, n: int, **values: Any) -> dict[str, Any]:
    return {"view": view, "n_known": n, **values}


def _baseline_median(base: Baseline, key: str) -> tuple[Median, str, str, bool]:
    """The same-faction median, or the Tauren-fill median when the same faction has too few.

    Returns (median, benchmark view, evidence path, filled). A filled median always
    caps the recommendation at LOW confidence.
    """
    med = base.medians[key]
    fill = base.tauren_fill
    if med.value.value is None and fill is not None and key in fill.medians:
        filled = fill.medians[key]
        if filled.value.value is not None:
            return filled, "tauren-fill", f"benchmarks.baseline.tauren_fill.medians.{key}", True
    return med, "same-faction-baseline", f"benchmarks.baseline.medians.{key}", False


def _talents(boss: BossData, subject: Entry, base: Baseline) -> list[Recommendation]:
    mine = subject.profile.talents
    top = base.talents.most_common()
    if mine.value is None or not top or base.talents.n_known < 3:
        return []
    build, count = top[0]
    share = base.talents.share(build) or 0.0
    if build == mine.value or share < _cfg()["build_share"]:
        return []
    return [
        Recommendation(
            rule="talent-build",
            boss=boss.boss,
            category="build",
            controllability=Controllability.GEAR_BUILD,
            severity=Tier.HIGH,
            confidence=_confidence([mine, base.membership], base.talents.n_known),
            finding=f"Talents {mine.value}; {count}/{base.talents.n_known} same-faction entries "
            f"use {build}.",
            recommendation=f"Consider the dominant build {build}.",
            observed={"talents": mine.value},
            benchmark=_bench(
                "same-faction-baseline", base.talents.n_known, dominant=build, share=share
            ),
            evidence=("subject.environment.talents", "benchmarks.baseline.talents"),
        )
    ]


def _darkmoon(boss: BossData, subject: Entry, base: Baseline) -> list[Recommendation]:
    mine = subject.profile.darkmoon_faire
    top = base.darkmoon.most_common()
    if mine.value is None or not top or base.darkmoon.n_known < 3:
        return []
    fortune, count = top[0]
    share = base.darkmoon.share(fortune) or 0.0
    if fortune in (mine.value, "none") or share < _cfg()["darkmoon_share"]:
        return []
    return [
        Recommendation(
            rule="darkmoon-faire",
            boss=boss.boss,
            category="buffs",
            controllability=Controllability.GEAR_BUILD,
            severity=Tier.MEDIUM,
            confidence=_confidence([mine, base.membership], base.darkmoon.n_known),
            finding=f"Darkmoon Faire buff at the pull: {mine.value}; {count}/"
            f"{base.darkmoon.n_known} same-faction entries had {fortune}.",
            recommendation=f"On Darkmoon Faire weeks take {fortune}.",
            observed={"darkmoon_faire": mine.value},
            benchmark=_bench(
                "same-faction-baseline", base.darkmoon.n_known, dominant=fortune, share=share
            ),
            evidence=("subject.environment.darkmoon_faire", "benchmarks.baseline.darkmoon"),
        )
    ]


def _trinkets(
    boss: BossData, subject: Entry, base: Baseline, names: dict[int, str]
) -> list[Recommendation]:
    trinkets = subject.hunter.gear.trinkets
    dist = base.trinkets
    if trinkets.value is None or dist.n_known < 3:
        return []
    worn = {t.item_id for t in trinkets.value}
    out = []
    for item, count in dist.most_common():
        share = dist.share(item) or 0.0
        if item in worn or share < _cfg()["trinket_share"]:
            continue
        label = names.get(item, f"item {item}")
        out.append(
            Recommendation(
                rule="trinket",
                boss=boss.boss,
                category="gear",
                controllability=Controllability.GEAR_BUILD,
                severity=Tier.MEDIUM,
                confidence=_confidence([trinkets, base.membership], dist.n_known),
                finding=f"{label} is worn by {count}/{dist.n_known} same-faction entries but "
                "not by the subject at the pull.",
                recommendation=f"Consider {label} for this fight.",
                observed={"trinkets": sorted(worn)},
                benchmark=_bench("same-faction-baseline", dist.n_known, item=item, share=share),
                evidence=("subject.hunter.gear.trinkets", "benchmarks.baseline.trinkets"),
            )
        )
    return out


def _pet(boss: BossData, subject: Entry, base: Baseline) -> list[Recommendation]:
    cfg = _cfg()
    pets = subject.hunter.pets
    if any(p.category.value is None for p in pets) or not hunter_pet_roster_known(subject):
        return []
    hunter_pets = subject.hunter.hunter_pets
    if not hunter_pets:
        return [
            Recommendation(
                rule="pet-absent",
                boss=boss.boss,
                category="pet",
                controllability=Controllability.PET,
                severity=Tier.HIGH,
                confidence=Tier.HIGH,
                finding="No Hunter pet took part in this fight.",
                recommendation="Bring a pet and keep it attacking.",
                observed={"hunter_pets": 0, "pet_linked_actors": [p.name for p in pets]},
                benchmark=_bench(
                    "same-faction-baseline",
                    base.medians["pet_dps"].n_known,
                    median_pet_dps=base.medians["pet_dps"].value.value,
                ),
                evidence=("subject.hunter.pets",),
            )
        ]
    out: list[Recommendation] = []
    pet = hunter_pets[0]
    med, view, med_path, filled = _baseline_median(base, "pet_dps")
    if (
        pet.dps.value is not None
        and med.value.value
        and (pet.dps.value < cfg["pet_dps_ratio"] * med.value.value)
    ):
        out.append(
            Recommendation(
                rule="pet-dps",
                boss=boss.boss,
                category="pet",
                controllability=Controllability.PET,
                severity=Tier.HIGH,
                confidence=Tier.LOW if filled else _confidence([pet.dps, med.value], med.n_known),
                finding=f"Pet {pet.name}: {pet.dps.value:.0f} DPS vs "
                f"{'Tauren-fill' if filled else 'same-faction'} median {med.value.value:.0f}.",
                recommendation="Review pet choice, buffs, uptime and survival.",
                observed={"pet": pet.name, "pet_dps": pet.dps.value, "family": pet.family.value},
                benchmark=_bench(view, med.n_known, median_pet_dps=med.value.value),
                evidence=("subject.hunter.hunter_pets", med_path),
            )
        )
    if pet.deaths.deaths.value:
        first = pet.deaths.deaths.value[0]
        out.append(
            Recommendation(
                rule="pet-death",
                boss=boss.boss,
                category="pet",
                controllability=Controllability.PET,
                severity=Tier.MEDIUM,
                confidence=Tier.HIGH if pet.deaths.complete else Tier.MEDIUM,
                finding=f"Pet {pet.name} died at {first.t_s:.1f} s.",
                recommendation="Keep the pet out of avoidable damage on this fight.",
                observed={"death_times_s": [d.t_s for d in pet.deaths.deaths.value]},
                benchmark={},
                evidence=("subject.hunter.hunter_pets",),
                limitations=("Encounter mechanics or raid assignments may explain the death.",),
            )
        )
    elif (
        pet.activity.value is not None
        and pet.activity.value.last_damage_before_end_s is not None
        and pet.activity.value.last_damage_before_end_s > cfg["pet_stop_early_s"]
    ):
        gap = pet.activity.value.last_damage_before_end_s
        out.append(
            Recommendation(
                rule="pet-stopped-early",
                boss=boss.boss,
                category="pet",
                controllability=Controllability.PET,
                severity=Tier.MEDIUM,
                confidence=Tier.MEDIUM,
                finding=f"Pet {pet.name} dealt no damage in the last {gap:.1f} s.",
                recommendation="Check whether the pet was recalled or idle before the kill.",
                observed={"last_damage_before_end_s": gap},
                benchmark={},
                evidence=("subject.hunter.hunter_pets",),
                limitations=("Phases, movement or targeting may explain the gap.",),
            )
        )
    return out


def _aimed(
    boss: BossData, subject: Entry, base: Baseline, utility: RaidUtility | None
) -> list[Recommendation]:
    rate = subject.hunter.shots["aimed_shot"].per_minute
    med, view, med_path, filled = _baseline_median(base, "aimed_per_min")
    if rate.value is None or med.value.value is None:
        return []
    if rate.value >= (1 - _cfg()["aimed_shortfall"]) * med.value.value:
        return []
    limitations: tuple[str, ...] = ()
    confidence = _confidence([rate, med.value], med.n_known)
    if utility is not None and utility.utility_inside_gap:
        limitations = (
            "Part of the shortfall falls in a window spent on raid utility "
            "(see the raid-assignment finding).",
        )
        confidence = Tier.LOW
    if filled:
        confidence = Tier.LOW
        limitations = (*limitations, "Median includes other-faction Tauren entries.")
    target = None if filled else base.shot_targets.get("aimed")
    return [
        Recommendation(
            rule="aimed-cadence",
            boss=boss.boss,
            category="rotation",
            controllability=Controllability.PLAYER,
            severity=Tier.HIGH,
            confidence=confidence,
            finding=f"{rate.value:.2f} Aimed Shots/min vs "
            f"{'Tauren-fill' if filled else 'same-faction'} median {med.value.value:.2f}.",
            recommendation="Fit an Aimed Shot into more Auto Shot cycles without clipping Autos.",
            observed={"aimed_per_min": rate.value},
            benchmark=_bench(
                view,
                med.n_known,
                median=med.value.value,
                target_range=None if target is None else target.value,
            ),
            evidence=("subject.hunter.shots.aimed_shot", med_path),
            limitations=limitations,
        )
    ]


def _rapid_fire(boss: BossData, subject: Entry, base: Baseline) -> list[Recommendation]:
    casts = subject.hunter.rapid_fire.casts
    if casts.value is None or base.rapid_fire_known < 3:
        return []
    share = base.rapid_fire_users / base.rapid_fire_known
    if casts.value or share < _cfg()["rapid_fire_share"]:
        return []
    med = base.medians["first_rapid_fire_s"]
    return [
        Recommendation(
            rule="rapid-fire-unused",
            boss=boss.boss,
            category="cooldowns",
            controllability=Controllability.PLAYER,
            severity=Tier.HIGH,
            confidence=_confidence([casts, base.membership], base.rapid_fire_known),
            finding=f"Rapid Fire was never cast; {base.rapid_fire_users}/{base.rapid_fire_known} "
            "same-faction entries used it.",
            recommendation="Use Rapid Fire on this fight.",
            observed={"rapid_fire_casts": 0},
            benchmark=_bench(
                "same-faction-baseline", base.rapid_fire_known, median_first_cast_s=med.value.value
            ),
            evidence=(
                "subject.hunter.rapid_fire",
                "benchmarks.baseline.medians.first_rapid_fire_s",
            ),
        )
    ]


def _explosives(boss: BossData, subject: Entry, base: Baseline) -> list[Recommendation]:
    stats = subject.hunter.explosives.values()
    if any(s.casts.value is None for s in stats) or base.explosive_known < 3:
        return []
    used = sum(len(s.casts.value or ()) for s in stats)
    share = base.explosive_users / base.explosive_known
    if used or share < _cfg()["explosive_share"]:
        return []
    return [
        Recommendation(
            rule="explosives-unused",
            boss=boss.boss,
            category="consumables",
            controllability=Controllability.PLAYER,
            severity=Tier.LOW,
            confidence=_confidence([base.membership], base.explosive_known),
            finding=f"No explosives used; {base.explosive_users}/{base.explosive_known} "
            "same-faction entries used them.",
            recommendation="Add Dense Dynamite or Sapper Charges in free GCDs.",
            observed={"explosive_casts": 0},
            benchmark=_bench(
                "same-faction-baseline", base.explosive_known, users=base.explosive_users
            ),
            evidence=("subject.hunter.explosives", "benchmarks.baseline.explosive_users"),
        )
    ]


_ROLE_TEXT = {"boss": "the boss", "non_boss": "adds and other NPCs"}


def _weave(boss: BossData, subject: Entry, base: Baseline) -> list[Recommendation]:
    """Weave advice per target role: only where most same-faction entries weave heavily."""
    mine = subject.raptor_roles.value
    if mine is None:
        return []
    found: list[Recommendation] = []
    for role in ("boss", "non_boss"):
        stats = getattr(base.weave, role)
        if stats.verdict.value != "yes" or getattr(mine, role):
            continue
        where = _ROLE_TEXT[role]
        found.append(
            Recommendation(
                rule="weave-adoption",
                boss=boss.boss,
                category="rotation",
                controllability=Controllability.PLAYER,
                severity=Tier.LOW,
                confidence=_confidence([stats.verdict, base.membership], stats.known),
                finding=f"No Raptor Strikes on {where}; {stats.with_five_raptors}/{stats.known} "
                f"same-faction entries cast five or more there.",
                recommendation="Once the ranged cycle is clean, add Raptor Strikes on "
                f"{where} only in free windows that cost no Auto Shot.",
                observed={"raptor_strikes": 0, "role": role},
                benchmark=_bench(
                    "same-faction-baseline",
                    stats.known,
                    role=role,
                    with_raptor=stats.with_raptor,
                    with_five_raptors=stats.with_five_raptors,
                    verdict=stats.verdict.value,
                    verdict_rule=stats.verdict.rule_id,
                ),
                evidence=(
                    "subject.raptor_roles",
                    f"benchmarks.baseline.weave.{role}",
                ),
                limitations=(
                    "Adoption among recorded entries is not proof weaving pays off here.",
                ),
            )
        )
    return found


def _raid_assignment(boss: BossData, utility: RaidUtility | None) -> list[Recommendation]:
    if utility is None or not utility.friendly_casts.value:
        return []
    casts = utility.friendly_casts.value
    return [
        Recommendation(
            rule="raid-utility",
            boss=boss.boss,
            category="assignment",
            controllability=Controllability.RAID_ASSIGNMENT,
            severity=Tier.HIGH,
            confidence=Tier.HIGH,
            finding=f"{len(casts)} crowd-control casts on raid members "
            f"({', '.join(f'{c.kind[3:]} {c.t_s:.1f}s' for c in casts)}).",
            recommendation="For a parse attempt, move this utility assignment to another player.",
            observed={
                "casts": [
                    {"kind": c.kind[3:], "t_s": c.t_s, "target_id": c.target_id} for c in casts
                ],
                "longest_aimed_gap_s": utility.longest_aimed_gap_s.value,
            },
            benchmark={},
            evidence=("subject.hunter.friendly_crowd_control", "encounter.raid_utility"),
        )
    ]


def _padding(
    boss: BossData,
    base: Baseline,
    subject_integrity: TargetIntegrity | None,
    cohort_shares: list[float],
) -> list[Recommendation]:
    cfg = _cfg()
    if subject_integrity is None or subject_integrity.foreign_share_pct.value is None:
        return []
    if len(cohort_shares) < 3:
        return []
    import statistics

    med = statistics.median(cohort_shares)
    mine = subject_integrity.foreign_share_pct.value
    if med < cfg["foreign_share_pct"] or mine > cfg["subject_foreign_max_pct"]:
        return []
    return [
        Recommendation(
            rule="foreign-target-padding",
            boss=boss.boss,
            category="raid strategy",
            controllability=Controllability.RAID_SPEED_ENVIRONMENT,
            severity=Tier.HIGH,
            confidence=_confidence(
                [subject_integrity.foreign_share_pct, base.membership], len(cohort_shares)
            ),
            finding=f"Same-faction entries do a median {med:.0f}% of their damage to units that "
            f"are not part of this encounter; the subject {mine:.0f}%.",
            recommendation="The leaderboard ceiling here needs a raid strategy that pulls extra "
            "targets into the encounter; compare native-target damage instead.",
            observed={"foreign_share_pct": mine},
            benchmark=_bench("same-faction-baseline", len(cohort_shares), median_foreign_pct=med),
            evidence=(
                "encounter.target_integrity",
                "encounter.cohort_target_integrity",
                "benchmarks.baseline.membership",
            ),
        )
    ]


def _raid_speed(boss: BossData, speed: RaidSpeed | None) -> list[Recommendation]:
    if speed is None or not speed.flagged:
        return []
    used = speed.vs_median if speed.basis == "median" else speed.vs_fastest
    assert used is not None and used.ratio.value is not None
    assert used.reference_s.value is not None
    # A kill-time ratio is a heuristic: at best MEDIUM; LOW on the fastest-kill
    # fallback or when the comparison rests on an inferred faction.
    weak = any(e.level is not EvidenceLevel.DERIVED for e in (used.ratio, used.membership))
    confidence = Tier.LOW if speed.basis == "fastest" or weak else Tier.MEDIUM
    return [
        Recommendation(
            rule="raid-speed-v2",
            boss=boss.boss,
            category="raid speed",
            controllability=Controllability.RAID_SPEED_ENVIRONMENT,
            severity=Tier.HIGH,
            confidence=confidence,
            finding=f"Kill took {speed.subject_s:.0f} s vs {used.reference_s.value:.0f} s "
            f"({used.reference}; {used.ratio.value:.1f}x).",
            recommendation="Kill length is a large part of this gap. Look at raid speed and "
            "environment alongside your own execution and assignments.",
            observed={"kill_s": speed.subject_s},
            benchmark=_bench(
                "same-faction-median" if speed.basis == "median" else "same-faction-fastest",
                used.n_known,
                basis=speed.basis,
                threshold=speed.threshold,
                reference=used.reference,
                reference_kill_s=used.reference_s.value,
                ratio=used.ratio.value,
            ),
            evidence=("subject.kill_duration_s", "benchmarks.raid_speed"),
            limitations=("A named heuristic on kill-time ratio; not a measured cause.",),
        )
    ]


def recommend(
    boss: BossData,
    split: CohortSplit,
    base: Baseline,
    speed: RaidSpeed | None,
    utility: RaidUtility | None,
    subject_integrity: TargetIntegrity | None,
    cohort_foreign_shares: list[float],
    item_names: dict[int, str],
) -> list[Recommendation]:
    subject = boss.subject
    if subject is None:
        return []
    del split
    return [
        *_talents(boss, subject, base),
        *_darkmoon(boss, subject, base),
        *_trinkets(boss, subject, base, item_names),
        *_pet(boss, subject, base),
        *_aimed(boss, subject, base, utility),
        *_rapid_fire(boss, subject, base),
        *_explosives(boss, subject, base),
        *_weave(boss, subject, base),
        *_raid_assignment(boss, utility),
        *_padding(boss, base, subject_integrity, cohort_foreign_shares),
        *_raid_speed(boss, speed),
    ]
