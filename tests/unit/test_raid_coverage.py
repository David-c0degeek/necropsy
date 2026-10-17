"""Missing or merely asserted evidence cannot close an encounter configuration."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from necropsy.analysis.class_catalog import TALENT_TREES, talent_tree
from necropsy.raids.scope import configurations, coverage_cells
from scripts.check_raid_coverage import Receipt, Reference, Register, audit, checked_path


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


def test_forged_complete_status_requires_content_and_real_independent_evidence() -> None:
    cell = coverage_cells()[0]
    counts, errors = audit(Register(version=1, records=[Receipt(key=cell.key, status="COMPLETE")]))
    assert counts == {"TODO": 951, "COMPLETE": 1}
    assert any("missing completion evidence" in e for e in errors)
    assert any("no usable real actor source" in e for e in errors)
    assert any("no sourced encounter facts" in e for e in errors)
    assert any("no boss-specific guidance" in e for e in errors)


def test_duplicate_unknown_or_illegal_cells_are_rejected() -> None:
    first = Receipt(key=coverage_cells()[0].key, status="IN_PROGRESS")
    invalid = Receipt(key="mc/50663/6/Holy/hps/Horde", status="BLOCKED_EVIDENCE")
    _, errors = audit(Register(version=1, records=[first, first, invalid]))
    assert any("duplicate cell" in e for e in errors)
    assert any("unknown or illegal cell" in e for e in errors)


def test_evidence_shortage_cannot_be_renamed_not_applicable() -> None:
    with pytest.raises(ValidationError):
        Receipt.model_validate({"key": coverage_cells()[0].key, "status": "NOT_APPLICABLE"})


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
                "key": coverage_cells()[0].key,
                "status": "COMPLETE",
                "references": {"implementation": ["PASS"]},
            }
        )
