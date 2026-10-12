"""Golden facts that need the full export (uv run pytest -m golden)."""

from __future__ import annotations

import pytest

from tests.analysis_db import connect, full_db
from tests.fixture_paths import is_lfs_pointer, raw_export_path
from tests.golden.fact_checks import CHECKS, matches
from tests.golden.facts import FactStatus, load_register

pytestmark = pytest.mark.golden

REGISTER = load_register()


@pytest.mark.parametrize("fact_id", sorted(CHECKS))
def test_full_fact(fact_id: str) -> None:
    raw = raw_export_path()
    if not raw.is_file() or is_lfs_pointer(raw):
        pytest.fail(f"{raw.name} is missing or an LFS pointer. Run `git lfs pull` first.")
    fact = REGISTER.by_id(fact_id)
    with connect(full_db()) as con:
        actual = CHECKS[fact_id].compute(con)
    ok = matches(fact.expected, actual, fact.tolerance)
    if not ok and fact.status is not FactStatus.VERIFIED_AGAINST_RAW:
        pytest.xfail(f"{fact_id} is {fact.status.value}: computed {actual!r}")
    assert ok, f"{fact_id}: {actual!r}"
