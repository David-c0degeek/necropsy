"""Druid sections for the shared analysis document, with exact applicable cohorts."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import duckdb

from necropsy.analysis import gamedata
from necropsy.analysis.benchmark import BossData, Entry, median_of
from necropsy.analysis.classes.classic_era.druid import LIMITATIONS
from necropsy.analysis.context import coverage
from necropsy.analysis.evidence import Evidenced, EvidenceLevel, EvidenceRef, observed, unknown
from necropsy.analysis.generic.catalog import ItemName, item_catalog
from necropsy.analysis.roles import DRUID_CATEGORIES, ComparisonKey, FightRole, ranking_policy
from necropsy.report.abilities import difference as _difference
from necropsy.report.abilities import rows as ability_rows
from necropsy.report.equipment import enrich_gear
from necropsy.report.rankings import top_metadata as _top_metadata
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
    names: dict[int, ItemName] | None = None,
) -> dict[str, Any]:
    pf = entry.participant
    env = to_data(entry.profile)
    env.pop("participant", None)
    env["gear"]["value"] = enrich_gear(
        env["gear"]["value"], names if names is not None else item_catalog(con)
    )
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
        "ability_use": to_data(entry.druid.casts),
    }


def _event_comparison(subject: Entry, example: Entry) -> dict[str, Any]:
    metrics = {
        name: _difference(value.value, example.druid.metrics[name].value)
        for name, value in subject.druid.metrics.items()
    }
    spells = ability_rows(
        subject.druid.casts.value,
        example.druid.casts.value,
        subject.participant.duration_ms / 1000,
        example.participant.duration_ms / 1000,
    )
    return {
        "player": example.participant.player,
        "leaderboard_position": example.participant.leaderboard_position,
        "report_code": example.participant.report_code,
        "fight_id": example.participant.fight_id,
        "build": to_data(example.druid.build),
        "build_matches": example.druid.build.value == subject.druid.build.value,
        "kill_duration_s": example.participant.duration_ms / 1000,
        "metrics": metrics,
        "spells": spells,
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


def boss_section(
    con: duckdb.DuckDBPyConnection,
    boss: BossData,
    partition: int | None,
    metric: str | None = None,
    selected_category: str | None = None,
    acquisition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    names = item_catalog(con)

    def section(entry: Entry) -> dict[str, Any]:
        return entry_section(con, entry, metric, names)

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
    selected_faction = (
        subject.profile.faction.value.value
        if subject is not None and subject.profile.faction.value is not None
        else (((acquisition or {}).get("key") or {}).get("faction") or {}).get("value")
    )
    reference = None
    overall_reference = None
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
        overall_reference = min(
            eligible, key=lambda e: e.participant.leaderboard_position or math.inf, default=None
        )
        reference = min(
            (
                e
                for e in eligible
                if selected_faction is None
                or (
                    e.profile.faction.value is not None
                    and e.profile.faction.value.value == selected_faction
                )
            ),
            key=lambda e: e.participant.leaderboard_position or math.inf,
            default=None,
        )
    key = None if subject is None else comparison_key(subject, partition, metric)
    # Talent-point distributions are context, not a spec filter. Keep all other
    # dimensions exact and retain every source's build in the comparison rows.
    applicable = tuple(
        e
        for e in boss.cohort
        if key is not None
        and (other := comparison_key(e, partition, metric)) is not None
        and replace(other, build=key.build) == key
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
    baseline_key = to_data(key)
    if baseline_key is not None:
        baseline_key.pop("build")
        baseline_key["build_policy"] = "recorded-per-entry; not filtered"
    baseline = {
        "key": baseline_key,
        "entries": len(applicable),
        "medians": medians,
        "excluded_incompatible": len(boss.cohort) - len(applicable),
        "builds_differing": sum(
            e.druid.build.value != subject.druid.build.value for e in applicable
        )
        if subject is not None
        else 0,
        "build_policy": "recorded-per-entry; not filtered",
        "limited_sample": len(applicable) < 3,
        "note": "Same class, encounter, faction, WCL category, duty, metric and partition. "
        "Builds are shown per source. Individual comparisons remain available with one or two "
        "sources; medians summarize three or more known values. Hybrid/uncertain/overridden duties "
        "have no aggregate baseline.",
    }
    top = _top_metadata(con, boss, partition, selected_category, metric, acquisition)
    subject_faction = (
        subject.profile.faction.value.value
        if subject is not None and subject.profile.faction.value is not None
        else ((acquisition or {}).get("key") or {}).get("faction", {}).get("value")
    )
    faction_top = (
        _top_metadata(con, boss, partition, selected_category, metric, acquisition, subject_faction)
        if subject_faction in ("Alliance", "Horde")
        else None
    )
    ranking = None if subject is None else _ranking(con, subject, metric)
    ranking_comparison = None
    ranking_reference = faction_top
    if ranking_reference is not None:
        ranking_comparison = {
            "player": ranking_reference["player"],
            "metric": ranking_reference["metric"],
            "scope": ranking_reference["scope"],
            "faction": ranking_reference["faction"],
            "faction_evidence": ranking_reference["faction_evidence"],
            "leaderboard_position": ranking_reference["leaderboard_position"],
            "report_code": ranking_reference["report_code"],
            "fight_id": ranking_reference["fight_id"],
            "reference_evidence": ranking_reference["category_score"],
            "basis": "saved-ranking-metadata",
            "n_sources": 1,
            **_difference(
                None if ranking is None else ranking["category_score"],
                ranking_reference["category_score"]["value"],
            ),
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
        FightRole.BALANCE: ["damage", "damage_per_second"],
        FightRole.FERAL: ["damage", "damage_per_second"],
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
        "subject": None if subject is None else section(subject),
        "cohort": [section(e) for e in applicable],
        "overall_cohort": [section(e) for e in boss.cohort],
        "benchmarks": {
            "ceiling": None,
            "baseline": baseline,
            "raid_speed": None,
            "cross_faction": None,
            "excluded": None,
            "overall_top": top,
        },
        "encounter": {
            "target_integrity": None,
            "raid_utility": None,
            "cohort_target_integrity": [],
        },
        "recommendations": [] if subject is None else _recommendations(subject, medians),
        "playbook": {
            "encounter_facts": to_data(gamedata.encounter_facts("naxxramas", boss.encounter_id)),
            "excluded_subject": section(boss.subject)
            if excluded is not None and boss.subject is not None
            else None,
            "selected_category": selected_category,
            "selected_metric": policy.metric if policy else metric,
            "personal_data": personal,
            "reference": None if reference is None else section(reference),
            "overall_reference": None if overall_reference is None else section(overall_reference),
            "selected_faction": selected_faction,
            "comparisons": []
            if subject is None
            else [_event_comparison(subject, e) for e in applicable],
            "ranking_comparison": ranking_comparison,
            "overall_comparison": None
            if subject is None or overall_reference is None
            else _event_comparison(subject, overall_reference),
            "same_faction_top": faction_top,
            "reference_note": "Highest-ranked acquired eligible example "
            "in your selected spec and faction; "
            "its build, race, buffs, fight duration and assignments may differ. "
            "Recorded differences do not establish their cause or an optimal rotation.",
            "guidance": practice + " Use the recorded first ten seconds as a practice example, "
            "not a universal optimal opener. Check assignments before copying it.",
            "primary_metrics": primary,
            "limitations": list(LIMITATIONS),
        },
    }
