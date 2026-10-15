"""Druid sections for the shared analysis document, with exact applicable cohorts."""

from __future__ import annotations

import json
import math
from typing import Any

import duckdb

from necropsy.analysis.benchmark import BossData, Entry, median_of
from necropsy.analysis.classes.classic_era.druid import LIMITATIONS
from necropsy.analysis.context import coverage
from necropsy.analysis.evidence import Evidenced, EvidenceLevel, EvidenceRef, observed, unknown
from necropsy.analysis.roles import DRUID_CATEGORIES, ComparisonKey, FightRole, ranking_policy
from necropsy.report.serialize import to_data
from necropsy.snapshot.model import Direction


def comparison_key(
    entry: Entry,
    partition: int | None,
    metric: str | None = None,
) -> ComparisonKey | None:
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
            metric or DRUID_CATEGORIES[category][0],
            partition,
            difficulty=entry.participant.difficulty,
        )
    except ValueError:
        return None


def _ranking(
    con: duckdb.DuckDBPyConnection,
    entry: Entry,
    metric: str | None = None,
) -> dict[str, Any]:
    """A saved WCL amount stays metadata; event throughput is a separate value."""
    rows = con.execute(
        """SELECT total FROM benchmark_participants WHERE report_code = ?
           AND fight_id = ? AND player = ? AND total IS NOT NULL""",
        [entry.participant.report_code, entry.participant.fight_id, entry.participant.player],
    ).fetchall()
    category = entry.druid.ranking_category.value
    metric = metric or (DRUID_CATEGORIES[category][0] if category else None)
    amounts = {r[0] for r in rows if math.isfinite(r[0]) and r[0] >= 0}
    score = (
        next(iter(amounts))
        if (
            category is not None and len(amounts) == 1 and len(amounts) == len({r[0] for r in rows})
        )
        else None
    )
    ref = EvidenceRef(
        entry.participant.report_code,
        entry.participant.fight_id,
        entry.participant.actor_id,
        "benchmark_participants",
        detail=f"saved {category} {metric} ranking amount",
    )
    return {
        "category": category,
        "metric": metric,
        "category_score": score,
        "category_score_evidence": to_data(
            observed(score, ref)
            if score is not None
            else unknown("missing or invalid category score", ref)
        ),
        "basis": "saved-ranking-metadata",
        "note": "A WCL category score; never an event baseline or a quality score.",
    }


def entry_section(
    con: duckdb.DuckDBPyConnection,
    entry: Entry,
    metric: str | None = None,
) -> dict[str, Any]:
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
        "ranking": _ranking(con, entry, metric),
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


def _personal_data(
    subject: Entry | None,
    category: str | None,
    acquisition: dict[str, Any] | None,
    excluded: dict[str, Any] | None,
) -> dict[str, Any]:
    label = "Tank" if category == "Guardian" else category or "the selected spec"
    record = acquisition or {}
    if subject is not None:
        status, message = "available", f"Personal {label} encounter data is available."
    elif record.get("attempted") is False:
        status = "not-assessed"
        message = f"Personal {label} data was not assessed: this boss was not acquired."
    else:
        status = "insufficient-data"
        message = f"Not enough personal data in {label} for this encounter. "
        message += "No matching encounter duty was established in the acquired data."
    return {
        "status": status,
        "message": message,
        "excluded_fight": excluded,
        "reasons": list((record.get("subject_pick") or {}).get("notes") or [])
        + list((record.get("coverage") or {}).get("reasons") or []),
        "note": "This describes available logs, not a claim that you have never played this role.",
    }


