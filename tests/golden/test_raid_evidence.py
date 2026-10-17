"""New raid captures retain independent arithmetic, readable outputs and packages."""

from __future__ import annotations

import json
from dataclasses import replace
from html import unescape
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.raids.scope import coverage_cells
from necropsy.report.offline import run_offline
from necropsy.report.package import package_name
from necropsy.report.render.class_view import bosses as class_bosses
from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest, sha256_file
from necropsy.snapshot.model import ActorRole, StreamStatus
from necropsy.snapshot.v1 import open_snapshot
from scripts.check_raid_coverage import ActorSource, Register, actor_problems
from scripts.check_raid_facts import check_register

pytestmark = pytest.mark.golden
ROOT = Path(__file__).parent / "raids"


def test_independent_raw_actor_facts() -> None:
    assert check_register(ROOT / "facts.json") == []


def test_independent_recipient_healing_and_absorption_facts() -> None:
    assert check_register(ROOT / "healing-facts.json") == []


def test_independent_npc_control_facts() -> None:
    assert check_register(ROOT / "control-facts.json") == []


def test_independent_actor_effect_facts() -> None:
    assert check_register(ROOT / "effect-facts.json") == []


def test_independent_npc_aura_facts() -> None:
    assert check_register(ROOT / "aura-facts.json") == []


def test_independent_owned_pet_facts() -> None:
    assert check_register(ROOT / "pet-facts.json") == []


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
    archive = ROOT / fixture.get("archive", f"raw/{fixture['label']}.zip")
    assert archive.resolve().is_relative_to(ROOT.resolve())
    assert sha256_file(archive) == fixture["sha256"], "Fetch the authorized raid LFS fixtures"
    assert archive.with_suffix(".sha256").read_text(encoding="utf-8").strip() == (
        f"{fixture['sha256']}  {archive.name}"
    )
    entries = load_entries_manifest(archive.with_suffix(".entries"))
    out = tmp_path / "report"
    db = tmp_path / "analysis.duckdb"
    run_offline(archive, out, db=db, expected_sha256=fixture["sha256"], entries=entries)
    doc = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    facts = json.loads((ROOT / "facts.json").read_text(encoding="utf-8"))["cases"]
    healing_facts = json.loads((ROOT / "healing-facts.json").read_text(encoding="utf-8"))["cases"]
    with VerifiedArchive(archive, entries=entries) as raw:
        marker = raw.read_json("necropsy-snapshot.json")
        if fixture.get("missing_pet_listings"):
            reader = open_snapshot(raw)
            assert reader.issues() == []
            streams = reader.expected_streams()
            players = [s for s in streams if s.role is ActorRole.PLAYER]
            pets = [s for s in streams if s.role is ActorRole.PET]
            unresolved = [s for s in streams if s.role is ActorRole.PET_DISCOVERY]
            scopes = [s for s in streams if s.role in {ActorRole.ENCOUNTER, ActorRole.CRITICAL}]
            assert len(players) == fixture["complete_player_streams"]
            assert len(pets) == fixture.get("complete_pet_streams", 0)
            assert len(unresolved) == fixture["missing_pet_listings"]
            assert len(scopes) == fixture.get("complete_encounter_scopes", 0)
            assert len(streams) == len(players) + len(pets) + len(scopes) + len(unresolved)
            assert all(reader.read_stream(s).status is StreamStatus.COMPLETE for s in players)
            assert all(reader.read_stream(s).status is StreamStatus.COMPLETE for s in pets)
            assert all(reader.read_stream(s).status is StreamStatus.COMPLETE for s in scopes)
            assert all(reader.read_stream(s).status is StreamStatus.MISSING for s in unresolved)
            expected_missing = fixture.get(
                "missing_pet_fights", [("BjygkHzvbZN3D6JX", 27), ("TnL9YBfXWp7RvJQK", 6)]
            )
            assert {(s.report_code, s.fight_id) for s in unresolved} == {
                tuple(pair) for pair in expected_missing
            }
    assert doc["zone"]["id"] == marker["zone"]["id"]
    if fixture.get("encounter_context"):
        assert doc["snapshot"]["format"] == "necropsy-live-snapshot-v2"
        assert len(marker["encounter_streams"]) == 2 * len(marker["fights"])
        assert all(
            p["actor_id"] is None and p["direction"] == "all" for p in marker["encounter_streams"]
        )
        assert {p["role"] for p in marker["encounter_streams"]} == {"encounter", "critical"}
    selected = [f for f in facts if f["fixture"] == fixture["label"]]
    assert len(selected) == fixture["sources"]
    assert sum(len(f["participants"]) for f in marker["fights"]) == len(selected)
    # Every class, including Hunter, must preserve raw owned arithmetic through
    # scope merging. These sums are never used as unvalidated ranked totals.
    with duckdb.connect(str(db), read_only=True) as con:
        for case in selected:
            report, fight, actor = case["report"], case["fight"], case["actor"]
            for metric, kind, owner in (
                ("damage", "damage", "source_id"),
                ("effective_healing", "heal", "source_id"),
                ("absorbed_amount", "absorbed", "source_id"),
                ("incoming_damage", "damage", "target_id"),
            ):
                row = con.execute(
                    f"SELECT coalesce(sum(amount),0) FROM events "
                    f"WHERE report_code=? AND fight_id=? AND {owner}=? AND type=?",
                    [report, fight, actor, kind],
                ).fetchone()
                assert row and row[0] == case["expected"]["totals"][metric], case["id"]
    expected_encounters = set(fixture.get("encounters", [selected[0]["expected"]["encounter_id"]]))
    assert {b["encounter_id"] for b in doc["bosses"]} == expected_encounters
    if fixture.get("cohort_counts"):
        assert {str(b["encounter_id"]): len(b["overall_cohort"]) for b in doc["bosses"]} == fixture[
            "cohort_counts"
        ]
    for boss in doc["bosses"]:
        expected = [f for f in selected if f["expected"]["encounter_id"] == boss["encounter_id"]]
        assert expected
        _assert_boss_replay(fixture, marker, doc, boss, expected, healing_facts, out)
    observations_fixture = fixture.get("observations_fixture", fixture["label"])
    _assert_actor_effect_windows(doc, observations_fixture)
    _assert_npc_aura_windows(doc, {observations_fixture, fixture["label"]})
    _assert_owned_pets(doc, fixture["label"], db)


