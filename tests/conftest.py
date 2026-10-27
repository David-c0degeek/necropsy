"""Shared pytest options."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Allow the manual live acceptance test to contact Warcraft Logs.",
    )


@contextlib.contextmanager
def cohort_depth(deep: int) -> Iterator[None]:
    """Run with another supported live cohort depth (the rule is a cached mapping)."""
    from necropsy.rules import load_rules
    from necropsy.wcl import acquire, cohort

    rule = load_rules("classic_era", "benchmarks")["live_cohort"]
    assert deep in rule["accepted_deep"], deep
    previous = rule["deep"]
    rule["deep"] = deep
    acquire._live.cache_clear()
    cohort._cfg.cache_clear()
    try:
        yield
    finally:
        rule["deep"] = previous
        acquire._live.cache_clear()
        cohort._cfg.cache_clear()


@pytest.fixture
def historical_cohort_depth() -> Iterator[None]:
    """Scenarios written for the historical depth of 5 comparisons per boss."""
    with cohort_depth(5):
        yield


@pytest.fixture(scope="module")
def historical_cohort_depth_module() -> Iterator[None]:
    with cohort_depth(5):
        yield
