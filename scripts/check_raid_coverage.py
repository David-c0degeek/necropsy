"""Audit durable raid evidence. Inventory exit 0 never means acceptance.

Usage: uv run python scripts/check_raid_coverage.py --inventory
       uv run python scripts/check_raid_coverage.py --require-complete
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
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
from necropsy.snapshot.v0 import V0Snapshot
from necropsy.snapshot.v1 import open_snapshot

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # run as a script: make the sibling tools importable
    sys.path.insert(0, str(ROOT))

from scripts.raid_batch import manifest_problems  # noqa: E402

REGISTER = ROOT / "tests/golden/raids/coverage.json"
DIMENSIONS = (
    "implementation",
    "mechanics_and_guidance",
    "synthetic_behavior",
    "independent_facts",
    "ranking_reconciliation",
    "render_review",
)
# A layer-based completion (D036) references one batch manifest instead of the
# six per-cell dimensions; scripts/raid_batch.py documents the layers.
BATCH = "batch"
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


_OPEN: dict[tuple[str, str, str], tuple[VerifiedArchive, V0Snapshot]] = {}
_OPEN_LIMIT = 2


def _opened(
    archive_path: Path, sha256: str, entries_path: Path
) -> tuple[VerifiedArchive, V0Snapshot]:
    """One strict open and stream proof per archive and manifest, reused in-process.

    Opening proves every encounter stream of the whole archive (seconds per call),
    and the proof depends only on the verified archive and manifest bytes. Each
    call still re-hashes both files in `checked_path` before it gets here, so the
    key names exactly the bytes that were proven. A few archives stay open; the
    oldest is closed when another is opened.
    """
    key = (str(archive_path), sha256, sha256_file(entries_path))
    if key not in _OPEN:
        archive = VerifiedArchive(
            archive_path, expected_sha256=sha256, entries=load_entries_manifest(entries_path)
        )
        archive.__enter__()
        try:
            reader = open_snapshot(archive)
        except BaseException:
            archive.__exit__(None, None, None)
            raise
        while len(_OPEN) >= _OPEN_LIMIT:
            old, _ = _OPEN.pop(next(iter(_OPEN)))
            old.__exit__(None, None, None)
        _OPEN[key] = (archive, reader)
    return _OPEN[key]


def actor_problems(root: Path, cell: CoverageCell, source: ActorSource) -> list[str]:
    """Use the strict archive reader; a ranking row or empty ZIP is insufficient."""
    archive_path = checked_path(root, source.archive)
    entries_path = checked_path(root, source.entries)
    checked_path(root, source.provenance)
    cfg = cell.configuration
    if source.partition not in load_rules("classic_era", "raid_scope")["partitions"]:
        return ["actor source uses an unsupported ruleset partition"]
    archive, reader = _opened(archive_path, source.archive.sha256, entries_path)
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
    actor = next((a for a in reports[0]["masterData"]["actors"] if a["id"] == source.actor), None)
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
    problem = ranking_problem(cell)
    if problem:
        problems.append(problem)
    return problems


VALIDATED_BASES = frozenset({"empirical"})
POLICY_CONDITIONS = frozenset(
    {
        "unique-name-realm-identity",
        "complete-source-target-streams",
        "owned-unit-listing-present",
        "friendly-recipients-only",
        "ranking-duration-equals-fight-duration",
    }
)
POLICY_FIELDS = frozenset(
    {"rule", "basis", "scope", "formula", "conditions", "bound", "validated", "evidence"}
)


def _policy_scope(policy: object) -> tuple[int, int, str, str, str]:
    """A metric policy's exact cell scope; anything malformed is refused."""
    if not isinstance(policy, dict) or set(policy) != POLICY_FIELDS:
        raise ValueError("ranking metric policy fields are incomplete or unknown")
    if policy["basis"] not in VALIDATED_BASES:
        raise ValueError(f"{policy['rule']}: basis {policy['basis']!r} is not validated")
    conditions = policy["conditions"]
    if not isinstance(conditions, list) or set(conditions) != POLICY_CONDITIONS:
        raise ValueError(f"{policy['rule']}: conditions must be exactly the declared set")
    if len(conditions) != len(POLICY_CONDITIONS):
        raise ValueError(f"{policy['rule']}: duplicated condition")
    for field in ("rule", "formula", "bound", "validated", "evidence"):
        if not isinstance(policy[field], str) or not policy[field].strip():
            raise ValueError(f"ranking metric policy needs {field}")
    scope = policy["scope"]
    keys = ("encounter_id", "class_id", "category", "metric", "faction")
    if not isinstance(scope, dict) or set(scope) != set(keys):
        raise ValueError(f"{policy['rule']}: scope must name exactly {', '.join(keys)}")
    if type(scope["encounter_id"]) is not int or type(scope["class_id"]) is not int:
        raise ValueError(f"{policy['rule']}: scope IDs must be integers")
    if not all(isinstance(scope[k], str) for k in keys[2:]):
        raise ValueError(f"{policy['rule']}: scope names must be strings")
    return (
        scope["encounter_id"],
        scope["class_id"],
        scope["category"],
        scope["metric"],
        scope["faction"],
    )


