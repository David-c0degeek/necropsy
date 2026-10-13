"""Benchmark cohorts and views for one boss.

Historical mode uses the cohort recorded in the snapshot: the overall top five
per boss. The views are:

- A, same-faction ceiling: the best-ranked entry of the subject's faction inside
  that recorded top five (not a separately queried same-faction top five).
- B, same-faction baseline: medians and adoption counts over the same-faction
  entries of that recorded sample. A small sample, not the 20-30 entry
  metadata baseline live acquisition will provide.
- C, cross-faction: every recorded entry, only when explicitly requested, and
  never merged into A or B.

Entries whose faction is unknown are left out of A and B and counted. When the
subject's or any included entry's faction is INFERRED, cohort membership is
inferred, and so is every median, range and ceiling built on it: aggregation
never upgrades an inferred membership to a confirmed one.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Iterable
from dataclasses import dataclass

import duckdb

from necropsy.analysis.classes.classic_era.hunter import HunterAnalysis, HunterClassicEra
from necropsy.analysis.context import ParticipantFight, participant_fights, pet_listing_known
from necropsy.analysis.encounters import EncounterRules, encounter_rules
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceLevel,
    EvidenceRef,
    Faction,
    complete_or_unknown,
    derived,
    inferred,
    unknown,
)
from necropsy.analysis.generic import cohort
from necropsy.analysis.generic.environment import EnvironmentProfile, environment_profile
from necropsy.analysis.generic.targets import RankingDamage, ranking_damage
from necropsy.rules import load_rules

MIN_BASELINE = 3


@dataclass(frozen=True, slots=True)
class Entry:
    """One analyzed participant fight: the subject's or a cohort entry."""

    participant: ParticipantFight
    profile: EnvironmentProfile
    hunter: HunterAnalysis
    ranking: RankingDamage
    pets_listed: bool

    @property
    def ranked_dps(self) -> float | None:
        value = self.ranking.ranked.value
        return None if value is None else value / (self.participant.duration_ms / 1000.0)


@dataclass(frozen=True, slots=True)
class BossData:
    encounter_id: int
    boss: str
    rules: EncounterRules
    subject: Entry | None
    cohort: tuple[Entry, ...]


def analyze_entry(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, rules: EncounterRules
) -> Entry:
    profile = environment_profile(con, pf)
    return Entry(
        participant=pf,
        profile=profile,
        hunter=HunterClassicEra().analyze(con, pf, profile),
        ranking=ranking_damage(con, pf, rules.excluded_from_ranking, rules.exclusion_rule),
        pets_listed=pet_listing_known(con, pf),
    )


def load_bosses(con: duckdb.DuckDBPyConnection, game: str, zone: str) -> list[BossData]:
    by_encounter: dict[int, list[ParticipantFight]] = {}
    for pf in participant_fights(con):
        by_encounter.setdefault(pf.encounter_id, []).append(pf)
    bosses: list[BossData] = []
    for encounter_id, pfs in by_encounter.items():
        rules = encounter_rules(game, zone, encounter_id)
        entries = [analyze_entry(con, pf, rules) for pf in pfs]
        subject = next((e for e in entries if e.participant.kind == "you"), None)
        top = tuple(
            sorted(
                (e for e in entries if e.participant.kind == "top"),
                key=lambda e: (e.participant.leaderboard_position or 99, e.participant.player),
            )
        )
        bosses.append(BossData(encounter_id, pfs[0].boss, rules, subject, top))
    return sorted(bosses, key=lambda b: _boss_order(game, zone).get(b.encounter_id, 999))


def _boss_order(game: str, zone: str) -> dict[int, int]:
    data = load_rules(game, f"zones/{zone}")
    return {int(e["id"]): i for i, e in enumerate(data["encounters"])}


@dataclass(frozen=True, slots=True)
class CohortSplit:
    same_faction: tuple[Entry, ...]
    other_faction: tuple[Entry, ...]
    unknown_faction: tuple[Entry, ...]


def split_by_faction(boss: BossData) -> CohortSplit | None:
    """None when the subject's faction is unknown (no realistic cohort can be formed)."""
    if boss.subject is None or boss.subject.profile.faction.value is None:
        return None
    mine = boss.subject.profile.faction.value
    same = tuple(e for e in boss.cohort if e.profile.faction.value is mine)
    unknown_rows = tuple(e for e in boss.cohort if e.profile.faction.value is None)
    other = tuple(e for e in boss.cohort if e.profile.faction.value not in (mine, None))
    return CohortSplit(same, other, unknown_rows)


def _member_refs(entries: Iterable[Entry], detail: str) -> tuple[EvidenceRef, ...]:
    """One reference per cohort member, so every aggregate can be audited."""
    return tuple(
        EvidenceRef(
            e.participant.report_code,
            e.participant.fight_id,
            e.participant.actor_id,
            "cohort",
            detail=f"{detail}: {e.participant.player}",
        )
        for e in entries
    )


