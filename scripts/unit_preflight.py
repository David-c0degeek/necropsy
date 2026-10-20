"""List what each cell of one capture unit still needs, before any work starts.

Usage: uv run python scripts/unit_preflight.py mc 6 Holy hps Alliance [--register PATH]

A capture unit is one configuration (class, category, metric, faction) in one
raid; one capture covers all of its bosses. For every cell of the unit this
reports each completion dimension as `referenced` (evidence is registered),
`missing` (nothing registered yet) or a named problem. Content checks reuse
`check_raid_coverage`: a missing sourced facts entry, missing boss guidance and
an unvalidated or malformed ranking policy are reported separately. The real
actor source is `missing` when none is registered and `unusable: ...` when the
registered archive fails the strict reader. `class_scoped_rules` counts the boss
strategy items and removal policies written for this class and metric, and the
boss presence rules; zeros mean only generic boss content applies, which the
contract does not accept as class coverage.

This is a work list, never acceptance. `referenced` means evidence exists, not
that it was reviewed; a capture-ready or fully referenced cell is not COMPLETE.
Exit 0 when the unit has cells, 2 for an unknown unit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from necropsy.raids.scope import CoverageCell, coverage_cells
from necropsy.rules import load_rules
from necropsy.snapshot.archive import ArchiveError
from necropsy.snapshot.model import SnapshotError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # run as a script: make the sibling tools importable
    sys.path.insert(0, str(ROOT))

from scripts import check_raid_coverage as coverage  # noqa: E402


def unit_cells(
    raid: str, class_id: int, category: str, metric: str, faction: str
) -> list[CoverageCell]:
    return [
        cell
        for cell in coverage_cells()
        if cell.raid == raid
        and cell.configuration.class_id == class_id
        and cell.configuration.category == category
        and cell.configuration.metric == metric
        and cell.configuration.faction == faction
    ]


def _actor_outcome(root: Path, cell: CoverageCell, receipt: coverage.Receipt | None) -> str:
    if receipt is None or receipt.real_actor_source is None:
        return "missing"
    try:
        problems = coverage.actor_problems(root, cell, receipt.real_actor_source)
    except (ValueError, OSError, ArchiveError, SnapshotError) as exc:
        return f"unusable: {exc}"
    return f"unusable: {'; '.join(problems)}" if problems else "usable"


def class_scoped(cell: CoverageCell) -> dict[str, int]:
    """Boss rules written for this class: zero means only generic content applies."""
    guidance = load_rules("classic_era", f"zones/{cell.raid}_guidance")
    cid, metric = cell.configuration.class_id, cell.configuration.metric

    def scoped(rows: Any) -> int:
        return sum(
            1
            for row in rows or ()
            if cid in (row.get("classes") or ()) and metric in row.get("metrics", (metric,))
        )

    strategy = (guidance.get("strategy") or {}).get(cell.encounter_id) or {}
    return {
        "strategy_items": scoped(strategy.get("items")),
        "removal_policies": scoped((guidance.get("removals") or {}).get(cell.encounter_id)),
        "presence_rules": len(
            (guidance.get("mechanic_presence") or {}).get(cell.encounter_id) or ()
        ),
    }


def cell_report(root: Path, cell: CoverageCell, receipt: coverage.Receipt | None) -> dict[str, Any]:
    content = coverage.content_problems(cell)
    dimensions = {
        d: "referenced" if receipt is not None and receipt.references.get(d) else "missing"
        for d in coverage.DIMENSIONS
    }
    return {
        "cell": cell.key,
        "boss": cell.boss,
        "status": receipt.status if receipt else "TODO",
        "real_actor_source": _actor_outcome(root, cell, receipt),
        "content_problems": content,
        "class_scoped_rules": class_scoped(cell),
        "dimensions": dimensions,
    }


def preflight(
    raid: str,
    class_id: int,
    category: str,
    metric: str,
    faction: str,
    register: coverage.Register,
    root: Path = coverage.ROOT,
) -> dict[str, Any]:
    receipts = {r.cell_id: r for r in register.records}
    cells = [
        cell_report(root, cell, receipts.get(cell.key))
        for cell in unit_cells(raid, class_id, category, metric, faction)
    ]
    shared = sorted({p for c in cells for p in c["content_problems"]})
    return {
        "unit": f"{raid}/{class_id}/{category}/{metric}/{faction}",
        "cells": cells,
        "summary": {
            "cells": len(cells),
            "complete": sum(c["status"] == "COMPLETE" for c in cells),
            "usable_actor_source": sum(c["real_actor_source"] == "usable" for c in cells),
            "content_problem_kinds": shared,
        },
        "note": (
            "Work list only; referenced evidence is not reviewed and no cell becomes COMPLETE here."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("raid")
    parser.add_argument("class_id", type=int)
    parser.add_argument("category")
    parser.add_argument("metric")
    parser.add_argument("faction")
    parser.add_argument("--register", type=Path, default=coverage.REGISTER)
    args = parser.parse_args(argv)
    register = coverage.Register.model_validate_json(args.register.read_text(encoding="utf-8"))
    report = preflight(args.raid, args.class_id, args.category, args.metric, args.faction, register)
    print(json.dumps(report, indent=2))
    return 0 if report["cells"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
