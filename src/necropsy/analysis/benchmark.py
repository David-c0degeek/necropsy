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

from necropsy.analysis.classes import plugin_for
from necropsy.analysis.classes.classic_era.combat import CombatAnalysis
from necropsy.analysis.classes.classic_era.druid import DruidAnalysis
from necropsy.analysis.classes.classic_era.hunter import Cast, HunterAnalysis
from necropsy.analysis.context import ParticipantFight, participant_fights, pet_listing_known
from necropsy.analysis.encounters import EncounterRules, encounter_rules
from necropsy.analysis.evidence import (
    Claim,
    Evidenced,
    EvidenceLevel,
    EvidenceRef,
    Faction,
    RaceStatus,
    WindfuryStatus,
    complete_or_unknown,
    derived,
    inferred,
    unknown,
)
from necropsy.analysis.generic import cohort
from necropsy.analysis.generic.environment import EnvironmentProfile, environment_profile
from necropsy.analysis.generic.targets import RankedTarget, RankingDamage, ranking_damage
from necropsy.analysis.roles import CLASS_NAMES, RoleOverride
from necropsy.rules import load_rules

MIN_BASELINE = 3


@dataclass(frozen=True, slots=True)
class RaptorRoles:
    """Raptor Strike casts by what they hit (rule cast-target-role-v1)."""

    boss: int
    non_boss: int
    native_adds: int | None
    """Non-boss casts on the encounter's own units; None without a native-target rule."""
    start_trash: int
    foreign: int | None
    """Non-boss casts on anything else; None without a native-target rule."""


@dataclass(frozen=True, slots=True)
class Entry:
    """One analyzed participant fight: the subject's or a cohort entry."""

    participant: ParticipantFight
    profile: EnvironmentProfile
    class_analysis: HunterAnalysis | DruidAnalysis | CombatAnalysis
    ranking: RankingDamage
    pets_listed: bool
    raptor_roles: Evidenced[RaptorRoles]

    @property
    def hunter(self) -> HunterAnalysis:
        if not isinstance(self.class_analysis, HunterAnalysis):
            raise TypeError("Hunter-only analysis requested for another class")
        return self.class_analysis

    @property
    def druid(self) -> DruidAnalysis:
        if not isinstance(self.class_analysis, DruidAnalysis):
            raise TypeError("Druid-only analysis requested for another class")
        return self.class_analysis

    @property
    def combat(self) -> CombatAnalysis:
        if not isinstance(self.class_analysis, CombatAnalysis):
            raise TypeError("Common combat analysis requested for a different class")
        return self.class_analysis

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


def raptor_roles(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    rules: EncounterRules,
    casts: Evidenced[tuple[Cast, ...]],
) -> Evidenced[RaptorRoles]:
    """Split Raptor Strike casts by target role: boss, or another hostile NPC.

    A cast whose target has no ID, no game ID, no proven hostile side, or is not
    an NPC (a hostile player or pet, or an unlisted actor type) makes the split
    UNKNOWN: it is never guessed into a role or counted as zero.
    """
    if casts.value is None:
        return unknown("Raptor Strike casts unknown", *casts.refs, coverage=casts.coverage)
    ids = sorted({c.target_id for c in casts.value if c.target_id is not None})
    actors = {
        int(actor_id): (game_id, kind)
        for actor_id, game_id, kind in con.execute(
            """SELECT actor_id, game_id, type FROM actors
               WHERE report_code = ? AND actor_id IN (SELECT unnest(?::BIGINT[]))""",
            [pf.report_code, ids],
        ).fetchall()
    }
    game_ids = {a: g for a, (g, _kind) in actors.items()}
    unresolved = [
        c
        for c in casts.value
        if c.target_id is None
        or game_ids.get(c.target_id) is None
        or actors[c.target_id][1] != "NPC"
        or c.target_friendly is not False
    ]
    if unresolved:
        return unknown(
            f"{len(unresolved)} Raptor Strike casts have no resolved hostile NPC target",
            *casts.refs,
            coverage=casts.coverage,
        )
    roles = [int(game_ids[c.target_id]) for c in casts.value if c.target_id is not None]
    boss = sum(1 for g in roles if rules.is_boss(g))
    others = [g for g in roles if not rules.is_boss(g)]
    trash = sum(1 for g in others if rules.is_start_trash(g))
    native = foreign = None
    if rules.native_game_ids is not None:
        native = sum(1 for g in others if rules.is_native(g, None))
        foreign = len(others) - native - trash
    return complete_or_unknown(
        RaptorRoles(boss, len(others), native, trash, foreign),
        casts.coverage,
        *casts.refs,
        rule_id="cast-target-role-v1",
        params={"encounter": rules.name},
    )


