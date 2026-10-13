"""`necropsy offline` on the committed subset (fast suite)."""

from __future__ import annotations

import dataclasses
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from necropsy.normalize.ingest import IngestError, ingest
from necropsy.report import offline as offline_module
from necropsy.report.analysis_json import AnalysisDocument, json_schema
from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import ArchiveError, load_entries_manifest
from tests.analysis_db import subset_db
from tests.fixture_paths import provenance, subset_entries_path, subset_path

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def document(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    out = tmp_path_factory.mktemp("offline")
    run_offline(subset_path(), out, db=subset_db())
    data = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_document_validates_against_the_schema(document: dict[str, Any]) -> None:
    AnalysisDocument.model_validate(document)
    assert document["schema_version"] == 1
    assert document["snapshot"]["scope"] == "subset"
    assert document["snapshot"]["archive_sha256"] == provenance()["subset"]["sha256"]
    assert document["options"] == {"cross_faction": False}
    assert [b["boss"] for b in document["bosses"]] == [
        "Patchwerk",
        "Grobbulus",
        "Gothik the Harvester",
        "Kel'Thuzad",
    ]


def test_committed_json_schema_is_current() -> None:
    committed = json.loads((REPO / "docs/analysis-json.schema.json").read_text(encoding="utf-8"))
    assert committed == json_schema()


def test_default_document_has_no_cross_faction_detail(document: dict[str, Any]) -> None:
    patchwerk = document["bosses"][0]
    assert patchwerk["benchmarks"]["cross_faction"] is None
    assert patchwerk["benchmarks"]["excluded"]["other_faction"] == 1
    factions = {row["environment"]["faction"]["value"] for row in patchwerk["cohort"]}
    assert factions == {"Alliance"}


def test_kel_thuzad_findings(document: dict[str, Any]) -> None:
    kt = next(b for b in document["bosses"] if b["boss"] == "Kel'Thuzad")
    rules = {r["rule"]: r for r in kt["recommendations"]}
    assert rules["raid-utility"]["controllability"] == "raid-assignment"
    assert "raid-speed-v1" in rules
    # The subset has one same-faction Kel'Thuzad entry, so no baseline and no cadence finding.
    assert "aimed-cadence" not in rules


def test_recommendation_evidence_paths_resolve(document: dict[str, Any]) -> None:
    for boss in document["bosses"]:
        for rec in boss["recommendations"]:
            for path in rec["evidence"]:
                node: Any = boss
                for part in path.split("."):
                    assert isinstance(node, dict) and part in node, (boss["boss"], path)
                    node = node[part]


def test_chronological_lists_stay_chronological(document: dict[str, Any]) -> None:
    casts = document["bosses"][0]["subject"]["hunter"]["shots"]["auto_shot"]["casts"]["value"]
    times = [c["t_s"] for c in casts]
    assert times == sorted(times) and len(times) == 28


def test_repeated_runs_are_byte_identical(tmp_path: Path) -> None:
    run_offline(subset_path(), tmp_path / "a", db=subset_db())
    run_offline(subset_path(), tmp_path / "b", db=subset_db())
    assert (tmp_path / "a/analysis.json").read_bytes() == (
        tmp_path / "b/analysis.json"
    ).read_bytes()


def test_cross_faction_is_opt_in(tmp_path: Path) -> None:
    run_offline(subset_path(), tmp_path, db=subset_db(), cross_faction=True)
    data = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))
    patchwerk = data["bosses"][0]
    assert patchwerk["benchmarks"]["cross_faction"]["rank_one"] == "Smcadogx"
    assert len(patchwerk["cohort"]) == 5


def test_failed_analysis_leaves_no_analysis_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("analysis failed")

    monkeypatch.setattr(offline_module, "build_document", boom)
    with pytest.raises(RuntimeError):
        run_offline(subset_path(), tmp_path, db=subset_db())
    assert not (tmp_path / "analysis.json").exists()
    assert [p.name for p in tmp_path.iterdir()] == []


def test_temporary_database_is_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[Path] = []
    real = ingest

    def spy(snapshot: Path, db: Path, **kwargs: Any) -> Any:
        created.append(db)
        return real(snapshot, db, **kwargs)

    monkeypatch.setattr(offline_module, "ingest", spy)
    run_offline(subset_path(), tmp_path / "out")
    assert created and not created[0].exists()
    assert (tmp_path / "out/analysis.json").exists()


def test_existing_matching_database_is_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def never(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("ingest should not run")

    monkeypatch.setattr(offline_module, "ingest", never)
    run_offline(subset_path(), tmp_path, db=subset_db())


def test_reuse_still_verifies_a_missing_archive(tmp_path: Path) -> None:
    sha = provenance()["subset"]["sha256"]
    with pytest.raises(ArchiveError, match="not found"):
        run_offline(tmp_path / "missing.zip", tmp_path / "out", db=subset_db(), expected_sha256=sha)
    assert not (tmp_path / "out").exists()


def test_reuse_refuses_a_wrong_expected_digest(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError, match="digest mismatch"):
        run_offline(subset_path(), tmp_path, db=subset_db(), expected_sha256="0" * 64)


def test_reuse_checks_members_against_the_manifest(tmp_path: Path) -> None:
    entries = load_entries_manifest(subset_entries_path())
    name = sorted(entries)[0]
    entries[name] = dataclasses.replace(entries[name], sha256="0" * 64)
    with pytest.raises(ArchiveError, match="digest differs"):
        run_offline(subset_path(), tmp_path, db=subset_db(), entries=entries)
    run_offline(
        subset_path(),
        tmp_path,
        db=subset_db(),
        entries=load_entries_manifest(subset_entries_path()),
    )


def test_a_changed_archive_is_not_analyzed_from_the_old_database(tmp_path: Path) -> None:
    changed = tmp_path / "changed.zip"
    shutil.copyfile(subset_path(), changed)
    with zipfile.ZipFile(changed, "a") as archive:
        archive.writestr("extra.txt", "x")
    with pytest.raises(IngestError):
        run_offline(changed, tmp_path / "out", db=subset_db())
    assert not (tmp_path / "out").exists()


def _break(document: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    broken: dict[str, Any] = json.loads(json.dumps(document))
    node: Any = broken
    *parents, last = path.split(".")
    for part in parents:
        node = node[int(part)] if isinstance(node, list) else node[part]
    node[last] = value
    return broken


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("schema_version", 2),
        ("mode", "live"),
        ("snapshot.archive_sha256", "nothex"),
        ("bosses.0.recommendations.0.confidence", "impossible"),
        ("bosses.0.recommendations.0.evidence", 17),
        ("bosses.0.recommendations.0.evidence", []),
        ("bosses.0.subject", {}),
        ("bosses.0.subject.kill_duration_s", 0),
        ("bosses.0.rules.ranking_exclusion_rule.basis", "documented"),
        ("bosses.0.subject.environment.faction.level", "certain"),
        ("bosses.0.subject.environment.faction.value", None),
    ],
)
def test_schema_rejects_malformed_documents(
    document: dict[str, Any], path: str, value: Any
) -> None:
    with pytest.raises(ValidationError):
        AnalysisDocument.model_validate(_break(document, path, value))


def test_empirical_ranking_rule_is_labelled(document: dict[str, Any]) -> None:
    rule = document["bosses"][0]["rules"]["ranking_exclusion_rule"]
    assert rule["basis"] == "empirical"
    assert rule["validation"]
