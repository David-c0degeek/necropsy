"""Druid sections for the shared analysis document, with exact applicable cohorts."""

from __future__ import annotations

from typing import Any

import duckdb

from necropsy.analysis.benchmark import BossData, Entry, median_of
from necropsy.analysis.classes.classic_era.druid import LIMITATIONS
from necropsy.analysis.evidence import Evidenced, EvidenceLevel
from necropsy.analysis.roles import DRUID_CATEGORIES, ComparisonKey, FightRole
from necropsy.report.serialize import to_data


def comparison_key(entry: Entry, partition: int | None) -> ComparisonKey | None:
    analysis = entry.druid
    category, role = analysis.ranking_category.value, analysis.role.value
    if (
        partition is None
        or entry.participant.difficulty is None
        or category is None
        or role is None
        or analysis.build.value is None
        or entry.profile.faction.value is None
        or role in (FightRole.HYBRID, FightRole.UNCERTAIN)
        or analysis.override is not None
    ):
        return None
    try:
        return ComparisonKey(
            2,
            entry.participant.encounter_id,
            entry.profile.faction.value.value,
            analysis.build.value,
            category,
            role,
            DRUID_CATEGORIES[category][0],
            partition,
            difficulty=entry.participant.difficulty,
        )
    except ValueError:
        return None


def _ranking(con: duckdb.DuckDBPyConnection, entry: Entry) -> dict[str, Any]:
    """A saved WCL amount stays metadata; event throughput is a separate value."""
    rows = con.execute(
        """SELECT total FROM benchmark_participants WHERE report_code = ?
           AND fight_id = ? AND player = ? AND total IS NOT NULL""",
        [entry.participant.report_code, entry.participant.fight_id, entry.participant.player],
    ).fetchall()
    category = entry.druid.ranking_category.value
    metric = DRUID_CATEGORIES[category][0] if category else None
    amounts = {r[0] for r in rows}
    return {
        "category": category,
        "metric": metric,
        "category_score": next(iter(amounts)) if len(amounts) == 1 else None,
        "basis": "saved-ranking-metadata",
        "note": "A WCL category score; never an event baseline or a quality score.",
    }


def entry_section(con: duckdb.DuckDBPyConnection, entry: Entry) -> dict[str, Any]:
    pf = entry.participant
    env = to_data(entry.profile)
    env.pop("participant", None)
    return {
        "player": pf.player,
        "server": pf.server,
        "kind": pf.kind,
        "leaderboard_position": pf.leaderboard_position,
        "report_code": pf.report_code,
        "fight_id": pf.fight_id,
        "kill_duration_s": pf.duration_ms / 1000,
        "environment": env,
        "ranking": _ranking(con, entry),
        "raptor_roles": to_data(entry.raptor_roles),
        "druid": to_data(entry.druid),
    }


def _recommendations(subject: Entry, medians: dict[str, Any]) -> list[dict[str, Any]]:
    druid = subject.druid
    role = druid.role.value
    items: list[dict[str, Any]] = []

    def add(
        rule: str, finding: str, action: str, paths: list[str], control: str = "player"
    ) -> None:
        items.append(
            {
                "rule": rule,
                "boss": subject.participant.boss,
                "category": "druid",
                "controllability": control,
                "severity": "low",
                "confidence": "low",
                "finding": finding,
                "recommendation": action,
                "observed": {},
                "benchmark": {},
                "evidence": paths,
                "limitations": list(LIMITATIONS),
            }
        )

    if role is None or role == FightRole.HYBRID:
        add(
            "druid-confirm-duties-v1",
            "Encounter duties are uncertain or mixed.",
            "Confirm your assignments and inspect each observed activity span; "
            "a whole-fight single-role comparison does not apply.",
            ["subject.druid.role", "subject.druid.observed_roles"],
            "raid-assignment",
        )
    deaths = druid.deaths.deaths.value
    if deaths:
        add(
            "druid-death-review-v1",
            f"{len(deaths)} deaths recorded in this fight.",
            "Review the incoming hits and healing support around each death with your raid; "
            "the log alone does not establish fault.",
            ["subject.druid.deaths"],
            "raid-assignment",
        )
    if role == FightRole.HEALER:
        over = druid.metrics["overhealing_pct"].value
        if over is not None and over > 50:
            add(
                "druid-healing-context-v1",
                f"Recorded overhealing was {over:.1f}%.",
                "Review spell ranks, timing and assigned targets with your healing team. "
                "Do not reduce assigned coverage just to improve an overheal statistic.",
                ["subject.druid.metrics.overhealing_pct", "subject.druid.healing_targets"],
                "raid-assignment",
            )
    if role in (FightRole.FERAL, FightRole.BALANCE):
        metric = "damage_per_second"
        median = medians.get(metric)
        current = druid.metrics[metric].value
        typical = None if median is None else median["value"]["value"]
        if current is not None and typical is not None and current < typical * 0.8:
            add(
                "druid-damage-review-v1",
                "Actor event DPS is below the comparable sample median.",
                "Compare cast timing, target choices, resources and external buffs before "
                "changing execution. Fight duration and assigned downtime can explain the gap.",
                [
                    "subject.druid.metrics.damage_per_second",
                    "benchmarks.baseline.medians.damage_per_second",
                ],
            )
    return items


