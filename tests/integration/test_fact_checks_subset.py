"""Golden facts computable from the committed subset (fast suite)."""

from __future__ import annotations

import pytest

from tests.analysis_db import connect, subset_db
from tests.golden.fact_checks import CHECKS, matches
from tests.golden.facts import FactStatus, load_register

REGISTER = load_register()
SUBSET_CHECKS = sorted(f for f, c in CHECKS.items() if c.scope == "subset")


def test_every_checker_has_a_fact() -> None:
    ids = {f.id for f in REGISTER.facts}
    assert sorted(set(CHECKS) - ids) == []


def test_verified_facts_are_backed_by_a_checker() -> None:
    unbacked = [
        f.id
        for f in REGISTER.facts
        if f.status is FactStatus.VERIFIED_AGAINST_RAW and f.id not in CHECKS
    ]
    assert unbacked == []


@pytest.mark.parametrize("fact_id", SUBSET_CHECKS)
def test_subset_fact(fact_id: str) -> None:
    fact = REGISTER.by_id(fact_id)
    with connect(subset_db()) as con:
        actual = CHECKS[fact_id].compute(con)
    ok = matches(fact.expected, actual, fact.tolerance)
    if not ok and fact.status is not FactStatus.VERIFIED_AGAINST_RAW:
        pytest.xfail(f"{fact_id} is {fact.status.value}: computed {actual!r}")
    assert ok, f"{fact_id}: {actual!r}"