def _assert_actor_effect_windows(doc: dict[str, Any], fixture: str) -> None:
    cases = json.loads((ROOT / "effect-facts.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        if case["fixture"] != fixture:
            continue
        boss = next(b for b in doc["bosses"] if b["encounter_id"] == case["encounter_id"])
        subject = boss["subject"] or boss["playbook"].get("excluded_subject")
        if subject and (subject["report_code"], subject["fight_id"]) == (
            case["report"],
            case["fight"],
        ):
            effects = boss["playbook"]["encounter_effects"]
        else:
            example = next(
                e
                for e in boss["playbook"]["cohort_encounter_effects"]
                if (e["report_code"], e["fight_id"], e["player"])
                == (case["report"], case["fight"], case["player"])
            )
            effects = example["effects"]
        for expected in case["window_expectations"]:
            effect = next(e for e in effects if e["ability_ids"] == [expected["spell"]])
            assert effect["windows"]["value"] == [
                [lo / 1000, hi / 1000, state] for lo, hi, state in expected["windows"]
            ]
            assert effect["known_affected_s"]["value"] == pytest.approx(
                expected["known_affected_ms"] / 1000
            )
            assert effect["unknown_state_s"]["value"] == pytest.approx(
                expected["unknown_state_ms"] / 1000
            )


def _assert_npc_aura_windows(doc: dict[str, Any], fixtures: set[str]) -> None:
    cases = json.loads((ROOT / "aura-facts.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        if case["fixture"] not in fixtures:
            continue
        boss = next(b for b in doc["bosses"] if b["encounter_id"] == case["encounter_id"])
        subject = boss["subject"] or boss["playbook"].get("excluded_subject")
        if subject and (subject["report_code"], subject["fight_id"]) == (
            case["report"],
            case["fight"],
        ):
            auras = boss["playbook"]["target_aura_windows"]
        else:
            example = next(
                e
                for e in boss["playbook"]["cohort_target_aura_windows"]
                if (e["report_code"], e["fight_id"]) == (case["report"], case["fight"])
            )
            auras = example["auras"]
        for ability in case["ability_ids"]:
            aura = next(a for a in auras if a["ability_id"] == ability)
            observed = [o for o in case["expected"]["observations"] if o["spell"] == ability]
            assert aura["applications"]["value"] == sum(o["kind"] == "applybuff" for o in observed)
            expected_targets = {
                (w["actor"], w["instance"])
                for w in case["window_expectations"]
                if w["spell"] == ability
            }
            assert {(t["actor_id"], t["instance"]) for t in aura["targets"]} == expected_targets
        for expected in case["window_expectations"]:
            aura = next(a for a in auras if a["ability_id"] == expected["spell"])
            target = next(
                t
                for t in aura["targets"]
                if (t["actor_id"], t["instance"]) == (expected["actor"], expected["instance"])
            )
            assert target["game_id"] in case["target_game_ids"]
            if expected["windows"] is None:
                assert target["windows"]["value"] is None
                assert target["known_active_s"]["value"] is None
                assert target["unknown_state_s"]["value"] is None
                assert "fights" in {ref["source"] for ref in target["windows"]["refs"]}
                continue
            assert target["windows"]["value"] == [
                [lo / 1000, hi / 1000, state] for lo, hi, state in expected["windows"]
            ]
            assert target["known_active_s"]["value"] == pytest.approx(
                expected["known_active"] / 1000
            )
            assert target["unknown_state_s"]["value"] == pytest.approx(
                expected["unknown_state"] / 1000
            )


def _assert_owned_pets(doc: dict[str, Any], fixture: str, db: Path) -> None:
    cases = json.loads((ROOT / "pet-facts.json").read_text(encoding="utf-8"))["cases"]
    entries = [
        e
        for boss in doc["bosses"]
        for e in [
            boss["subject"],
            boss["playbook"].get("excluded_subject"),
            *boss["overall_cohort"],
        ]
        if e is not None
    ]
    with duckdb.connect(str(db), read_only=True) as con:
        for case in cases:
            if case["fixture"] != fixture:
                continue
            entry = next(
                e
                for e in entries
                if (e["report_code"], e["fight_id"], e["player"])
                == (case["report"], case["fight"], case["player"])
            )
            expected = case["expected"]
            owner = case["actor"]
            ids = {p["actor"] for p in expected["pets"]}
            coverage = con.execute(
                "SELECT DISTINCT actor_id,owner_actor_id,direction,status FROM stream_coverage "
                "WHERE report_code=? AND fight_id=? AND role='pet' AND owner_actor_id=?",
                [case["report"], case["fight"], owner],
            ).fetchall()
            assert set(coverage) == {
                (actor, owner, direction, "complete")
                for actor in ids
                for direction in ("source", "target")
            }
            assert {p["actor_id"] for p in entry["hunter"]["pets"]} == ids
            assert entry["pets_listed"] is expected["listing_complete"]
            for pet in expected["pets"]:
                for field, kind, emitter in (
                    ("damage", "damage", "source_id"),
                    ("incoming_damage", "damage", "target_id"),
                    ("effective_healing", "heal", "source_id"),
                    ("absorbed_amount", "absorbed", "source_id"),
                ):
                    actual = con.execute(
                        f"SELECT coalesce(sum(amount),0) FROM events WHERE report_code=? "
                        f"AND fight_id=? AND {emitter}=? AND type=?",
                        [case["report"], case["fight"], pet["actor"], kind],
                    ).fetchone()
                    assert actual and actual[0] == pet["totals"][field], (case["id"], field)
                trained = next(
                    (p for p in entry["hunter"]["hunter_pets"] if p["actor_id"] == pet["actor"]),
                    None,
                )
                if pet["catalog"].get("gameID") == 15901:
                    # The owned item summon is not the owner's trained Hunter pet.
                    other = next(
                        p for p in entry["hunter"]["pets"] if p["actor_id"] == pet["actor"]
                    )
                    assert other["category"]["value"] == "other"
                    assert trained is None
                if trained is not None:
                    assert trained["damage"]["value"] == pet["totals"]["damage"]
                    assert [
                        d["t_s"] * 1000 for d in trained["deaths"]["deaths"]["value"]
                    ] == pytest.approx(pet["deaths_ms"])
                    bounds = pet["damage_bounds_ms"]
                    activity = trained["activity"]["value"]
                    assert activity["first_damage_s"] == (
                        None if bounds is None else bounds[0] / 1000
                    )
                    assert activity["last_damage_before_end_s"] == (
                        None if bounds is None else (expected["duration_ms"] - bounds[1]) / 1000
                    )
            if not ids and expected["listing_complete"]:
                assert entry["hunter"]["hunter_pets"] == []
                assert entry["hunter"]["total_pet_dps"]["value"] == 0
            if any(p["game_id"] == 8836 for p in expected["unattributed_friendly_pets"]):
                assert entry["hunter"]["pet_roster_complete"] is True
                assert entry["ranking"]["ranked"]["value"] is None
            if case["id"] in {"aq40-expanded-owned-pets-10", "aq40-expanded-owned-pets-12"}:
                # Raw Claw/Dash casts identify this Cat; the separate item summon
                # must not inflate its trained-pet rate, even beside an unowned Chicken.
                cat = next(p for p in expected["pets"] if p["catalog"]["gameID"] == 13379216)
                assert {p["actor_id"] for p in entry["hunter"]["hunter_pets"]} == {cat["actor"]}
                assert entry["hunter"]["total_pet_dps"]["value"] == pytest.approx(
                    cat["totals"]["damage"] * 1000 / expected["duration_ms"], rel=0, abs=1e-6
                )
            if case["id"] == "aq40-owned-pets-1":
                # Only a melee event was observed before this owned unit died.
                # Ownership alone cannot turn it into a classified trained pet.
                assert entry["hunter"]["pets"][0]["category"]["value"] is None
                assert entry["hunter"]["total_pet_dps"]["value"] is None
            if case["id"] == "aq40-owned-pets-8":
                assert case["encounter_id"] == 50715
                assert ids == {17} and entry["hunter"]["pet_roster_complete"] is True
                assert all(
                    p["actor"] == 159 and p["fight_owner"] is None
                    for p in expected["unattributed_friendly_pets"]
                )
                assert entry["ranking"]["ranked"]["value"] is None


def _assert_boss_replay(
    fixture: dict[str, Any],
    marker: dict[str, Any],
    doc: dict[str, Any],
    boss: dict[str, Any],
    expected: list[dict[str, Any]],
    healing_facts: list[dict[str, Any]],
    out: Path,
) -> None:
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
            assert (
                combat["metrics"]["raw_source_absorption"]["value"]
                == case["expected"]["totals"]["absorbed_amount"]
            )
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
            recipient_facts = next(
                (f for f in healing_facts if f["actor_case"] == case["id"]), None
            )
            if recipient_facts is not None:
                independent = recipient_facts["expected"]
                for raw_key, metric in (
                    ("friendly_healing", "effective_healing"),
                    ("boss_healing", "healing_to_bosses"),
                    ("unclassified_healing", "unclassified_healing"),
                    ("raw_healing", "raw_source_healing"),
                    ("friendly_absorption", "effective_absorption"),
                    ("boss_absorption", "absorption_to_bosses"),
                    ("unclassified_absorption", "unclassified_absorption"),
                    ("raw_absorption", "raw_source_absorption"),
                    ("friendly_healing_and_absorption", "healing_and_absorption"),
                ):
                    assert combat["metrics"][metric]["value"] == independent[raw_key]
                combined = independent["friendly_healing_and_absorption"]
                if combined is not None:
                    assert combat["metrics"]["healing_and_absorption_per_second"][
                        "value"
                    ] == pytest.approx(combined * 1000 / independent["duration_ms"])
        else:
            # Ranking reconciliation is a separate gate; an unvalidated raid
            # cannot turn these raw amounts into claimed ranked damage.
            assert entry["ranking"]["ranked"]["value"] is None
            assert entry["ranking"]["ranked_dps_evidence"]["value"] is not None
    assert (out / "report.html").is_file() and (out / "playbook.html").is_file()
    assert (out / package_name(doc)).is_file()
    context = boss["playbook"].get("duty_context")
    if boss["encounter_id"] in fixture.get("missing_subject_encounters", []):
        assert boss["subject"] is None
        assert boss["playbook"].get("excluded_subject") is None
        assert boss["playbook"].get("duty_context") is None
        personal_context = dict(
            class_bosses(doc, "missing-personal", "combat")[boss["encounter_id"]]["context"]
        )
        assert personal_context["Build"] == personal_context["Encounter duty"] == "Unknown"
    else:
        assert context is not None
        assert context["player"] == marker["subject"]["name"]
    if fixture["label"] == "mc-golemagg-context-fury":
        (magma,) = boss["playbook"]["encounter_effects"]
        assert magma["ability_ids"] == [13880]
        assert magma["known_affected_s"]["value"] == 25.239
        assert magma["unknown_state_s"]["value"] == 14.094
        assert magma["windows"]["value"] == [
            [0, 14.094, None],
            [14.094, 26.789, True],
            [26.789, 31.359, True],
            [31.359, 38.668, True],
            [38.668, 39.333, True],
        ]
    if fixture["label"] == "mc-majordomo-context-frost-control":
        assert len(marker["fights"]) == 5
        assert len(marker["encounter_streams"]) == 10
        # Six participants include two Mages in the same fight. Normalization
        # merges their shared scopes, keeping each actor's distinct arithmetic.
        assert len(actual) == 6
    if fixture["label"] == "mc-majordomo-context-holy":
        reflection, shield = boss["playbook"]["target_aura_windows"]
        assert reflection["applications"]["value"] == 1
        assert shield["applications"]["value"] == 0
        (target,) = reflection["targets"]
        assert (target["actor_id"], target["instance"], target["game_id"]) == (80, 3, 11664)
        assert target["windows"]["value"] == [
            [0, 29.036, None],
            [29.036, 34.5, True],
            [34.5, 34.518, False],
            [34.518, 35.927, None],
        ]
        assert target["known_active_s"]["value"] == 5.464
        assert target["unknown_state_s"]["value"] == 30.445
        # Independent raw review: one actor represents four Elite instances;
        # their same-time application has different actual removal boundaries.
        example = next(
            e
            for e in boss["playbook"]["cohort_target_aura_windows"]
            if e["report_code"] == "JqLRy1GvDjMkPYp2"
        )
        buff = example["auras"][0]
        assert buff["applications"]["value"] == 5
        elites = {t["instance"]: t for t in buff["targets"] if t["actor_id"] == 78}
        assert {i: t["known_active_s"]["value"] for i, t in elites.items()} == {
            1: 6.348,
            2: 8.439,
            3: 9.973,
            4: 2.637,
        }
    if fixture["label"] in ("mc-sulfuron-holy", "mc-sulfuron-rogue"):
        assert boss["encounter_id"] == 50669
        assert "mechanic_removals" not in boss["playbook"]
        assert "control_applications" not in boss["playbook"]
        rules = {item["rule"] for item in boss["playbook"]["encounter_strategy"]["items"]}
        assert ("sulfuron-assigned-interrupts-v1" in rules) is (
            fixture["label"] == "mc-sulfuron-rogue"
        )
        assert ("sulfuron-friendly-magic-removal-v1" in rules) is (
            fixture["label"] == "mc-sulfuron-holy"
        )
    if fixture["label"] in ("mc-shazzrah-holy", "mc-shazzrah-hunter"):
        (effect,) = boss["playbook"]["encounter_effects"]
        apply, duration = (
            (6.500, 22.094) if fixture["label"] == "mc-shazzrah-holy" else (9.683, 12.942)
        )
        assert effect["ability_ids"] == [19713]
        assert effect["windows"]["value"] == [[0, apply, None], [apply, duration, True]]
        assert effect["known_affected_s"]["value"] == pytest.approx(duration - apply)
        assert effect["unknown_state_s"]["value"] == apply
        assert effect["transitions"]["value"] == [[apply, "applydebuff", 19713]]
        assert "mechanic_removals" not in boss["playbook"]
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
    if fixture["label"] == "mc-garr-context-warlock":
        contexts = json.loads((ROOT / "control-facts.json").read_text(encoding="utf-8"))["cases"]
        for case in contexts:
            subject = boss["subject"] or boss["playbook"].get("excluded_subject")
            if subject and (subject["report_code"], subject["fight_id"]) == (
                case["report"],
                case["fight"],
            ):
                auras = boss["playbook"]["target_aura_windows"]
            else:
                example = next(
                    e
                    for e in boss["playbook"]["cohort_target_aura_windows"]
                    if (e["report_code"], e["fight_id"]) == (case["report"], case["fight"])
                )
                auras = example["auras"]
            by_spell = {a["ability_id"]: a for a in auras}
            for spell in case["ability_ids"]:
                aura = by_spell[spell]
                raw = [e for e in case["expected"]["observations"] if e["spell"] == spell]
                assert all(
                    e["caster"]["type"] == "Player"
                    and e["caster"]["subType"] == "Warlock"
                    and e["target"]["gameID"] == 12099
                    for e in raw
                )
                assert aura["applications"]["value"] == sum(e["kind"] == "applydebuff" for e in raw)
                manual = [w for w in case["window_expectations"] if w["spell"] == spell]
                assert {(t["actor_id"], t["instance"]) for t in aura["targets"]} == {
                    (w["actor"], w["instance"]) for w in manual
                }
                for window in manual:
                    target = next(
                        t
                        for t in aura["targets"]
                        if (t["actor_id"], t["instance"]) == (window["actor"], window["instance"])
                    )
                    assert target["windows"]["value"] == [
                        [lo / 1000, hi / 1000, state] for lo, hi, state in window["windows"]
                    ]
                    assert target["known_active_s"]["value"] == pytest.approx(
                        window["known_active"] / 1000
                    )
                    assert target["unknown_state_s"]["value"] == pytest.approx(
                        window["unknown_state"] / 1000
                    )
                    assert target["windows"]["coverage"][0]["actor"] is None
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
        if context is not None:
            assert context["limitation"] in html
        if fixture["label"] == "mc-majordomo-context-holy":
            assert "Magic Reflection: 1 recorded applications." in html
            assert "Flamewaker Elite · instance 3: 5.46s known active; 30.45s" in html
            assert reflection["limitation"] in html
            assert "Almsivi: 53104 friendly healing; 8010 credited absorption; 1701.06/s" in html
        if fixture["label"] == "mc-golemagg-context-holy":
            assert "Almsivi: 48145 friendly healing; 688 credited absorption; 1050.85/s" in html
        if fixture["label"] == "mc-golemagg-context-fury":
            assert "Magma Splash: 25.24s known affected; 14.09s with unknown state." in html
        if fixture["label"] == "mc-shazzrah-holy":
            assert "Shazzrah's Curse: 15.59s known affected; 6.50s with unknown state." in html
        if fixture["label"] == "mc-shazzrah-hunter":
            assert "Shazzrah's Curse: 3.26s known affected; 9.68s with unknown state." in html
        if fixture["label"] == "mc-geddon-holy":
            assert "Ignite Mana: 0.20s known affected; 16.04s with unknown state." in html
        if fixture["label"] == "mc-geddon-hunter":
            assert "Ignite Mana: 5.04s known affected; 21.03s with unknown state." in html
        if fixture["label"] == "mc-gehennas-mage":
            assert "Gehennas' Curse: 6.05s known affected; 9.72s with unknown state." in html
        if fixture["label"] == "mc-gehennas-holy":
            assert "Gehennas' Curse: 4.06s known affected; 6.36s with unknown state." in html
            assert "your own curse window does not describe every patient" in html
        if fixture["label"] == "mc-garr-context-warlock":
            assert "Encounter-wide Firesworn Banish (Rank 1): 0 recorded applications." in html
            assert "Firesworn instance 2: 27.29s known active." in html
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