def analyze_entry(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    rules: EncounterRules,
    override: RoleOverride | None = None,
) -> Entry:
    profile = environment_profile(con, pf)
    row = con.execute(
        "SELECT sub_type FROM actors WHERE report_code = ? AND actor_id = ?",
        [pf.report_code, pf.actor_id],
    ).fetchone()
    class_id = next((cid for cid, name in CLASS_NAMES.items() if row and name == row[0]), None)
    plugin = None if class_id is None else plugin_for("classic_era", class_id)
    if plugin is None:
        raise ValueError(f"unsupported participant class: {None if row is None else row[0]}")
    result = plugin.analyze(con, pf, profile)
    if override is not None:
        from dataclasses import replace

        if not isinstance(result, DruidAnalysis):
            raise ValueError("role overrides are supported only for Druid subject fights")
        result = replace(result, override=override, selected_role=override.role)
    if not isinstance(result, HunterAnalysis | DruidAnalysis | CombatAnalysis):
        raise TypeError("class plugin returned an unsupported analysis contract")
    ranking = (
        ranking_damage(con, pf, rules.excluded_from_ranking, rules.exclusion_rule)
        if isinstance(result, HunterAnalysis)
        else RankingDamage(
            unknown(f"{plugin.name} event damage is distinct from a WCL category score"),
            unknown(f"Hunter ranking rules do not apply to {plugin.name}"),
            unknown(f"Hunter ranking rules do not apply to {plugin.name}"),
            (pf.actor_id,),
            unknown(f"see {plugin.name} damage targets"),
        )
    )
    return Entry(
        participant=pf,
        profile=profile,
        class_analysis=result,
        ranking=ranking,
        pets_listed=pet_listing_known(con, pf),
        raptor_roles=raptor_roles(con, pf, rules, result.shots["raptor_strike"].casts)
        if isinstance(result, HunterAnalysis)
        else unknown("not a Hunter ability"),
    )


def load_bosses(
    con: duckdb.DuckDBPyConnection,
    game: str,
    zone: str,
    role_overrides: dict[tuple[str, int], RoleOverride] | None = None,
) -> list[BossData]:
    overrides = role_overrides or {}
    by_encounter: dict[int, list[ParticipantFight]] = {}
    participants = participant_fights(con)
    subject_keys = {(p.report_code, p.fight_id) for p in participants if p.kind == "you"}
    if set(overrides) - subject_keys:
        raise ValueError("role overrides must identify acquired subject fights")
    for pf in participants:
        by_encounter.setdefault(pf.encounter_id, []).append(pf)
    bosses: list[BossData] = []
    for encounter_id, pfs in by_encounter.items():
        rules = encounter_rules(game, zone, encounter_id)
        entries = [
            analyze_entry(
                con,
                pf,
                rules,
                overrides.get((pf.report_code, pf.fight_id)) if pf.kind == "you" else None,
            )
            for pf in pfs
        ]
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
class WeaveRole:
    """Raptor Strike adoption on one target role."""

    known: int
    with_raptor: int
    with_five_raptors: int
    verdict: Evidenced[str]
    """INFERRED advisory: yes, opportunistic or no (rule weave-verdict-v2)."""


@dataclass(frozen=True, slots=True)
class WeaveAdoption:
    entries: int
    known: int
    with_raptor: int
    """Entries with at least one Raptor Strike on any target (descriptive)."""
    with_five_raptors: int
    boss: WeaveRole
    non_boss: WeaveRole
    """Every hostile NPC that is not the boss: adds, start trash, pulled-in trash."""


