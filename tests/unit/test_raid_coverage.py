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
        "batches/mc-healers-1.json",
        "receipts/mc-healers-1-priest.json",
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
    assert len(cells) == len({c.key for c in cells}) == 1462
    assert len(configs) == 34
    assert len({c.encounter_id for c in cells}) == 43
    by_raid = {raid: [c for c in cells if c.raid == raid] for raid in {c.raid for c in cells}}
    assert {raid: len(rows) for raid, rows in by_raid.items()} == {
        "aq40": 306,
        "bwl": 306,
        "mc": 340,
        "naxxramas": 510,
    }
    assert {c.zone_id for c in by_raid["naxxramas"]} == {2006}
    assert len({c.encounter_id for c in by_raid["naxxramas"]}) == 15
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
    assert counts == {"TODO": 1462}
    assert errors == []


# Naxx bosses whose Balance Druid Alliance DPS cell has a scoped ranking policy.
NAXX_BALANCE_DPS_POLICY_ENCOUNTERS = (51109, 51111, 51114, 51116, 51117, 51119, 51120, 51121)


def test_a_raid_wide_ranking_rule_never_reconciles_a_cell() -> None:
    """Naxxramas's empirical exclusion rule does not stand in for a cell policy."""
    naxx = [c for c in coverage_cells() if c.raid == "naxxramas"]
    assert load_rules("classic_era", "zones/naxxramas")["ranking_exclusions_rule"]["basis"] == (
        "empirical"
    )
    scoped = {f"naxxramas/{e}/2/Balance/dps/Alliance" for e in NAXX_BALANCE_DPS_POLICY_ENCOUNTERS}
    assert {coverage_check.ranking_problem(c) for c in naxx if c.key not in scoped} == {
        "ranking policy remains unvalidated"
    }


def test_content_audit_passes_the_exact_cell_category_to_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from necropsy.analysis.encounters import strategy as strategy_module

    def with_tank_strategy(game: str, name: str) -> dict[str, Any]:
        if name != "zones/naxxramas_guidance":
            return load_rules(game, name)
        return {
            "strategy": {
                51118: {
                    "source": "https://example.test/patchwerk",
                    "retrieved": "2026-10-22",
                    "items": [
                        {
                            "rule": f"patchwerk-guardian-{section}-v1",
                            "section": section,
                            "classes": [2],
                            "metrics": ["dps"],
                            "categories": ["Guardian"],
                            "text": "Confirm the raid assignment.",
                        }
                        for section in ("before", "during", "raid")
                    ],
                }
            }
        }

    monkeypatch.setattr(strategy_module, "load_rules", with_tank_strategy)
    cells = [
        c
        for c in coverage_cells()
        if c.raid == "naxxramas"
        and c.encounter_id == 51118
        and c.configuration.class_id == 2
        and c.configuration.metric == "dps"
    ]
    for cell in cells:
        problems = coverage_check.content_problems(cell)
        assert ("no boss-specific guidance" in problems) is (
            cell.configuration.category != "Guardian"
        )
        assert "ranking policy remains unvalidated" in problems


def test_raid_scoped_audit_skips_other_raids_but_not_unknown_cells() -> None:
    mc = next(c for c in coverage_cells() if c.raid == "mc")
    records = [
        Receipt(cell_id=mc.key, status="COMPLETE"),
        Receipt(cell_id="naxxramas/99999/1/Fury/dps/Horde", status="TODO"),
    ]
    counts, errors = audit(Register(version=1, records=records), raid="naxxramas")
    assert counts == {"TODO": 510}
    assert errors == ["unknown or illegal cell: naxxramas/99999/1/Fury/dps/Horde"]
    counts, errors = audit(Register(version=1, records=records[:1]), raid="mc")
    assert counts == {"TODO": 339, "COMPLETE": 1}
    assert any(e.startswith(f"{mc.key}: missing completion evidence") for e in errors)


@pytest.mark.parametrize("content_available", [True, False])
def test_forged_complete_status_requires_content_and_real_independent_evidence(
    monkeypatch: pytest.MonkeyPatch, content_available: bool
) -> None:
    if not content_available:
        original_load = load_rules

        def missing_facts(game: str, name: str) -> dict[str, Any]:
            return {"encounters": []} if name.endswith("_facts") else original_load(game, name)

        monkeypatch.setattr(coverage_check, "load_rules", missing_facts)
        monkeypatch.setattr(coverage_check, "encounter_strategy", lambda *_args, **_kwargs: None)
    cell = coverage_cells()[0]
    counts, errors = audit(
        Register(version=1, records=[Receipt(cell_id=cell.key, status="COMPLETE")])
    )
    assert counts == {"TODO": 1461, "COMPLETE": 1}
    assert any("missing completion evidence" in e for e in errors)
    assert any("no usable real actor source" in e for e in errors)
    assert any("no sourced encounter facts" in e for e in errors) is (not content_available)
    assert any("no boss-specific guidance" in e for e in errors) is (not content_available)
    assert any("ranking policy remains unvalidated" in e for e in errors)


PILOT = "mc/50668/6/Holy/hps/Alliance"
DPS_CELL = "naxxramas/{}/2/Balance/dps/Alliance"


def _cell(key: str) -> Any:
    return {c.key: c for c in coverage_cells()}[key]


