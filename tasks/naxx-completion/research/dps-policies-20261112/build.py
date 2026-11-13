"""Build cell-scoped Naxx DPS and HPS ranking policies for every captured configuration.

This generalizes the C1 matrix (`../c1-dps-policy-matrix/`) from one
configuration to every DPS archive in the comparison follow-up register. The
admission is exactly the register's: `comparison_followup.cells` runs
`freeze_dps_ranking.compute` on each same-faction comparison's published row.
This builder only records the freezer result of each admitted row and applies
the C1 decision rule per cell:

- a DPS cell at a boss with production `ranking_exclusions` stays OPEN here
  (untested by this evidence; `../dps-exclusion-policies-20261112/` covers it,
  D027). The lists name damage targets only: HPS takes no target exclusions, so
  an HPS cell is decided at every boss (D029);
- a cell already covered by a committed policy is left as it is;
- a cell stays OPEN with any arithmetic contradiction, with any refusal that is
  not about pet ownership, or with fewer than the packaged minimum of distinct
  admitted players;
- every other cell gets one policy. Ownership refusals (pet listings disagree,
  unproven pet set: no `pets.json`, D026) are unknown, never matches.

Check mode (the default) writes nothing and fails if a fresh build differs from
the committed matrix, policy fragment and evidence files. `--write` creates
them and refuses to overwrite. The archives need Git LFS.

    uv run python tasks/naxx-completion/research/dps-policies-20261112/build.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from necropsy.analysis.class_catalog import CLASS_NAMES  # noqa: E402
from necropsy.rules import load_rules  # noqa: E402
from scripts import comparison_followup as followup  # noqa: E402
from scripts import freeze_dps_ranking as dps  # noqa: E402
from scripts.check_raid_coverage import POLICY_CONDITIONS  # noqa: E402

HERE = Path(__file__).resolve().parent
REGISTER = ROOT / "tasks/naxx-completion/followup-comparisons.json"
MATRIX = HERE / "matrix.json"
FRAGMENT = HERE / "policies.yaml"
EVIDENCE = ROOT / "tests/golden/raids"
CONDITIONS = [
    "unique-name-realm-identity",
    "complete-source-target-streams",
    "owned-unit-listing-present",
    "owner-and-owned-unit-targets-subtracted",
    "ranking-duration-equals-fight-duration",
    "encounter-has-no-production-ranking-exclusions",
]
FORMULA = (
    "WCL DPS equals the actor's damage plus its listed owned units' damage, less "
    "damage to the actor or its owned units, divided by the fight duration. No "
    "target exclusions."
)
HPS_CONDITIONS = [
    "unique-name-realm-identity",
    "complete-source-target-streams",
    "owned-unit-listing-present",
    "friendly-recipients-only",
    "ranking-duration-equals-fight-duration",
]
HPS_FORMULA = (
    "WCL HPS equals the actor's heal amounts (overheal excluded) plus its absorbed "
    "events plus the same for its listed owned units, on friendly recipients (the "
    "fight's friendly players and pets, or a unit the event marks targetIsFriendly, "
    "such as a mind-controlled NPC), divided by the fight duration. No target "
    "exclusions."
)
BOUND = (
    "Within one unit of the published last decimal place; the upstream rounding "
    "mode is not established."
)
METHOD = (
    "Freezer admission (scripts/freeze_dps_ranking.py) through the comparison "
    "follow-up register; the golden test re-enumerates every row from raw pages "
    "without freezer, analyzer or metric code. A row is consistent when "
    "|ranked * 1000 / duration - published| < 10^-(published decimals) and the "
    "ranking duration equals the fight duration."
)
CONTRADICTION = "published DPS contradicts raw"
CONTRADICTIONS = {CONTRADICTION, "published HPS contradicts raw"}
OWNERSHIP = "pet listings disagree"
SLUGS = {
    51107: "anubrekhan",
    51108: "gluth",
    51109: "gothik",
    51110: "faerlina",
    51111: "grobbulus",
    51112: "heigan",
    51113: "razuvious",
    51114: "kelthuzad",
    51115: "loatheb",
    51116: "maexxna",
    51117: "noth",
    51118: "patchwerk",
    51119: "sapphiron",
    51120: "thaddius",
    51121: "horsemen",
}
CLASS_IDS = {name: class_id for class_id, name in CLASS_NAMES.items()}


class _NoAliases(yaml.SafeDumper):
    """Write every policy's conditions in full, like the hand-written entries."""

    def ignore_aliases(self, data: Any) -> bool:
        return True


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def ownership_refusal(reason: str) -> bool:
    return reason == OWNERSHIP or (
        reason.startswith('"There is no item named')
        and reason.endswith("/pets.json' in the archive\"")
    )