def _weave_role(counts: list[int], refs: tuple[EvidenceRef, ...], role: str) -> WeaveRole:
    rule = load_rules("classic_era", "benchmarks")["weave_verdict"]
    one = sum(1 for c in counts if c >= 1)
    five = sum(1 for c in counts if c >= int(rule["heavy_raptors"]))
    if len(counts) < int(rule["min_known"]):
        verdict: Evidenced[str] = unknown(
            f"only {len(counts)} entries with known Raptor targets", *refs
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
                "role": role,
                "share": share,
                "heavy_raptors": int(rule["heavy_raptors"]),
                "known": len(counts),
            },
            note="adoption among recorded entries; not proof weaving pays off for this player",
        )
    return WeaveRole(len(counts), one, five, verdict)


def weave_adoption(entries: tuple[Entry, ...]) -> WeaveAdoption:
    heavy = int(load_rules("classic_era", "benchmarks")["weave_verdict"]["heavy_raptors"])
    counts = [
        len(e.hunter.shots["raptor_strike"].casts.value)
        for e in entries
        if e.hunter.shots["raptor_strike"].casts.value is not None
    ]
    roles = [e.raptor_roles.value for e in entries if e.raptor_roles.value is not None]
    refs = _member_refs(entries, "Raptor Strike targets")
    return WeaveAdoption(
        entries=len(entries),
        known=len(counts),
        with_raptor=sum(1 for c in counts if c >= 1),
        with_five_raptors=sum(1 for c in counts if c >= heavy),
        boss=_weave_role([r.boss for r in roles], refs, "boss"),
        non_boss=_weave_role([r.non_boss for r in roles], refs, "non-boss"),
    )


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


FILL_RACE = "Tauren"
_PROVEN_RACE = (RaceStatus.API_CONFIRMED, RaceStatus.RACIAL_EVENT_CONFIRMED)


@dataclass(frozen=True, slots=True)
class TaurenFill:
    """Rule tauren-fill-v1: other-faction Tauren entries for metrics the same faction cannot
    supply. A separate view, never merged into the same-faction baseline or ceiling."""

    needed_for: tuple[str, ...]
    """Same-faction medians with fewer than the minimum known values."""
    eligible: tuple[str, ...]
    excluded: tuple[tuple[str, str], ...]
    """(player, reason) for other-faction entries that were not used."""
    medians: dict[str, Median]
    membership: Evidenced[str]


def fill_eligibility(entry: Entry) -> str | None:
    """None when eligible, else the reason the entry is left out.

    Orc and Troll racials change damage and cadence too much to compare (user
    decision 2026-10-13); Windfury changes melee weaving, which Alliance lacks, so
    it must be shown absent on trusted streams, not merely unseen.
    """
    race = entry.profile.race
    if race.status not in _PROVEN_RACE or race.race.value is None:
        return "race not proven"
    if race.race.value != FILL_RACE:
        return f"race {race.race.value}"
    wf = entry.profile.windfury.status_evidence
    if wf.value is not WindfuryStatus.NOT_OBSERVED or wf.claim is not Claim.COMPLETE:
        return "Windfury not proven absent"
    return None


def tauren_fill(
    same_faction: tuple[Entry, ...],
    candidates: tuple[Entry, ...],
    medians: dict[str, Median],
    metrics: dict[str, Callable[[Entry], Evidenced[float]]],
) -> TaurenFill | None:
    needed = tuple(k for k, m in medians.items() if m.value.value is None)
    if not needed:
        return None
    eligible: list[Entry] = []
    excluded: list[tuple[str, str]] = []
    for e in candidates:
        reason = fill_eligibility(e)
        if reason is None:
            eligible.append(e)
        else:
            excluded.append((e.participant.player, reason))
    pool = (*same_faction, *eligible)
    filled = {
        k: median_of(pool, metrics[k], f"{k} (Tauren fill)", inferred_membership=True)
        for k in needed
    }
    refs = _member_refs(pool, "same-faction or Tauren-fill entry")
    member: Evidenced[str] = (
        inferred(
            "same faction plus proven Tauren",
            *refs,
            rule_id="tauren-fill-v1",
            note="other-faction Tauren entries added because the same faction has too few",
        )
        if refs
        else unknown("no entries")
    )
    return TaurenFill(
        needed,
        tuple(e.participant.player for e in eligible),
        tuple(excluded),
        filled,
        member,
    )