def ranking_problem(cell: CoverageCell) -> str | None:
    """A cell-scoped metric policy, else the raid's damage rule, must be validated."""
    zone = load_rules("classic_era", f"zones/{cell.raid}")
    config = cell.configuration
    key = (cell.encounter_id, config.class_id, config.category, config.metric, config.faction)
    for policy in zone.get("ranking_metric_policies") or ():
        try:
            scope = _policy_scope(policy)
        except ValueError as exc:
            return f"malformed ranking metric policy: {exc}"
        if scope == key:
            return None
    if zone["ranking_exclusions_rule"]["basis"] not in VALIDATED_BASES:
        return "ranking policy remains unvalidated"
    return None


def batch_problems(root: Path, receipt: Receipt) -> list[str]:
    """One batch reference, naming this cell, whose layers all verify now."""
    refs = receipt.references[BATCH]
    if len(refs) != 1 or len(receipt.references) != 1:
        return ["a batch completion references exactly one manifest and nothing else"]
    if refs[0].locator != receipt.cell_id:
        return ["batch reference names another cell"]
    if receipt.real_actor_source is None:
        return []  # reported by the caller
    try:
        manifest = json.loads(checked_path(root, refs[0]).read_text(encoding="utf-8"))
    except ValueError as exc:
        return [str(exc)]
    return manifest_problems(
        root, manifest, receipt.cell_id, receipt.real_actor_source.model_dump()
    )


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
        unknown = set(record.references) - {*DIMENSIONS, BATCH}
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
        if BATCH in receipt.references:
            problems.extend(f"{key}: {p}" for p in batch_problems(root, receipt))
        else:
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


def _batch_artifacts(root: Path, ref: Reference) -> list[Reference]:
    try:
        manifest = json.loads(checked_path(root, ref).read_text(encoding="utf-8"))
    except ValueError, OSError:
        return []  # the audit reports an unusable manifest
    return [
        Reference(path=path, sha256=digest, locator=f"{ref.path}#artifacts")
        for path, digest in (manifest.get("artifacts") or {}).items()
    ]


def staged_problems(register: Register, root: Path = ROOT) -> list[str]:
    """Working-tree hashes must also identify the bytes a fresh checkout receives."""
    references = {}
    for receipt in register.records:
        source = receipt.real_actor_source
        refs = [source.archive, source.entries, source.provenance] if source else []
        refs.extend(ref for values in receipt.references.values() for ref in values)
        for ref in receipt.references.get(BATCH, ()):
            refs.extend(_batch_artifacts(root, ref))
        for ref in refs:
            references[ref.path, ref.sha256] = ref
    problems = []
    for ref in references.values():
        try:
            path = checked_path(root, ref)
            result = subprocess.run(
                ["git", "show", f":{ref.path}"], cwd=root, capture_output=True, check=False
            )
            if result.returncode:
                problems.append(f"{ref.path}: evidence is not staged in Git")
                continue
            blob = result.stdout
            digest = hashlib.sha256(blob).hexdigest()
            if path.suffix == ".zip" and blob.startswith(b"version https://git-lfs.github.com/"):
                pointer = re.fullmatch(
                    rb"version https://git-lfs.github.com/spec/v1\r?\n"
                    rb"oid sha256:([0-9a-f]{64})\r?\nsize ([0-9]+)\r?\n?",
                    blob,
                )
                if pointer is None:
                    problems.append(f"{ref.path}: malformed staged LFS pointer")
                    continue
                digest = pointer[1].decode("ascii")
                if int(pointer[2]) != path.stat().st_size:
                    problems.append(f"{ref.path}: staged LFS size differs from evidence")
            if digest != ref.sha256:
                problems.append(f"{ref.path}: staged evidence differs from receipt hash")
        except (ValueError, OSError) as exc:
            problems.append(f"{ref.path}: cannot verify staged evidence: {exc}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inventory", action="store_true")
    mode.add_argument("--require-complete", action="store_true")
    parser.add_argument("--register", type=Path, default=REGISTER)
    parser.add_argument(
        "--staged", action="store_true", help="also verify receipt hashes against staged Git bytes"
    )
    args = parser.parse_args()
    register = Register.model_validate_json(args.register.read_text(encoding="utf-8"))
    counts, problems = audit(register)
    if args.staged:
        problems.extend(staged_problems(register))
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