def membership(entries: Iterable[Entry], subject: Entry | None) -> Evidenced[str]:
    """Which faction the same-faction entries share, graded by the weakest faction proof.

    INFERRED when the subject's or any member's faction is INFERRED (rule
    same-faction-membership-v1); UNKNOWN without a subject faction.
    """
    members = list(entries)
    if subject is None or subject.profile.faction.value is None:
        return unknown("subject faction unknown")
    faction = subject.profile.faction.value.value
    refs = _member_refs([subject], "subject") + _member_refs(members, "same-faction member")
    proofs = [subject.profile.faction, *(e.profile.faction for e in members)]
    weakest = sorted({p.rule_id or "unnamed" for p in proofs if p.level is EvidenceLevel.INFERRED})
    if weakest:
        return inferred(
            faction,
            *refs,
            rule_id="same-faction-membership-v1",
            params={"inferred_by": ",".join(weakest)},
            note="membership rests on an inferred faction",
        )
    return derived(faction, *refs, rule_id="same-faction-membership-v1")


@dataclass(frozen=True, slots=True)
class Median:
    value: Evidenced[float]
    n_known: int
    n_unknown: int


def median_of(
    entries: tuple[Entry, ...],
    metric: Callable[[Entry], Evidenced[float]],
    detail: str,
    *,
    inferred_membership: bool = False,
) -> Median:
    values = [metric(e) for e in entries]
    known = [v.value for v in values if v.value is not None]
    refs = _member_refs(entries, detail)
    if len(known) < MIN_BASELINE:
        return Median(
            unknown(f"only {len(known)} known values (need {MIN_BASELINE})", *refs),
            len(known),
            len(values) - len(known),
        )
    med = float(statistics.median(known))
    value: Evidenced[float]
    if inferred_membership:
        value = inferred(med, *refs, rule_id="median-over-inferred-membership")
    elif any(v.level is EvidenceLevel.INFERRED for v in values):
        value = inferred(med, *refs, rule_id="median-over-inferred-inputs")
    else:
        value = derived(med, *refs, rule_id="cohort-median")
    return Median(value, len(known), len(values) - len(known))


def per_minute(entry: Entry, kind: str) -> Evidenced[float]:
    return entry.hunter.shots[kind].per_minute


def hunter_pet_dps(entry: Entry) -> Evidenced[float]:
    """The Hunter pet's DPS; 0 when it is known that no Hunter pet took part."""
    pets = entry.hunter.hunter_pets
    if not entry.pets_listed or any(p.category.value is None for p in entry.hunter.pets):
        return unknown("pet listing missing or a pet-linked actor is unclassified")
    if not pets:
        note = "no Hunter pet took part in the fight"
        if entry.hunter.pets:
            refs = [r for p in entry.hunter.pets for r in p.category.refs]
            cov = [c for p in entry.hunter.pets for c in p.category.coverage]
            if cov:
                return complete_or_unknown(0.0, cov, *refs, rule_id="no-hunter-pet", note=note)
            return derived(0.0, *refs, rule_id="no-hunter-pet", note=note)
        ref = EvidenceRef(
            entry.participant.report_code,
            entry.participant.fight_id,
            entry.participant.actor_id,
            "stream_coverage",
            detail="pet listing is empty",
        )
        return derived(0.0, ref, rule_id="no-hunter-pet", note=note)
    if len(pets) != 1:
        return unknown(f"{len(pets)} Hunter pets")
    return pets[0].dps


def kill_seconds(entry: Entry) -> Evidenced[float]:
    d = entry.profile.kill_duration_ms
    return (
        unknown("kill duration unknown") if d.value is None else derived(d.value / 1000.0, *d.refs)
    )


def first_rapid_fire(entry: Entry) -> Evidenced[float]:
    casts = entry.hunter.rapid_fire.casts
    if casts.value is None:
        return unknown("casts unknown", *casts.refs)
    if not casts.value:
        return unknown("no Rapid Fire cast")
    return derived(casts.value[0].t_s, *casts.refs)


@dataclass(frozen=True, slots=True)
class WeaveAdoption:
    entries: int
    known: int
    with_raptor: int
    with_five_raptors: int
    verdict: Evidenced[str]
    """INFERRED advisory: yes, opportunistic or no (rule weave-verdict-v1)."""


