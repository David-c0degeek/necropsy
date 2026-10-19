"""Shared document adapter for the remaining Classic Era class plugins."""

from __future__ import annotations

import math
from typing import Any

import duckdb

from necropsy.analysis import gamedata
from necropsy.analysis.benchmark import BossData, Entry, median_of
from necropsy.analysis.classes.classic_era import healer_notes
from necropsy.analysis.classes.classic_era.combat import LIMITATIONS
from necropsy.analysis.evidence import EvidenceRef, observed, unknown
from necropsy.analysis.generic.catalog import ItemName, item_catalog
from necropsy.analysis.roles import ranking_policy
from necropsy.analysis.taxonomy import build_matches
from necropsy.raids import raid_for_encounter
from necropsy.report.abilities import difference, rows
from necropsy.report.equipment import enrich_gear
from necropsy.report.rankings import top_metadata
from necropsy.report.serialize import to_data


def _entry(
    con: duckdb.DuckDBPyConnection,
    entry: Entry,
    metric: str,
    names: dict[int, ItemName],
) -> dict[str, Any]:
    pf, data = entry.participant, entry.combat
    env = to_data(entry.profile)
    env.pop("participant", None)
    env["gear"]["value"] = enrich_gear(env["gear"]["value"], names)
    scores = con.execute(
        "SELECT total FROM benchmark_participants WHERE report_code=? AND fight_id=? AND player=?",
        [pf.report_code, pf.fight_id, pf.player],
    ).fetchall()
    values = {
        r[0] for r in scores if type(r[0]) in (int, float) and math.isfinite(r[0]) and r[0] >= 0
    }
    score = (
        next(iter(values))
        if data.ranking_category.value is not None
        and len(values) == 1
        and all(r[0] in values for r in scores)
        else None
    )
    ref = EvidenceRef(pf.report_code, pf.fight_id, pf.actor_id, "benchmark_participants")
    return {
        "player": pf.player,
        "server": pf.server,
        "kind": pf.kind,
        "leaderboard_position": pf.leaderboard_position,
        "report_code": pf.report_code,
        "fight_id": pf.fight_id,
        "kill_duration_s": pf.duration_ms / 1000,
        "environment": env,
        "ranking": {
            "category": data.ranking_category.value,
            "metric": metric,
            "category_score": score,
            "category_score_evidence": to_data(
                observed(score, ref) if score is not None else unknown("ranking score unknown", ref)
            ),
            "basis": "saved-ranking-metadata",
            "note": "Saved WCL score, separate from event throughput and quality.",
        },
        "raptor_roles": to_data(entry.raptor_roles),
        "combat": to_data(data),
        "ability_use": to_data(data.casts),
    }


def _comparison(subject: Entry, reference: Entry) -> dict[str, Any]:
    return {
        "player": reference.participant.player,
        "leaderboard_position": reference.participant.leaderboard_position,
        "report_code": reference.participant.report_code,
        "fight_id": reference.participant.fight_id,
        "kill_duration_s": reference.participant.duration_ms / 1000,
        "build": to_data(reference.combat.build),
        "build_matches": build_matches(reference.combat.build.value, subject.combat.build.value),
        "metrics": {
            name: difference(value.value, reference.combat.metrics[name].value)
            for name, value in subject.combat.metrics.items()
        },
        "spells": rows(
            subject.combat.casts.value,
            reference.combat.casts.value,
            subject.participant.duration_ms / 1000,
            reference.participant.duration_ms / 1000,
        ),
    }


