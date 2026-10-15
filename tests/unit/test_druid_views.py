"""Selected-spec personal analysis and top-player learning remain separate."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import duckdb
import pytest

from necropsy.analysis.benchmark import load_bosses
from necropsy.analysis.evidence import observed
from necropsy.analysis.roles import FightRole, selected_spec
from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import build_document, dumps
from necropsy.report.druid import boss_section
from necropsy.report.package import build_outputs
from tests.druid_fixture import snapshot
from tests.snapshot_builder import ENCOUNTER


def _database(tmp_path: Path, *, partial: bool = False) -> duckdb.DuckDBPyConnection:
    raw = snapshot(tmp_path, ["Healing Touch"] * 3, partial=partial)
    db = tmp_path / "view.duckdb"
    ingest(raw, db)
    return duckdb.connect(str(db))


def test_missing_personal_data_keeps_a_labelled_example_without_a_baseline(tmp_path: Path) -> None:
    with _database(tmp_path) as con:
        boss = load_bosses(con, "classic_era", "naxxramas")[0]
        assert boss.subject is not None
        example = replace(
            boss.subject,
            participant=replace(
                boss.subject.participant,
                kind="top",
                player="Example healer",
                leaderboard_position=2,
            ),
        )
        section = boss_section(
            con,
            replace(boss, subject=None, cohort=(example,)),
            1,
            "hps",
            "Restoration",
        )
    assert section["subject"] is None
    assert section["playbook"]["personal_data"]["status"] == "insufficient-data"
    assert section["playbook"]["reference"]["player"] == "Example healer"
    assert section["playbook"]["reference"]["leaderboard_position"] == 2
    assert section["benchmarks"]["baseline"]["key"] is None
    assert section["benchmarks"]["baseline"]["medians"] == {}
    assert section["recommendations"] == []


@pytest.mark.parametrize("role", [FightRole.HYBRID, FightRole.TANK])
def test_incompatible_duties_are_never_healing_examples(tmp_path: Path, role: FightRole) -> None:
    with _database(tmp_path) as con:
        boss = load_bosses(con, "classic_era", "naxxramas")[0]
        assert boss.subject is not None
        example = replace(
            boss.subject,
            class_analysis=replace(
                boss.subject.druid, role=observed(role, *boss.subject.druid.role.refs)
            ),
            participant=replace(boss.subject.participant, kind="top", leaderboard_position=1),
        )
        section = boss_section(
            con, replace(boss, subject=None, cohort=(example,)), 1, "hps", "Restoration"
        )
    assert section["playbook"]["reference"] is None


def test_partial_streams_never_supply_an_example_even_with_a_role_label(tmp_path: Path) -> None:
    with _database(tmp_path, partial=True) as con:
        boss = load_bosses(con, "classic_era", "naxxramas")[0]
        assert boss.subject is not None
        example = replace(
            boss.subject,
            class_analysis=replace(
                boss.subject.druid,
                role=observed(
                    FightRole.HEALER,
                    *boss.subject.druid.role.refs,
                ),
            ),
            participant=replace(boss.subject.participant, kind="top", leaderboard_position=1),
        )
        section = boss_section(
            con, replace(boss, subject=None, cohort=(example,)), 1, "hps", "Restoration"
        )
    assert section["playbook"]["reference"] is None


def test_tank_view_does_not_grade_a_non_tank_guardian_parse(tmp_path: Path) -> None:
    with _database(tmp_path) as con:
        boss = load_bosses(con, "classic_era", "naxxramas")[0]
        assert boss.subject is not None
        source = replace(
            boss.subject,
            class_analysis=replace(
                boss.subject.druid,
                ranking_category=observed("Guardian", *boss.subject.druid.ranking_category.refs),
            ),
        )
        section = boss_section(con, replace(boss, subject=source), 1, "dps", "Guardian")
    assert section["subject"] is None
    assert "Tank" in section["playbook"]["personal_data"]["message"]
    assert section["playbook"]["excluded_subject"]["druid"]["role"]["value"] == "restoration"
    assert section["recommendations"] == []


def test_every_requested_boss_renders_when_no_player_entries_exist(tmp_path: Path) -> None:
    with _database(tmp_path) as con:
        con.execute("DELETE FROM benchmark_participants")
        acquisition = {
            "selected_category": "Restoration",
            "bosses": [
                {"encounter_id": ENCOUNTER, "boss": "Patchwerk", "attempted": True},
                {"encounter_id": 51119, "boss": "Sapphiron", "attempted": False},
            ],
        }
        con.execute(
            "UPDATE snapshot_meta SET mode='live', partition_id=1, acquisition=?",
            [json.dumps(acquisition)],
        )
        doc = build_document(con)
    assert len(doc["bosses"]) == 2
    assert all(b["subject"] is None for b in doc["bosses"])
    sapphiron = next(b for b in doc["bosses"] if b["encounter_id"] == 51119)
    assert sapphiron["playbook"]["personal_data"]["status"] == "not-assessed"
    outputs = build_outputs(dumps(doc).encode())
    page = outputs["playbook.html"]
    assert page is not None
    text = page.decode()
    assert 'id="boss-51119"' in text and "Selected spec: Restoration" in text
    assert "0 encounters with your matching data" in text
    assert "No eligible event example" in text


@pytest.mark.parametrize(
    ("value", "canonical"),
    [
        ("Tank", "Guardian"),
        ("boomkin", "Balance"),
        ("restoration", "Restoration"),
    ],
)
def test_user_spec_names_select_canonical_categories(value: str, canonical: str) -> None:
    assert selected_spec(value) == canonical


@pytest.mark.parametrize(
    ("rank", "spec", "expected"),
    [
        (1, "Restoration", True),
        (2, "Restoration", False),
        (1, "Balance", False),
    ],
)
def test_saved_rank_one_metadata_is_scoped_and_never_creates_personal_data(
    tmp_path: Path,
    rank: int,
    spec: str,
    expected: bool,
) -> None:
    with _database(tmp_path) as con:
        boss = load_bosses(con, "classic_era", "naxxramas")[0]
        row = {
            "name": "Top player",
            "class": "Druid",
            "spec": spec,
            "amount": 500,
            "rank": rank,
            "hardModeLevel": 0,
            "report": {"code": "TopReport", "fightID": 3},
        }
        con.execute("DELETE FROM rankings WHERE kind='leaderboard'")
        con.execute(
            "INSERT INTO rankings (source,kind,encounter_id,page,row_index,raw) "
            "VALUES ('leaderboards/test.json','leaderboard',?,1,0,?)",
            [ENCOUNTER, json.dumps(row)],
        )
        record = {
            "key": {
                k: {"value": v, "status": "enforced"}
                for k, v in {
                    "class_name": "Druid",
                    "spec": "Restoration",
                    "partition": 1,
                    "encounter": ENCOUNTER,
                    "role": "restoration",
                    "metric": "hps",
                }.items()
            }
        }
        section = boss_section(con, replace(boss, subject=None), 1, "hps", "Restoration", record)
    top = section["benchmarks"]["overall_top"]
    assert (top is not None) is expected
    if top is not None:
        assert top["category_score"]["value"] == 500 and top["metric"] == "hps"
        assert top["basis"] == "saved-ranking-metadata"
    assert section["playbook"]["reference"] is None
    assert section["subject"] is None and section["recommendations"] == []
