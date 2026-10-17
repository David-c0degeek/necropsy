"""New raid captures retain independent arithmetic, readable outputs and packages."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from necropsy.raids.scope import coverage_cells
from necropsy.report.offline import run_offline
from necropsy.report.package import package_name
from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest, sha256_file
from scripts.check_raid_coverage import ActorSource, Register, actor_problems
from scripts.check_raid_facts import check_register

pytestmark = pytest.mark.golden
ROOT = Path(__file__).parent / "raids"


def test_independent_raw_actor_facts() -> None:
    assert check_register(ROOT / "facts.json") == []


def test_real_actor_receipts_reject_wrong_configuration_or_variant() -> None:
    repo = ROOT.parents[2]
    register = Register.model_validate_json((ROOT / "coverage.json").read_text(encoding="utf-8"))
    cells = {c.key: c for c in coverage_cells()}
    assert len(register.records) >= 3
    for receipt in register.records:
        source = receipt.real_actor_source
        assert isinstance(source, ActorSource)
        cell = cells[receipt.key]
        assert actor_problems(repo, cell, source) == []
        wrong_faction = replace(
            cell,
            configuration=replace(cell.configuration, faction="Other faction"),
        )
        assert actor_problems(repo, wrong_faction, source)
        assert actor_problems(repo, cell, source.model_copy(update={"partition": 3}))
        assert actor_problems(repo, replace(cell, encounter_id=1), source)


@pytest.mark.parametrize(
    "fixture",
    json.loads((ROOT / "provenance.json").read_text(encoding="utf-8"))["fixtures"],
    ids=lambda f: f["label"],
)
def test_seed_capture_replays_with_raw_arithmetic_and_correct_raid(
    fixture: dict[str, Any], tmp_path: Path
) -> None:
    archive = ROOT / "raw" / f"{fixture['label']}.zip"
    assert sha256_file(archive) == fixture["sha256"], "Fetch the authorized raid LFS fixtures"
    entries = load_entries_manifest(archive.with_suffix(".entries"))
    out = tmp_path / "report"
    run_offline(archive, out, expected_sha256=fixture["sha256"], entries=entries)
    doc = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    facts = json.loads((ROOT / "facts.json").read_text(encoding="utf-8"))["cases"]
    with VerifiedArchive(archive, entries=entries) as raw:
        marker = raw.read_json("necropsy-snapshot.json")
    assert doc["zone"]["id"] == marker["zone"]["id"]
    assert len(doc["bosses"]) == 1
    boss = doc["bosses"][0]
    expected = [f for f in facts if f["fixture"] == fixture["label"]]
    actual = ([boss["subject"]] if boss["subject"] else []) + boss["overall_cohort"]
    for case in expected:
        entry = next(
            e
            for e in actual
            if (e["report_code"], e["fight_id"], e["player"])
            == (case["report"], case["fight"], case["player"])
        )
        assert entry["kill_duration_s"] * 1000 == pytest.approx(case["expected"]["duration_ms"])
        if entry.get("combat"):
            for metric in ("damage", "effective_healing", "incoming_damage"):
                assert (
                    entry["combat"]["metrics"][metric]["value"]
                    == case["expected"]["totals"][metric]
                )
        else:
            # Ranking reconciliation is a separate gate; an unvalidated raid
            # cannot turn these raw amounts into claimed ranked damage.
            assert entry["ranking"]["ranked"]["value"] is None
            assert entry["ranking"]["ranked_dps_evidence"]["value"] is not None
    assert (out / "report.html").is_file() and (out / "playbook.html").is_file()
    assert (out / package_name(doc)).is_file()
