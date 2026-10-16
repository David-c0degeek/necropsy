"""Talent intent, evidence and WCL pools remain independent."""

import json
from pathlib import Path
from typing import Any

import pytest

from necropsy.analysis.class_catalog import TALENT_TREES, WCL_CATEGORIES, talent_tree
from necropsy.analysis.evidence import EvidenceLevel, EvidenceRef, observed, unknown
from necropsy.analysis.roles import ranking_policy
from necropsy.analysis.taxonomy import build_matches, primary_tree, race_validity, talent_points
from necropsy.normalize.ingest import _talent_points
from necropsy.tui.service import categories


def test_wcl_catalog_matches_recorded_primary_metadata() -> None:
    receipt = json.loads(
        (Path(__file__).parents[2] / "docs/assets/class-taxonomy-2026-10-16.json").read_text(
            encoding="utf-8"
        )
    )
    actual = {
        c["id"]: {s["slug"]: (s["id"], s["name"]) for s in c["specs"]} for c in receipt["catalog"]
    }
    assert actual == WCL_CATEGORIES
    for class_id, items in WCL_CATEGORIES.items():
        for slug in items:
            assert ranking_policy(class_id, slug).class_id == class_id


@pytest.mark.parametrize(
    ("class_id", "label", "slug"),
    [
        (8, "DPS", "Assassination"),
        (10, "DPS", "Destruction"),
        (11, "Tank", "Protection"),
        (7, "Healer", "Holy"),
        (2, "Tank", "Guardian"),
    ],
)
def test_category_display_does_not_become_talent_diagnosis(
    class_id: int,
    label: str,
    slug: str,
) -> None:
    assert (label, slug) in categories(class_id)
    assert ranking_policy(class_id, slug).category == slug
    assert WCL_CATEGORIES[class_id][slug][1] == label


def test_all_game_trees_exist_without_fabricating_ranking_pools() -> None:
    assert sum(map(len, TALENT_TREES.values())) == 27
    assert sum(map(len, WCL_CATEGORIES.values())) == 19
    assert talent_tree(3, "Beastmastery") == "Beast Mastery"
    assert talent_tree(3, "Marksman") == "Marksmanship"
    assert talent_tree(8, "Combat") == "Combat"
    assert talent_tree(4, "Arcane") == "Arcane"
    with pytest.raises(ValueError):
        ranking_policy(8, "Combat")
    with pytest.raises(ValueError):
        talent_tree(8, "Arcane")


@pytest.mark.parametrize(
    "raw",
    [
        [{"id": 0}] * 7,
        [{"id": True}, {"id": 30}, {"id": 20}],
        [{"id": -1}, {"id": 32}, {"id": 20}],
        [{"id": 20}, {"id": 32}, {"id": 20}],
        [],
        None,
    ],
)
def test_placeholders_malformed_and_bool_totals_cannot_become_builds(raw: Any) -> None:
    assert talent_points(raw, "id") is None
    assert _talent_points(raw) is None


def test_report_guid_and_event_id_shapes_preserve_totals_without_spell_names() -> None:
    ref = EvidenceRef("report", 1, 1, "combatantinfo")
    points = [17, 34, 0]
    event = [{"id": n} for n in points]
    details = [{"guid": n, "name": "Unrelated spell decoration"} for n in points]
    assert talent_points(event, "id") == talent_points(details, "guid") == "17/34/0"
    tree = primary_tree(8, observed("17/34/0", ref))
    assert tree.value == "Combat" and tree.level is EvidenceLevel.DERIVED
    assert primary_tree(11, observed("0/33/18", ref)).value == "Fury"
    assert ranking_policy(11, "Protection").role == "tank"
    assert primary_tree(10, observed("9/21/21", ref)).value is None
    assert primary_tree(3, unknown("missing")).value is None
    assert primary_tree(3, observed("0/0/0", ref)).value is None


def test_build_match_is_three_state() -> None:
    assert build_matches(None, None) is None
    assert build_matches("17/34/0", None) is None
    assert build_matches("invalid", "invalid") is None
    assert build_matches("17/34/0", "17/34/0") is True
    assert build_matches("17/34/0", "19/32/0") is False


@pytest.mark.parametrize(
    ("class_id", "race", "faction", "expected"),
    [
        (2, "Night Elf", "Alliance", True),
        (2, "Tauren", "Horde", True),
        (3, "Gnome", "Alliance", False),
        (6, "Human", "Horde", False),
        (2, None, "Alliance", None),
        (11, "Orc", None, None),
        (11, "Unknown race", "Horde", False),
    ],
)
def test_catalog_constraints_validate_identity_without_guessing_race(
    class_id: int,
    race: str | None,
    faction: str | None,
    expected: bool | None,
) -> None:
    assert race_validity(class_id, race, faction) is expected
