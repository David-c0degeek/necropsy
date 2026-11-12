"""Build cell-scoped Naxx DPS policies at the five bosses with production exclusions (D027).

`../dps-policies-20261112/` left every cell at Anub'Rekhan, Gluth, Faerlina,
Heigan and Razuvious open, because no policy evidence tested their production
`ranking_exclusions`. The register already admits rows there exclusion-neutrally
(D025) and keeps rows whose ranked amount depends on the list as unverified.

A production exclusion list names target game IDs. It does not depend on the
attacker's class, so it is tested per boss: the list counts as exercised when at
least MIN_WITNESSES matched rows, from any configuration, have positive damage
to excluded targets. Per cell, a policy then needs:

- at least the packaged minimum of distinct players whose published DPS the
  freezer matches with the exact production list (excluded damage zero or
  positive);
- no arithmetic contradiction in the cell, with or without the list;
- only ownership refusals.

Each policy carries the boss's list witnesses, so the golden test re-proves
the list (matched with it, contradicted without it) next to the cell's rows.

Check mode (the default) writes nothing and fails if a fresh build differs;
`--write` refuses to overwrite. It replays the register's admission (about 9
minutes) and needs Git LFS.

    uv run python tasks/naxx-completion/research/dps-exclusion-policies-20261112/build.py
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "dps_policies", HERE.parent / "dps-policies-20261112/build.py"
)
assert _spec is not None and _spec.loader is not None
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

from necropsy.rules import load_rules  # noqa: E402
from scripts import comparison_followup as followup  # noqa: E402
from scripts.check_raid_coverage import EXCLUSION_POLICY_CONDITIONS  # noqa: E402

ROOT = base.ROOT
MATRIX = HERE / "matrix.json"
FRAGMENT = HERE / "policies.yaml"
MIN_WITNESSES = 3
EXERCISED = "production exclusions exercised and untested"
MISMATCH = "arithmetic mismatch under the untested production exclusions"
MARKER = "policy-exclusions-20261112"
CONDITIONS = [
    "unique-name-realm-identity",
    "complete-source-target-streams",
    "owned-unit-listing-present",
    "owner-and-owned-unit-targets-subtracted",
    "ranking-duration-equals-fight-duration",
    "production-ranking-exclusions-exercised",
]
FORMULA = (
    "WCL DPS equals the actor's damage plus its listed owned units' damage, less "
    "damage to the actor or its owned units and less damage to the encounter's "
    "production-excluded target game IDs, divided by the fight duration."
)
METHOD = base.METHOD + (
    " Damage to the production-excluded target game IDs is subtracted; the boss's list "
    "witnesses are re-proved to match with the list and to contradict without it."
)


def row_of(cell: dict[str, Any], who: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    config = cell["configuration"]
    row = {
        "id": f"{who['report']}-{who['fight']}-{spec['actor']}",
        "purpose": "policy-scope",
        "report": who["report"],
        "fight": who["fight"],
        "actor": spec["actor"],
        "player": who["player"],
        "realm": who["realm"],
        "kind": "cohort",
        "faction": config["faction"],
        "faction_status": "observed",
        "status": "arithmetic-match",
        "leaderboard_member": spec["leaderboard_member"],
        "page": spec["page"],
        "row": spec["row"],
        "excluded_game_ids": spec["excluded_game_ids"],
        "owned_actor_ids": result["owned_actor_ids"],
        "duration_ms": result["duration_ms"],
        "published": result["published"],
        "totals": result["totals"],
        "residual": result["residual"],
    }
    if result.get("catalog_pets_out_of_scope"):
        row["catalog_pets_out_of_scope"] = result["catalog_pets_out_of_scope"]
    return row


def build() -> dict[Path, str]:
    register = base.json.loads(base.REGISTER.read_bytes())
    zone = load_rules("classic_era", "zones/naxxramas")
    lists = {
        e["id"]: sorted(int(x["game_id"]) for x in e.get("ranking_exclusions") or ())
        for e in zone["encounters"]
    }
    archives = sorted({c["archive"]["path"] for c in register["cells"]})
    cells, captured = base.admitted_results(archives)
    base.require(cells == register["cells"], "register differs from a fresh admission")
    floor = followup.minimum()

    def result_for(cell: dict[str, Any], who: dict[str, Any]) -> dict[str, Any]:
        key = (cell["archive"]["sha256"], who["report"], who["fight"], who["player"], who["realm"])
        return captured[key]

    # Boss-level witnesses: matched rows with positive damage to excluded targets.
    witnesses: dict[int, list[dict[str, Any]]] = {e: [] for e, ids in lists.items() if ids}
    for cell in cells:
        if cell["encounter_id"] not in witnesses or cell["configuration"]["metric"] != "dps":
            continue
        for who in cell["unverified"]:
            if who["reason"] != EXERCISED:
                continue
            result = result_for(cell, who)
            base.require(
                result["spec"]["excluded_game_ids"] == lists[cell["encounter_id"]]
                and result["totals"]["excluded"] > 0,
                f"{who['report']}/{who['fight']}: witness without the production list",
            )
            witnesses[cell["encounter_id"]].append(
                row_of(cell, who, result) | {"purpose": "list-witness", "archive": cell["archive"]}
            )
    for rows in witnesses.values():
        rows.sort(key=lambda r: (r["archive"]["path"], r["report"], r["fight"], r["actor"]))
    matrix_cells = []
    policies = []
    files: dict[Path, str] = {}
    for cell in cells:
        config = cell["configuration"]
        encounter = cell["encounter_id"]
        if encounter not in witnesses or config["metric"] != "dps":
            continue
        scope = {
            "encounter_id": encounter,
            "class_id": base.CLASS_IDS[config["class"]],
            "category": config["category"],
            "metric": config["metric"],
            "faction": config["faction"],
        }
        matched = list(cell["admitted"]) + [
            u for u in cell["unverified"] if u["reason"] == EXERCISED
        ]
        contradictions = [r for r in cell["refused"] if r["reason"] == base.CONTRADICTION] + [
            u for u in cell["unverified"] if u["reason"] == MISMATCH
        ]
        other = [
            r
            for r in cell["refused"]
            if r["reason"] != base.CONTRADICTION and not base.ownership_refusal(r["reason"])
        ]
        distinct = len({(a["player"], a["realm"]) for a in matched})
        if len(witnesses[encounter]) < MIN_WITNESSES:
            decision = (
                f"OPEN: {len(witnesses[encounter])} list witnesses, fewer than {MIN_WITNESSES}"
            )
        elif contradictions:
            decision = f"OPEN: {len(contradictions)} contradiction(s) retained"
        elif other:
            decision = f"OPEN: {len(other)} non-ownership refusal(s) retained"
        elif distinct < floor:
            decision = f"OPEN: {distinct} matched players, fewer than {floor}"
        else:
            decision = "POLICY"
        entry = {
            "scope": scope,
            "boss": cell["boss"],
            "archive": cell["archive"]["path"],
            "matched": len(matched),
            "matched_distinct_players": distinct,
            "exercising_rows": len(matched) - len(cell["admitted"]),
            "refused": len(cell["refused"]),
            "contradictions": len(contradictions),
            "other_refusals": sorted({r["reason"] for r in other}),
            "decision": decision,
        }
        if decision == "POLICY":
            slug = "-".join(
                (base.SLUGS[encounter], config["category"], config["class"], config["faction"])
            ).lower()
            rule = f"naxx-{slug}-dps-v1"
            evidence_path = base.EVIDENCE / f"dps-ranking-naxx-{slug}.json"
            rows = [row_of(cell, who, result_for(cell, who)) for who in matched]
            for row in rows:
                base.require(row["excluded_game_ids"] == lists[encounter], f"{rule}: list")
            refusals = [
                r | {"faction": config["faction"], "faction_status": "observed"}
                for r in cell["refused"]
            ]
            n = len(rows) + len(refusals)
            evidence = {
                "version": 1,
                "rule": rule,
                "scope": scope,
                "method": METHOD,
                "archive": cell["archive"],
                "tested_exclusions": lists[encounter],
                "dispositions": {"n": n, "k": len(rows), "r": len(refusals), "c": 0},
                "rows": rows,
                "refusals": refusals,
                "list_witnesses": witnesses[encounter],
            }
            files[evidence_path] = base.dump(evidence)
            label = f"{cell['boss']} {config['category']} {config['class']} {config['faction']}"
            policies.append(
                {
                    "rule": rule,
                    "basis": "empirical",
                    "scope": scope,
                    "formula": FORMULA,
                    "conditions": CONDITIONS,
                    "bound": base.BOUND,
                    "validated": (
                        f"{len(rows)} admitted of {n} in-scope {label} rows ({distinct} distinct "
                        f"non-subject players, {entry['exercising_rows']} exercising the list); "
                        f"{len(refusals)} ownership refusals, unknown; 0 contradictions; "
                        f"{len(witnesses[encounter])} boss-level list witnesses. {MARKER}."
                    ),
                    "evidence": evidence_path.relative_to(ROOT).as_posix(),
                    "tested_exclusions": lists[encounter],
                }
            )
            entry["rule"] = rule
        matrix_cells.append(entry)
    base.require(set(CONDITIONS) == EXCLUSION_POLICY_CONDITIONS, "condition shape drifted")
    matrix = {
        "kind": "Naxx cell-scoped DPS policy matrix at bosses with production exclusions (D027)",
        "inputs": {
            "register_sha256": base.sha256(base.REGISTER),
            "builder_sha256": base.sha256(Path(__file__)),
            "base_builder_sha256": base.sha256(HERE.parent / "dps-policies-20261112/build.py"),
            "freezer_sha256": base.sha256(ROOT / "scripts/freeze_dps_ranking.py"),
        },
        "minimum_matched_players": floor,
        "minimum_list_witnesses": MIN_WITNESSES,
        "list_witnesses": {str(e): len(rows) for e, rows in witnesses.items()},
        "cells": matrix_cells,
        "policies": len(policies),
        "limits": [
            "Raw-to-published arithmetic for exactly each cell scope; no engine emission, "
            "product score, grade or COMPLETE cell.",
            "The list is tested per boss across configurations, not per cell.",
            "Ownership refusals are unknown, never matches or contradictions.",
        ],
    }
    files[MATRIX] = base.dump(matrix)
    files[FRAGMENT] = yaml.dump(
        policies, Dumper=base._NoAliases, sort_keys=False, allow_unicode=True, width=88
    )
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    files = build()
    for path, text in files.items():
        if args.write:
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        else:
            base.require(path.read_bytes() == text.encode("utf-8"), f"{path} differs")
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(f"{'WROTE' if args.write else 'PASS'}: {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
