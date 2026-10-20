"""A unit spec writes, pins and registers only its closed cells. Open cells stay
open; registration refuses anything not committed, not verified or not bound to
the registered actor source, before either register changes; a failed
replacement keeps the previous closure."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts import close_unit as cu
from scripts import closure_pins

HEAD = "raid,zone_id,encounter_id,boss,variant,class_id,class,category,metric,faction,"
HEAD += "implementation,mechanics_and_guidance,synthetic_behavior,real_actor_source,"
HEAD += "independent_facts,ranking_reconciliation,render_review,status,owner,notes"
CELLS = ("mc/1/6/Holy/hps/Alliance", "mc/2/6/Holy/hps/Alliance")
FIELDS = {f: {"evidence": [f]} for f in cu.FIELDS}
ARCHIVE = hashlib.sha256(b"archive\n").hexdigest()


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, check=True, text=True)
    return done.stdout.strip()


def commit(root: Path, message: str = "c") -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def row(encounter: str) -> str:
    todo = ",".join(["TODO"] * 7)
    key = f"mc,2000,{encounter},B{encounter},standard,6,Paladin,Holy,hps,Alliance"
    return f"{key},{todo},IN_PROGRESS,agent,"


def source(fight: int, actor: int) -> dict[str, object]:
    return {
        "archive": {"path": "raw.bin", "sha256": ARCHIVE, "locator": "x"},
        "report": "r",
        "fight": fight,
        "actor": actor,
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.invalid")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "config", "core.autocrlf", "false")
    files = {
        "rule.yaml": "rule\n",
        "raw.bin": "archive\n",
        "review.json": "{}\n",
        "facts.json": "{}\n",
        cu.MATRIX: "\n".join([HEAD, row("1"), row("2")]) + "\n",
        cu.COVERAGE: json.dumps(
            {
                "version": 1,
                "records": [
                    {
                        "cell_id": CELLS[0],
                        "status": "IN_PROGRESS",
                        "real_actor_source": source(3, 4),
                    },
                    {
                        "cell_id": CELLS[1],
                        "status": "IN_PROGRESS",
                        "real_actor_source": source(5, 6),
                    },
                ],
            }
        )
        + "\n",
    }
    for path, text in files.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_bytes(text.encode())
    (tmp_path / cu.CLOSURES).mkdir(parents=True)
    commit(tmp_path, "evidence")
    return tmp_path


def spec(second: dict[str, object]) -> dict[str, object]:
    return {
        "unit": "mc/6/Holy/hps/Alliance",
        "archive": {"path": "raw.bin", "report": "r"},
        "evidence_files": ["rule.yaml"],
        "source_review": "review.json",
        "evidence_pinning": "blobs",
        "shared": {"fields": copy.deepcopy(FIELDS), "limitations": ["shared"]},
        "cells": {
            CELLS[0]: {
                "fight": 3,
                "actor": 4,
                "fields": {"render_review": {"evidence": ["cell"]}},
                "limitations": ["cell"],
                "references": {"independent_facts": [["facts.json", "case-1"]]},
                "coverage_note": "closed",
                "matrix_note": "closed",
            },
            CELLS[1]: second,
        },
    }


def registers(root: Path) -> tuple[bytes, bytes]:
    return (root / cu.COVERAGE).read_bytes(), (root / cu.MATRIX).read_bytes()


def test_closed_cells_are_pinned_and_registered_and_open_cells_stay_open(repo: Path) -> None:
    unit = spec({"open": "no class-scoped guidance"})
    assert cu.closures(unit, "HEAD", False, root=repo) == 0
    closure = json.loads((repo / cu.closure_path(CELLS[0])).read_bytes())
    assert closure["commit"] == git(repo, "rev-parse", "HEAD")
    assert closure["archive"]["fight"] == 3
    assert closure["fields"]["render_review"] == {"evidence": ["cell"]}
    assert closure["fields"]["implementation"] == {"evidence": ["implementation"]}
    assert closure["limitations"] == ["shared", "cell"]
    assert not (repo / cu.closure_path(CELLS[1])).exists()
    assert not list((repo / cu.CLOSURES).glob(".*"))
    with pytest.raises(ValueError, match="exists"):
        cu.closures(unit, "HEAD", False, root=repo)
    commit(repo, "closures")
    assert cu.register(unit, root=repo) == 0
    records = {r["cell_id"]: r for r in json.loads((repo / cu.COVERAGE).read_bytes())["records"]}
    closed = records[CELLS[0]]
    assert closed["status"] == "COMPLETE"
    assert [r["path"] for r in closed["references"]["independent_facts"]] == ["facts.json"]
    assert closed["references"]["render_review"][0]["locator"] == "fields.render_review"
    assert records[CELLS[1]]["status"] == "IN_PROGRESS"
    rows = (repo / cu.MATRIX).read_text(encoding="utf-8").splitlines()
    assert ",COMPLETE,agent,closed" in rows[1]
    assert rows[2].endswith(",IN_PROGRESS,agent,")


def test_an_uncommitted_or_hand_edited_closure_is_never_registered(repo: Path) -> None:
    unit = spec({"open": "x"})
    cu.closures(unit, "HEAD", False, root=repo)
    path = repo / cu.closure_path(CELLS[0])
    data = json.loads(path.read_bytes())
    data["commit"] = "not-a-commit"
    path.write_text(json.dumps(data), encoding="utf-8")
    before = registers(repo)
    with pytest.raises(ValueError, match="not committed at HEAD"):
        cu.register(unit, root=repo)
    assert registers(repo) == before
    commit(repo, "bad closure")
    with pytest.raises(ValueError, match=r"mc-1-6-holy-hps-alliance\.json: "):
        cu.register(unit, root=repo)
    assert registers(repo) == before


def test_a_closure_for_another_actor_or_an_uncommitted_reference_is_refused(repo: Path) -> None:
    unit = spec({"open": "x"})
    unit["cells"][CELLS[0]]["fight"] = 9  # type: ignore[index]
    cu.closures(unit, "HEAD", False, root=repo)
    commit(repo, "closure for fight 9")
    before = registers(repo)
    with pytest.raises(ValueError, match="differs from the registered source"):
        cu.register(unit, root=repo)
    assert registers(repo) == before
    unit = spec({"open": "x"})
    cu.closures(unit, "HEAD", True, root=repo)
    commit(repo, "closure for fight 3")
    (repo / "facts.json").write_text('{"edited": true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"facts\.json differs from its HEAD blob"):
        cu.register(unit, root=repo)
    assert registers(repo) == before


def test_a_failed_replacement_keeps_the_previous_closure(repo: Path) -> None:
    unit = spec({"open": "x"})
    cu.closures(unit, "HEAD", False, root=repo)
    path = repo / cu.closure_path(CELLS[0])
    old = path.read_bytes()
    (repo / "rule.yaml").write_text("edited\n", encoding="utf-8")
    with pytest.raises(closure_pins.PinError, match=r"rule\.yaml"):
        cu.closures(unit, "HEAD", True, root=repo)
    assert path.read_bytes() == old
    assert not list((repo / cu.CLOSURES).glob(".*"))


def test_missing_fields_are_refused_before_anything_is_written(repo: Path) -> None:
    unit = spec({"open": "x"})
    del unit["shared"]["fields"]["ranking_reconciliation"]  # type: ignore[index]
    with pytest.raises(ValueError, match="fields missing ranking_reconciliation"):
        cu.closures(unit, "HEAD", False, root=repo)
    assert not list((repo / cu.CLOSURES).iterdir())
