"""Expose build evidence independently of declared intent and WCL pool policy."""

from __future__ import annotations

from typing import Any

import duckdb

from necropsy.analysis.benchmark import BossData
from necropsy.analysis.class_catalog import TALENT_TREES, WCL_CATEGORIES
from necropsy.analysis.evidence import (
    EvidenceLevel,
    EvidenceRef,
    derived,
    inferred,
    observed,
    unknown,
)
from necropsy.analysis.taxonomy import category_metadata, primary_tree, race_validity
from necropsy.report.serialize import to_data


def section(
    con: duckdb.DuckDBPyConnection,
    class_id: int,
    bosses: list[BossData],
    acquisition: dict[str, Any],
) -> dict[str, Any]:
    entries = []
    for boss in bosses:
        for entry in ((boss.subject,) if boss.subject else ()) + boss.cohort:
            pf, profile = entry.participant, entry.profile
            data = entry.druid if class_id == 2 else entry.combat if class_id != 3 else None
            category = data.ranking_category if data else unknown("ranking category unavailable")
            if data is None:
                specs = {
                    r[0]
                    for r in con.execute(
                        "SELECT spec FROM benchmark_participants "
                        "WHERE report_code=? AND fight_id=? "
                        "AND player=? AND server IS NOT DISTINCT FROM ?",
                        [pf.report_code, pf.fight_id, pf.player, pf.server],
                    ).fetchall()
                }
                if len(specs) == 1 and next(iter(specs)) in WCL_CATEGORIES[class_id]:
                    category = observed(
                        next(iter(specs)),
                        EvidenceRef(
                            pf.report_code, pf.fight_id, pf.actor_id, "benchmark_participants"
                        ),
                    )
            faction = profile.faction.value.value if profile.faction.value else None
            valid = race_validity(class_id, profile.race.race.value, faction)
            grade = (
                inferred
                if EvidenceLevel.INFERRED in (profile.race.race.level, profile.faction.level)
                else derived
            )
            validity = (
                grade(
                    valid,
                    *profile.race.race.refs,
                    *profile.faction.refs,
                    rule_id="classic-era-race-class-faction-v1",
                    note="Catalog consistency only; does not establish character identity.",
                )
                if valid is not None
                else unknown("race, class or faction evidence unavailable")
            )
            entries.append(
                {
                    "player": pf.player,
                    "server": pf.server,
                    "kind": pf.kind,
                    "report_code": pf.report_code,
                    "fight_id": pf.fight_id,
                    "encounter_id": pf.encounter_id,
                    "boss": boss.boss,
                    "tree_points": to_data(profile.talents),
                    "primary_tree": to_data(primary_tree(class_id, profile.talents)),
                    "wcl_category": category_metadata(class_id, category.value),
                    "wcl_category_evidence": to_data(category),
                    "duty": to_data(data.role if data else unknown("no separate duty classifier")),
                    "assignment": to_data(
                        data.assignment if data else unknown("assignment not supplied")
                    ),
                    "race": to_data(profile.race.race),
                    "faction": to_data(profile.faction),
                    "race_class_faction_valid": to_data(validity),
                }
            )
    return {
        "game": "classic_era",
        "class_id_namespace": "wcl-vanilla",
        "talent_trees": list(TALENT_TREES[class_id]),
        "declared_talent_tree": acquisition.get("declared_talent_tree"),
        "declaration_basis": "user-declared preference; not observed fight evidence",
        "comparison_pool": category_metadata(class_id, acquisition.get("selected_category")),
        "comparison_scope": "WCL category; talent builds are recorded per fight, not filtered",
        "role_scope": "WCL category policy at acquisition; "
        "inferred duty qualifies event comparisons",
        "entries": entries,
    }