def boss_section(
    con: duckdb.DuckDBPyConnection, boss: BossData, partition: int | None
) -> dict[str, Any]:
    subject = boss.subject
    key = None if subject is None else comparison_key(subject, partition)
    applicable = tuple(
        e for e in boss.cohort if key is not None and comparison_key(e, partition) == key
    )
    medians: dict[str, Any] = {}
    if subject is not None:
        inferred_members = any(
            e.profile.faction.level is EvidenceLevel.INFERRED
            or e.druid.role.level is EvidenceLevel.INFERRED
            for e in applicable
        )
        for name in subject.druid.metrics:

            def metric(entry: Entry, metric_name: str = name) -> Evidenced[float]:
                return entry.druid.metrics[metric_name]

            medians[name] = to_data(
                median_of(
                    applicable,
                    metric,
                    name,
                    inferred_membership=inferred_members,
                )
            )
    baseline = {
        "key": to_data(key),
        "entries": len(applicable),
        "medians": medians,
        "excluded_incompatible": len(boss.cohort) - len(applicable),
        "note": "Exact class, encounter, faction, build, WCL category, role, metric and partition; "
        "three known values required. Hybrid/uncertain/overridden duties "
        "have no aggregate baseline.",
    }
    role = (
        FightRole.UNCERTAIN if subject is None else subject.druid.role.value or FightRole.UNCERTAIN
    )
    practice = {
        FightRole.FERAL: "Review form changes and energy readings around attacks and finishers. "
        "Compare cast timing only after checking targets, fight length and assigned downtime.",
        FightRole.BALANCE: "Review your damage-cast sequence, target changes and resource/cooldown "
        "timing. A cast gap alone does not prove an execution mistake.",
        FightRole.HEALER: "Check your assigned targets, healing spell use and cooldown timing with "
        "the healing team. Preserve required coverage instead of chasing HPS or lower overheal.",
        FightRole.TANK: "Review direct encounter hits, incoming healing and defensive timing "
        "around tank activity. Missing threat or form coverage remains unknown.",
        FightRole.HYBRID: "Review each evidenced duty separately with the raid. Keep transitions "
        "and assignments visible; a whole-fight single-role comparison does not apply.",
    }.get(
        role, "Confirm encounter assignments and review the observed activity before changing play."
    )
    primary = {
        FightRole.HEALER: ["effective_healing", "effective_healing_per_second", "overhealing_pct"],
        FightRole.TANK: ["incoming_damage", "incoming_damage_per_second", "healing_received"],
    }.get(role, ["damage", "damage_per_second", "effective_healing", "incoming_damage"])
    return {
        "encounter_id": boss.encounter_id,
        "boss": boss.boss,
        "rules": {
            "ranking_exclusions": [],
            "native_targets": None,
            "ranking_exclusion_rule": {
                "rule": "not-applied-to-druid",
                "basis": "none",
                "validation": None,
            },
        },
        "subject": None if subject is None else entry_section(con, subject),
        "cohort": [entry_section(con, e) for e in applicable],
        "overall_cohort": [entry_section(con, e) for e in boss.cohort],
        "benchmarks": {
            "ceiling": None,
            "baseline": baseline,
            "raid_speed": None,
            "cross_faction": None,
            "excluded": None,
        },
        "encounter": {
            "target_integrity": None,
            "raid_utility": None,
            "cohort_target_integrity": [],
        },
        "recommendations": [] if subject is None else _recommendations(subject, medians),
        "playbook": {
            "guidance": practice + " Use the recorded first ten seconds as a practice example, "
            "not a universal optimal opener. Check assignments before copying it.",
            "primary_metrics": primary,
            "limitations": list(LIMITATIONS),
        },
    }
