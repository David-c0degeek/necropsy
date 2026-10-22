"""Frozen drafts cannot silently lose coverage or broaden proposed applicability."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import check_guidance_proposal as checker

BUNDLE = "tasks/naxx-completion/research/coordinator-guidance-drafts.json"


@pytest.fixture
def prepared(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    bundle = json.loads((checker.ROOT / BUNDLE).read_bytes())
    for name in (bundle["source_path"], bundle["proposed_yaml_path"]):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((checker.ROOT / name).read_bytes())
    proposal = yaml.safe_load((tmp_path / bundle["proposed_yaml_path"]).read_bytes())
    return tmp_path, bundle, proposal


def save(root: Path, bundle: dict[str, Any], proposal: dict[str, Any]) -> Path:
    raw = yaml.safe_dump(proposal, sort_keys=False, allow_unicode=True).encode()
    (root / bundle["proposed_yaml_path"]).write_bytes(raw)
    bundle["proposed_yaml_sha256"] = hashlib.sha256(raw).hexdigest()
    path = root / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path


def test_real_proposal_replays_without_any_writes() -> None:
    inputs = [checker.ROOT / BUNDLE]
    bundle = json.loads(inputs[0].read_bytes())
    inputs.extend(checker.ROOT / bundle[k] for k in ("source_path", "proposed_yaml_path"))
    before = [p.read_bytes() for p in inputs]
    assert checker.check(inputs[0]) == {
        "drafts": 510,
        "bosses": 15,
        "withheld_profiles": 2,
        "content_review": "pending",
        "model_calls": 0,
        "writes": 0,
    }
    assert [p.read_bytes() for p in inputs] == before


@pytest.mark.parametrize(
    "mutation",
    ["missing", "duplicate", "illegal-faction", "source-pin", "digest", "unknown-applicability"],
)
def test_recipe_mutations_are_refused(
    prepared: tuple[Path, dict[str, Any], dict[str, Any]], mutation: str
) -> None:
    root, bundle, proposal = prepared
    first = bundle["recipes"][0]
    if mutation == "missing":
        bundle["recipes"].pop()
    elif mutation == "duplicate":
        bundle["recipes"][-1] = first
    elif mutation == "illegal-faction":
        paladin = next(r for r in bundle["recipes"] if r["order"]["class_id"] == 6)
        paladin["order"]["faction"] = "Horde"
    elif mutation == "source-pin":
        first["order"]["input"]["sha256"] = "0" * 64
    elif mutation == "digest":
        first["draft_sha256"] = "0" * 64
    else:
        bundle["profiles"]["51118"][0]["applies"] = "everyone"
    with pytest.raises(ValueError):
        checker.check(save(root, bundle, proposal), root)


@pytest.mark.parametrize(
    "mutation", ["class", "metric", "section", "text", "extra-item", "missing-boss", "tank-leak"]
)
def test_repinned_projection_mutations_are_refused(
    prepared: tuple[Path, dict[str, Any], dict[str, Any]], mutation: str
) -> None:
    root, bundle, proposal = prepared
    entry = proposal["strategy"][51118]
    row = entry["items"][0]
    if mutation == "class":
        row["classes"].append(3)
    elif mutation == "metric":
        row = next(r for r in entry["items"] if r["metrics"] == ["hps"])
        row["metrics"].append("dps")
    elif mutation == "section":
        row["section"] = "during"
    elif mutation == "text":
        row["text"] += " Every player missed a cooldown."
    elif mutation == "extra-item":
        entry["items"].append(dict(row, rule="patchwerk-invented-v1"))
    elif mutation == "missing-boss":
        proposal["strategy"].pop(51121)
    else:
        profile = next(p for p in bundle["profiles"]["51118"] if p["applies"] == "tank-category")
        entry["items"].append(
            {
                "rule": "patchwerk-druid-hateful-tank-loadout-v1",
                "section": "before",
                "classes": [2],
                "metrics": ["dps"],
                "text": profile["text"],
                "support": profile["support"],
            }
        )
    with pytest.raises(ValueError, match="proposed integration differs"):
        checker.check(save(root, bundle, proposal), root)


def test_duplicate_yaml_and_json_keys_are_refused(
    prepared: tuple[Path, dict[str, Any], dict[str, Any]],
) -> None:
    root, bundle, proposal = prepared
    path = save(root, bundle, proposal)
    yaml_path = root / bundle["proposed_yaml_path"]
    raw = yaml_path.read_bytes() + b"strategy: {}\n"
    yaml_path.write_bytes(raw)
    bundle["proposed_yaml_sha256"] = hashlib.sha256(raw).hexdigest()
    path.write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate YAML key"):
        checker.check(path, root)
    path.write_text('{"recipes": [], "recipes": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        checker.check(path, root)


def test_input_escape_is_refused(prepared: tuple[Path, dict[str, Any], dict[str, Any]]) -> None:
    root, bundle, proposal = prepared
    bundle["source_path"] = "../outside.json"
    with pytest.raises(ValueError, match="escapes"):
        checker.check(save(root, bundle, proposal), root)