def admitted_results(archives: list[str]) -> tuple[list[dict[str, Any]], dict[tuple, dict]]:
    """Run the register's admission and keep each admitted row's freezer result."""
    captured: dict[tuple, dict[str, Any]] = {}
    original = dps.compute

    def recording(spec: dict[str, Any], base: Path, metric: str = "dps") -> dict[str, Any]:
        result = original(spec, base, metric=metric)
        key = (spec["sha256"], spec["report"], spec["fight"], spec["player"], spec["realm"])
        captured[key] = result
        return result

    dps.compute = recording
    try:
        cwd = Path.cwd()
        os.chdir(ROOT)  # the register keeps archive paths relative to the repository
        try:
            cells = [cell for path in archives for cell in followup.cells(Path(path))]
        finally:
            os.chdir(cwd)
    finally:
        dps.compute = original
    return cells, captured


def build() -> dict[Path, str]:
    register = json.loads(REGISTER.read_bytes())
    zone = load_rules("classic_era", "zones/naxxramas")
    exclusions = {e["id"]: bool(e.get("ranking_exclusions")) for e in zone["encounters"]}
    existing = {
        tuple(p["scope"][k] for k in ("encounter_id", "class_id", "category", "metric", "faction"))
        for p in zone.get("ranking_metric_policies") or ()
        if "policy-20261112" not in p.get("validated", "")  # this builder's own output
    }
    archives = sorted({c["archive"]["path"] for c in register["cells"]})
    cells, captured = admitted_results(archives)
    # The register must be exactly what this admission produces.
    require(cells == register["cells"], "register differs from a fresh admission")
    floor = followup.minimum()
    matrix_cells = []
    policies = []
    files: dict[Path, str] = {}
    for cell in cells:
        config = cell["configuration"]
        encounter = cell["encounter_id"]
        class_id = CLASS_IDS[config["class"]]
        scope = {
            "encounter_id": encounter,
            "class_id": class_id,
            "category": config["category"],
            "metric": config["metric"],
            "faction": config["faction"],
        }
        key = tuple(scope.values())
        refused = cell["refused"]
        contradictions = [r for r in refused if r["reason"] in CONTRADICTIONS]
        other = [
            r
            for r in refused
            if r["reason"] not in CONTRADICTIONS and not ownership_refusal(r["reason"])
        ]
        distinct = cell["admitted_distinct_players"]
        metric = config["metric"]
        if metric == "dps" and exclusions[encounter]:
            decision = "OPEN: production ranking exclusions untested by policy evidence"
        elif key in existing:
            decision = "EXISTING: committed policy"
        elif contradictions:
            decision = f"OPEN: {len(contradictions)} contradiction(s) retained"
        elif other:
            decision = f"OPEN: {len(other)} non-ownership refusal(s) retained"
        elif distinct < floor:
            decision = f"OPEN: {distinct} admitted players, fewer than {floor}"
        else:
            decision = "POLICY"
        entry = {
            "scope": scope,
            "boss": cell["boss"],
            "archive": cell["archive"]["path"],
            "admitted": len(cell["admitted"]),
            "admitted_distinct_players": distinct,
            "refused": len(refused),
            "contradictions": len(contradictions),
            "other_refusals": sorted({r["reason"] for r in other}),
            "decision": decision,
        }
        if decision == "POLICY":
            slug = "-".join(
                (SLUGS[encounter], config["category"], config["class"], config["faction"])
            ).lower()
            rule = f"naxx-{slug}-{metric}-v1"
            evidence_path = EVIDENCE / f"{metric}-ranking-naxx-{slug}.json"
            rows = []
            for a in cell["admitted"]:
                result = captured[
                    (cell["archive"]["sha256"], a["report"], a["fight"], a["player"], a["realm"])
                ]
                spec = result["spec"]
                if metric == "dps":
                    require(result["totals"]["excluded"] == 0, f"{rule}: excluded damage")
                row = {
                    "id": f"{a['report']}-{a['fight']}-{spec['actor']}",
                    "purpose": "policy-scope",
                    "report": a["report"],
                    "fight": a["fight"],
                    "actor": spec["actor"],
                    "player": a["player"],
                    "realm": a["realm"],
                    "kind": "cohort",
                    "faction": config["faction"],
                    "faction_status": "observed",
                    "status": "arithmetic-match",
                    "leaderboard_member": spec["leaderboard_member"],
                    "page": spec["page"],
                    "row": spec["row"],
                    "owned_actor_ids": result["owned_actor_ids"],
                    "duration_ms": result["duration_ms"],
                    "published": result["published"],
                    "totals": result["totals"],
                    "residual": result["residual"],
                }
                if result.get("catalog_pets_out_of_scope"):
                    row["catalog_pets_out_of_scope"] = result["catalog_pets_out_of_scope"]
                if result.get("fight_active_catalog_units"):
                    row["fight_active_catalog_units"] = result["fight_active_catalog_units"]
                rows.append(row)
            refusals = [
                r | {"faction": config["faction"], "faction_status": "observed"} for r in refused
            ]
            n = len(rows) + len(refusals)
            dispositions = {"n": n, "k": len(rows), "r": len(refusals), "c": 0}
            evidence = {
                "version": 1,
                "rule": rule,
                "scope": scope,
                "method": METHOD,
                "archive": cell["archive"],
                "dispositions": dispositions,
                "rows": rows,
                "refusals": refusals,
            }
            files[evidence_path] = dump(evidence)
            label = f"{cell['boss']} {config['category']} {config['class']} {config['faction']}"
            policies.append(
                {
                    "rule": rule,
                    "basis": "empirical",
                    "scope": scope,
                    "formula": FORMULA if metric == "dps" else HPS_FORMULA,
                    "conditions": CONDITIONS if metric == "dps" else HPS_CONDITIONS,
                    "bound": BOUND,
                    "validated": (
                        f"{len(rows)} admitted of {n} in-scope {label} rows ({distinct} distinct "
                        f"non-subject players); {len(refusals)} ownership refusals, unknown; "
                        "0 contradictions. policy-20261112."
                    ),
                    "evidence": evidence_path.relative_to(ROOT).as_posix(),
                }
            )
            entry["rule"] = rule
        matrix_cells.append(entry)
    require(set(CONDITIONS) == POLICY_CONDITIONS["dps"], "DPS condition shape drifted")
    require(set(HPS_CONDITIONS) == POLICY_CONDITIONS["hps"], "HPS condition shape drifted")
    matrix = {
        "kind": "Naxx cell-scoped DPS and HPS policy matrix; every register configuration",
        "inputs": {
            "register_sha256": sha256(REGISTER),
            "builder_sha256": sha256(Path(__file__)),
            "freezer_sha256": sha256(ROOT / "scripts/freeze_dps_ranking.py"),
        },
        "minimum_admitted_players": floor,
        "cells": matrix_cells,
        "policies": len(policies),
        "limits": [
            "Raw-to-published arithmetic for exactly each cell scope; no engine emission, "
            "product score, grade or COMPLETE cell.",
            "Ownership refusals are unknown, never matches or contradictions.",
            "An empty target-exclusion set is positively exercised only where admitted rows "
            "damage more than one target game ID.",
        ],
    }
    files[MATRIX] = dump(matrix)
    files[FRAGMENT] = yaml.dump(
        policies, Dumper=_NoAliases, sort_keys=False, allow_unicode=True, width=88
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
            require(path.read_bytes() == text.encode("utf-8"), f"{path} differs from a fresh build")
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(f"{'WROTE' if args.write else 'PASS'}: {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