def _top_metadata(
    con: duckdb.DuckDBPyConnection,
    boss: BossData,
    partition: int | None,
    category: str | None,
    metric: str | None,
    acquisition: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """A saved first leaderboard row is a category score, never a proven duty."""
    if category is None or acquisition is None:
        return None
    policy = ranking_policy(2, category, metric)
    key = acquisition.get("key") or {}
    for name, value in {
        "class_name": "Druid",
        "spec": category,
        "partition": partition,
        "encounter": boss.encounter_id,
        "role": policy.role,
    }.items():
        dimension = key.get(name) or {}
        if (
            dimension.get("value") != value
            or type(dimension.get("value")) is not type(value)
            or dimension.get("status") != "enforced"
        ):
            return None
    if "metric" in key and key["metric"].get("value") != policy.metric:
        return None
    rows = con.execute(
        "SELECT source, raw FROM rankings WHERE kind = 'leaderboard' AND encounter_id = ? "
        "AND page = 1 AND row_index = 0 AND starts_with(source, 'leaderboards/')",
        [boss.encounter_id],
    ).fetchall()
    if len(rows) != 1:
        return None
    source, raw = rows[0]
    row = json.loads(raw) if isinstance(raw, str) else raw
    amount = row.get("amount")
    if (
        row.get("class") not in (2, "Druid")
        or row.get("spec") != category
        or type(amount) not in (int, float)
        or not math.isfinite(amount)
        or amount < 0
        or type(row.get("hardModeLevel")) is not int
        or row["hardModeLevel"] != 0
        or not isinstance(row.get("name"), str)
        or not row["name"].strip()
        or any(
            name in row and (type(row[name]) is not int or row[name] != 1)
            for name in ("rank", "position")
        )
    ):
        return None
    report = row.get("report") or {}
    code, fight = report.get("code"), report.get("fightID")
    ref = EvidenceRef(
        code if isinstance(code, str) else "",
        fight if type(fight) is int else None,
        None,
        "leaderboard",
        detail=f"{source}: page 1 row 0; {category} {policy.metric}",
    )
    return {
        "player": row["name"],
        "leaderboard_position": 1,
        "category": category,
        "metric": policy.metric,
        "category_score": to_data(observed(float(amount), ref)),
        "report_code": code,
        "fight_id": fight,
        "basis": "saved-ranking-metadata",
        "note": "Rank-one category metadata does not prove encounter duty or an optimal strategy.",
    }


def boss_section(
    con: duckdb.DuckDBPyConnection,
    boss: BossData,
    partition: int | None,
    metric: str | None = None,
    selected_category: str | None = None,
    acquisition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    subject = boss.subject
    policy = ranking_policy(2, selected_category, metric) if selected_category else None
    excluded = None
    if (
        subject is not None
        and policy is not None
        and (
            subject.druid.ranking_category.value != policy.category
            or subject.druid.role.value is None
            or subject.druid.role.value.value != policy.role
        )
    ):
        excluded = {
            "report": subject.participant.report_code,
            "fight": subject.participant.fight_id,
            "inferred_role": subject.druid.role.value,
            "reason": "acquired fight does not establish the selected encounter duty",
        }
        subject = None
    personal = _personal_data(subject, selected_category, acquisition, excluded)
    reference = None
    if policy is not None:
        eligible = [
            e
            for e in boss.cohort
            if (candidate_key := comparison_key(e, partition, policy.metric)) is not None
            and type(e.participant.leaderboard_position) is int
            and e.participant.leaderboard_position > 0
            and candidate_key.category == policy.category
            and candidate_key.role.value == policy.role
            and all(
                coverage(con, e.participant, e.participant.actor_id, d).trusted
                for d in (Direction.SOURCE, Direction.TARGET)
            )
        ]
        reference = min(
            eligible, key=lambda e: e.participant.leaderboard_position or math.inf, default=None
        )
    key = None if subject is None else comparison_key(subject, partition, metric)
    applicable = tuple(
        e for e in boss.cohort if key is not None and comparison_key(e, partition, metric) == key
    )
    medians: dict[str, Any] = {}
    if subject is not None:
        inferred_members = any(
            e.profile.faction.level is EvidenceLevel.INFERRED
            or e.druid.role.level is EvidenceLevel.INFERRED
            for e in applicable
        )
        for name in subject.druid.metrics:

            def metric_value(entry: Entry, metric_name: str = name) -> Evidenced[float]:
                return entry.druid.metrics[metric_name]

            medians[name] = to_data(
                median_of(
                    applicable,
                    metric_value,
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
        (FightRole(policy.role) if policy else FightRole.UNCERTAIN)
        if subject is None
        else subject.druid.role.value or FightRole.UNCERTAIN
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
        "subject": None if subject is None else entry_section(con, subject, metric),
        "cohort": [entry_section(con, e, metric) for e in applicable],
        "overall_cohort": [entry_section(con, e, metric) for e in boss.cohort],
        "benchmarks": {
            "ceiling": None,
            "baseline": baseline,
            "raid_speed": None,
            "cross_faction": None,
            "excluded": None,
            "overall_top": _top_metadata(
                con, boss, partition, selected_category, metric, acquisition
            ),
        },
        "encounter": {
            "target_integrity": None,
            "raid_utility": None,
            "cohort_target_integrity": [],
        },
        "recommendations": [] if subject is None else _recommendations(subject, medians),
        "playbook": {
            "excluded_subject": entry_section(con, boss.subject, metric)
            if excluded is not None and boss.subject is not None
            else None,
            "selected_category": selected_category,
            "selected_metric": policy.metric if policy else metric,
            "personal_data": personal,
            "reference": None if reference is None else entry_section(con, reference, metric),
            "reference_note": "Highest-ranked acquired eligible example in this spec; "
            "its build, faction, fight duration and assignments may differ. "
            "This example does not establish an optimal rotation or a personal performance gap.",
            "guidance": practice + " Use the recorded first ten seconds as a practice example, "
            "not a universal optimal opener. Check assignments before copying it.",
            "primary_metrics": primary,
            "limitations": list(LIMITATIONS),
        },
    }