TargetKey = tuple[str, int | str | None]
"""Stable target identity: ('NPC', game ID) for NPCs; one category per other actor type
(players, pets: different people in different raids are not comparable one by one);
('unidentified', name) for an NPC-less target without a game ID."""

CATEGORY_LABELS = {"Player": "Players (e.g. mind-controlled raid members)", "Pet": "Pets"}


@dataclass(frozen=True, slots=True)
class TargetShare:
    kind: str
    game_id: int | None
    """None for a category row (all players, all pets)."""
    name: str | None
    """Display label: the most common name for an NPC (ties: alphabetical), or the
    category label for players and pets."""
    aliases: tuple[str, ...]
    """Every other name seen for the same identity (renamed or localized labels)."""
    median_share_pct: Evidenced[float]
    """Median share of ranked damage over same-faction entries with known ranked
    damage (0 where such an entry did not hit it); UNKNOWN with fewer than the
    minimum known entries."""
    n_known: int
    n_unknown: int
    """Same-faction entries whose ranked damage is unknown; never counted as 0."""
    subject_share_pct: Evidenced[float]
    """COMPLETE when the subject's ranked damage is: a 0 is a proven absence."""


@dataclass(frozen=True, slots=True)
class RankedTargetShares:
    """Which targets make up ranked damage on this boss (rule ranked-target-share-v1)."""

    counted: tuple[TargetShare, ...]
    excluded: tuple[str, ...]
    """Targets the encounter rule leaves out, as seen in any entry."""


def _target_key(r: RankedTarget) -> TargetKey:
    if r.kind == "NPC" and r.game_id is not None:
        return ("NPC", r.game_id)
    if r.kind is not None and r.kind != "NPC":
        return (r.kind, None)
    if r.game_id is None:
        return ("unidentified", r.name)
    return ("unlisted", r.game_id)


def _share_map(entry: Entry) -> dict[TargetKey, float] | None:
    """Share of ranked damage per target identity; None unless ranked damage is known."""
    ranked = entry.ranking.ranked.value
    rows = entry.ranking.by_target.value
    if ranked is None or rows is None or ranked <= 0:
        return None
    out: dict[TargetKey, float] = {}
    for r in rows:
        if r.category == "counted":
            key = _target_key(r)
            out[key] = out.get(key, 0.0) + 100.0 * r.damage / ranked
    return out


def non_boss_share(entry: Entry, rules: EncounterRules) -> float | None:
    """Percent of ranked damage on anything but the boss; None unless ranked damage is known."""
    shares = _share_map(entry)
    if shares is None:
        return None
    return sum(
        v
        for (kind, gid), v in shares.items()
        if not (kind == "NPC" and isinstance(gid, int) and rules.is_boss(gid))
    )


