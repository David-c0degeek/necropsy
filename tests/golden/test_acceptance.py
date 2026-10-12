"""Milestone acceptance over the golden-fact register (uv run pytest -m acceptance).

Expected to fail until every mandatory fact is verified against raw data and
every other unverified fact has a recorded resolution.
"""

import pytest

from tests.golden.facts import load_register

pytestmark = pytest.mark.acceptance


def test_register_meets_acceptance() -> None:
    problems = load_register().acceptance_problems()
    assert not problems, "\n".join(problems)
