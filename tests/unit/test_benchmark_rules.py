"""Encounter rules and benchmark helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from necropsy.analysis import benchmark
from necropsy.analysis.encounters import encounter_rules
from necropsy.analysis.evidence import (
    EvidenceLevel,
    EvidenceRef,
    Faction,
    derived,
    inferred,
    unknown,
)

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
    def __init__(self, raptors: int | None = None) -> None:
        self.participant = _Participant()
        self.hunter = _Hunter(raptors)


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
    assert result.verdict.value == verdict
    if verdict is not None:
        assert result.verdict.level is EvidenceLevel.INFERRED
        assert result.verdict.rule_id == "weave-verdict-v1"


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
