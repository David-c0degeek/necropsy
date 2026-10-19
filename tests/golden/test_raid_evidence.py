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


def test_independent_summon_observations() -> None:
    assert check_register(ROOT / "summon-facts.json") == []


def test_independent_owned_mechanic_removals() -> None:
    assert check_register(ROOT / "removal-facts.json") == []


def test_independent_raid_interrupt_observations() -> None:
    assert check_register(ROOT / "interrupt-facts.json") == []


def test_independent_absorption_ability_facts() -> None:
    assert check_register(ROOT / "absorption-ability-facts.json") == []


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
    _assert_cohort_exclusions(doc, fixture)
    observations_fixture = fixture.get("observations_fixture", fixture["label"])
    _assert_actor_effect_windows(doc, observations_fixture)
    _assert_npc_aura_windows(doc, {observations_fixture, fixture["label"]})
    _assert_owned_pets(doc, fixture["label"], db)
    _assert_summon_bounds(doc, observations_fixture, out)
    _assert_mechanic_removals(doc, observations_fixture, out)
    _assert_raid_interrupts(doc, fixture["label"], out)
    _assert_absorption_abilities(doc, fixture["label"], out)


# Independent duty boundary for the final Shadow capture; the runtime must keep
# every case it lists out of the eligible comparison cohort.
DUTY_BOUNDARIES = {"mc-shadow-priest-raid-context": ROOT / "shadow-priest-duty-boundary.json"}


def _assert_cohort_exclusions(doc: dict[str, Any], fixture: dict[str, Any]) -> None:
    excluded = fixture.get("excluded_cohort_sources", [])
    if "eligible_cohort_counts" in fixture:
        assert {str(b["encounter_id"]): len(b["cohort"]) for b in doc["bosses"]} == fixture[
            "eligible_cohort_counts"
        ]
    if fixture["label"] in DUTY_BOUNDARIES:
        boundary = json.loads(DUTY_BOUNDARIES[fixture["label"]].read_text(encoding="utf-8"))
        assert boundary["archive_sha256"] == fixture["sha256"]
        cases = boundary["holy_nova_heavy"] + boundary["class_identity_conflicts"]
        key = ("report", "fight", "actor", "player", "kind")
        assert sorted(tuple(c[k] for k in key) for c in cases) == sorted(
            tuple(c[k] for k in key) for c in excluded
        )
    for case in excluded:
        where = (case["report"], case["fight"], case["player"])
        retained = [
            entry
            for boss in doc["bosses"]
            for entry in boss["overall_cohort"]
            if (entry["report_code"], entry["fight_id"], entry["player"]) == where
        ]
        # Retained as context with unresolved duty, never an eligible comparison.
        assert len(retained) == 1, case
        assert retained[0]["combat"]["role"]["value"] is None, case
        assert not any(
            (entry["report_code"], entry["fight_id"], entry["player"]) == where
            for boss in doc["bosses"]
            for entry in boss["cohort"]
        ), case


def _assert_absorption_abilities(doc: dict[str, Any], fixture: str, out: Path) -> None:
    cases = json.loads((ROOT / "absorption-ability-facts.json").read_text(encoding="utf-8"))[
        "cases"
    ]
    cases = [case for case in cases if case["fixture"] == fixture]
    if not cases:
        return
    rows = [
        example
        for boss in doc["bosses"]
        for example in boss["playbook"]["healing_context"]["absorption_examples"]
    ]
    examples = {
        (example["report_code"], example["fight_id"], example["actor_id"]): example
        for example in rows
    }
    assert len(examples) == len(rows) == len(cases)
    for case in cases:
        example = examples[(case["report"], case["fight"], case["actor"])]["breakdown"]
        expected = case["expected"]
        assert example["absorption"]["value"] == expected["friendly_absorption"]
        if not expected["ability_absorption"]:
            assert example["review"] is None
        assert [a["ability_id"] for a in example["abilities"]] == [
            a["ability_id"] for a in expected["ability_absorption"]
        ]
        for actual, ability in zip(
            example["abilities"], expected["ability_absorption"], strict=True
        ):
            assert actual["absorption"]["value"] == ability["amount"]
            assert actual["effects"]["value"] == ability["events"]
            assert sorted(actual["observations"]["value"]) == sorted(
                [e["ms"], e["target"], e["amount"]] for e in ability["observations"]
            )
            assert [
                (r["actor_id"], r["absorption"]["value"], r["effects"]["value"])
                for r in actual["recipients"]
            ] == [(r["actor_id"], r["amount"], r["events"]) for r in ability["recipients"]]
    for name in ("report.html", "playbook.html"):
        html = unescape((out / name).read_text(encoding="utf-8"))
        assert "Power Word: Shield (10901): 2406 credited absorption; 4 absorption effects" in html
        assert "Persistent Shield (26470): 4845 credited absorption; 17 absorption effects" in html
        assert "Agree shield priorities with your tanks and healers" in html


