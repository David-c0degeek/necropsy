"""Recommendation rules: suppression on unknown inputs and confidence tiering."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from necropsy.analysis import recommendations as rec
from necropsy.analysis.benchmark import Median, raid_speed
from necropsy.analysis.evidence import EvidenceRef, Faction, derived, inferred, unknown

REF = EvidenceRef("R", 1, 1, "x")
BOSS: Any = SimpleNamespace(boss="Patchwerk")


def _subject(aimed: Any) -> Any:
    shots = {"aimed_shot": SimpleNamespace(per_minute=aimed)}
    return SimpleNamespace(hunter=SimpleNamespace(shots=shots))


def _base(median: Any, n_known: int = 4) -> Any:
    medians = {"aimed_per_min": Median(median, n_known, 0)}
    return SimpleNamespace(medians=medians, shot_targets={}, tauren_fill=None)


def test_aimed_rule_emits_nothing_when_an_input_is_unknown() -> None:
    assert rec._aimed(BOSS, _subject(unknown("x")), _base(derived(8.0, REF)), None) == []
    assert rec._aimed(BOSS, _subject(derived(5.0, REF)), _base(unknown("x")), None) == []


def test_aimed_rule_needs_a_real_shortfall() -> None:
    assert rec._aimed(BOSS, _subject(derived(7.3, REF)), _base(derived(8.0, REF)), None) == []
    [found] = rec._aimed(BOSS, _subject(derived(7.0, REF)), _base(derived(8.0, REF)), None)
    assert found.confidence is rec.Tier.HIGH
    assert found.controllability is rec.Controllability.PLAYER
    assert found.limitations == ()


def test_confidence_drops_with_inferred_inputs_and_small_samples() -> None:
    subject = _subject(derived(5.0, REF))
    [medium] = rec._aimed(BOSS, subject, _base(inferred(8.0, REF, rule_id="r")), None)
    assert medium.confidence is rec.Tier.MEDIUM
    [small] = rec._aimed(BOSS, subject, _base(derived(8.0, REF), n_known=3), None)
    assert small.confidence is rec.Tier.MEDIUM


def test_raid_utility_inside_the_gap_qualifies_the_finding() -> None:
    utility: Any = SimpleNamespace(utility_inside_gap=True)
    [found] = rec._aimed(BOSS, _subject(derived(5.0, REF)), _base(derived(8.0, REF)), utility)
    assert found.confidence is rec.Tier.LOW
    assert found.limitations


def test_recommend_without_subject_is_empty() -> None:
    boss: Any = SimpleNamespace(subject=None)
    assert rec.recommend(boss, None, None, None, None, None, [], {}) == []  # type: ignore[arg-type]


def _fighter(faction: Any, duration_ms: int) -> Any:
    return SimpleNamespace(
        participant=SimpleNamespace(
            report_code="R", fight_id=1, actor_id=1, player="P", duration_ms=duration_ms
        ),
        profile=SimpleNamespace(faction=faction),
    )


SEEN = derived(Faction.ALLIANCE, REF)
GUESSED = inferred(Faction.ALLIANCE, REF, rule_id="raid-class-faction-v1")


def _speed(subject: Any, others: list[Any], median_s: float | None, member: Any) -> Any:
    kill = Median(
        unknown("x")
        if median_s is None
        else (derived(median_s, REF) if member is SEEN else inferred(median_s, REF, rule_id="r")),
        0 if median_s is None else 3,
        0,
    )
    base: Any = SimpleNamespace(medians={"kill_s": kill}, membership=member)
    return raid_speed(tuple(others), subject, base)


def test_raid_speed_uses_the_median_and_always_reports_the_fastest() -> None:
    subject = _fighter(SEEN, 67_000)
    others = [_fighter(SEEN, 42_000), _fighter(SEEN, 53_000), _fighter(SEEN, 60_000)]
    speed = _speed(subject, others, 52.551, SEEN)
    assert speed.basis == "median" and speed.threshold == 1.5 and not speed.flagged
    assert speed.vs_fastest is not None
    assert speed.vs_fastest.reference_s.value == 42.0
    assert round(speed.vs_fastest.ratio.value, 2) == 1.6
    assert rec._raid_speed(BOSS, speed) == []


def test_raid_speed_falls_back_to_the_fastest_kill_at_two_x() -> None:
    subject = _fighter(SEEN, 116_000)
    speed = _speed(subject, [_fighter(SEEN, 21_000), _fighter(SEEN, 30_000)], None, SEEN)
    assert speed.basis == "fastest" and speed.threshold == 2.0 and speed.flagged
    [found] = rec._raid_speed(BOSS, speed)
    assert found.confidence is rec.Tier.LOW
    assert found.benchmark["view"] == "same-faction-fastest"
    near = _speed(_fighter(SEEN, 40_000), [_fighter(SEEN, 21_000)], None, SEEN)
    assert near.basis == "fastest" and not near.flagged


def test_raid_speed_confidence_follows_membership() -> None:
    others = [_fighter(SEEN, 90_000)] * 3
    confirmed = _speed(_fighter(SEEN, 177_000), others, 92.0, SEEN)
    [found] = rec._raid_speed(BOSS, confirmed)
    assert found.confidence is rec.Tier.MEDIUM
    guessed = _speed(_fighter(SEEN, 177_000), others, 92.0, GUESSED)
    [weak] = rec._raid_speed(BOSS, guessed)
    assert weak.confidence is rec.Tier.LOW


def test_raid_speed_does_not_assert_a_cause() -> None:
    speed = _speed(_fighter(SEEN, 177_000), [_fighter(SEEN, 90_000)] * 3, 92.0, SEEN)
    [found] = rec._raid_speed(BOSS, speed)
    assert "not individual execution" not in found.recommendation
    assert "your own execution" in found.recommendation


def test_no_entries_means_no_fastest_comparison() -> None:
    speed = _speed(_fighter(SEEN, 100_000), [], None, SEEN)
    assert speed.vs_fastest is None and speed.basis is None and not speed.flagged


def test_baseline_rules_carry_inferred_membership() -> None:
    mine = derived("12/33/6", REF)
    talents = SimpleNamespace(
        most_common=lambda: [("20/31/0", 4)], n_known=5, share=lambda build: 0.8
    )
    subject: Any = SimpleNamespace(profile=SimpleNamespace(talents=mine))
    for member, tier in ((SEEN, rec.Tier.HIGH), (GUESSED, rec.Tier.MEDIUM)):
        base: Any = SimpleNamespace(talents=talents, membership=member)
        [found] = rec._talents(BOSS, subject, base)
        assert found.confidence is tier


def test_padding_confidence_carries_membership() -> None:
    share = derived(2.0, REF)
    integrity: Any = SimpleNamespace(foreign_share_pct=share)
    shares = [40.0, 50.0, 60.0, 70.0]
    for member, tier in ((SEEN, rec.Tier.HIGH), (GUESSED, rec.Tier.MEDIUM)):
        base: Any = SimpleNamespace(membership=member)
        [found] = rec._padding(BOSS, base, integrity, shares)
        assert found.confidence is tier
        assert "benchmarks.baseline.membership" in found.evidence