def ranked_target_shares(
    entries: tuple[Entry, ...], subject: Entry, member: Evidenced[str]
) -> RankedTargetShares:
    rule = "ranked-target-share-v1"
    known = [(e, m) for e, m in ((e, _share_map(e)) for e in entries) if m is not None]
    n_unknown = len(entries) - len(known)
    mine = _share_map(subject)
    names: dict[TargetKey, list[str]] = {}
    for e in (*entries, subject):
        for r in e.ranking.by_target.value or ():
            key = _target_key(r)
            # Category rows (players, pets) get a fixed label, never individual names.
            if r.category == "counted" and r.name and key[1] is not None:
                names.setdefault(key, []).append(r.name)
    keys = sorted({k for _, m in known for k in m} | set(mine or {}), key=repr)
    # The ranked totals the shares divide by, with their own references.
    cohort_refs = tuple(ref for e, _ in known for ref in e.ranking.ranked.refs)
    ranked = subject.ranking.ranked
    weak = member.level is not EvidenceLevel.DERIVED
    shares = []
    for key in keys:
        values = [m.get(key, 0.0) for _, m in known]
        if len(values) < MIN_BASELINE:
            med: Evidenced[float] = unknown(
                f"only {len(values)} entries with known ranked damage", *cohort_refs
            )
        else:
            value = float(statistics.median(values))
            med = (
                inferred(value, *cohort_refs, rule_id=rule, note="inferred faction membership")
                if weak
                else derived(value, *cohort_refs, rule_id=rule)
            )
        own: Evidenced[float] = (
            unknown("subject ranked damage unknown", *ranked.refs, coverage=ranked.coverage)
            if mine is None
            else complete_or_unknown(
                mine.get(key, 0.0), ranked.coverage, *ranked.refs, rule_id=rule
            )
        )
        counts: dict[str, int] = {}
        for n in names.get(key, []):
            counts[n] = counts.get(n, 0) + 1
        ordered = sorted(counts, key=lambda n: (-counts[n], n))
        if key[1] is None:
            label: str | None = CATEGORY_LABELS.get(key[0], key[0])
        elif ordered:
            label = ordered[0]
        else:
            label = key[1] if isinstance(key[1], str) else None
        game_id = key[1] if isinstance(key[1], int) else None
        shares.append(
            TargetShare(
                key[0], game_id, label, tuple(ordered[1:]), med, len(values), n_unknown, own
            )
        )
    shares.sort(key=lambda s: (-(s.median_share_pct.value or 0.0), repr((s.kind, s.game_id))))
    excluded = sorted(
        {
            f"{r.name} ({r.game_id})"
            for e in (*entries, subject)
            for r in (e.ranking.by_target.value or ())
            if r.category == "excluded"
        }
    )
    return RankedTargetShares(tuple(shares), tuple(excluded))


@dataclass(frozen=True, slots=True)
class FamilyCount:
    family: str
    observed: int
    inferred: int


@dataclass(frozen=True, slots=True)
class PetFamilies:
    """Hunter-pet families among entries; every entry is accounted for exactly once."""

    entries: int
    families: tuple[FamilyCount, ...]
    """Entries with one Hunter pet whose family is known, by family and grade."""
    unknown_family: int
    no_hunter_pet: int
    """Pet listing present and classified, but no Hunter pet took part."""
    listing_missing: int
    unclassified: int
    """A pet-linked actor could not be classified."""
    multiple_hunter_pets: int


def pet_families(entries: Iterable[Entry]) -> PetFamilies:
    counts: dict[str, list[int]] = {}
    total = unknown_family = none = missing = unclassified = multiple = 0
    for e in entries:
        total += 1
        pets = e.hunter.hunter_pets
        if not e.pets_listed:
            missing += 1
        elif any(p.category.value is None for p in e.hunter.pets):
            unclassified += 1
        elif not pets:
            none += 1
        elif len(pets) > 1:
            multiple += 1
        elif pets[0].family.value is None:
            unknown_family += 1
        else:
            slot = counts.setdefault(str(pets[0].family.value), [0, 0])
            slot[0 if pets[0].family.level is EvidenceLevel.OBSERVED else 1] += 1
    families = tuple(
        FamilyCount(name, observed_n, inferred_n)
        for name, (observed_n, inferred_n) in sorted(
            counts.items(), key=lambda kv: (-(kv[1][0] + kv[1][1]), kv[0])
        )
    )
    return PetFamilies(total, families, unknown_family, none, missing, unclassified, multiple)


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
    pet_families: PetFamilies | None = None
    """Hunter-pet families among the entries, with how each family is known."""
    tauren_fill: TaurenFill | None = None
    """Only on a same-faction baseline whose medians lack known values (rule tauren-fill-v1)."""