def _assert_raid_interrupts(doc: dict[str, Any], fixture: str, out: Path) -> None:
    cases = [
        c
        for c in json.loads((ROOT / "interrupt-facts.json").read_bytes())["cases"]
        if c["fixture"] == fixture
    ]
    for case in cases:
        boss = next(b for b in doc["bosses"] if b["encounter_id"] == 50669)
        contexts = boss["playbook"]["raid_interrupt_contexts"]
        assert len({(c["report_code"], c["fight_id"]) for c in contexts}) == len(contexts)
        [context] = [
            c
            for c in contexts
            if (c["report_code"], c["fight_id"]) == (case["report"], case["fight"])
        ]
        expected = case["expected"]["qualified_interrupts"]
        assert context["interrupts"]["value"] == len(expected)
        assert context["scope"] == "friendly-raid-roster"
        assert context["interrupts"]["coverage"] == [
            {
                "report": case["report"],
                "fight": case["fight"],
                "actor": None,
                "direction": "all",
                "trusted": True,
                "role": "encounter",
            }
        ]
        assert [e["value"] for e in context["observations"]] == [
            dict(
                source_actor_id=e["source"],
                source_name=e["source_name"],
                source_class="Shaman",
                target_actor_id=e["target"],
                target_game_id=11662,
                target_instance=e["target_instance"],
                elapsed_ms=e["ms"],
                interrupt_ability_id=e["ability"],
                stopped_ability_id=19775,
            )
            for e in expected
        ]
        for name in ("report.html", "playbook.html"):
            html = unescape((out / name).read_text(encoding="utf-8"))
            assert "not credited to the selected player or ranking category" in html
            assert all(f"{e['source_name']} (raid Shaman {e['source']})" in html for e in expected)


def _assert_mechanic_removals(doc: dict[str, Any], fixture: str, out: Path) -> None:
    cases = json.loads((ROOT / "removal-facts.json").read_bytes())["cases"]
    for case in cases:
        if case["fixture"] != fixture:
            continue
        boss = next(b for b in doc["bosses"] if b["encounter_id"] == case["encounter_id"])
        subject = boss["subject"]
        personal = subject and (subject["report_code"], subject["fight_id"], subject["player"]) == (
            case["report"],
            case["fight"],
            case["player"],
        )
        if personal:
            removals = boss["playbook"]["mechanic_removals"]
        else:
            example = next(
                e
                for e in boss["playbook"]["cohort_mechanic_removals"]
                if (e["report_code"], e["fight_id"], e["player"])
                == (case["report"], case["fight"], case["player"])
            )
            removals = example["removals"]
        [removal] = [r for r in removals if r["removed_ability_ids"] == case["removed_ability_ids"]]
        expected = case["expected"]["owned_removals"]
        assert removal["removals"]["value"] == len(expected)
        assert removal["observations"]["value"] == [
            [e["ms"] / 1000, e["target"], e["ability"], e["removed"]] for e in expected
        ]
        assert {(c["actor"], c["direction"]) for c in removal["removals"]["coverage"]} == {
            (case["actor"], "source"),
            (None, "all"),
        }
        assert all(c["trusted"] for c in removal["removals"]["coverage"])
        assert (
            next(c for c in removal["removals"]["coverage"] if c["actor"] is None)["role"]
            == "encounter"
        )
        if personal or expected:
            for page in ("report.html", "playbook.html"):
                html = unescape((out / page).read_text(encoding="utf-8"))
                prefix = "" if personal else f"{case['player']} · "
                assert (
                    f"{prefix}{removal['label']}: {len(expected)} "
                    "recorded successful effects." in html
                )
                assert "Missing opportunity evidence cannot support a utility score." in html
        if case["encounter_id"] == 50668:
            if personal:
                paired = boss["playbook"].get("exposure_removal_correlations", [])
            else:
                paired = next(
                    (
                        e["correlations"]
                        for e in boss["playbook"].get("cohort_exposure_removal_correlations", [])
                        if (e["report_code"], e["fight_id"], e["player"])
                        == (case["report"], case["fight"], case["player"])
                    ),
                    [],
                )
            expected_pair = {
                ("mc-holy-raid-context", "Inkia"): [7667, 9275, 1608, 988],
                ("mc-holy-paladin-raid-context", "Anrylla"): [7262, 10144, 2882, 4987],
            }.get((fixture, case["player"]))
            if expected_pair is not None:
                assert len(paired) == 1
                assert paired[0]["intervals_ms"]["value"] == [expected_pair]
                for page in ("report.html", "playbook.html"):
                    html = unescape((out / page).read_text(encoding="utf-8"))
                    start, end, elapsed, _ability = expected_pair
                    assert (
                        f"recorded exposure from {start / 1000:.3f}s to {end / 1000:.3f}s "
                        f"({elapsed / 1000:.3f}s)" in html
                    )
                    assert "Agree self-clear priorities" in html
                    assert "reaction quality" in html
            else:
                assert paired == []


