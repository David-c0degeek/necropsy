"""New raid captures retain independent arithmetic, readable outputs and packages."""

from __future__ import annotations

import json
from dataclasses import replace
from html import unescape
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
        cell = cells[receipt.cell_id]
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
    actual = (
        ([boss["subject"]] if boss["subject"] else [])
        + (
            [boss["playbook"]["excluded_subject"]]
            if boss["playbook"].get("excluded_subject")
            else []
        )
        + boss["overall_cohort"]
    )
    for case in expected:
        entry = next(
            e
            for e in actual
            if (e["report_code"], e["fight_id"], e["player"])
            == (case["report"], case["fight"], case["player"])
        )
        assert entry["kill_duration_s"] * 1000 == pytest.approx(case["expected"]["duration_ms"])
        if entry.get("combat") or entry.get("druid"):
            combat = entry.get("combat") or entry["druid"]
            for metric in ("damage", "effective_healing", "incoming_damage"):
                field = "raw_source_healing" if metric == "effective_healing" else metric
                assert combat["metrics"][field]["value"] == case["expected"]["totals"][metric]
            if fixture["label"] == "bwl-combined-guardian":
                boss_healing = {"Trashhealz": 125000, "Obviously": 75000, "Belkala": 460963}
                hostile = boss_healing.get(entry["player"], 0)
                assert combat["metrics"]["healing_to_bosses"]["value"] == hostile
                assert combat["metrics"]["effective_healing"]["value"] == (
                    case["expected"]["totals"]["effective_healing"] - hostile
                )
        else:
            # Ranking reconciliation is a separate gate; an unvalidated raid
            # cannot turn these raw amounts into claimed ranked damage.
            assert entry["ranking"]["ranked"]["value"] is None
            assert entry["ranking"]["ranked_dps_evidence"]["value"] is not None
    assert (out / "report.html").is_file() and (out / "playbook.html").is_file()
    assert (out / package_name(doc)).is_file()
    context = boss["playbook"]["duty_context"]
    assert context["player"] == marker["subject"]["name"]
    if fixture["label"] == "mc-protection":
        # Separately enumerated target pages: only NPC 12118's melee, excluding
        # the Protector and every outgoing cast. See the provenance receipt.
        counts = {"Maasumi": 9, "Doljin": 15, "Pale": 7, "Frozion": 15, "Panzèrzug": 8, "Cailo": 19}
        assert context["melee_events"]["value"] == counts[context["player"]]
        assert boss["subject"] is None and boss["playbook"]["comparisons"] == []
        for entry in actual:
            assert entry["combat"]["role"]["value"] is None
            assert "boss melee pressure" in entry["combat"]["role"]["note"]
            assert entry["combat"]["assignment"]["value"] is None
    strategy = boss["playbook"]["encounter_strategy"]
    assert {item["section"] for item in strategy["items"]} == {"before", "during", "raid"}
    for page in ("report.html", "playbook.html"):
        html = unescape((out / page).read_text(encoding="utf-8"))
        for item in strategy["items"]:
            assert item["text"] in html and item["source"] in html
            assert item["kind"] == "general-strategy"
            assert item["retrieved"] == "2026-10-17"
        assert strategy["limitation"] in html
        assert "Recorded boss melee events against you:" in html
        assert context["limitation"] in html
        if fixture["label"] == "bwl-combined-guardian":
            assert "Effective healing uses recorded friendly recipients." in html
            for amount, player in (
                (125000, "Trashhealz"),
                (75000, "Obviously"),
                (460963, "Belkala"),
            ):
                assert (
                    f"Recorded healing credited to encounter bosses: {amount} ({player})." in html
                )
