"""Ability use is class-neutral, coverage-aware and separate from damage ticks."""

from pathlib import Path

import duckdb
import pytest

from necropsy.analysis.benchmark import load_bosses
from necropsy.analysis.generic.metrics import ability_counts
from necropsy.normalize.ingest import ingest
from necropsy.report.abilities import rows
from tests.druid_fixture import snapshot


@pytest.mark.parametrize("partial", [False, True])
def test_ability_use_counts_actor_casts_not_healing_events(tmp_path: Path, partial: bool) -> None:
    raw = snapshot(tmp_path, ["Healing Touch"] * 3, partial=partial)
    db = tmp_path / "counts.duckdb"
    ingest(raw, db)
    with duckdb.connect(str(db)) as con:
        subject = load_bosses(con, "classic_era", "naxxramas")[0].subject
        assert subject is not None
        counts = ability_counts(con, subject.participant)
    assert counts.value == (None if partial else {"Healing Touch": 3})
    assert counts.refs and counts.coverage


def test_ability_comparison_preserves_unknown_versus_known_absence() -> None:
    comparison = rows(None, {"Aimed Shot": 4}, 60, 120)
    assert comparison[0]["counts"] == {
        "yours": None,
        "reference": 4,
        "difference": None,
        "difference_pct": None,
    }
    assert comparison[0]["per_minute"]["reference"] == 2
    assert comparison[0]["per_minute"]["yours"] is None
    absent = rows({}, {"Shred": 2}, 60, 60)
    assert absent[0]["counts"]["yours"] == 0
