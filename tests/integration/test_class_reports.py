"""Every new class/category traverses the real offline report/package pipeline."""

import json
from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from tests.class_fixture import CASES, snapshot


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
