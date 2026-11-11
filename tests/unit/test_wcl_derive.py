"""Ownership and critical-domain guards for the versioned full-fight projections."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from necropsy.wcl.derive import (
    CRITICAL_RULE,
    SOURCE_RULE,
    DerivationUnsupported,
    project_pages,
    source_actor_ids,
)


def report() -> dict[str, Any]:
    return {
        "masterData": {
            "actors": [
                {"id": 5, "type": "Player"},
                {"id": 7, "petOwner": 5},
                {"id": 9, "petOwner": 7},
                {"id": 11, "petOwner": 5},
            ]
        },
        "fights": [{"id": 1, "friendlyPets": [{"id": 7, "petOwner": 5}]}],
    }


def test_source_includes_unlisted_catalog_units_and_transitive_ownership() -> None:
    assert source_actor_ids(report(), 1, 5) == (5, 7, 9, 11)
    assert source_actor_ids(report(), 1, 7) == (7, 9)


def test_unowned_environment_actor_and_observed_noncritical_hit_type_are_supported() -> None:
    data = report()
    data["masterData"]["actors"].append({"id": -1, "type": "NPC", "name": "Environment"})
    assert source_actor_ids(data, 1, 5) == (5, 7, 9, 11)
    pages = [
        {"data": [{"timestamp": 1, "type": "damage", "hitType": 15}], "nextPageTimestamp": None}
    ]
    assert project_pages(pages, CRITICAL_RULE) == [{"data": [], "nextPageTimestamp": None}]


@pytest.mark.parametrize(
    "case",
    [
        "duplicate",
        "cycle",
        "conflict",
        "bool-owner",
        "missing-owner",
        "missing-fight",
        "missing-list",
        "malformed-catalog",
    ],
)
def test_ambiguous_ownership_is_unsupported(case: str) -> None:
    data = report()
    if case == "duplicate":
        data["masterData"]["actors"].append({"id": 5})
    elif case == "cycle":
        data["masterData"]["actors"][0]["petOwner"] = 9
    elif case == "conflict":
        data["fights"][0]["friendlyPets"][0]["petOwner"] = 11
    elif case == "bool-owner":
        data["masterData"]["actors"][1]["petOwner"] = True
    elif case == "missing-owner":
        data["masterData"]["actors"][0]["petOwner"] = 99
    elif case == "missing-fight":
        data["fights"] = []
    elif case == "missing-list":
        data["fights"][0]["friendlyPets"] = None
    elif case == "malformed-catalog":
        data["masterData"] = []
    with pytest.raises(DerivationUnsupported):
        source_actor_ids(data, 1, 5)


def test_projection_preserves_empty_pages_order_duplicates_and_input() -> None:
    event = {"timestamp": 6, "type": "damage", "sourceID": 7, "hitType": 2}
    pages: list[dict[str, Any]] = [
        {"data": [{"timestamp": 1, "type": "cast", "sourceID": 20}], "nextPageTimestamp": 5},
        {"data": [event, dict(event)], "nextPageTimestamp": None},
    ]
    before = copy.deepcopy(pages)
    projected = project_pages(pages, SOURCE_RULE, actor_ids=(5, 7))
    assert projected == [
        {"data": [], "nextPageTimestamp": 5},
        {"data": [event, event], "nextPageTimestamp": None},
    ]
    assert project_pages(pages, CRITICAL_RULE) == projected
    assert pages == before


@pytest.mark.parametrize("hit", [None, True, 9, 999, -1, "2"])
def test_unknown_hit_type_cannot_certify_critical_absence(hit: Any) -> None:
    pages = [
        {"data": [{"timestamp": 1, "type": "damage", "hitType": hit}], "nextPageTimestamp": None}
    ]
    with pytest.raises(DerivationUnsupported, match="hit type"):
        project_pages(pages, CRITICAL_RULE)
