"""Encounter mechanics and missing optional metadata must not erase healing analysis."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.analysis.benchmark import Entry, load_bosses
from necropsy.analysis.evidence import unknown
from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import build_document, dumps
from necropsy.report.druid import boss_section
from necropsy.report.package import build_outputs
from tests.druid_fixture import snapshot


@pytest.mark.parametrize("casts", [0, 1, 2])
@pytest.mark.parametrize("partial", [False, True])
def test_loatheb_sparse_heals_need_actions_and_complete_streams(
    tmp_path: Path,
    casts: int,
    partial: bool,
) -> None:
    archive = snapshot(tmp_path, ["Healing Touch"] * casts, partial=partial)
    db = tmp_path / "test.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE fights SET encounter_id=51115, name='Loatheb'")
        con.execute("UPDATE benchmark_participants SET encounter_id=51115, boss='Loatheb'")
        boss = boss_section(
            con, load_bosses(con, "classic_era", "naxxramas")[0], 1, "hps", "Restoration"
        )
    personal = boss["subject"]
    if casts and not partial:
        assert personal is not None
        assert personal["druid"]["role"]["value"] == "restoration"
        assert personal["druid"]["role"]["params"]["healing_minimum_casts"] == 1
        assert any("Corrupted Mind" in s for s in boss["playbook"]["assessment_limits"])
    else:
        assert personal is None


def test_other_encounters_do_not_infer_healer_from_one_heal(tmp_path: Path) -> None:
    archive = snapshot(tmp_path, ["Healing Touch"])
    db = tmp_path / "test.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        entry = load_bosses(con, "classic_era", "naxxramas")[0].subject
    assert entry is not None and entry.druid.role.value is None


def test_loatheb_incidental_heal_does_not_override_balance_duty(tmp_path: Path) -> None:
    archive = snapshot(tmp_path, ["Starfire"] * 20 + ["Healing Touch"])
    db = tmp_path / "test.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE fights SET encounter_id=51115, name='Loatheb'")
        con.execute("UPDATE benchmark_participants SET encounter_id=51115, boss='Loatheb'")
        entry = load_bosses(con, "classic_era", "naxxramas")[0].subject
    assert entry is not None and entry.druid.role.value == "balance-dps"
    assert entry.druid.observed_roles.value is not None
    assert "restoration" in entry.druid.observed_roles.value


@pytest.mark.parametrize("overheal", ["absent", None, "invalid", -1])
def test_sparse_overheal_is_zero_but_invalid_values_stay_unknown(
    tmp_path: Path,
    overheal: str | int | None,
) -> None:
    archive = snapshot(tmp_path, ["Healing Touch"] * 3)
    db = tmp_path / "test.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        row = con.execute(
            "SELECT event_uid, raw FROM events WHERE type='heal' ORDER BY timestamp LIMIT 1"
        ).fetchone()
        assert row is not None
        uid, raw = row
        event = json.loads(raw)
        if overheal == "absent":
            event.pop("overheal")
        else:
            event["overheal"] = overheal
        con.execute(
            "UPDATE events SET overheal=NULL, raw=? WHERE event_uid=?", [json.dumps(event), uid]
        )
        doc = build_document(con)
    values = doc["bosses"][0]["subject"]["druid"]["metrics"]
    if overheal == "absent":
        assert values["overhealing"]["value"] == 100
        assert values["overhealing_pct"]["value"] == 25
        assert values["overhealing"]["rule"] == "wcl-sparse-overheal-v1"
    else:
        assert values["overhealing"]["value"] is None
        assert values["overhealing_pct"]["value"] is None
        assert "Overhealing review unavailable" in str(
            doc["bosses"][0]["playbook"]["assessment_limits"]
        )


def _examples(entry: Entry, n: int = 3) -> tuple[Entry, ...]:
    return tuple(
        replace(
            entry,
            participant=replace(
                entry.participant,
                player=f"Healer {i}",
                kind="top",
                leaderboard_position=i + 1,
            ),
        )
        for i in range(n)
    )


def test_missing_talents_keep_medians_individual_comparisons_and_findings(tmp_path: Path) -> None:
    archive = snapshot(tmp_path, ["Healing Touch"] * 3)
    db = tmp_path / "test.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE combatant_info SET talent_points=NULL, talents=NULL")
        boss = load_bosses(con, "classic_era", "naxxramas")[0]
        entry = boss.subject
        assert entry is not None and entry.druid.build.value is None
        example = replace(
            entry,
            class_analysis=replace(
                entry.druid,
                metrics={
                    **entry.druid.metrics,
                    "effective_healing_per_second": replace(
                        entry.druid.metrics["effective_healing_per_second"], value=6.0
                    ),
                },
            ),
        )
        result = boss_section(
            con, replace(boss, cohort=_examples(example)), 1, "hps", "Restoration"
        )
    base = result["benchmarks"]["baseline"]
    assert base["entries"] == 3 and base["builds_unknown"] == 3
    assert base["builds_differing"] == 0
    assert base["medians"]["effective_healing_per_second"]["value"]["value"] == 6
    assert result["playbook"]["reference"] is not None
    assert all(c["build_matches"] is None for c in result["playbook"]["comparisons"])
    rec = next(
        r for r in result["recommendations"] if r["rule"] == "druid-healing-throughput-review-v1"
    )
    assert rec["observed"]["value"] == 3
    assert rec["benchmark"]["n_known"] == 3 and rec["benchmark"]["value"] == 6
    # Shared validation, rendering and package creation must accept the unknown builds.
    doc = build_document_for_section(tmp_path, result)
    outputs = build_outputs(dumps(doc).encode())
    html = outputs["playbook.html"]
    assert html is not None and b"Tentative advice: limited evidence" in html
    for limit in result["playbook"]["assessment_limits"]:
        assert limit.encode() in html
    report = outputs["report.html"]
    assert report is not None and b"3 source builds are unknown" in report
    assert b"event comparisons do not require talent data" in report


def build_document_for_section(tmp_path: Path, section: dict[str, Any]) -> dict[str, Any]:
    with duckdb.connect(str(tmp_path / "test.duckdb")) as con:
        doc = build_document(con)
    doc["bosses"][0] = section
    return doc


@pytest.mark.parametrize("case", ["normal", "low", "sparse", "unknown", "loatheb"])
def test_healer_reviews_require_known_comparable_values_and_respect_mechanics(
    tmp_path: Path,
    case: str,
) -> None:
    archive = snapshot(tmp_path, ["Healing Touch"] * 3)
    db = tmp_path / "test.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        if case == "loatheb":
            con.execute("UPDATE fights SET encounter_id=51115, name='Loatheb'")
            con.execute("UPDATE benchmark_participants SET encounter_id=51115, boss='Loatheb'")
        boss = load_bosses(con, "classic_era", "naxxramas")[0]
        entry = boss.subject
        assert entry is not None
        metrics = dict(entry.druid.metrics)
        for name in ("healing_casts_per_minute", "effective_healing_per_second"):
            current = metrics[name].value
            assert current is not None
            metrics[name] = (
                unknown("no reliable healing reading")
                if case == "unknown"
                else replace(metrics[name], value=current * (1 if case == "normal" else 2))
            )
        example = replace(entry, class_analysis=replace(entry.druid, metrics=metrics))
        result = boss_section(
            con,
            replace(boss, cohort=_examples(example, 2 if case == "sparse" else 3)),
            1,
            "hps",
            "Restoration",
        )
    rules = {r["rule"] for r in result["recommendations"]}
    assert ("druid-healing-cadence-review-v1" in rules) == (case == "low")
    assert ("druid-healing-throughput-review-v1" in rules) == (case == "low")


@pytest.mark.parametrize("case", ["unused", "used", "sparse", "unknown", "longer"])
def test_cooldown_review_requires_complete_counts_and_relevant_examples(
    tmp_path: Path,
    case: str,
) -> None:
    archive = snapshot(tmp_path, ["Healing Touch"] * 3)
    db = tmp_path / "test.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        boss = load_bosses(con, "classic_era", "naxxramas")[0]
        entry = boss.subject
        assert entry is not None
        subject = replace(
            entry,
            class_analysis=replace(
                entry.druid,
                casts=(
                    unknown("incomplete source")
                    if case == "unknown"
                    else replace(
                        entry.druid.casts,
                        value={"Healing Touch": 3, "Innervate": int(case == "used")},
                    )
                ),
            ),
        )
        example = replace(
            entry,
            class_analysis=replace(
                entry.druid, casts=replace(entry.druid.casts, value={"Innervate": 1})
            ),
        )
        if case == "longer":
            example = replace(example, participant=replace(example.participant, end_time=200000))
        result = boss_section(
            con,
            replace(boss, subject=subject, cohort=_examples(example, 2 if case == "sparse" else 3)),
            1,
            "hps",
            "Restoration",
        )
    recs = [r for r in result["recommendations"] if r["rule"] == "druid-healing-cooldown-review-v1"]
    assert bool(recs) == (case == "unused")
    if recs:
        assert recs[0]["observed"] == {"spell": "Innervate", "casts": 0}
        assert recs[0]["benchmark"]["users"] == 3
