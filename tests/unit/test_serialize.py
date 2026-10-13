"""Deterministic JSON conversion of analysis objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pytest

from necropsy.analysis.evidence import EvidenceRef, derived, unknown
from necropsy.report.serialize import JSON_EVENT_REFS, evidence, to_data


class _Colour(StrEnum):
    RED = "red"


@dataclass(frozen=True)
class _Row:
    name: str
    colour: _Colour
    ratio: float
    tags: frozenset[str]


def test_to_data_converts_and_rounds() -> None:
    row = _Row("a", _Colour.RED, 1 / 3, frozenset({"z", "b"}))
    assert to_data(row) == {"name": "a", "colour": "red", "ratio": 0.333333, "tags": ["b", "z"]}
    assert to_data((3, 1, 2)) == [3, 1, 2]
    assert to_data({1: True}) == {"1": True}


def test_to_data_refuses_unknown_types() -> None:
    with pytest.raises(TypeError, match="object"):
        to_data(object())


def test_evidence_caps_listed_events_but_keeps_the_count() -> None:
    ids = tuple((f"u{i}", 0) for i in range(JSON_EVENT_REFS + 5))
    ref = EvidenceRef("R", 1, 2, "events", event_ids=ids, event_count=len(ids))
    data = evidence(derived(4, ref, rule_id="r", note="n"))
    [out] = data["refs"]
    assert len(out["events"]) == JSON_EVENT_REFS
    assert out["event_count"] == JSON_EVENT_REFS + 5
    assert (data["value"], data["level"], data["rule"], data["note"]) == (4, "derived", "r", "n")


def test_unknown_evidence_has_null_value() -> None:
    data = evidence(unknown("missing"))
    assert data["value"] is None and data["level"] == "unknown"
    assert "refs" not in data
