"""A batch completes a cell only while every layer still verifies: its manifest
bytes, its pinned artifacts, the exact boss/configuration/actor identity, and
engine and content digests that equal the checkout's. Unrelated shared edits
leave it complete; relevant ones make it stale without touching other cells."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import raid_batch as rb

HEAD = "raid,zone_id,encounter_id,boss,variant,class_id,class,category,metric,faction,"
HEAD += "implementation,mechanics_and_guidance,synthetic_behavior,real_actor_source,"
HEAD += "independent_facts,ranking_reconciliation,render_review,status,owner,notes"
CELL = "mc/1/6/Holy/hps/Alliance"
OTHER = "mc/2/6/Holy/hps/Alliance"
ARCHIVE_PATH = "tests/golden/raids/raw/cap/a.zip"
ENTRIES_PATH = "tests/golden/raids/raw/cap/a.entries"
RANKING = "tests/golden/raids/hps-ranking-one.json"


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, check=True, text=True)
    return done.stdout.strip()


def put(root: Path, path: str, data: Any) -> None:
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        file.write_bytes(data)
    elif isinstance(data, str):
        file.write_text(data, encoding="utf-8", newline="\n")
    else:
        file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(root: Path, path: str) -> str:
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


def source(root: Path, actor: int) -> dict[str, Any]:
    return {
        "archive": {"path": ARCHIVE_PATH, "sha256": sha(root, ARCHIVE_PATH), "locator": "x"},
        "entries": {"path": ENTRIES_PATH, "sha256": sha(root, ENTRIES_PATH), "locator": "x"},
        "provenance": {"path": ARCHIVE_PATH, "sha256": sha(root, ARCHIVE_PATH), "locator": "x"},
        "report": "R",
        "fight": actor,
        "actor": actor,
        "partition": 1,
    }


def receipt(commit: str, archive_sha: str, entries_sha: str) -> dict[str, Any]:
    clean: dict[str, Any] = {"missing": {"report.html": [], "playbook.html": []}, "expected": 1}
    boss: dict[str, Any] = {"outcome": "checked", "sections_missing": []}
    boss.update({k: clean for k in ("strategy", "facts", "class_notes", "removals")})
    return {
        "commit": commit,
        "unit": {"class_id": 6, "category": "Holy", "metric": "hps", "faction": "Alliance"},
        "archive": {"path": ARCHIVE_PATH.replace("/", "\\"), "sha256": archive_sha},
        "entries": {"path": ENTRIES_PATH.replace("/", "\\"), "sha256": entries_sha},
        "wheel": {
            "payload": {"files": 3, "mismatched": [], "not_in_git": [], "missing_from_wheel": []}
        },
        "source_equals_installed": True,
        "content": {"bosses": {"1": boss, "2": boss}},
        "content_source_missing": 0,
        "visual": {
            p: {"exit": 0, "summary": "5 screens, 0 with findings"}
            for p in ("report.html", "playbook.html")
        },
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "config", "core.autocrlf", "false")
    put(root, "src/necropsy/engine.py", "VALUE = 1\n")
    zones = "src/necropsy/rules/classic_era/zones"

    def policy(enc: int) -> dict[str, Any]:
        return {
            "rule": f"mc-{enc}-policy",
            "evidence": RANKING,
            "scope": {
                "encounter_id": enc,
                "class_id": 6,
                "category": "Holy",
                "metric": "hps",
                "faction": "Alliance",
            },
        }

    put(
        root,
        f"{zones}/mc.yaml",
        yaml.safe_dump({"rule": "mc", "ranking_metric_policies": [policy(1)]}),
    )
    guidance = {
        "rule": "g",
        "strategy": {
            1: {"source": "s", "items": [{"rule": "a", "text": "one", "classes": [6]}]},
            2: {"source": "s", "items": [{"rule": "b", "text": "two"}]},
        },
    }
    put(root, f"{zones}/mc_guidance.yaml", yaml.safe_dump(guidance))
    facts = {"rule": "f", "encounters": [{"id": 1, "timings": []}, {"id": 2, "timings": []}]}
    put(root, f"{zones}/mc_facts.yaml", yaml.safe_dump(facts))
    put(root, ARCHIVE_PATH, b"archive")
    put(root, ENTRIES_PATH, b"entries")
    archive_sha = sha(root, ARCHIVE_PATH)
    cases = [
        {"id": f"actor-{n}", "report": "R", "fight": n, "actor": n, "sha256": archive_sha}
        for n in (7, 8)
    ]
    put(root, rb.FACTS, {"version": 1, "cases": cases})
    healing = [{**c, "id": f"heal-{c['actor']}", "actor_case": c["id"]} for c in cases]
    put(root, rb.HEALING_FACTS, {"version": 1, "kind": "k", "cases": healing})
    put(root, RANKING, {"version": 1, "rule": "mc-1-policy", "rows": []})
    records = [
        {
            "cell_id": CELL,
            "status": "IN_PROGRESS",
            "references": {},
            "real_actor_source": source(root, 7),
            "note": "",
        },
        {
            "cell_id": OTHER,
            "status": "IN_PROGRESS",
            "references": {},
            "real_actor_source": source(root, 8),
            "note": "",
        },
    ]
    put(root, rb.COVERAGE, {"version": 1, "records": records})
    rows = [HEAD] + [
        f"mc,2000,{e},B{e},standard,6,Paladin,Holy,hps,Alliance,"
        + ",".join(["TODO"] * 7)
        + ",IN_PROGRESS,agent,"
        for e in (1, 2)
    ]
    put(root, "tasks/raid-completion/coverage-matrix.csv", "\n".join(rows) + "\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    commit = git(root, "rev-parse", "HEAD")
    put(root, "work/receipt.json", receipt(commit, archive_sha, sha(root, ENTRIES_PATH)))
    return root


def spec(root: Path) -> dict[str, Any]:
    return {
        "batch": "b1",
        "captures": {
            "cap": {
                "receipt": str(root / "work/receipt.json"),
                "visual_sample": {"picture": "p.png", "by": "owner", "result": "fine"},
            }
        },
        "cells": {c: {"coverage_note": "n", "matrix_note": "m"} for c in (CELL, OTHER)},
    }


def written(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    assert rb.write(spec(repo), repo) == 0
    manifest = json.loads((repo / rb.BATCHES / "b1.json").read_text(encoding="utf-8"))
    records = json.loads((repo / rb.COVERAGE).read_text(encoding="utf-8"))["records"]
    return manifest, {r["cell_id"]: r for r in records}


def problems(
    repo: Path, manifest: dict[str, Any], records: dict[str, Any], cell: str = CELL
) -> list[str]:
    return rb.manifest_problems(repo, manifest, cell, records[cell]["real_actor_source"])


def test_write_registers_cells_against_one_manifest(repo: Path) -> None:
    manifest, records = written(repo)
    record = records[CELL]
    assert record["status"] == "COMPLETE"
    ref = record["references"]["batch"][0]
    assert ref == {
        "path": f"{rb.BATCHES}/b1.json",
        "sha256": sha(repo, f"{rb.BATCHES}/b1.json"),
        "locator": CELL,
    }
    assert set(manifest["cells"]) == {CELL, OTHER}
    assert manifest["cells"][CELL]["ranking"]["path"] == RANKING
    assert "ranking" not in manifest["cells"][OTHER]  # no cell-scoped policy there
    assert [f["locator"] for f in manifest["cells"][CELL]["facts"]] == ["actor-7", "heal-7"]
    assert (repo / manifest["captures"]["cap"]["receipt"]["path"]).is_file()
    matrix = (repo / "tasks/raid-completion/coverage-matrix.csv").read_text(encoding="utf-8")
    assert matrix.count(",COMPLETE,agent,m") == 2
    assert problems(repo, manifest, records) == []
    assert problems(repo, manifest, records, OTHER) == []


def test_unrelated_shared_edits_do_not_cascade(repo: Path) -> None:
    manifest, records = written(repo)
    zones = repo / "src/necropsy/rules/classic_era/zones"
    guidance = yaml.safe_load((zones / "mc_guidance.yaml").read_text(encoding="utf-8"))
    guidance["strategy"][1]["items"].append({"rule": "c", "text": "druid", "classes": [11]})
    guidance["strategy"][3] = {"source": "s", "items": [{"rule": "d", "text": "new boss"}]}
    (zones / "mc_guidance.yaml").write_text(yaml.safe_dump(guidance), encoding="utf-8")
    facts = json.loads((repo / rb.FACTS).read_text(encoding="utf-8"))
    facts["cases"].append({"id": "actor-99", "report": "Q", "fight": 1, "actor": 1, "sha256": "0"})
    (repo / rb.FACTS).write_text(json.dumps(facts), encoding="utf-8")
    put(repo, "src/necropsy/rules/classic_era/zones/bwl.yaml", "rule: bwl\n")
    assert problems(repo, manifest, records) == []


def test_content_edit_makes_only_that_boss_stale(repo: Path) -> None:
    manifest, records = written(repo)
    zones = repo / "src/necropsy/rules/classic_era/zones"
    guidance = yaml.safe_load((zones / "mc_guidance.yaml").read_text(encoding="utf-8"))
    guidance["strategy"][1]["items"][0]["text"] = "changed"
    (zones / "mc_guidance.yaml").write_text(yaml.safe_dump(guidance), encoding="utf-8")
    assert problems(repo, manifest, records) == [
        "stale content verification: review this boss and configuration again"
    ]
    assert problems(repo, manifest, records, OTHER) == []


def test_engine_edit_makes_the_raid_stale(repo: Path) -> None:
    manifest, records = written(repo)
    (repo / "src/necropsy/engine.py").write_text("VALUE = 2\n", encoding="utf-8")
    assert "stale engine verification: re-attest the batch" in problems(repo, manifest, records)
    put(repo, "src/necropsy/engine.py", "VALUE = 1\n")
    put(repo, "src/necropsy/new_module.py", "X = 1\n")  # untracked package code counts too
    assert "stale engine verification: re-attest the batch" in problems(repo, manifest, records)


def test_missing_or_changed_artifacts_are_refused(repo: Path) -> None:
    manifest, records = written(repo)
    (repo / RANKING).write_text('{"rule": "mc-1-policy", "rows": [1]}\n', encoding="utf-8")
    assert f"missing or changed batch artifact: {RANKING}" in problems(repo, manifest, records)
    receipt = manifest["captures"]["cap"]["receipt"]["path"]
    (repo / receipt).unlink()
    found = problems(repo, manifest, records)
    assert f"missing or changed batch artifact: {receipt}" in found
    assert any(p.startswith("unreadable batch receipt") for p in found)


def test_wrong_identity_is_refused(repo: Path) -> None:
    manifest, records = written(repo)
    wrong = copy.deepcopy(manifest)
    wrong["cells"][CELL]["actor"] = 8
    assert "batch identity differs from the registered actor source" in problems(
        repo, wrong, records
    )
    assert rb.manifest_problems(repo, manifest, "mc/3/6/Holy/hps/Alliance", {}) == [
        "batch manifest does not list the cell"
    ]
    other_source = copy.deepcopy(records)
    other_source[CELL]["real_actor_source"]["fight"] = 9
    assert "batch identity differs from the registered actor source" in problems(
        repo, manifest, other_source
    )
    moved = copy.deepcopy(manifest)
    moved["cells"][CELL]["facts"][0]["digest"] = "0" * 64
    assert "independent fact cases differ from the batch" in problems(repo, moved, records)


def test_receipt_must_show_the_cells_boss_cleanly(repo: Path) -> None:
    data = json.loads((repo / "work/receipt.json").read_text(encoding="utf-8"))
    data["content"]["bosses"]["1"]["strategy"] = {"missing": {"report.html": ["one"]}}
    data["visual"]["report.html"]["summary"] = "5 screens, 1 with findings"
    put(repo, "work/receipt.json", data)
    with pytest.raises(ValueError, match=r"every text of the cell's boss.*visual checks"):
        rb.write(spec(repo), repo)
    assert not (repo / rb.BATCHES).exists()
    records = json.loads((repo / rb.COVERAGE).read_text(encoding="utf-8"))["records"]
    assert {r["status"] for r in records} == {"IN_PROGRESS"}


def test_write_refuses_a_dirty_package_or_a_stale_receipt(repo: Path) -> None:
    put(repo, "src/necropsy/engine.py", "VALUE = 3\n")
    with pytest.raises(ValueError, match="differs from HEAD"):
        rb.write(spec(repo), repo)
    git(repo, "commit", "-qam", "engine change")
    with pytest.raises(ValueError, match="receipt engine differs from HEAD"):
        rb.write(spec(repo), repo)


def test_changed_manifest_bytes_fail_the_register(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import check_raid_coverage as crc

    _, records = written(repo)
    receipt = crc.Receipt.model_validate(records[CELL])
    assert crc.batch_problems(repo, receipt) == []
    path = repo / rb.BATCHES / "b1.json"
    path.write_bytes(path.read_bytes().replace(b'"b1"', b'"b2"'))
    assert crc.batch_problems(repo, receipt) == [
        f"missing or changed evidence: {rb.BATCHES}/b1.json"
    ]
    mixed = receipt.model_copy(
        update={"references": {**receipt.references, "render_review": receipt.references["batch"]}}
    )
    assert crc.batch_problems(repo, mixed) == [
        "a batch completion references exactly one manifest and nothing else"
    ]


def test_a_receipt_from_an_equivalent_earlier_commit_is_reused(repo: Path) -> None:
    put(repo, "src/necropsy/rules/classic_era/zones/bwl.yaml", "rule: bwl\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "another raid's rules")
    manifest, records = written(repo)
    assert manifest["commit"] != manifest["attested_at"] == git(repo, "rev-parse", "HEAD")
    assert problems(repo, manifest, records) == []
