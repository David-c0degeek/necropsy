"""Druid role and coverage contracts through the shared snapshot pipeline."""

from __future__ import annotations

import json
import zipfile
from dataclasses import replace
from pathlib import Path

import duckdb
import pytest

from necropsy.analysis.benchmark import load_bosses
from necropsy.analysis.evidence import EvidenceLevel
from necropsy.analysis.roles import ComparisonKey, FightRole, ranking_policy
from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import build_document, dumps
from necropsy.report.package import build_outputs
from tests.druid_fixture import document as _document
from tests.druid_fixture import snapshot as _snapshot
from tests.snapshot_builder import ENCOUNTER, FIGHT


@pytest.mark.parametrize(
    ("names", "role"),
    [
        (["Starfire"] * 3, "balance-dps"),
        (["Hurricane"] * 3, "balance-dps"),
        (["Shred"] * 3, "feral-dps"),
        (["Ravage"] * 3, "feral-dps"),
        (["Healing Touch"] * 3, "restoration"),
        (["Swiftmend"] * 3, "restoration"),
        (["Shred"] * 3 + ["Healing Touch"] * 3, "hybrid"),
        (["Maul"] * 3, None),
        ([], None),
    ],
)
def test_role_uses_actions_instead_of_talents(
    tmp_path: Path,
    names: list[str],
    role: str | None,
) -> None:
    doc = _document(tmp_path, names)
    analysis = doc["bosses"][0]["subject"]["druid"]
    assert analysis["role"]["value"] == role
    assert analysis["build"]["value"] == "0/0/51"
    assert analysis["ranking_category"]["value"] == "Restoration"
    assert analysis["threat"]["value"] is None


def test_partial_stream_never_proves_complete_role_or_healing(tmp_path: Path) -> None:
    d = _document(tmp_path, ["Healing Touch"] * 3, partial=True)["bosses"][0]["subject"]["druid"]
    assert d["role"]["value"] is None
    assert d["observed_roles"]["value"] == ["restoration"]
    assert d["metrics"]["effective_healing"]["value"] is None
    assert d["metrics"]["overhealing"]["value"] is None
    assert d["metrics"]["overhealing_pct"]["value"] is None
    assert len(d["timeline"]) >= 6


@pytest.mark.parametrize(
    ("primary", "secondary", "expected"),
    [
        ("Starfire", "Healing Touch", "balance-dps"),
        ("Shred", "Healing Touch", "feral-dps"),
        ("Healing Touch", "Moonfire", "restoration"),
    ],
)
def test_incidental_secondary_casts_are_preserved_without_forcing_hybrid(
    tmp_path: Path,
    primary: str,
    secondary: str,
    expected: str,
) -> None:
    doc = _document(tmp_path, [primary] * 20 + [secondary] * 3)
    d = doc["bosses"][0]["subject"]["druid"]
    assert d["role"]["value"] == expected
    assert len(d["observed_roles"]["value"]) == 2
    assert sum(span["qualifies_as_duty"] for span in d["activity_spans"]) == 1


def test_healing_amount_excludes_overheal_and_outputs_work(tmp_path: Path) -> None:
    doc = _document(tmp_path, ["Healing Touch"] * 3)
    boss = doc["bosses"][0]
    d = boss["subject"]["druid"]
    assert d["metrics"]["effective_healing"]["value"] == 300
    assert d["metrics"]["overhealing"]["value"] == 150
    assert d["metrics"]["overhealing_pct"]["value"] == pytest.approx(100 / 3)
    assert d["metrics"]["effective_healing_per_second"]["value"] == 3
    assert "hunter" not in boss["subject"]
    outputs = build_outputs(dumps(doc).encode())
    for name in ("report.html", "playbook.html"):
        html = outputs[name]
        assert html is not None
        assert b"Druid" in html and b"Same-faction shot" not in html
        assert b"boss-51118" in html
        if name == "report.html":
            assert b"restoration" in html and b"effective healing" in html
        else:
            assert b"During the fight" in html and b"<table" not in html
    package = outputs["necropsy-99-2006.zip"]
    assert package is not None
    archive = tmp_path / "package.zip"
    archive.write_bytes(package)
    with zipfile.ZipFile(archive) as zf:
        assert "tables/roles.csv" in zf.namelist()
        assert "tables/timeline.csv" in zf.namelist()
        assert json.loads(zf.read("analysis.json"))["subject"]["class_id"] == 2


def test_older_druid_optional_detail_fields_still_render(tmp_path: Path) -> None:
    doc = _document(tmp_path, ["Healing Touch"] * 3)
    boss = doc["bosses"][0]
    boss["subject"]["druid"].pop("healing_spells")
    boss["subject"]["druid"].pop("defensive_uptime_s")
    boss["playbook"].pop("primary_metrics")
    outputs = build_outputs(dumps(doc).encode())
    assert outputs["report.html"] and outputs["playbook.html"]