def baseline(
    entries: tuple[Entry, ...],
    subject: Entry | None,
    *,
    same_faction: bool = True,
    fill_candidates: tuple[Entry, ...] = (),
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

    metrics: dict[str, Callable[[Entry], Evidenced[float]]] = {
        "auto_per_min": lambda e: per_minute(e, "auto_shot"),
        "aimed_per_min": lambda e: per_minute(e, "aimed_shot"),
        "multi_per_min": lambda e: per_minute(e, "multi_shot"),
        "pet_dps": hunter_pet_dps,
        "kill_s": kill_seconds,
        "first_rapid_fire_s": first_rapid_fire,
    }
    medians = {k: med(f, k) for k, f in metrics.items()}
    # Kill time stays same-faction only: the raid-speed comparison never uses fill.
    fill = (
        tauren_fill(
            entries,
            fill_candidates,
            {k: m for k, m in medians.items() if k != "kill_s"},
            metrics,
        )
        if same_faction and fill_candidates
        else None
    )
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
        pet_families=pet_families(entries),
        tauren_fill=fill,
    )


@dataclass(frozen=True, slots=True)
class KillComparison:
    reference: str
    """`same-faction median` or the fastest entry's player name."""
    reference_s: Evidenced[float]
    ratio: Evidenced[float]
    """Subject kill time / reference kill time."""
    n_known: int
    membership: Evidenced[str]


@dataclass(frozen=True, slots=True)
class RaidSpeed:
    """Subject kill time against the same-faction median and the fastest same-faction kill."""

    subject_s: float
    vs_median: KillComparison
    vs_fastest: KillComparison | None
    basis: str | None
    """`median` or `fastest`: which comparison decides `flagged`; None when neither is known."""
    threshold: float | None
    flagged: bool


def _ratio(mine_s: float, ref: Evidenced[float], rule: str) -> Evidenced[float]:
    if ref.value is None or ref.value <= 0:
        return unknown("reference kill time unknown", *ref.refs)
    value = mine_s / ref.value
    if ref.level is EvidenceLevel.INFERRED:
        return inferred(value, *ref.refs, rule_id=rule)
    return derived(value, *ref.refs, rule_id=rule)


def raid_speed(entries: tuple[Entry, ...], subject: Entry, base: Baseline) -> RaidSpeed:
    """Rule raid-speed-v2. Uses true same-faction kill times only, never filled entries."""
    rule = load_rules("classic_era", "benchmarks")["raid_speed"]
    rule_id = str(rule["rule"])
    mine = subject.participant.duration_ms / 1000.0
    median = base.medians["kill_s"]
    vs_median = KillComparison(
        "same-faction median",
        median.value,
        _ratio(mine, median.value, rule_id),
        median.n_known,
        base.membership,
    )
    vs_fastest = None
    if entries:
        fastest = min(entries, key=lambda e: (e.participant.duration_ms, e.participant.player))
        member = membership((fastest,), subject)
        seconds = fastest.participant.duration_ms / 1000.0
        ref = EvidenceRef(
            fastest.participant.report_code,
            fastest.participant.fight_id,
            fastest.participant.actor_id,
            "fights",
            detail=f"fastest same-faction kill: {fastest.participant.player}",
        )
        reference = (
            inferred(seconds, ref, rule_id=rule_id)
            if member.level is not EvidenceLevel.DERIVED
            else derived(seconds, ref, rule_id=rule_id)
        )
        vs_fastest = KillComparison(
            fastest.participant.player,
            reference,
            _ratio(mine, reference, rule_id),
            len(entries),
            member,
        )
    basis: str | None = None
    threshold: float | None = None
    ratio: float | None = None
    if vs_median.ratio.value is not None:
        basis, threshold, ratio = "median", float(rule["ratio"]), vs_median.ratio.value
    elif vs_fastest is not None and vs_fastest.ratio.value is not None:
        basis, threshold = "fastest", float(rule["fallback_ratio"])
        ratio = vs_fastest.ratio.value
    flagged = ratio is not None and threshold is not None and ratio >= threshold
    return RaidSpeed(mine, vs_median, vs_fastest, basis, threshold, flagged)


def best_entry(entries: tuple[Entry, ...]) -> Entry | None:
    return entries[0] if entries else None


def faction_of(entry: Entry) -> Faction | None:
    return entry.profile.faction.value
