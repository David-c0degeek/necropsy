"""Report view model: playbook states, grading and labels."""

from __future__ import annotations

from typing import Any

import pytest

from necropsy.report.render import view as v


def _fact(yours: str | None, typical: str | bool | None = False) -> v.Fact:
    def value(level: str | None) -> v.Value:
        return v.Value("Unknown", "unknown", "x") if level is None else v.Value("1", level)

    return v.Fact("x", value(yours), None if typical is False else value(typical))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("facts", "status"),
    [
        ([_fact("observed", "derived"), _fact("derived")], "no-change"),
        ([_fact("observed", None), _fact("derived")], "partial"),
        ([_fact(None), _fact("derived")], "partial"),
        ([_fact(None), _fact(None, None)], "insufficient"),
        ([], "insufficient"),
    ],
)
def test_group_states(facts: list[v.Fact], status: str) -> None:
    assert v._group_status([], tuple(facts))[0] == status


def test_cards_always_mean_action() -> None:
    card: Any = object()
    state, text = v._group_status([card, card], (_fact(None),))
    assert (state, text) == ("action", "2 things to review")


def _baseline(level: str) -> dict[str, Any]:
    return {
        "membership": {"level": level},
        "talents": {"counts": {"20/31/0": 3, "12/33/6": 1}, "n_known": 4, "n_unknown": 0},
    }


def test_comparison_distributions_keep_the_membership_grade() -> None:
    confirmed = v._distribution_top(_baseline("derived"), "talents", {})
    assert (confirmed.text, confirmed.level) == ("20/31/0 (3/4)", "derived")
    guessed = v._distribution_top(_baseline("inferred"), "talents", {})
    assert guessed.level == "inferred" and guessed.note
    missing = v._distribution_top(None, "talents", {})
    assert missing.level == "unknown"


def test_evidence_labels_are_reader_facing() -> None:
    section = {
        "subject": {
            "environment": {"talents": {"value": "1/2/3", "level": "observed", "claim": "value"}}
        }
    }
    ev = v.evidence_view(section, "subject.environment.talents")
    assert ev.label == "Your talent build"
    assert ev.parts[0].path == "subject.environment.talents"


def test_unknown_values_keep_their_reason() -> None:
    shown = v.value_of({"value": None, "level": "unknown", "claim": "value", "note": "why"})
    assert (shown.text, shown.known, shown.note) == ("Unknown", False, "why")
