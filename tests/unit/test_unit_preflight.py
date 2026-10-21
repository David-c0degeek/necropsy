"""The unit preflight is a work list: it separates missing from unusable evidence
and generic from class-scoped boss content, and never implies completion."""

from __future__ import annotations

from pathlib import Path

from scripts import check_raid_coverage as coverage
from scripts import unit_preflight as up

REF = {"path": "tests/golden/raids/facts.json", "sha256": "0" * 64, "locator": "x"}
SOURCE = {
    "archive": {"path": "absent.zip", "sha256": "0" * 64, "locator": "x"},
    "entries": {"path": "absent.entries", "sha256": "0" * 64, "locator": "x"},
    "provenance": {"path": "absent.json", "sha256": "0" * 64, "locator": "x"},
    "report": "r",
    "fight": 1,
    "actor": 1,
    "partition": 1,
}


def _register(*records: dict[str, object]) -> coverage.Register:
    return coverage.Register.model_validate({"version": 1, "records": list(records)})


def test_a_unit_lists_every_boss_of_its_raid_for_one_configuration() -> None:
    cells = up.unit_cells("mc", 6, "Holy", "hps", "Alliance")
    assert len(cells) == 10
    assert {c.configuration.faction for c in cells} == {"Alliance"}
    assert up.unit_cells("mc", 6, "Holy", "hps", "Nowhere") == []


def test_missing_referenced_unusable_and_class_scoped_outcomes(tmp_path: Path) -> None:
    register = _register(
        {
            "cell_id": "mc/50663/6/Holy/hps/Alliance",
            "status": "IN_PROGRESS",
            "references": {"independent_facts": [REF]},
        },
        {
            "cell_id": "mc/50664/6/Holy/hps/Alliance",
            "status": "IN_PROGRESS",
            "real_actor_source": SOURCE,
        },
    )
    report = up.preflight("mc", 6, "Holy", "hps", "Alliance", register, root=tmp_path)
    cells = {c["cell"]: c for c in report["cells"]}
    lucifron = cells["mc/50663/6/Holy/hps/Alliance"]
    assert lucifron["real_actor_source"] == "missing"
    assert lucifron["dimensions"]["independent_facts"] == "referenced"
    assert lucifron["dimensions"]["render_review"] == "missing"
    assert lucifron["class_scoped_rules"]["strategy_items"] > 0
    magmadar = cells["mc/50664/6/Holy/hps/Alliance"]
    assert magmadar["real_actor_source"].startswith("unusable: ")
    assert set(magmadar["class_scoped_rules"]) == {
        "strategy_items",
        "removal_policies",
        "presence_rules",
    }
    # A class with no boss rules of its own reports zeros, not missing counts.
    (rogue,) = [
        c
        for c in up.unit_cells("mc", 8, "Assassination", "dps", "Alliance")
        if c.encounter_id == 50664
    ]
    assert up.class_scoped(rogue) == {
        "strategy_items": 0,
        "removal_policies": 0,
        "presence_rules": 0,
    }
    unregistered = cells["mc/50672/6/Holy/hps/Alliance"]
    assert unregistered["status"] == "TODO"
    assert set(unregistered["dimensions"].values()) == {"missing"}
    assert report["summary"]["complete"] == 0
    assert "no cell becomes COMPLETE" in report["note"]


def test_an_unknown_unit_exits_2(tmp_path: Path) -> None:
    path = tmp_path / "coverage.json"
    path.write_text('{"version": 1, "records": []}', encoding="utf-8")
    assert up.main(["mc", "6", "Holy", "hps", "Nowhere", "--register", str(path)]) == 2
