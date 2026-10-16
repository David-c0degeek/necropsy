"""Every new class/category traverses the real offline report/package pipeline."""

import json
from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from tests.class_fixture import CASES, snapshot


@pytest.mark.parametrize(
    ("class_id", "category", "ability", "role", "points", "tree"),
    [
        (8, "Assassination", "Sinister Strike", "dps", (17, 34, 0), "Combat"),
        (11, "Protection", "Shield Slam", "tank", (0, 33, 18), "Fury"),
        (10, "Destruction", "Shadow Bolt", "dps", (9, 21, 21), None),
        (4, "Frost", "Frostbolt", "dps", (31, 0, 20), "Arcane"),
    ],
)
def test_build_category_and_duty_remain_separate_through_offline_report(
    tmp_path: Path,
    class_id: int,
    category: str,
    ability: str,
    role: str,
    points: tuple[int, ...],
    tree: str | None,
) -> None:
    archive = snapshot(tmp_path, class_id, category, ability, role, tree_totals=points)
    out = tmp_path / "out"
    run_offline(archive, out)
    doc = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    identity = doc["taxonomy"]["entries"][0]
    assert identity["primary_tree"]["value"] == tree
    assert identity["wcl_category"]["slug"] == category
    assert identity["duty"]["value"] == role
    assert doc["taxonomy"]["comparison_pool"]["slug"] == category
    assert identity["race"]["value"] is None
    assert identity["race_class_faction_valid"]["value"] is None
    assert doc["bosses"][0]["subject"] is not None
    page = (out / "playbook.html").read_text(encoding="utf-8")
    assert "does not narrow the leaderboard" in page
    assert "Observed builds, categories, duties and race evidence" in page


def test_malformed_talent_evidence_does_not_create_a_match_in_shared_report(tmp_path: Path) -> None:
    archive = snapshot(
        tmp_path, 8, "Assassination", "Sinister Strike", "dps", tree_totals=(0, 0, 0, 0, 0, 0, 0)
    )
    out = tmp_path / "out"
    run_offline(archive, out)
    doc = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    assert doc["taxonomy"]["entries"][0]["tree_points"]["value"] is None
    assert doc["bosses"][0]["playbook"]["comparisons"][0]["build_matches"] is None


@pytest.mark.parametrize(("class_id", "category", "ability", "role"), CASES)
def test_class_snapshot_produces_role_aware_execution_and_package(
    tmp_path: Path,
    class_id: int,
    category: str,
    ability: str,
    role: str,
) -> None:
    archive = snapshot(tmp_path, class_id, category, ability, role)
    out = tmp_path / "out"
    run_offline(archive, out)
    document = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    boss = document["bosses"][0]
    assert boss["subject"] is not None
    assert boss["subject"]["combat"]["role"]["value"] == role
    assert boss["playbook"]["selected_category"] == category
    assert boss["playbook"]["reference"]["player"] == "Leader"
    assert len(boss["playbook"]["comparisons"]) == 1
    assert boss["benchmarks"]["baseline"]["medians"]["damage_per_second"]["value"]["value"] is None
    page = (out / "playbook.html").read_text(encoding="utf-8")
    assert "Execution plan" in page and "first use" in page and ability in page
    assert "Ability use vs Leader" in page
    assert "Druid" not in page and "Raptor" not in page
    assert list(out.glob("necropsy-*.zip"))


def test_partial_personal_casts_are_excluded_but_leader_practice_remains(tmp_path: Path) -> None:
    archive = snapshot(tmp_path, 4, "Fire", "Fireball", "dps", partial=True)
    out = tmp_path / "out"
    run_offline(archive, out)
    doc = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    boss = doc["bosses"][0]
    assert boss["subject"] is None
    assert boss["playbook"]["reference"]["player"] == "Leader"
    assert boss["playbook"]["comparisons"] == []
    assert boss["playbook"]["excluded_subject"]["ability_use"]["value"] is None


@pytest.mark.parametrize("mixed", [False, True])
def test_ranking_category_does_not_override_missing_tank_duty_or_mixed_actions(
    tmp_path: Path,
    mixed: bool,
) -> None:
    archive = (
        snapshot(tmp_path, 7, "Shadow", "Mind Flay", "dps", secondary_healing=True)
        if mixed
        else snapshot(tmp_path, 11, "Protection", "Shield Slam", "tank", subject_tank_hits=False)
    )
    out = tmp_path / "out"
    run_offline(archive, out)
    boss = json.loads((out / "analysis.json").read_text(encoding="utf-8"))["bosses"][0]
    assert boss["subject"] is None
    assert boss["playbook"]["comparisons"] == []
    excluded = boss["playbook"]["excluded_subject"]["combat"]
    assert excluded["role"]["value"] == ("hybrid" if mixed else None)
    assert boss["playbook"]["reference"]["player"] == "Leader"


@pytest.mark.parametrize(("category", "role"), [("Holy", "healer"), ("Retribution", "dps")])
def test_dual_use_holy_shock_uses_its_recorded_effect_to_infer_duty(
    tmp_path: Path,
    category: str,
    role: str,
) -> None:
    archive = snapshot(tmp_path, 6, category, "Holy Shock", role)
    out = tmp_path / "out"
    run_offline(archive, out)
    boss = json.loads((out / "analysis.json").read_text(encoding="utf-8"))["bosses"][0]
    assert boss["subject"] is not None
    assert boss["subject"]["combat"]["role"]["value"] == role