def boss_section(
    con: duckdb.DuckDBPyConnection,
    boss: BossData,
    partition: int | None,
    metric: str | None,
    category: str | None,
    acquisition: dict[str, Any] | None,
    class_id: int,
) -> dict[str, Any]:
    policy = ranking_policy(class_id, category, metric)
    category, metric = policy.category, policy.metric
    names = item_catalog(con)
    faction = (((acquisition or {}).get("key") or {}).get("faction") or {}).get("value")
    if faction is None and boss.subject is not None and boss.subject.profile.faction.value:
        faction = boss.subject.profile.faction.value.value

    def eligible(entry: Entry) -> bool:
        return (
            entry.combat.class_id.value == class_id
            and entry.combat.ranking_category.value == category
            and entry.combat.role.value == policy.role
            and entry.participant.difficulty == 3
            and entry.participant.kill is True
            and partition is not None
        )

    subject = (
        boss.subject
        if boss.subject is not None
        and eligible(boss.subject)
        and boss.subject.profile.faction.value is not None
        and boss.subject.profile.faction.value.value == faction
        else None
    )
    overall = tuple(
        e
        for e in boss.cohort
        if eligible(e)
        and type(e.participant.leaderboard_position) is int
        and e.participant.leaderboard_position > 0
    )
    same = tuple(
        e
        for e in overall
        if faction is not None
        and e.profile.faction.value is not None
        and e.profile.faction.value.value == faction
    )

    def first(entries: tuple[Entry, ...]) -> Entry | None:
        return min(
            entries, key=lambda e: e.participant.leaderboard_position or math.inf, default=None
        )

    leader, global_leader = first(same), first(overall)
    comparable = same if subject is not None else ()

    def measurement(entry: Entry, name: str) -> Any:
        return entry.combat.metrics[name]

    from functools import partial

    medians = {
        name: to_data(
            median_of(comparable, partial(measurement, name=name), name, inferred_membership=True)
        )
        for name in (subject.combat.metrics if subject else {})
    }
    key = (
        {
            "class_id": class_id,
            "category": category,
            "role": policy.role,
            "metric": metric,
            "faction": faction,
            "partition": partition,
            "encounter": boss.encounter_id,
        }
        if subject is not None and faction is not None
        else None
    )
    top = top_metadata(con, boss, partition, category, metric, acquisition, class_id=class_id)
    faction_top = (
        top_metadata(con, boss, partition, category, metric, acquisition, faction, class_id)
        if faction in ("Alliance", "Horde")
        else None
    )

    def section(entry: Entry | None) -> dict[str, Any] | None:
        return None if entry is None else _entry(con, entry, metric, names)

    personal = section(subject)
    ranking_comparison = None
    if faction_top:
        ranking_comparison = {
            **{
                k: faction_top[k]
                for k in (
                    "player",
                    "metric",
                    "scope",
                    "faction",
                    "faction_evidence",
                    "leaderboard_position",
                    "report_code",
                    "fight_id",
                )
            },
            "reference_evidence": faction_top["category_score"],
            "basis": "saved-ranking-metadata",
            "n_sources": 1,
            **difference(
                None if personal is None else personal["ranking"]["category_score"],
                faction_top["category_score"]["value"],
            ),
        }
    focus = {
        "dps": "Review your opening casts, core ability cadence, targets and cooldown timing.",
        "healer": "Review assigned targets, healing choices and cooldowns with the healing team.",
        "tank": "Review encounter hits, incoming healing and defensive timing with your tanks.",
    }[policy.role]
    primary = {
        "dps": ["damage_per_second"],
        "healer": ["effective_healing_per_second", "overhealing_pct"],
        "tank": ["incoming_damage_per_second", "healing_received_per_second"],
    }[policy.role]
    return {
        "encounter_id": boss.encounter_id,
        "boss": boss.boss,
        "rules": {
            "ranking_exclusions": [],
            "ranking_exclusion_rule": {
                "rule": "class-event-metrics",
                "basis": "none",
                "validation": None,
            },
            "native_targets": None,
        },
        "subject": personal,
        "benchmarks": {
            "ceiling": None,
            "raid_speed": None,
            "cross_faction": None,
            "excluded": None,
            "baseline": {
                "key": key,
                "entries": len(comparable),
                "excluded_incompatible": len(boss.cohort) - len(same),
                "medians": medians,
                "limited_sample": len(same) < 3,
                "note": "Same class, faction, category, observed duty and metric. "
                "Builds remain context; "
                "one or two sources give individual comparisons, medians require three values.",
            },
            "overall_top": top,
        },
        "cohort": [section(e) for e in same],
        "overall_cohort": [section(e) for e in boss.cohort],
        "encounter": {
            "target_integrity": None,
            "raid_utility": None,
            "cohort_target_integrity": [],
        },
        "recommendations": [],
        "playbook": {
            "selected_category": category,
            "selected_metric": metric,
            "selected_faction": faction,
            "n_event_sources": len(same),
            "encounter_facts": to_data(
                gamedata.encounter_facts(
                    raid_for_encounter(boss.encounter_id).slug, boss.encounter_id
                )
            ),
            "personal_data": {
                "status": "available" if subject else "insufficient-data",
                "message": (
                    "Matching personal encounter acquired."
                    if subject
                    else f"No matching personal {category} encounter in the acquired logs."
                ),
                "reasons": []
                if subject
                else ["Missing encounter or category/duty/coverage mismatch."],
                "note": "Available logs cannot prove that you have never played this spec.",
            },
            "excluded_subject": section(boss.subject) if subject is None else None,
            "reference": section(leader),
            "overall_reference": section(global_leader),
            "reference_note": (
                "Highest-ranked acquired eligible example in your spec and faction; "
                "build, buffs, fight length and assignments may differ."
                if leader is not None
                else "No eligible recorded example is available in your spec and faction."
            ),
            "comparisons": [] if subject is None else [_comparison(subject, e) for e in same],
            "ranking_comparison": ranking_comparison,
            "same_faction_top": faction_top,
            "overall_comparison": (
                _comparison(subject, global_leader)
                if subject is not None and global_leader is not None
                else None
            ),
            "primary_metrics": primary,
            "class_notes": (
                []
                if subject is None or policy.role != "healer"
                else to_data(
                    healer_notes.notes(
                        subject.combat,
                        class_id,
                        subject.participant.actor_id,
                        subject.participant.duration_ms / 1000,
                    )
                )
            ),
            "limitations": list(LIMITATIONS),
            "guidance": focus
            + (
                " Use the leader's recorded opener and ability mix as practice "
                "references; confirm assignments before copying them."
                if leader is not None
                else " No eligible recorded opener or ability mix is available for comparison."
            ),
        },
    }
