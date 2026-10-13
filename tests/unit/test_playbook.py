"""Playbook decision helpers: thresholds and unknown handling."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from necropsy.analysis import playbook
from necropsy.analysis.evidence import (
    EvidenceLevel,
    EvidenceRef,
    WindfuryStatus,
    derived,
    observed,
    unknown,
)

REF = EvidenceRef("R", 1, 1, "x")


def casts(value: Any) -> Any:
    return SimpleNamespace(casts=value)


def _entry(wf: WindfuryStatus, swings: int | None, rf: Any = None, refocus: Any = None) -> Any:
    shots = {"raptor_strike": casts(derived((), REF))}
    return SimpleNamespace(
        participant=SimpleNamespace(player="P", leaderboard_position=1, duration_ms=100_000),
        profile=SimpleNamespace(
            faction=derived(None, REF)
            if False
            else SimpleNamespace(value=None, level=EvidenceLevel.UNKNOWN),
            race=SimpleNamespace(race=observed("Orc", REF)),
            windfury=SimpleNamespace(
                status=wf, procs=derived(3, REF), attributed_damage=unknown("x")
            ),
        ),
        ranked_dps=1000.0,
        hunter=SimpleNamespace(
            white_melee_swings=derived(swings, REF) if swings is not None else unknown("x"),
            white_melee_damage=derived(5000, REF),
            shots=shots,
            gear=SimpleNamespace(
                ranged=unknown("x"), main_hand=unknown("x"), off_hand=unknown("x")
            ),
            rapid_fire=casts(rf if rf is not None else unknown("x")),
            refocus=casts(refocus if refocus is not None else unknown("x")),
        ),
    )


def test_melee_package_needs_windfury_or_enough_swings() -> None:
    assert playbook._melee_package(_entry(WindfuryStatus.CONFIRMED, 0), 5) is not None
    assert playbook._melee_package(_entry(WindfuryStatus.NOT_OBSERVED, 5), 5) is not None
    assert playbook._melee_package(_entry(WindfuryStatus.NOT_OBSERVED, 4), 5) is None
    assert playbook._melee_package(_entry(WindfuryStatus.UNKNOWN, None), 5) is None
    package = playbook._melee_package(_entry(WindfuryStatus.CONFIRMED, 13), 5)
    assert package is not None and package.white_dps == 50.0
    assert package.windfury_matched_damage is None  # unknown stays unknown
    assert package.windfury_matched_level == "unknown"


def test_cooldowns_keep_unknown_apart_from_not_used() -> None:
    cast = SimpleNamespace(t_s=4.2)
    subject_unknown = _entry(WindfuryStatus.UNKNOWN, 0)
    subject_none = _entry(WindfuryStatus.UNKNOWN, 0, rf=derived((), REF))
    rank_one = _entry(WindfuryStatus.UNKNOWN, 0, rf=derived((cast,), REF))
    plan = playbook._cooldown(subject_unknown, (rank_one,), (rank_one,), rank_one, "rapid_fire")
    assert plan.subject_used is None and plan.subject_first_s is None
    plan = playbook._cooldown(subject_none, (rank_one,), (rank_one,), rank_one, "rapid_fire")
    assert plan.subject_used is False
    assert plan.rank_one is not None and plan.rank_one.first_s == 4.2
    assert plan.rank_one.used is True
    first = plan.same_faction_first_s
    assert first.value is None and first.level == "unknown" and first.n_values == 1
    # Rank 1 with complete, empty casts is a proven non-use, not an unknown.
    plan = playbook._cooldown(subject_none, (), (), subject_none, "rapid_fire")
    assert plan.rank_one is not None
    assert (plan.rank_one.first_s, plan.rank_one.used) == (None, False)
    plan = playbook._cooldown(subject_none, (), (), subject_unknown, "rapid_fire")
    assert plan.rank_one is not None and plan.rank_one.used is None


def test_aggregates_need_three_known_values_and_keep_the_grade() -> None:
    one = playbook.aggregate([4.0], False)
    two = playbook.aggregate([4.0, 6.0, playbook.NO_VALUE, None], False)
    three = playbook.aggregate([4.0, 6.0, 9.0, playbook.NO_VALUE, None], False)
    assert one.value is None and "need 3" in (one.reason or "")
    nobody = playbook.aggregate([playbook.NO_VALUE] * 4, False)
    assert (
        nobody.level == "unknown"
        and nobody.reason == "0 of 4 known entries cast it (need 3 timings)"
    )
    assert (two.value, two.n_values, two.n_without, two.n_unknown) == (None, 2, 1, 1)
    assert (three.value, three.level) == (6.0, "derived")
    guessed = playbook.aggregate([4.0, 6.0, 9.0], True)
    assert guessed.level == "inferred" and guessed.reason
    assert playbook.aggregate([4.0, 6.0, 9.0], False, "min").value == 4.0
    assert playbook.aggregate([4.0, 6.0, 9.0], False, "max").value == 9.0


def test_matched_windfury_damage_is_labelled_inferred() -> None:
    entry = _entry(WindfuryStatus.CONFIRMED, 13)
    entry.profile.windfury.attributed_damage = SimpleNamespace(
        value=500, level=EvidenceLevel.INFERRED
    )
    package = playbook._melee_package(entry, 5)
    assert package is not None
    assert (package.windfury_matched_damage, package.windfury_matched_level) == (500, "inferred")