def test_scoped_hps_policy_validates_only_its_exact_cell() -> None:
    assert coverage_check.ranking_problem(_cell(PILOT)) is None
    assert coverage_check.ranking_problem(_cell("mc/50663/6/Holy/hps/Alliance")) is None
    for key in (
        "mc/50664/7/Holy/hps/Alliance",
        "mc/50672/6/Holy/hps/Alliance",
        "mc/50668/6/Protection/dps/Alliance",
        "mc/50668/7/Holy/hps/Horde",
        "bwl/50610/6/Holy/hps/Alliance",
    ):
        assert coverage_check.ranking_problem(_cell(key)) == "ranking policy remains unvalidated"
    zone = load_rules("classic_era", "zones/mc")
    assert zone["ranking_exclusions_rule"]["basis"] == "unvalidated"


def test_scoped_dps_policy_validates_only_its_exact_cell() -> None:
    for encounter in NAXX_BALANCE_DPS_POLICY_ENCOUNTERS:
        assert coverage_check.ranking_problem(_cell(DPS_CELL.format(encounter))) is None
    for key in (
        "naxxramas/51109/2/Balance/dps/Horde",
        "naxxramas/51109/2/Feral/dps/Alliance",
        "naxxramas/51109/2/Balance/hps/Alliance",
        "naxxramas/51108/2/Balance/dps/Alliance",  # Gluth: exclusions untested, stays open
        "naxxramas/51118/2/Balance/dps/Alliance",  # Patchwerk: no admitted row
    ):
        assert coverage_check.ranking_problem(_cell(key)) == "ranking policy remains unvalidated"


def _with_zone(monkeypatch: pytest.MonkeyPatch, zone_name: str, change: Any) -> None:
    original_load = load_rules

    def mutated(game: str, name: str) -> dict[str, Any]:
        data = original_load(game, name)
        if name != zone_name:
            return data
        data = {
            **data,
            "encounters": [dict(e) for e in data["encounters"]],
            "ranking_metric_policies": [
                {**p, "scope": dict(p["scope"]), "conditions": list(p["conditions"])}
                for p in data["ranking_metric_policies"]
            ],
        }
        change(data)
        return data

    monkeypatch.setattr(coverage_check, "load_rules", mutated)


def test_an_added_production_exclusion_reopens_an_untested_dps_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def add_exclusion(data: dict[str, Any]) -> None:
        gothik = next(e for e in data["encounters"] if e["id"] == 51109)
        gothik["ranking_exclusions"] = [{"game_id": 16124, "name": "Unrelenting Trainee"}]

    _with_zone(monkeypatch, "zones/naxxramas", add_exclusion)
    problem = coverage_check.ranking_problem(_cell(DPS_CELL.format(51109)))
    assert problem is not None and "production ranking exclusions" in problem
    assert coverage_check.ranking_problem(_cell(DPS_CELL.format(51111))) is None


@pytest.mark.parametrize(
    ("zone_name", "key", "change"),
    [
        # A DPS policy may not borrow the healing condition set, nor HPS the damage set.
        (
            "zones/naxxramas",
            "naxxramas/51109/2/Balance/dps/Alliance",
            lambda p: p.update(conditions=sorted(coverage_check.POLICY_CONDITIONS["hps"])),
        ),
        (
            "zones/mc",
            PILOT,
            lambda p: p.update(conditions=sorted(coverage_check.POLICY_CONDITIONS["dps"])),
        ),
        (
            "zones/naxxramas",
            "naxxramas/51109/2/Balance/dps/Alliance",
            lambda p: p.update(conditions=p["conditions"][:-1]),
        ),
        ("zones/mc", PILOT, lambda p: p["scope"].update(metric="tps")),
    ],
)
def test_conditions_are_exactly_the_set_for_the_policy_metric(
    monkeypatch: pytest.MonkeyPatch, zone_name: str, key: str, change: Any
) -> None:
    def mutate_first(data: dict[str, Any]) -> None:
        change(data["ranking_metric_policies"][0])

    _with_zone(monkeypatch, zone_name, mutate_first)
    problem = coverage_check.ranking_problem(_cell(key))
    assert problem is not None and problem.startswith("malformed ranking metric policy")


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


def test_strict_opens_are_reused_per_proven_bytes_and_closed_on_eviction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []

    class Archive:
        def __init__(self, path: Path, **_: object) -> None:
            self.name = path.name

        def __enter__(self) -> Archive:
            events.append(f"open {self.name}")
            return self

        def __exit__(self, *_: object) -> None:
            events.append(f"close {self.name}")

    def prove(archive: Archive) -> str:
        if archive.name == "bad.zip":
            raise ValueError("incomplete stream")
        return f"reader {archive.name}"

    monkeypatch.setattr(coverage_check, "VerifiedArchive", Archive)
    monkeypatch.setattr(coverage_check, "open_snapshot", prove)
    monkeypatch.setattr(coverage_check, "load_entries_manifest", lambda path: None)
    monkeypatch.setattr(coverage_check, "_OPEN", {})
    entries = tmp_path / "e.entries"
    entries.write_text("a\n", encoding="utf-8")
    first = coverage_check._opened(tmp_path / "a.zip", "1" * 64, entries)
    assert coverage_check._opened(tmp_path / "a.zip", "1" * 64, entries) is first
    coverage_check._opened(tmp_path / "b.zip", "2" * 64, entries)
    coverage_check._opened(tmp_path / "c.zip", "3" * 64, entries)
    assert events == ["open a.zip", "open b.zip", "open c.zip", "close a.zip"]
    entries.write_text("changed\n", encoding="utf-8")
    coverage_check._opened(tmp_path / "c.zip", "3" * 64, entries)
    assert events[-2:] == ["open c.zip", "close b.zip"]
    with pytest.raises(ValueError, match="incomplete stream"):
        coverage_check._opened(tmp_path / "bad.zip", "4" * 64, entries)
    assert events[-2:] == ["open bad.zip", "close bad.zip"]
