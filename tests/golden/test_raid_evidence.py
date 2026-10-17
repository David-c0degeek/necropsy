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
    if fixture["label"] in ("mc-geddon-holy", "mc-geddon-hunter"):
        (effect,) = boss["playbook"]["encounter_effects"]
        apply, duration = (
            (16.037, 16.240) if fixture["label"] == "mc-geddon-holy" else (21.033, 26.071)
        )
        assert effect["ability_ids"] == [19659]
        assert effect["known_affected_s"]["value"] == pytest.approx(duration - apply)
        assert effect["unknown_state_s"]["value"] == apply
        assert effect["windows"]["value"] == [[0, apply, None], [apply, duration, True]]
        assert effect["transitions"]["value"] == [[apply, "applydebuff", 19659]]
        assert "removals" not in effect
        strategy_rules = {item["rule"] for item in boss["playbook"]["encounter_strategy"]["items"]}
        assert ("geddon-healer-bomb-coverage-v1" in strategy_rules) is (
            fixture["label"] == "mc-geddon-holy"
        )
        assert ("geddon-hunter-pet-recovery-v1" in strategy_rules) is (
            fixture["label"] == "mc-geddon-hunter"
        )
    if fixture["label"] == "mc-gehennas-mage":
        assert marker["subject"]["name"] == "Suffel"
        (curse,) = boss["playbook"]["encounter_effects"]
        assert curse["known_affected_s"]["value"] == pytest.approx(6.051)
        assert curse["unknown_state_s"]["value"] == pytest.approx(9.718)
        assert curse["windows"]["value"] == [
            [0, 9.718, None],
            [9.718, 15.769, True],
            [15.769, 26.050, False],
        ]
        assert curse["transitions"]["value"] == [
            [9.718, "applydebuff", 19716],
            [15.769, "removedebuff", 19716],
        ]
        rules = {item["rule"] for item in boss["playbook"]["encounter_strategy"]["items"]}
        assert "gehennas-assigned-decurse-v1" in rules
        assert "gehennas-healing-recipient-context-v1" not in rules
    if fixture["label"] == "mc-gehennas-holy":
        assert marker["subject"]["name"] == "Almsivi"
        (curse,) = boss["playbook"]["encounter_effects"]
        assert curse["known_affected_s"]["value"] == pytest.approx(4.057)
        assert curse["unknown_state_s"]["value"] == pytest.approx(6.363)
        assert curse["windows"]["value"] == [
            [0, 6.363, None],
            [6.363, 10.420, True],
            [10.420, 24.391, False],
        ]
        assert curse["transitions"]["value"] == [
            [6.363, "applydebuff", 19716],
            [10.420, "removedebuff", 19716],
        ]
        assert "mechanic_removals" not in boss["playbook"]
    if fixture["label"].startswith("mc-garr-"):
        (control,) = boss["playbook"]["control_applications"]
        positive = fixture["label"] == "mc-garr-control-warlock"
        assert control["applications"]["value"] == (1 if positive else 0)
        assert control["observations"]["value"] == ([[4.258, 100, 8, 18647]] if positive else [])
        assert "uptime" in control["limitation"] and "not a failed duty" in control["limitation"]
    if fixture["label"] == "mc-magmadar-holy":
        assert "mechanic_removals" not in boss["playbook"]
        assert "cohort_mechanic_removals" not in boss["playbook"]
        (fear,) = boss["playbook"]["encounter_effects"]
        assert fear["known_affected_s"]["value"] == 7.996
        assert fear["unknown_state_s"]["value"] == 9.307
        assert fear["windows"]["value"] == [
            [0, 9.307, None],
            [9.307, 17.303, True],
            [17.303, 44.090, False],
        ]
        assert fear["transitions"]["value"] == [
            [9.307, "applydebuff", 19408],
            [17.303, "removedebuff", 19408],
        ]
    if fixture["label"] == "mc-magmadar-hunter":
        assert boss["playbook"]["mechanic_removals"][0]["removals"]["value"] == 0
        examples = boss["playbook"]["cohort_mechanic_removals"]
        assert {e["player"]: e["removals"][0]["removals"]["value"] for e in examples} == {
            "Xelown": 1,
            "Fleskhunter": 0,
            "Charies": 1,
            "Clicker": 1,
            "Cartman": 0,
        }
        for example in examples:
            removal = example["removals"][0]
            assert removal["is_buff"] is True
            assert removal["target_game_ids"] == [11982]
            assert removal["removing_ability_ids"] == [19801]
        (fear,) = boss["playbook"]["encounter_effects"]
        assert fear["known_affected_s"]["value"] == 0
        assert fear["unknown_state_s"]["value"] == 34.485
    if fixture["label"] in ("mc-balance-healing", "mc-mage-fire", "mc-holy"):
        # Independent actor-source dispel enumeration, filtering isBuff=false
        # and exact removed mechanic ID. Cast presence is deliberately irrelevant.
        expected_removals = {
            "mc-balance-healing": {"Truudee": (5, 0, 0), "Ragny": (12, 0, 0), "海兰": (1, 0, 0)},
            "mc-mage-fire": {"Benoii": (1, 0, 0), "Darkwizzardo": (1, 0, 0)},
            "mc-holy": {"Bluebeard": (0, 0, 1), "Maoainai": (0, 1, 0)},
        }[fixture["label"]]
        examples = boss["playbook"]["cohort_mechanic_removals"]
        assert len(examples) == 5
        for example in examples:
            expected_counts = expected_removals.get(example["player"], (0, 0, 0))
            assert tuple(r["removals"]["value"] for r in example["removals"]) == expected_counts
        assert all(r["removals"]["value"] == 0 for r in boss["playbook"]["mechanic_removals"])
    if fixture["label"] == "mc-holy":
        # Independent target-only enumeration on the 38.851-second pull.
        # Damage at 22.145 is not an aura transition.
        effects = {e["rule"]: e for e in boss["playbook"]["encounter_effects"]}
        curse = effects["lucifron-curse-exposure-v1"]
        assert curse["known_affected_s"]["value"] == pytest.approx(7.672)
        assert curse["unknown_state_s"]["value"] == pytest.approx(13.760)
        assert curse["windows"]["value"] == [
            [0, 13.760, None],
            [13.760, 21.432, True],
            [21.432, 38.851, False],
        ]
        assert curse["transitions"]["value"] == [
            [13.760, "applydebuff", 19703],
            [21.432, "removedebuff", 19703],
        ]
        doom = effects["lucifron-doom-exposure-v1"]
        assert doom["known_affected_s"]["value"] == pytest.approx(14.059)
        assert doom["unknown_state_s"]["value"] == pytest.approx(12.141)
        assert doom["windows"]["value"] == [
            [0, 12.141, None],
            [12.141, 22.145, True],
            [22.145, 34.796, False],
            [34.796, 38.851, True],
        ]
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
        if fixture["label"] == "mc-geddon-holy":
            assert "Ignite Mana: 0.20s known affected; 16.04s with unknown state." in html
        if fixture["label"] == "mc-geddon-hunter":
            assert "Ignite Mana: 5.04s known affected; 21.03s with unknown state." in html
        if fixture["label"] == "mc-gehennas-mage":
            assert "Gehennas' Curse: 6.05s known affected; 9.72s with unknown state." in html
        if fixture["label"] == "mc-gehennas-holy":
            assert "Gehennas' Curse: 4.06s known affected; 6.36s with unknown state." in html
            assert "your own curse window does not describe every patient" in html
        if fixture["label"].startswith("mc-garr-"):
            count = 1 if fixture["label"] == "mc-garr-control-warlock" else 0
            assert f"Recorded Firesworn Banish applications: {count}." in html
            assert control["limitation"] in html
            if count:
                assert "4.26s · Firesworn Banish applied; target instance 8." in html
        if fixture["label"] == "mc-magmadar-holy":
            assert "Panic: 8.00s known affected; 9.31s with unknown state." in html
            assert "Magmadar Frenzy removals: 0" not in html
        if fixture["label"] == "mc-magmadar-hunter":
            assert "Xelown · Magmadar Frenzy removals: 1 recorded successful effects." in html
            assert "Panic: 0.00s known affected; 34.48s with unknown state." in html
        if fixture["label"] == "mc-balance-healing":
            assert "Ragny · Lucifron's Curse removals: 12 recorded successful effects." in html
        if fixture["label"] == "mc-mage-fire":
            assert "Benoii · Lucifron's Curse removals: 1 recorded successful effects." in html
        if fixture["label"] == "mc-holy":
            assert "Lucifron's Curse: 7.67s known affected; 13.76s with unknown state." in html
            assert "Impending Doom: 14.06s known affected; 12.14s with unknown state." in html
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