def test_non_finite_saved_category_score_stays_unknown(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path, ["Starfire"] * 3)
    db = tmp_path / "analysis.duckdb"
    ingest(snapshot, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE benchmark_participants SET total = 'Infinity'::DOUBLE")
        doc = build_document(con)
    assert doc["bosses"][0]["subject"]["ranking"]["category_score"] is None
    assert "Infinity" not in dumps(doc)


def test_cohort_dimensions_cannot_mix_roles_or_metrics() -> None:
    key = ComparisonKey(
        2, ENCOUNTER, "Alliance", "0/0/51", "Restoration", FightRole.HEALER, "hps", 1
    )
    for changes in (
        {"metric": "dps"},
        {"role": FightRole.TANK},
        {"build": ""},
        {"role": FightRole.HYBRID},
        {"category": "Feral"},
    ):
        with pytest.raises(ValueError):
            replace(key, **changes)
    assert ranking_policy(2, "Guardian").metric == "dps"
    assert ranking_policy(2, "Restoration").metric == "hps"
    assert ranking_policy(2, "Balance", "hps").role == "restoration"
    assert replace(key, category="Balance").metric == "hps"
    with pytest.raises(ValueError, match="category"):
        ranking_policy(2)


def test_druid_baseline_includes_different_builds_and_retains_inferred_membership(
    tmp_path: Path,
) -> None:
    from necropsy.report.druid import boss_section

    archive = _snapshot(tmp_path, ["Healing Touch"] * 3)
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db), read_only=True) as con:
        boss = load_bosses(con, "classic_era", "naxxramas")[0]
        entry = boss.subject
        assert entry is not None
        # Different talent points remain useful within the selected spec and faction.
        from necropsy.analysis.evidence import observed

        incompatible = replace(
            entry,
            class_analysis=replace(
                entry.druid,
                build=observed("1/0/50", *entry.profile.talents.refs),
            ),
        )
        cohort = tuple(
            replace(
                entry,
                participant=replace(
                    entry.participant,
                    player=f"Healer {n}",
                    kind="top",
                ),
            )
            for n in range(3)
        )
        result = boss_section(con, replace(boss, cohort=(*cohort, incompatible)), 1)
        median = result["benchmarks"]["baseline"]["medians"]["effective_healing_per_second"]
        assert median["n_known"] == 4
        assert median["value"]["value"] == 3
        assert median["value"]["level"] == "inferred"
        assert result["benchmarks"]["baseline"]["excluded_incompatible"] == 0
        assert result["benchmarks"]["baseline"]["builds_differing"] == 1


def test_registry_selects_druid_and_keeps_hunter_guard(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path, ["Starfire"] * 3)
    db = tmp_path / "analysis.duckdb"
    ingest(snapshot, db)
    with duckdb.connect(str(db), read_only=True) as con:
        entry = load_bosses(con, "classic_era", "naxxramas")[0].subject
        assert entry is not None and entry.druid.role.level is EvidenceLevel.INFERRED
        with pytest.raises(TypeError, match="Hunter-only"):
            _ = entry.hunter


def test_override_preserves_observation_and_declines_baseline(tmp_path: Path) -> None:
    from necropsy.analysis.roles import RoleOverride, load_overrides

    snapshot = _snapshot(tmp_path, ["Healing Touch"] * 3)
    db = tmp_path / "analysis.duckdb"
    ingest(snapshot, db)
    path = tmp_path / "overrides.json"
    path.write_text(
        json.dumps({"REPORT1/7": {"role": "feral-tank", "reason": "Assigned off-tank"}})
    )
    overrides = load_overrides(path)
    assert overrides[("REPORT1", FIGHT)] == RoleOverride(FightRole.TANK, "Assigned off-tank")
    with duckdb.connect(str(db), read_only=True) as con:
        doc = build_document(con, role_overrides=overrides)
        with pytest.raises(ValueError, match="acquired subject"):
            build_document(con, role_overrides={("WRONG", 7): RoleOverride(FightRole.TANK, "test")})
    boss = doc["bosses"][0]
    assert boss["subject"]["druid"]["role"]["value"] == "restoration"
    assert boss["subject"]["druid"]["selected_role"] == "feral-tank"
    assert boss["subject"]["druid"]["override"]["reason"] == "Assigned off-tank"
    assert boss["benchmarks"]["baseline"]["key"] is None


@pytest.mark.parametrize(("melee", "expected"), [(True, "hybrid"), (False, "feral-dps")])
def test_tank_duty_needs_direct_hits_and_mixed_actions_are_retained(
    tmp_path: Path,
    melee: bool,
    expected: str,
) -> None:
    snapshot = _snapshot(tmp_path, ["Maul"] * 3 + ["Shred"] * 3)
    db = tmp_path / "analysis.duckdb"
    ingest(snapshot, db)
    with duckdb.connect(str(db)) as con:
        con.execute(
            "INSERT INTO actors (report_code,actor_id,name,type,game_id) "
            "VALUES ('REPORT1',50,'Patchwerk','NPC',16028)"
        )
        for i in range(3):
            raw = {"melee": melee, "isAoE": not melee}
            con.execute(
                "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
                "type,source_id,target_id,ability_game_id,amount,raw) "
                "VALUES ('REPORT1',7,?,0,?,'damage',50,1,9999,1000,?)",
                [f"hit-{i}", 5000 + i * 1000, json.dumps(raw)],
            )
        d = build_document(con)["bosses"][0]["subject"]["druid"]
    assert d["role"]["value"] == expected
    if melee:
        assert len(d["activity_spans"]) == 2
    assert d["forms"]["bear"]["value"] is None


def test_resource_side_is_not_an_actor_id_and_unknown_capacity_stays_unknown(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(tmp_path, ["Starfire"] * 3)
    db = tmp_path / "analysis.duckdb"
    ingest(snapshot, db)
    with duckdb.connect(str(db)) as con:
        # resourceActor 2 means event target, which is not the Druid here.
        for side, capacity in ((1, 100), (2, 100), (1, 0)):
            raw = {
                "resourceActor": side,
                "classResources": [{"type": 0, "amount": 25, "max": capacity}],
            }
            con.execute(
                "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
                "type,source_id,target_id,raw) VALUES ('REPORT1',7,?,0,8000,'cast',1,50,?)",
                [f"resource-{side}-{capacity}", json.dumps(raw)],
            )
        readings = build_document(con)["bosses"][0]["subject"]["druid"]["resources"]
    assert len(readings) == 2
    assert sorted(r["evidence"]["level"] for r in readings) == ["observed", "unknown"]