def weave_adoption(entries: tuple[Entry, ...]) -> WeaveAdoption:
    counts = [
        len(e.hunter.shots["raptor_strike"].casts.value)
        for e in entries
        if e.hunter.shots["raptor_strike"].casts.value is not None
    ]
    rule = load_rules("classic_era", "benchmarks")["weave_verdict"]
    one = sum(1 for c in counts if c >= 1)
    five = sum(1 for c in counts if c >= int(rule["heavy_raptors"]))
    refs = _member_refs(entries, "Raptor Strike count")
    if len(counts) < int(rule["min_known"]):
        verdict: Evidenced[str] = unknown(
            f"only {len(counts)} entries with known Raptor counts", *refs
        )
    else:
        share = float(rule["share"])
        label = (
            "yes"
            if five >= share * len(counts)
            else "opportunistic"
            if one >= share * len(counts)
            else "no"
        )
        verdict = inferred(
            label,
            *refs,
            rule_id=str(rule["rule"]),
            params={
                "share": share,
                "heavy_raptors": int(rule["heavy_raptors"]),
                "known": len(counts),
            },
            note="adoption among recorded entries; not proof weaving pays off for this player",
        )
    return WeaveAdoption(len(entries), len(counts), one, five, verdict)


def shot_target_range(median: Median, subject: Entry) -> Evidenced[tuple[int, int]]:
    """floor..ceil of (median casts per minute x the subject's kill minutes)."""
    if median.value.value is None:
        return unknown("baseline rate unknown", *median.value.refs)
    expected = median.value.value * subject.participant.duration_ms / 60000.0
    projected = (math.floor(expected), math.ceil(expected))
    params = {
        "rate_per_min": median.value.value,
        "kill_minutes": subject.participant.duration_ms / 60000.0,
    }
    if median.value.level is EvidenceLevel.INFERRED:
        return inferred(
            projected,
            *median.value.refs,
            rule_id="shot-target-range-v1",
            params=params,
            note="projected from an inferred median",
        )
    return derived(projected, *median.value.refs, rule_id="shot-target-range-v1", params=params)


@dataclass(frozen=True, slots=True)
class Baseline:
    entries: int
    membership: Evidenced[str]
    """Who the entries are; INFERRED when any faction in the selection is inferred."""
    medians: dict[str, Median]
    shot_targets: dict[str, Evidenced[tuple[int, int]]]
    weave: WeaveAdoption
    talents: cohort.Distribution[str]
    darkmoon: cohort.Distribution[str]
    items: cohort.Distribution[int]
    trinkets: cohort.Distribution[int]
    explosive_users: int
    explosive_known: int
    rapid_fire_users: int
    rapid_fire_known: int


def baseline(
    entries: tuple[Entry, ...], subject: Entry | None, *, same_faction: bool = True
) -> Baseline:
    """Medians and distributions over `entries`.

    With `same_faction`, the entries were selected by the subject's faction and
    carry that selection's membership grade; otherwise (the cross-faction view)
    membership is simply every recorded entry.
    """
    member = (
        membership(entries, subject)
        if same_faction
        else derived("any", *_member_refs(entries, "recorded entry"), rule_id="all-entries")
    )
    weak = member.level is not EvidenceLevel.DERIVED

    def med(metric: Callable[[Entry], Evidenced[float]], detail: str) -> Median:
        return median_of(entries, metric, detail, inferred_membership=weak)

    medians = {
        "auto_per_min": med(lambda e: per_minute(e, "auto_shot"), "Auto/min"),
        "aimed_per_min": med(lambda e: per_minute(e, "aimed_shot"), "Aimed/min"),
        "multi_per_min": med(lambda e: per_minute(e, "multi_shot"), "Multi/min"),
        "pet_dps": med(hunter_pet_dps, "Hunter-pet DPS"),
        "kill_s": med(kill_seconds, "kill duration"),
        "first_rapid_fire_s": med(first_rapid_fire, "first Rapid Fire"),
    }
    targets = {}
    if subject is not None:
        for kind in ("auto", "aimed", "multi"):
            targets[kind] = shot_target_range(medians[f"{kind}_per_min"], subject)
    explosive_counts = [
        sum(len(s.casts.value or ()) for s in e.hunter.explosives.values())
        for e in entries
        if all(s.casts.value is not None for s in e.hunter.explosives.values())
    ]
    rf_counts = [
        len(e.hunter.rapid_fire.casts.value)
        for e in entries
        if e.hunter.rapid_fire.casts.value is not None
    ]
    profiles = [e.profile for e in entries]
    return Baseline(
        entries=len(entries),
        membership=member,
        medians=medians,
        shot_targets=targets,
        weave=weave_adoption(entries),
        talents=cohort.talent_distribution(profiles),
        darkmoon=cohort.darkmoon_distribution(profiles),
        items=cohort.item_prevalence(profiles),
        trinkets=cohort.slot_item_prevalence(profiles, (12, 13)),
        explosive_users=sum(1 for c in explosive_counts if c),
        explosive_known=len(explosive_counts),
        rapid_fire_users=sum(1 for c in rf_counts if c),
        rapid_fire_known=len(rf_counts),
    )


def best_entry(entries: tuple[Entry, ...]) -> Entry | None:
    return entries[0] if entries else None


def faction_of(entry: Entry) -> Faction | None:
    return entry.profile.faction.value