def _assert_summon_bounds(doc: dict[str, Any], fixture: str, out: Path) -> None:
    cases = json.loads((ROOT / "summon-facts.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        if case["fixture"] != fixture:
            continue
        boss = next(b for b in doc["bosses"] if b["encounter_id"] == case["encounter_id"])
        subject = boss["subject"]
        if subject and (subject["report_code"], subject["fight_id"]) == (
            case["report"],
            case["fight"],
        ):
            observations = boss["playbook"]["summon_observations"]
        else:
            example = next(
                example
                for example in boss["playbook"]["cohort_summon_observations"]
                if (example["report_code"], example["fight_id"]) == (case["report"], case["fight"])
            )
            observations = example["summons"]
        [observation] = observations
        assert observation["summons"]["value"] == len(case["expected"]["summons"])
        assert sorted(observation["transitions"]["value"]) == sorted(
            [row[0] / 1000, row[1], row[3], row[4]] for row in case["expected"]["summons"]
        )
        targets = {(t["actor_id"], t["instance"]): t for t in observation["targets"]}
        assert len(targets) == len(observation["targets"])
        assert len(targets) == len(case["boundary_expectations"])
        for expected in case["boundary_expectations"]:
            target = targets[expected["actor"], expected["instance"]]
            assert target["game_id"] == 176525
            for actual, key in (
                ("summoned_s", "summoned_ms"),
                ("first_positive_overkill_s", "first_positive_overkill_ms"),
                ("elapsed_to_overkill_s", "elapsed_to_overkill_ms"),
            ):
                value = expected[key]
                assert target[actual]["value"] == (None if value is None else value / 1000)
            coverage = target["elapsed_to_overkill_s"]["coverage"]
            assert coverage and coverage[0]["role"] == "encounter"
    if any(case["fixture"] == fixture for case in cases):
        for page in ("report.html", "playbook.html"):
            html = (out / page).read_text(encoding="utf-8")
            assert "Observed summon event bounds." in html
            assert "Groups can overlap." in html
            assert "from summon to first positive-overkill marker." in html


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
    if fixture in {"aq40-hunter-expanded-context", "aq40-hunter-cohort-context"}:
        sartura = next(b for b in doc["bosses"] if b["encounter_id"] == 50711)
        assert sartura["subject"]["hunter"]["total_pet_dps"]["value"] == 0
        assert sartura["playbook"]["pet"]["no_hunter_pet"] is True
        median = sartura["benchmarks"]["baseline"]["medians"]["pet_dps"]
        assert median["n_known"] == 5 and median["value"]["value"] == 0
        assert not any(r["rule"] == "pet-absent" for r in sartura["recommendations"])
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
            hunter = entry.get("hunter")
            pet_analysis = hunter if hunter is not None else entry["combat"]
            assert {p["actor_id"] for p in pet_analysis["pets"]} == ids
            assert (
                entry["pets_listed"] if hunter is not None else pet_analysis["pets_known"]
            ) is expected["listing_complete"]
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
                if hunter is None:
                    reported = next(
                        p for p in pet_analysis["pets"] if p["actor_id"] == pet["actor"]
                    )
                    assert reported["damage"]["value"] == pet["totals"]["damage"]
                    assert reported["dps"]["value"] == pytest.approx(
                        pet["totals"]["damage"] * 1000 / expected["duration_ms"]
                    )
                    if fixture in {
                        "mc-restoration-shaman-raid-context",
                        "mc-elemental-shaman-initial-raid-context",
                        "mc-elemental-shaman-raid-context",
                    }:
                        support = reported["healing_support"]
                        assert support["owner_actor_id"] == owner
                        assert support["game_id"] == pet["catalog"]["gameID"]
                        assert support["healing"]["value"] == pet["totals"]["effective_healing"]
                        assert support["absorption"]["value"] == pet["totals"]["absorbed_amount"]
                        assert support["combined_per_second"]["value"] == pytest.approx(
                            (pet["totals"]["effective_healing"] + pet["totals"]["absorbed_amount"])
                            * 1000
                            / expected["duration_ms"]
                        )
                    continue
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
            if hunter is None:
                continue
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
    if (
        fixture["label"] in {"aq40-hunter-expanded-context", "aq40-hunter-cohort-context"}
        and boss["encounter_id"] == 50711
    ):
        for name, absence in (
            ("report.html", "None took part"),
            ("playbook.html", "No Hunter pet took part (listing recorded)."),
        ):
            html = (out / name).read_text(encoding="utf-8")
            section = html.split('id="boss-50711"', 1)[1].split('<section class="boss"', 1)[0]
            assert absence in section
            assert "Bring a pet and keep it attacking." not in section
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
    if boss["encounter_id"] in fixture.get("excluded_subject_encounters", []):
        assert boss["subject"] is None
        excluded = boss["playbook"]["excluded_subject"]
        assert excluded["player"] == marker["subject"]["name"]
        assert excluded["combat"]["role"]["value"] is None
        assert boss["playbook"]["personal_data"]["status"] == "insufficient-data"
        assert boss["recommendations"] == []
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
        # Format 1 archives have no encounter All scope: the raw facts are unchanged, but
        # complete counts now require event-set proof (certainty correction, D029).
        format1 = fixture["label"] in ("mc-garr-control-warlock", "mc-garr-warlock")
        assert control["applications"]["value"] == (None if format1 else 0)
        assert control["observations"]["value"] == (
            [[4.258, 100, 8, 18647]] if positive else None if format1 else []
        )
        assert [(r["target_actor_id"], r["target_instance"]) for r in control["review"]] == (
            [(100, 8)] if positive else []
        )
        # Independently frozen owned curse occurrences (garr-owned-curses-frozen.json).
        (curse,) = boss["playbook"]["curse_applications"]
        cursed = [[5.764, 101, None, 17937]] if positive else [[1.711, 106, None, 17937]]
        assert curse["observations"]["value"] == cursed
        assert curse["applications"]["value"] == (None if format1 else 1)
        assert [(r["ability_id"], r["target_actor_id"]) for r in curse["review"]] == [
            (17937, cursed[0][1])
        ]
        assert "another Warlock's curse is not yours" in curse["limitation"]
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
        # A capture with no personal fight on any boss has nothing to say about "you".
        personal = any(b["subject"] or b["playbook"].get("excluded_subject") for b in doc["bosses"])
        assert ("Recorded boss melee events against you:" in html) is personal
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
            positive = fixture["label"] == "mc-garr-control-warlock"
            format1 = fixture["label"] in ("mc-garr-control-warlock", "mc-garr-warlock")
            count = "Unknown" if format1 else 0
            assert f"Recorded Firesworn Banish applications: {count}." in html
            assert control["limitation"] in html
            if positive:
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
