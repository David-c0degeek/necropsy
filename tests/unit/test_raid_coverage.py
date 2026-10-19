"""Missing or merely asserted evidence cannot close an encounter configuration."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from necropsy.analysis.class_catalog import TALENT_TREES, talent_tree
from necropsy.raids.scope import configurations, coverage_cells
from necropsy.rules import load_rules
from scripts import check_raid_coverage as coverage_check
from scripts.check_raid_coverage import (
    Receipt,
    Reference,
    Register,
    audit,
    checked_path,
    staged_problems,
)


@pytest.mark.parametrize(
    "relative",
    [
        "facts.json",
        "provenance.json",
        "healing-facts.json",
        "coverage.json",
        "raw/mc-holy.entries",
        "raw/mc-holy.sha256",
        "raw/mc-holy-raid/74578049-2000-20261017T175812.entries",
        "raw/mc-holy-raid/74578049-2000-20261017T175812.sha256",
    ],
)
def test_git_preserves_evidence_bytes_including_windows_line_endings(relative: str) -> None:
    root = Path(__file__).parents[2]
    payload = b'{"evidence": "exact bytes"}\r\n'
    command = ["git", "hash-object", "--stdin"]
    original = subprocess.run(command, cwd=root, input=payload, capture_output=True, check=True)
    filtered = subprocess.run(
        [*command, "--path", f"tests/golden/raids/{relative}"],
        cwd=root,
        input=payload,
        capture_output=True,
        check=True,
    )
    assert filtered.stdout == original.stdout, "Git would invalidate a frozen SHA-256 reference"


def test_era_scope_contains_every_legal_configuration_and_variant() -> None:
    cells = coverage_cells()
    configs = configurations()
    assert len(cells) == len({c.key for c in cells}) == 952
    assert len(configs) == 34
    assert len({c.encounter_id for c in cells}) == 28
    assert len({(c.class_id, c.category) for c in configs}) == 19
    assert {c.variant for c in cells if c.encounter_id == 50631} == {"combined"}
    assert not any(c.class_id == 6 and c.faction == "Horde" for c in configs)
    assert not any(c.class_id == 9 and c.faction == "Alliance" for c in configs)
    assert {(c.category, c.metric) for c in configs if c.class_id == 2} == {
        ("Balance", "dps"),
        ("Balance", "hps"),
        ("Feral", "dps"),
        ("Guardian", "dps"),
        ("Restoration", "hps"),
    }
    assert sum(len(trees) for trees in TALENT_TREES.values()) == 27
    for class_id, trees in TALENT_TREES.items():
        assert all(talent_tree(class_id, tree) == tree for tree in trees)


def test_inventory_preserves_every_missing_obligation() -> None:
    counts, errors = audit(Register(version=1, records=[]))
    assert counts == {"TODO": 952}
    assert errors == []


@pytest.mark.parametrize("content_available", [True, False])
def test_forged_complete_status_requires_content_and_real_independent_evidence(
    monkeypatch: pytest.MonkeyPatch, content_available: bool
) -> None:
    if not content_available:
        original_load = load_rules

        def missing_facts(game: str, name: str) -> dict[str, Any]:
            return {"encounters": []} if name.endswith("_facts") else original_load(game, name)

        monkeypatch.setattr(coverage_check, "load_rules", missing_facts)
        monkeypatch.setattr(coverage_check, "encounter_strategy", lambda *_args: None)
    cell = coverage_cells()[0]
    counts, errors = audit(
        Register(version=1, records=[Receipt(cell_id=cell.key, status="COMPLETE")])
    )
    assert counts == {"TODO": 951, "COMPLETE": 1}
    assert any("missing completion evidence" in e for e in errors)
    assert any("no usable real actor source" in e for e in errors)
    assert any("no sourced encounter facts" in e for e in errors) is (not content_available)
    assert any("no boss-specific guidance" in e for e in errors) is (not content_available)
    assert any("ranking policy remains unvalidated" in e for e in errors)


PILOT = "mc/50668/6/Holy/hps/Alliance"


def _cell(key: str) -> Any:
    return {c.key: c for c in coverage_cells()}[key]


def test_scoped_hps_policy_validates_only_its_exact_cell() -> None:
    assert coverage_check.ranking_problem(_cell(PILOT)) is None
    for key in (
        "mc/50668/7/Holy/hps/Alliance",
        "mc/50663/6/Holy/hps/Alliance",
        "mc/50668/6/Protection/dps/Alliance",
        "mc/50668/7/Holy/hps/Horde",
        "bwl/50610/6/Holy/hps/Alliance",
    ):
        assert coverage_check.ranking_problem(_cell(key)) == "ranking policy remains unvalidated"
    zone = load_rules("classic_era", "zones/mc")
    assert zone["ranking_exclusions_rule"]["basis"] == "unvalidated"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(basis="validated"),
        lambda p: p.update(basis="unvalidated"),
        lambda p: p.update(conditions=p["conditions"][:-1]),
        lambda p: p.update(conditions=[*p["conditions"], p["conditions"][0]]),
        lambda p: p.update(conditions=[*p["conditions"][:-1], "anything-goes"]),
        lambda p: p.update(extra="field"),
        lambda p: p.pop("evidence"),
        lambda p: p.update(validated=" "),
        lambda p: p["scope"].update(encounter_id="50668"),
        lambda p: p["scope"].pop("faction"),
    ],
)
def test_malformed_or_unvalidated_policy_never_skips_the_ranking_problem(
    monkeypatch: pytest.MonkeyPatch, mutate: Any
) -> None:
    original_load = load_rules

    def mutated(game: str, name: str) -> dict[str, Any]:
        data = original_load(game, name)
        if name != "zones/mc":
            return data
        data = {**data, "ranking_metric_policies": [dict(data["ranking_metric_policies"][0])]}
        policy = data["ranking_metric_policies"][0]
        policy["scope"] = dict(policy["scope"])
        policy["conditions"] = list(policy["conditions"])
        mutate(policy)
        return data

    monkeypatch.setattr(coverage_check, "load_rules", mutated)
    problem = coverage_check.ranking_problem(_cell(PILOT))
    assert problem is not None and problem.startswith("malformed ranking metric policy")


def test_duplicate_unknown_or_illegal_cells_are_rejected() -> None:
    first = Receipt(cell_id=coverage_cells()[0].key, status="IN_PROGRESS")
    invalid = Receipt(cell_id="mc/50663/6/Holy/hps/Horde", status="BLOCKED_EVIDENCE")
    _, errors = audit(Register(version=1, records=[first, first, invalid]))
    assert any("duplicate cell" in e for e in errors)
    assert any("unknown or illegal cell" in e for e in errors)


def test_evidence_shortage_cannot_be_renamed_not_applicable() -> None:
    with pytest.raises(ValidationError):
        Receipt.model_validate({"cell_id": coverage_cells()[0].key, "status": "NOT_APPLICABLE"})


def test_evidence_references_bind_actual_portable_bytes(tmp_path: Path) -> None:
    fixture = tmp_path / "facts.json"
    fixture.write_text('{"amount": 42}', encoding="utf-8")
    ref = Reference(
        path="facts.json", sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(), locator="amount"
    )
    assert checked_path(tmp_path, ref) == fixture
    fixture.write_text('{"amount": 43}', encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        checked_path(tmp_path, ref)
    for path in ("../outside.json", "workspace/facts.json", "tasks/facts.json"):
        with pytest.raises(ValueError):
            checked_path(tmp_path, ref.model_copy(update={"path": path}))


def test_pass_label_is_not_an_evidence_reference() -> None:
    with pytest.raises(ValidationError):
        Receipt.model_validate(
            {
                "cell_id": coverage_cells()[0].key,
                "status": "COMPLETE",
                "references": {"implementation": ["PASS"]},
            }
        )


@pytest.mark.parametrize(
    "scenario,valid",
    [
        ("normalized-metadata", False),
        ("exact-metadata", True),
        ("unstaged-metadata", False),
        ("changed-metadata", False),
        ("lfs", True),
        ("lfs-wrong-digest", False),
        ("lfs-wrong-size", False),
        ("lfs-malformed", False),
    ],
)
def test_staged_receipts_check_git_transformations_and_lfs_identity(
    tmp_path: Path, scenario: str, valid: bool
) -> None:
    def git(*args: str, data: bytes | None = None) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=tmp_path, input=data, capture_output=True, check=True
        ).stdout

    git("init", "-q")
    payload = b'{"amount":42}\r\n'
    attributes = b"* text=auto eol=lf\n"
    if scenario == "exact-metadata":
        attributes += b"evidence.json -text\n"
    (tmp_path / ".gitattributes").write_bytes(attributes)
    filename = "evidence.json"
    if scenario.startswith("lfs"):
        filename = "capture.zip"
        payload = b"PK synthetic archive bytes"
        digest = hashlib.sha256(payload).hexdigest()
        oid = "0" * 64 if scenario == "lfs-wrong-digest" else digest
        size = len(payload) + (1 if scenario == "lfs-wrong-size" else 0)
        pointer = (
            f"version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {size}\n"
        ).encode()
        if scenario == "lfs-malformed":
            pointer = b"version https://git-lfs.github.com/spec/v1\n"
        blob_id = git("hash-object", "-w", "--stdin", data=pointer).decode().strip()
        git("update-index", "--add", "--cacheinfo", "100644", blob_id, filename)
        (tmp_path / filename).write_bytes(payload)
    else:
        (tmp_path / filename).write_bytes(payload)
        if scenario != "unstaged-metadata":
            git("-c", "core.safecrlf=false", "add", "--", filename)
        if scenario == "changed-metadata":
            payload = b'{"amount":43}\r\n'
            (tmp_path / filename).write_bytes(payload)
    ref = Reference(path=filename, sha256=hashlib.sha256(payload).hexdigest(), locator="bytes")
    register = Register(
        version=1,
        records=[
            Receipt(cell_id="test", status="IN_PROGRESS", references={"independent_facts": [ref]})
        ],
    )
    problems = staged_problems(register, tmp_path)
    assert (not problems) is valid, problems
