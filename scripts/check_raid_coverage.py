"""Audit durable raid evidence. Inventory exit 0 never means acceptance.

Usage: uv run python scripts/check_raid_coverage.py --inventory
       uv run python scripts/check_raid_coverage.py --require-complete
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.analysis.encounters.strategy import encounter_strategy
from necropsy.raids.scope import CoverageCell, coverage_cells
from necropsy.rules import load_rules
from necropsy.snapshot.archive import (
    ArchiveError,
    VerifiedArchive,
    load_entries_manifest,
    sha256_file,
)
from necropsy.snapshot.model import SnapshotError, StreamStatus
from necropsy.snapshot.v1 import open_snapshot

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "tests/golden/raids/coverage.json"
DIMENSIONS = (
    "implementation",
    "mechanics_and_guidance",
    "synthetic_behavior",
    "independent_facts",
    "ranking_reconciliation",
    "render_review",
)
Status = Literal["TODO", "IN_PROGRESS", "BLOCKED_EVIDENCE", "BLOCKED_REVIEW", "COMPLETE"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Reference(Strict):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    locator: str = Field(min_length=1)


class ActorSource(Strict):
    archive: Reference
    entries: Reference
    provenance: Reference
    report: str = Field(min_length=1)
    fight: int = Field(gt=0)
    actor: int = Field(gt=0)
    partition: int = Field(gt=0)


class Receipt(Strict):
    cell_id: str
    status: Status
    references: dict[str, list[Reference]] = Field(default_factory=dict)
    real_actor_source: ActorSource | None = None
    note: str = ""


class Register(Strict):
    version: Literal[1]
    records: list[Receipt]


def checked_path(root: Path, ref: Reference) -> Path:
    """Receipts refer to portable repository evidence, never developer caches."""
    path = (root / ref.path).resolve()
    if Path(ref.path).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError(f"nonportable evidence path: {ref.path}")
    if any(p in {"tasks", "workspace", ".git"} for p in Path(ref.path).parts):
        raise ValueError(f"disposable evidence path: {ref.path}")
    if not path.is_file() or sha256_file(path) != ref.sha256:
        raise ValueError(f"missing or changed evidence: {ref.path}")
    return path


def actor_problems(root: Path, cell: CoverageCell, source: ActorSource) -> list[str]:
    """Use the strict archive reader; a ranking row or empty ZIP is insufficient."""
    archive_path = checked_path(root, source.archive)
    entries_path = checked_path(root, source.entries)
    checked_path(root, source.provenance)
    cfg = cell.configuration
    if source.partition not in load_rules("classic_era", "raid_scope")["partitions"]:
        return ["actor source uses an unsupported ruleset partition"]
    with VerifiedArchive(
        archive_path,
        expected_sha256=source.archive.sha256,
        entries=load_entries_manifest(entries_path),
    ) as archive:
        reader = open_snapshot(archive)
        descriptor = reader.descriptor()
        if descriptor.mode != "live":
            return ["new raid actor source must retain live acquisition identity"]
        marker = archive.read_json("necropsy-snapshot.json")
        subject = marker["subject"]
        if (
            descriptor.zone.id != cell.zone_id
            or descriptor.zone.partition != source.partition
            or subject["class_id"] != cfg.class_id
            or subject.get("ranking_category") != cfg.category
            or subject.get("ranking_metric", "dps") != cfg.metric
            or subject["faction"] != cfg.faction
        ):
            return ["actor source category/metric/faction/zone differs from cell"]
        fights = [
            f
            for f in descriptor.fights
            if f.report_code == source.report and f.fight_id == source.fight
        ]
        if not fights or not any(
            p.encounter_id == cell.encounter_id for f in fights for p in f.participants
        ):
            return ["actor source has no matching encounter"]
        reports = [r for r in reader.reports() if r.get("code") == source.report]
        if len(reports) != 1 or reports[0].get("visibility") != "public":
            return ["actor source is not a verified public report"]
        actor = next(
            (a for a in reports[0]["masterData"]["actors"] if a["id"] == source.actor), None
        )
        if (
            actor is None
            or actor.get("type") != "Player"
            or actor.get("subType") != CLASS_NAMES[cfg.class_id]
            or not any(
                p.player == actor["name"] and p.spec == cfg.category
                for f in fights
                for p in f.participants
            )
        ):
            return ["actor identity/class/category is not established by selected participants"]
        streams = [
            s
            for s in reader.expected_streams()
            if s.report_code == source.report
            and s.fight_id == source.fight
            and s.actor_id == source.actor
        ]
        if {s.direction.value for s in streams} != {"source", "target"}:
            return ["actor source lacks both actor stream directions"]
        reads = [reader.read_stream(s) for s in streams]
        if any(r.status is not StreamStatus.COMPLETE for r in reads):
            return ["actor source has incomplete streams"]
        if not any(r.events for r in reads):
            return ["actor source is budget-only or empty"]
    return []


def content_problems(cell: CoverageCell) -> list[str]:
    facts = load_rules("classic_era", f"zones/{cell.raid}_facts")
    fact = next((f for f in facts["encounters"] if f["id"] == cell.encounter_id), None)
    problems = []
    if not fact or not fact.get("source"):
        problems.append("no sourced encounter facts")
    strategy = encounter_strategy(
        cell.raid, cell.encounter_id, 1, cell.configuration.class_id, cell.configuration.metric
    )
    if strategy is None or {i.section for i in strategy.items} != {"before", "during", "raid"}:
        problems.append("no boss-specific guidance")
    ranking = load_rules("classic_era", f"zones/{cell.raid}")["ranking_exclusions_rule"]
    if ranking["basis"] == "unvalidated":
        problems.append("ranking policy remains unvalidated")
    return problems


def audit(register: Register, root: Path = ROOT) -> tuple[Counter[str], list[str]]:
    cells = {cell.key: cell for cell in coverage_cells()}
    records: dict[str, Receipt] = {}
    problems = []
    for record in register.records:
        if record.cell_id in records:
            problems.append(f"duplicate cell: {record.cell_id}")
        if record.cell_id not in cells:
            problems.append(f"unknown or illegal cell: {record.cell_id}")
        records[record.cell_id] = record
        unknown = set(record.references) - set(DIMENSIONS)
        if unknown:
            problems.append(f"{record.cell_id}: unknown evidence dimensions {sorted(unknown)}")
        for refs in record.references.values():
            for ref in refs:
                try:
                    checked_path(root, ref)
                except ValueError as exc:
                    problems.append(f"{record.cell_id}: {exc}")
    counts: Counter[str] = Counter()
    for key, cell in cells.items():
        receipt = records.get(key)
        counts[receipt.status if receipt else "TODO"] += 1
        if receipt is None or receipt.status != "COMPLETE":
            continue
        missing = [d for d in DIMENSIONS if not receipt.references.get(d)]
        if missing:
            problems.append(f"{key}: missing completion evidence {', '.join(missing)}")
        problems.extend(f"{key}: {p}" for p in content_problems(cell))
        if receipt.real_actor_source is None:
            problems.append(f"{key}: no usable real actor source")
        else:
            try:
                problems.extend(
                    f"{key}: {p}" for p in actor_problems(root, cell, receipt.real_actor_source)
                )
            except (ValueError, OSError, ArchiveError, SnapshotError) as exc:
                problems.append(f"{key}: invalid actor evidence: {exc}")
    return counts, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inventory", action="store_true")
    mode.add_argument("--require-complete", action="store_true")
    parser.add_argument("--register", type=Path, default=REGISTER)
    args = parser.parse_args()
    register = Register.model_validate_json(args.register.read_text(encoding="utf-8"))
    counts, problems = audit(register)
    print(
        json.dumps(
            {"cells": sum(counts.values()), "statuses": dict(counts), "problems": problems},
            indent=2,
        )
    )
    if problems or (args.require_complete and counts["COMPLETE"] != sum(counts.values())):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
