"""Encounter rules and benchmark helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from necropsy.analysis import benchmark
from necropsy.analysis.encounters import encounter_rules
from necropsy.analysis.evidence import (
    Claim,
    CoverageRef,
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
from necropsy.analysis.generic.targets import RankedTarget

REF = EvidenceRef("R", 1, 1, "x")


def test_naxx_encounter_rules() -> None:
    faerlina = encounter_rules("classic_era", "naxxramas", 51110)
    assert faerlina.excluded_from_ranking(16506, "Naxxramas Worshipper")
    assert not faerlina.excluded_from_ranking(16505, "Naxxramas Follower")
    assert faerlina.native_game_ids is None
    with pytest.raises(ValueError, match="native"):
        faerlina.is_native(1, None)
    gothik = encounter_rules("classic_era", "naxxramas", 51109)
    assert gothik.is_native(16127, None)
    assert not gothik.is_native(16447, "Plagued Ghoul")
    other = encounter_rules("classic_era", "naxxramas", 1)
    assert other.ranking_excluded_game_ids == frozenset()
    assert other.native_game_ids is None


class _Shots:
    def __init__(self, raptors: int | None) -> None:
        self.casts = derived(tuple(range(raptors)), REF) if raptors is not None else unknown("x")


class _Hunter:
    def __init__(self, raptors: int | None) -> None:
        self.shots = {"raptor_strike": _Shots(raptors)}


class _Participant:
    report_code = "R"
    player = "P"
    fight_id = 1
    actor_id = 1
    duration_ms = 84038


class _Entry:
    def __init__(self, raptors: int | None = None, boss_share: int | None = None) -> None:
        """`raptors` casts; `boss_share` of them on the boss (all on the boss when None)."""
        self.participant = _Participant()
        self.hunter = _Hunter(raptors)
        if raptors is None:
            self.raptor_roles: Any = unknown("x")
        else:
            on_boss = raptors if boss_share is None else boss_share
            roles = benchmark.RaptorRoles(on_boss, raptors - on_boss, None, 0, None)
            self.raptor_roles = derived(roles, REF)


def _weave(counts: list[int | None]) -> Any:
    return benchmark.weave_adoption(tuple(_Entry(c) for c in counts))  # type: ignore[misc]


@pytest.mark.parametrize(
    ("counts", "verdict"),
    [
        ([9, 8, 6, 0], "yes"),
        ([1, 2, 0, 1], "opportunistic"),
        ([1, 0, 0, 0], "no"),
        ([9, 8, None], None),
    ],
)
def test_weave_verdict(counts: list[int | None], verdict: str | None) -> None:
    result = _weave(counts)
    assert result.boss.verdict.value == verdict
    if verdict is not None:
        assert result.boss.verdict.level is EvidenceLevel.INFERRED
        assert result.boss.verdict.rule_id == "weave-verdict-v2"
        assert dict(result.boss.verdict.params)["role"] == "boss"
        assert result.non_boss.verdict.value == "no"


def test_weave_is_judged_per_role() -> None:
    # Gothik-like: Raptor Strikes only on adds, never on the boss.
    entries = (_Entry(6, 0), _Entry(3, 0), _Entry(0), _Entry(0), _Entry(0))
    result = benchmark.weave_adoption(entries)  # type: ignore[arg-type]
    assert (result.boss.with_raptor, result.boss.verdict.value) == (0, "no")
    assert (result.non_boss.with_raptor, result.non_boss.with_five_raptors) == (2, 1)
    assert result.non_boss.verdict.value == "no"  # 2/5 is under the 0.5 share
    assert result.with_raptor == 2


def test_unresolved_raptor_targets_are_unknown_not_zero() -> None:
    entries = [_Entry(4, 4), _Entry(4, 4), _Entry(4, 4)]
    entries[2].raptor_roles = unknown("1 Raptor Strike casts have no resolved hostile target")
    result = benchmark.weave_adoption(tuple(entries))  # type: ignore[arg-type]
    assert result.boss.known == 2 and result.boss.verdict.value is None
    assert result.known == 3


def test_weave_counts_are_descriptive() -> None:
    result = _weave([9, 1, 0, None])
    assert (result.entries, result.known, result.with_raptor, result.with_five_raptors) == (
        4,
        3,
        2,
        1,
    )


def test_median_needs_three_known_values() -> None:
    entries = tuple(_Entry() for _ in range(4))
    values: dict[int, float | None] = {0: 1.0, 1: 3.0, 2: None, 3: None}

    def metric(e: Any) -> Any:
        v = values[entries.index(e)]
        return unknown("x") if v is None else derived(v, REF)

    small = benchmark.median_of(entries, metric, "x")  # type: ignore[arg-type]
    assert small.value.level is EvidenceLevel.UNKNOWN
    assert (small.n_known, small.n_unknown) == (2, 2)
    values[2] = 5.0
    enough = benchmark.median_of(entries, metric, "x")  # type: ignore[arg-type]
    assert enough.value.value == 3.0


def test_shot_target_range() -> None:
    median = benchmark.Median(derived(5.968134377675227, REF), 4, 0)
    result = benchmark.shot_target_range(median, _Entry())  # type: ignore[arg-type]
    assert result.value == (8, 9)
    assert result.rule_id == "shot-target-range-v1"
    missing = benchmark.shot_target_range(benchmark.Median(unknown("x"), 2, 0), _Entry())  # type: ignore[arg-type]
    assert missing.level is EvidenceLevel.UNKNOWN


def _member(faction: Any, aimed: Any) -> Any:
    shots = {"aimed_shot": SimpleNamespace(per_minute=aimed)}
    return SimpleNamespace(
        participant=SimpleNamespace(
            report_code="R", fight_id=1, actor_id=1, player="P", duration_ms=60000
        ),
        profile=SimpleNamespace(faction=faction),
        hunter=SimpleNamespace(shots=shots),
    )


SEEN = derived(Faction.ALLIANCE, REF)
GUESSED = inferred(Faction.ALLIANCE, REF, rule_id="raid-class-faction-v1")


def _aimed_median(subject: Any, members: list[Any]) -> Any:
    entries = tuple(members)
    weak = benchmark.membership(entries, subject).level is not EvidenceLevel.DERIVED
    return benchmark.median_of(
        entries,
        lambda e: e.hunter.shots["aimed_shot"].per_minute,
        "Aimed/min",
        inferred_membership=weak,
    )


def test_confirmed_membership_gives_a_derived_median() -> None:
    subject = _member(SEEN, derived(5.0, REF))
    med = _aimed_median(subject, [_member(SEEN, derived(v, REF)) for v in (6.0, 7.0, 8.0)])
    assert med.value.level is EvidenceLevel.DERIVED
    assert len(med.value.refs) == 3  # one auditable reference per member


def test_inferred_subject_faction_makes_the_median_inferred() -> None:
    subject = _member(GUESSED, derived(5.0, REF))
    med = _aimed_median(subject, [_member(SEEN, derived(v, REF)) for v in (6.0, 7.0, 8.0)])
    assert med.value.level is EvidenceLevel.INFERRED
    member = benchmark.membership((), subject)
    assert member.level is EvidenceLevel.INFERRED
    assert dict(member.params)["inferred_by"] == "raid-class-faction-v1"


def test_inferred_member_faction_makes_the_median_inferred() -> None:
    subject = _member(SEEN, derived(5.0, REF))
    members = [
        _member(SEEN, derived(6.0, REF)),
        _member(SEEN, derived(7.0, REF)),
        _member(GUESSED, derived(8.0, REF)),
    ]
    assert _aimed_median(subject, members).value.level is EvidenceLevel.INFERRED


def test_inferred_median_projects_an_inferred_range() -> None:
    median = benchmark.Median(inferred(6.0, REF, rule_id="r"), 3, 0)
    found = benchmark.shot_target_range(median, _Entry())  # type: ignore[arg-type]
    assert found.level is EvidenceLevel.INFERRED
    assert found.value == (8, 9)


def _horde(race: str | None, status: RaceStatus, wf: Any, aimed: float = 6.0) -> Any:
    entry = _member(SEEN, derived(aimed, REF))
    entry.profile.race = SimpleNamespace(
        race=derived(race, REF) if race else unknown("x"), status=status
    )
    entry.profile.windfury = SimpleNamespace(status_evidence=wf)
    return entry


WF_ABSENT = complete_or_unknown(
    WindfuryStatus.NOT_OBSERVED, [CoverageRef("R", 1, 1, "source", True)], REF
)
WF_SEEN = derived(WindfuryStatus.CONFIRMED, REF)
CONFIRMED = RaceStatus.RACIAL_EVENT_CONFIRMED


@pytest.mark.parametrize(
    ("entry", "reason"),
    [
        (_horde("Tauren", CONFIRMED, WF_ABSENT), None),
        (_horde("Tauren", RaceStatus.API_CONFIRMED, WF_ABSENT), None),
        (_horde("Troll", CONFIRMED, WF_ABSENT), "race Troll"),
        (_horde("Orc", CONFIRMED, WF_ABSENT), "race Orc"),
        (_horde(None, RaceStatus.UNKNOWN, WF_ABSENT), "race not proven"),
        (_horde("Tauren", RaceStatus.INFERRED, WF_ABSENT), "race not proven"),
        (_horde("Tauren", CONFIRMED, WF_SEEN), "Windfury not proven absent"),
        (_horde("Tauren", CONFIRMED, unknown("x")), "Windfury not proven absent"),
    ],
)
def test_fill_eligibility(entry: Any, reason: str | None) -> None:
    assert benchmark.fill_eligibility(entry) == reason


def test_tauren_fill_is_a_separate_inferred_view() -> None:
    same = tuple(_member(SEEN, derived(v, REF)) for v in (5.0, 7.0))
    others = (
        _horde("Tauren", CONFIRMED, WF_ABSENT, 9.0),
        _horde("Troll", CONFIRMED, WF_ABSENT, 20.0),
    )
    metric = {"aimed_per_min": lambda e: e.hunter.shots["aimed_shot"].per_minute}
    medians = {"aimed_per_min": benchmark.median_of(same, metric["aimed_per_min"], "Aimed/min")}
    assert medians["aimed_per_min"].value.value is None  # only two same-faction values
    fill = benchmark.tauren_fill(same, others, medians, metric)
    assert fill is not None
    assert fill.needed_for == ("aimed_per_min",)
    assert fill.excluded == (("P", "race Troll"),)
    filled = fill.medians["aimed_per_min"]
    assert filled.value.value == 7.0 and filled.value.level is EvidenceLevel.INFERRED
    assert fill.membership.rule_id == "tauren-fill-v1"


def test_no_fill_when_the_same_faction_suffices() -> None:
    same = tuple(_member(SEEN, derived(v, REF)) for v in (5.0, 6.0, 7.0))
    metric = {"aimed_per_min": lambda e: e.hunter.shots["aimed_shot"].per_minute}
    medians = {"aimed_per_min": benchmark.median_of(same, metric["aimed_per_min"], "x")}
    fill = benchmark.tauren_fill(same, (_horde("Tauren", CONFIRMED, WF_ABSENT),), medians, metric)
    assert fill is None


TRUSTED = CoverageRef("R", 1, 1, "source", True)


def _ranked(
    rows: list[tuple[int | None, str, int, str]] | None, ranked: int | None, kind: str = "NPC"
) -> Any:
    entry = _member(SEEN, derived(1.0, REF))
    by_target = (
        unknown("x")
        if rows is None
        else derived(
            tuple(RankedTarget(i, g, n, kind, d, c) for i, (g, n, d, c) in enumerate(rows)), REF
        )
    )
    entry.ranking = SimpleNamespace(
        ranked=unknown("x") if ranked is None else complete_or_unknown(ranked, [TRUSTED], REF),
        by_target=by_target,
    )
    return entry


def test_ranked_target_shares() -> None:
    boss = (16060, "Gothik", 0, "counted")
    ghoul = (16447, "Plagued Ghoul", 0, "counted")
    cohort = (
        _ranked([(*boss[:2], 20, "counted"), (*ghoul[:2], 80, "counted")], 100),
        _ranked([(*boss[:2], 50, "counted"), (*ghoul[:2], 50, "counted")], 100),
        _ranked([(*boss[:2], 100, "counted"), (16506, "Worshipper", 40, "excluded")], 100),
        _ranked(None, None),  # unknown entry: not counted as zero
    )
    subject = _ranked([(*boss[:2], 10, "counted")], 10)
    shares = benchmark.ranked_target_shares(cohort, subject, SEEN)
    by_name = {s.name: s for s in shares.counted}
    assert by_name["Plagued Ghoul"].median_share_pct.value == 50.0
    assert (by_name["Plagued Ghoul"].n_known, by_name["Plagued Ghoul"].n_unknown) == (3, 1)
    zero = by_name["Plagued Ghoul"].subject_share_pct
    assert zero.value == 0.0 and zero.claim is Claim.COMPLETE and zero.coverage == (TRUSTED,)
    assert by_name["Gothik"].median_share_pct.value == 50.0
    assert by_name["Gothik"].subject_share_pct.value == 100.0
    assert shares.excluded == ("Worshipper (16506)",)
    inferred_shares = benchmark.ranked_target_shares(cohort, subject, GUESSED)
    assert inferred_shares.counted[0].median_share_pct.level is EvidenceLevel.INFERRED
    few = benchmark.ranked_target_shares(cohort[2:], subject, SEEN)
    assert all(s.median_share_pct.value is None for s in few.counted)


def test_one_npc_identity_across_labels_and_instances() -> None:
    cohort = (
        _ranked([(16060, "Gothik", 60, "counted"), (16060, "Gothik", 40, "counted")], 100),
        _ranked([(16060, "Gothik", 100, "counted")], 100),
        _ranked([(16060, "Gothik der Ernter", 100, "counted")], 100),
    )
    subject = _ranked([(16060, "Gothik der Ernter", 10, "counted")], 10)
    shares = benchmark.ranked_target_shares(cohort, subject, SEEN)
    [only] = shares.counted
    assert (only.kind, only.game_id, only.name) == ("NPC", 16060, "Gothik")
    assert only.aliases == ("Gothik der Ernter",)
    assert only.median_share_pct.value == 100.0
    assert only.subject_share_pct.value == 100.0


def test_unknown_subject_ranking_gives_unknown_shares() -> None:
    cohort = tuple(_ranked([(16060, "Gothik", 100, "counted")], 100) for _ in range(3))
    shares = benchmark.ranked_target_shares(cohort, _ranked(None, None), SEEN)
    assert shares.counted[0].subject_share_pct.level is EvidenceLevel.UNKNOWN


def test_players_are_one_category_without_personal_aliases() -> None:
    cohort = tuple(
        _ranked([(0, name, 30, "counted")], 100, kind="Player") for name in ("Ann", "Bob", "Cid")
    )
    subject = _ranked([(0, "Dee", 10, "counted")], 100, kind="Player")
    [row] = benchmark.ranked_target_shares(cohort, subject, SEEN).counted
    assert (row.kind, row.game_id, row.aliases) == ("Player", None, ())
    assert row.name is not None and row.name.startswith("Players")
    assert row.median_share_pct.value == 30.0 and row.subject_share_pct.value == 10.0
