"""Every new class/category traverses the real offline report/package pipeline."""

import json
from html import unescape
from pathlib import Path

import pytest

from necropsy.report.analysis_json import dumps
from necropsy.report.offline import run_offline
from necropsy.report.render import render_report, view_of
from necropsy.report.render.class_view import bosses as class_bosses
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
    page = (out / "report.html").read_text(encoding="utf-8")
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
    assert "During the fight" in page and ability in page
    assert "Before the pull" in page and "Coordinate with the raid" in page
    assert "<table" not in page and "Ability use vs Leader" not in page
    assert "Not proof of an optimal opener" in page
    report = (out / "report.html").read_text(encoding="utf-8")
    assert "Execution plan" in report and "first use" in report and ability in report
    assert "Ability use vs Leader" in report
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


@pytest.mark.parametrize("include_reference", [False, True])
def test_practice_guidance_requires_an_eligible_recorded_reference(
    tmp_path: Path, include_reference: bool
) -> None:
    archive = snapshot(
        tmp_path, 7, "Holy", "Flash Heal", "healer", include_reference=include_reference
    )
    out = tmp_path / "guidance"
    run_offline(archive, out)
    document = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    boss = document["bosses"][0]
    assert boss["subject"] is not None
    playbook = boss["playbook"]
    assert (playbook["reference"] is not None) is include_reference
    assert ("Use the leader's recorded opener" in playbook["guidance"]) is include_reference
    assert ("Highest-ranked acquired eligible example" in playbook["reference_note"]) is (
        include_reference
    )
    for name in ("report.html", "playbook.html"):
        html = unescape((out / name).read_text(encoding="utf-8"))
        assert ("Use the leader's recorded opener" in html) is include_reference
        if not include_reference:
            assert "No eligible recorded opener or ability mix is available" in html


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


def test_saved_event_copy_indices_render_as_values_and_are_deterministic(tmp_path: Path) -> None:
    archive = snapshot(tmp_path, 4, "Fire", "Fireball", "dps")
    out = tmp_path / "events"
    run_offline(archive, out)
    document = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    boss = document["bosses"][0]
    event = boss["subject"]["combat"]["timeline"][0]
    event.update(uid="a" * 64, copy=3)
    boss["subject"]["combat"]["cooldowns"] = [{**event, "uid": "b" * 64, "copy": 4}]
    boss["overall_cohort"][0]["combat"]["timeline"][0].update(uid="c" * 64, copy=5)
    saved = dumps(document).encode("utf-8")
    report = render_report(view_of(saved))
    for uid, copy in (("a" * 64, 3), ("b" * 64, 4), ("c" * 64, 5)):
        assert f"{uid}/{copy}" in report
    assert "built-in method" not in report
    # Separate JSON loads create different dictionaries; their addresses cannot
    # become event identities or change a reproducible saved report.
    assert report == render_report(view_of(saved))
    # Older saved rows may lack a copy index. Missing/null is explicit unknown,
    # never a fallback to a dictionary method with a process-specific address.
    event.pop("copy")
    boss["subject"]["combat"]["cooldowns"][0]["copy"] = None
    boss["overall_cohort"][0]["combat"]["timeline"][0].pop("copy")
    old_saved = dumps(document).encode("utf-8")
    old_report = render_report(view_of(old_saved))
    for uid in ("a" * 64, "b" * 64, "c" * 64):
        assert f"{uid}/Unknown" in old_report
    assert "built-in method" not in old_report
    assert old_report == render_report(view_of(old_saved))


@pytest.mark.parametrize("personal", ["missing", "excluded", "unknown-duty"])
def test_reference_build_and_duty_never_become_personal_context(
    tmp_path: Path, personal: str
) -> None:
    archive = snapshot(tmp_path, 7, "Holy", "Flash Heal", "healer")
    out = tmp_path / "context"
    run_offline(archive, out)
    document = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    boss = document["bosses"][0]
    subject = boss["subject"]
    subject["combat"]["build"]["value"] = "10/41/0"
    leader = boss["playbook"]["reference"]
    leader["combat"]["build"]["value"] = "31/20/0"
    leader["combat"]["role"]["value"] = "healer"
    boss["subject"] = None
    boss["playbook"]["excluded_subject"] = None if personal == "missing" else subject
    if personal == "unknown-duty":
        subject["combat"]["role"]["value"] = None
    saved = dumps(document).encode("utf-8")
    view = class_bosses(json.loads(saved), "test-context", "combat")[boss["encounter_id"]]
    context = dict(view["context"])
    assert context["Build"] == ("Unknown" if personal == "missing" else "10/41/0")
    assert context["Encounter duty"] == ("healer" if personal == "excluded" else "Unknown")
    assert view["metrics"][0][1].text == "Unknown"
    assert view["metrics"][1][1].text != "Unknown"
    report = render_report(view_of(saved))
    strip = report.split('<div class="context-strip">', 1)[1].split("</details>", 1)[0]
    assert "31/20/0" not in strip
    assert context["Build"] in strip and context["Encounter duty"] in strip
    assert "No personal finding is available." in report
    assert "Ability use vs Leader" in report
    assert report == render_report(view_of(saved))
