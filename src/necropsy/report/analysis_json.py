"""Build the versioned analysis.json document from the analysis database.

analysis.json is the only input the report and playbook renderers use. It is
deterministic: the same snapshot and options always produce the same bytes
(no wall-clock time, rounded floats, ordered lists, sorted keys).
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import datetime
from typing import Annotated, Any, Literal

import duckdb
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from necropsy import __version__
from necropsy.analysis import gamedata
from necropsy.analysis.benchmark import (
    BossData,
    Entry,
    baseline,
    best_entry,
    hunter_pet_dps,
    load_bosses,
    membership,
    raid_speed,
    ranked_target_shares,
    split_by_faction,
)
from necropsy.analysis.encounters import encounter_rules
from necropsy.analysis.encounters.findings import raid_utility, target_integrity
from necropsy.analysis.evidence import (
    Claim,
    Evidenced,
    EvidenceLevel,
    EvidenceRef,
    observed,
    unknown,
)
from necropsy.analysis.generic.catalog import ItemName, item_catalog, rank_percent
from necropsy.analysis.generic.metrics import ability_counts
from necropsy.analysis.overview import build as build_overview
from necropsy.analysis.playbook import build as build_playbook
from necropsy.analysis.recommendations import Controllability, Tier, recommend
from necropsy.analysis.roles import RoleOverride
from necropsy.report.equipment import enrich_gear
from necropsy.report.serialize import to_data
from necropsy.rules import load_rules

SCHEMA_ID = "necropsy.analysis"
SCHEMA_VERSION = 1
GAME = "classic_era"
ZONE = "naxxramas"

HISTORICAL_LIMITATIONS = (
    "Historical mode: the cohort is the overall top five per boss recorded in the snapshot, "
    "not a separately queried same-faction top five.",
    "The same-faction ceiling is the best-ranked entry of the subject's faction inside that "
    "recorded top five.",
    "Same-faction medians come from that small recorded sample (at most five entries), not "
    "from a 20-30 entry metadata baseline.",
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventRef(_Strict):
    uid: str
    copy_: int = Field(alias="copy")


class Reference(_Strict):
    source: str
    report: str
    fight: int | None = None
    actor: int | None = None
    events: list[EventRef] | None = None
    event_count: int | None = Field(default=None, ge=0)
    detail: str | None = None


class CoverageReference(_Strict):
    report: str
    fight: int
    actor: int
    direction: Literal["source", "target"]
    trusted: bool


class Evidence(_Strict):
    """Every evidence object in the document, wherever it is nested."""

    value: Any
    level: EvidenceLevel
    claim: Claim
    rule: str | None = None
    params: dict[str, Any] | None = None
    note: str | None = None
    refs: list[Reference] | None = None
    coverage: list[CoverageReference] | None = None

    @model_validator(mode="after")
    def _unknown_has_no_value(self) -> Evidence:
        if self.level is EvidenceLevel.UNKNOWN and self.value is not None:
            raise ValueError("an unknown value must be null")
        if self.level is not EvidenceLevel.UNKNOWN and self.value is None:
            raise ValueError(f"a {self.level.value} value must not be null")
        return self


def _evidence_tree(node: Any) -> Any:
    """Validate every nested object shaped like evidence (has `level` and `claim`)."""
    if isinstance(node, dict):
        if "level" in node and "claim" in node:
            Evidence.model_validate(node)
            _evidence_tree(node.get("value"))
        else:
            for child in node.values():
                _evidence_tree(child)
    elif isinstance(node, list):
        for child in node:
            _evidence_tree(child)
    return node


EvidenceTree = Annotated[dict[str, Any], AfterValidator(_evidence_tree)]
"""An analysis section: free-form keys whose evidence objects are all validated."""


class Options(_Strict):
    cross_faction: bool


class Snapshot(_Strict):
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope: Literal["full", "subset"]
    format: str
    source_fight_count: int = Field(ge=0)
    selected_fights: int = Field(ge=0)
    database_schema_version: int


class Subject(_Strict):
    id: int
    name: str
    server: str
    region: str
    class_id: int


class Zone(_Strict):
    id: int
    name: str
    partition: int | None


class CohortInfo(_Strict):
    kind: str
    top_n: int
    limitations: list[str]


class CoverageSummary(_Strict):
    streams: int = Field(ge=0)
    streams_not_complete: int = Field(ge=0)
    event_anomalies: int = Field(ge=0)
    snapshot_issues: int = Field(ge=0)


class ExclusionRule(_Strict):
    rule: str
    basis: Literal["empirical", "none"]
    """`empirical`: found from recorded rankings, not from WCL documentation."""
    validation: str | None


class BossRules(_Strict):
    ranking_exclusions: list[int]
    ranking_exclusion_rule: ExclusionRule
    native_targets: list[int] | None


class EntrySection(_Strict):
    player: str
    server: str | None
    kind: str
    leaderboard_position: int | None
    report_code: str
    fight_id: int
    kill_duration_s: float = Field(gt=0)
    environment: EvidenceTree
    ranking: EvidenceTree
    raptor_roles: EvidenceTree
    hunter: EvidenceTree | None = None
    druid: EvidenceTree | None = None
    combat: EvidenceTree | None = None
    ability_use: Evidence | None = None
    pets_listed: bool | None = None
    set_pieces: list[dict[str, Any]] | None = None
    set_armor: list[dict[str, Any]] | None = None
    """Item sets worn with two or more pieces (game client data); absent in older documents."""
    """Whether the export listed this Hunter's pets; None in documents written before
    this field existed (read as unknown)."""


class Ceiling(_Strict):
    label: str
    player: str
    leaderboard_position: int | None
    ranked_dps: float | None
    ranked_dps_evidence: Evidence | None = None
    kill_duration_s: float
    membership: Evidence


class Excluded(_Strict):
    other_faction: int = Field(ge=0)
    unknown_faction: int = Field(ge=0)


class CrossFaction(_Strict):
    label: str
    baseline: EvidenceTree
    rank_one: str | None


class Benchmarks(_Strict):
    ceiling: Ceiling | None
    baseline: EvidenceTree | None
    raid_speed: EvidenceTree | None
    cross_faction: CrossFaction | None
    excluded: Excluded | None
    overall_top: EvidenceTree | None = None
    """Recorded leaderboard rank 1, any faction (absent in older documents)."""
    overall_top_unavailable_reason: str | None = None
    faction_mix: dict[str, Any] | None = None


class EncounterFindings(_Strict):
    target_integrity: EvidenceTree | None
    raid_utility: EvidenceTree | None
    cohort_target_integrity: list[EvidenceTree]
    cohort_median_foreign_share_pct: float | None = None
    ranked_target_shares: EvidenceTree | None = None


class BenchmarkRef(BaseModel):
    model_config = ConfigDict(extra="allow")

    """Empty for findings about the subject alone (no benchmark view)."""

    view: str | None = None
    n_known: int | None = Field(default=None, ge=0)


class RecommendationSection(_Strict):
    rule: str
    boss: str
    category: str
    controllability: Controllability
    severity: Tier
    confidence: Tier
    finding: str
    recommendation: str
    observed: dict[str, Any]
    benchmark: BenchmarkRef
    evidence: list[str] = Field(min_length=1)
    """Dotted paths into the same boss section."""
    limitations: list[str]


class BossSection(_Strict):
    encounter_id: int
    boss: str
    rules: BossRules
    subject: EntrySection | None
    benchmarks: Benchmarks
    encounter: EncounterFindings
    cohort: list[EntrySection]
    recommendations: list[RecommendationSection]
    overall_cohort: list[EntrySection] | None = None
    playbook: dict[str, Any] | None = None
    """Structured playbook decisions (rule set playbook-v1); absent in older documents."""
    """Every recorded leaderboard row, any faction, for context (absent in older documents)."""


class AnalysisDocument(_Strict):
    """Top-level structure of analysis.json (schema_version 1)."""

    schema_id: Literal["necropsy.analysis"]
    schema_version: Literal[1]
    necropsy_version: str
    mode: Literal["historical", "live"]
    options: Options
    snapshot: Snapshot
    subject: Subject
    zone: Zone
    cohort: CohortInfo
    coverage: CoverageSummary
    bosses: list[BossSection]
    overview: EvidenceTree | None = None
    """Zone-wide summaries (rule set overview-v1); absent in older documents."""
    game_data: dict[str, Any] | None = None
    """Where the static item/set/enchant data comes from (game client build)."""
    acquisition: dict[str, Any] | None = None
    """Live snapshots: every requested boss with its acquisition coverage, the run's
    endpoint, stop reason and cohort provenance. Absent for historical snapshots."""


Names = dict[int, ItemName]


def _set_pieces(e: Entry) -> list[dict[str, Any]] | None:
    gear = e.profile.gear.value
    if gear is None:
        return None
    return [
        {"set": name, "pieces": n}
        for name, n in gamedata.set_pieces(g.item_id for g in gear if g.item_id)
    ]


def _set_armor(e: Entry) -> list[dict[str, Any]] | None:
    gear = e.profile.gear.value
    if gear is None:
        return None
    return [to_data(s) for s in gamedata.set_armor(g.item_id for g in gear if g.item_id)]


def _leaderboard_top(con: duckdb.DuckDBPyConnection, boss: BossData) -> dict[str, Any] | None:
    meta = con.execute("SELECT mode, partition_id, acquisition FROM snapshot_meta").fetchone()
    if meta is None or meta[0] != "live":
        return None
    acquisition = _json(meta[2]) or {}
    record: dict[str, Any] = next(
        (r for r in acquisition.get("bosses") or [] if r.get("encounter_id") == boss.encounter_id),
        {},
    )
    key = record.get("key") or {}
    if set(key) != {
        "site",
        "game",
        "zone",
        "partition",
        "encounter",
        "role",
        "class_name",
        "difficulty",
        "faction",
        "size",
        "spec",
    }:
        return None
    required = {
        "site": "vanilla.warcraftlogs.com",
        "game": GAME,
        "zone": 2006,
        "partition": meta[1],
        "encounter": boss.encounter_id,
        "role": "dps",
        "class_name": "Hunter",
        "difficulty": 0,
    }
    for name, value in required.items():
        dim = key.get(name) or {}
        if (
            type(dim.get("value")) is not type(value)
            or dim.get("value") != value
            or dim.get("status") != "enforced"
        ):
            return None
    size, spec = key.get("size") or {}, key.get("spec") or {}
    if (
        size.get("value") is not None
        or size.get("status") != "recorded"
        or not (
            (spec.get("value") == "all Hunter specs" and spec.get("status") == "recorded")
            or (spec.get("value") == "Marksmanship" and spec.get("status") == "enforced")
        )
    ):
        return None
    rows = con.execute(
        """SELECT source, raw FROM rankings WHERE kind = 'leaderboard'
           AND encounter_id = ? AND page = 1 AND row_index = 0
           AND starts_with(source, 'leaderboards/')""",
        [boss.encounter_id],
    ).fetchall()
    if len(rows) != 1:
        return None
    source_member, raw = rows[0]
    row = _json(raw)
    amount, difficulty = row.get("amount"), row.get("hardModeLevel")
    if (
        type(amount) not in (int, float)
        or not math.isfinite(amount)
        or amount < 0
        or not (
            row.get("class") == "Hunter" or (type(row.get("class")) is int and row["class"] == 3)
        )
        or type(difficulty) is not int
        or difficulty != 0
        or not isinstance(row.get("name"), str)
        or not row["name"].strip()
    ):
        return None
    for ordering in ("rank", "position"):
        if ordering in row and (type(row[ordering]) is not int or row[ordering] != 1):
            return None
    report = row.get("report") or {}
    if spec.get("status") == "enforced" and row.get("spec") != spec.get("value"):
        return None
    code = report.get("code") if isinstance(report, dict) else None
    fight = report.get("fightID") if isinstance(report, dict) else None
    ref = EvidenceRef(
        code if isinstance(code, str) else "",
        fight if type(fight) is int else None,
        None,
        "leaderboard",
        detail=f"{source_member}, page 1 row 0; Hunter DPS; partition {meta[1]}",
    )
    faction: Evidenced[str] = unknown("character faction is not proven by ranking metadata", ref)
    verdicts = [
        v
        for v in (record.get("selection") or {}).get("verdicts", [])
        if v.get("position") == 1 and v.get("status") == "observed"
    ]
    if len(verdicts) == 1 and verdicts[0].get("faction") in ("Alliance", "Horde"):
        faction = observed(
            verdicts[0]["faction"],
            EvidenceRef(
                code if isinstance(code, str) else "",
                fight if type(fight) is int else None,
                None,
                "acquisition",
                detail="rank 1 faction verification: " + str(verdicts[0].get("reason")),
            ),
        )
    captured = (record.get("selection") or {}).get("leaderboard_captured_at")
    if captured is not None:
        try:
            if datetime.fromisoformat(captured).utcoffset() is None:
                captured = None
        except TypeError, ValueError:
            captured = None
    return {
        "player": row["name"],
        "leaderboard_position": 1,
        "ranked_dps": float(amount),
        "ranked_dps_evidence": to_data(observed(float(amount), ref)),
        "faction": to_data(faction),
        "kill_duration_s": row["duration"] / 1000.0
        if type(row.get("duration")) is int and row["duration"] > 0
        else None,
        "basis": "leaderboard-metadata",
        "source_member": source_member,
        "captured_at": captured,
        "event_sample_acquired": False,
    }


def _overall_top(
    con: duckdb.DuckDBPyConnection, boss: BossData
) -> tuple[dict[str, Any] | None, str | None]:
    """Rank 1 of the recorded leaderboard, whatever its faction; None if not recorded."""
    first = [e for e in boss.cohort if e.participant.leaderboard_position == 1]
    if len(first) != 1:
        return _leaderboard_top(con, boss), None
    e = first[0]
    if e.ranked_dps is None:
        metadata = _leaderboard_top(con, boss)
        if metadata is not None:
            ref = metadata["ranked_dps_evidence"]["refs"][0]
            if (
                metadata["player"] == e.participant.player
                and ref["report"] == e.participant.report_code
                and ref["fight"] == e.participant.fight_id
            ):
                metadata["faction"] = to_data(e.profile.faction)
                metadata["kill_duration_s"] = e.participant.duration_ms / 1000.0
                metadata["event_sample_acquired"] = True
                return metadata, None
            return None, "Rank-one identity conflicts between acquired entry and saved leaderboard."
    result = {
        "player": e.participant.player,
        "leaderboard_position": 1,
        "faction": to_data(e.profile.faction),
        "ranked_dps": None if e.ranked_dps is None else round(e.ranked_dps, 6),
        **({"ranked_dps_evidence": to_data(e.recorded_dps)} if e.recorded_dps is not None else {}),
        "kill_duration_s": e.participant.duration_ms / 1000.0,
    }
    return result, None


def _faction_mix(boss: BossData, split: Any) -> dict[str, Any]:
    by: dict[str, int] = {}
    inferred = 0
    for e in boss.cohort:
        faction = e.profile.faction
        key = "unknown" if faction.value is None else str(faction.value.value)
        by[key] = by.get(key, 0) + 1
        if faction.level is EvidenceLevel.INFERRED:
            inferred += 1
    return {
        "recorded_entries": len(boss.cohort),
        "by_faction": dict(sorted(by.items())),
        "inferred_faction_entries": inferred,
        "same_faction": None if split is None else len(split.same_faction),
        "other_faction": None if split is None else len(split.other_faction),
        "unknown_faction": None if split is None else len(split.unknown_faction),
    }


def _entry(
    con: duckdb.DuckDBPyConnection, e: Entry, names: Names, detail: bool, percent: Any = None
) -> dict[str, Any]:
    pf = e.participant
    hunter = to_data(e.hunter)
    hunter["total_pet_dps"] = to_data(hunter_pet_dps(e))
    hunter["pet_roster_complete"] = e.hunter_pets_listed
    hunter.pop("participant", None)
    if not detail:
        hunter.pop("auto_intervals", None)
    gear = to_data(e.profile.gear)
    gear["value"] = enrich_gear(gear["value"], names)
    env = to_data(e.profile)
    env.pop("participant", None)
    env["gear"] = gear
    dps = e.ranked_dps
    return {
        "player": pf.player,
        "server": pf.server,
        "kind": pf.kind,
        "leaderboard_position": pf.leaderboard_position,
        "report_code": pf.report_code,
        "fight_id": pf.fight_id,
        "kill_duration_s": pf.duration_ms / 1000.0,
        "environment": env,
        "ranking": {
            **to_data(e.ranking),
            "ranked_dps": None if dps is None else round(dps, 6),
            **(
                {"ranked_dps_evidence": to_data(e.recorded_dps)}
                if e.recorded_dps is not None
                else {}
            ),
            "rank_percent": None if percent is None else to_data(percent),
        },
        "raptor_roles": to_data(e.raptor_roles),
        "pets_listed": e.pets_listed,
        "set_pieces": _set_pieces(e),
        "set_armor": _set_armor(e),
        "hunter": hunter,
        "ability_use": to_data(ability_counts(con, pf)),
    }


def _boss(
    con: duckdb.DuckDBPyConnection, boss: BossData, cross_faction: bool, names: Names
) -> dict[str, Any]:
    split = split_by_faction(boss)
    subject = boss.subject
    rules = {
        "ranking_exclusions": sorted(boss.rules.ranking_excluded_game_ids),
        "ranking_exclusion_rule": {
            "rule": boss.rules.exclusion_rule,
            "basis": boss.rules.exclusion_basis,
            "validation": boss.rules.exclusion_validation,
        },
        "native_targets": None
        if boss.rules.native_game_ids is None
        else sorted(boss.rules.native_game_ids),
    }
    encounter: dict[str, Any] = {
        "target_integrity": None,
        "raid_utility": None,
        "cohort_target_integrity": [],
    }
    top, top_reason = _overall_top(con, boss)
    benchmarks: dict[str, Any] = {
        "ceiling": None,
        "baseline": None,
        "raid_speed": None,
        "cross_faction": None,
        "excluded": None,
        "overall_top": top,
        "faction_mix": _faction_mix(boss, split),
    }
    if top_reason is not None:
        benchmarks["overall_top_unavailable_reason"] = top_reason
    recommendations: list[dict[str, Any]] = []
    cohort_rows: list[Entry] = []
    playbook: Any = None
    if subject is not None:
        encounter["raid_utility"] = to_data(raid_utility(subject.hunter))
    if subject is not None and split is not None:
        base = baseline(split.same_faction, subject, fill_candidates=split.other_faction)
        comparator = best_entry(split.same_faction)
        benchmarks["ceiling"] = (
            None
            if comparator is None
            else {
                "label": "best same-faction entry inside the recorded overall top five",
                "player": comparator.participant.player,
                "leaderboard_position": comparator.participant.leaderboard_position,
                "ranked_dps": None
                if comparator.ranked_dps is None
                else round(comparator.ranked_dps, 6),
                **(
                    {"ranked_dps_evidence": to_data(comparator.recorded_dps)}
                    if comparator.recorded_dps is not None
                    else {}
                ),
                "kill_duration_s": comparator.participant.duration_ms / 1000.0,
                "membership": to_data(membership((comparator,), subject)),
            }
        )
        benchmarks["baseline"] = to_data(base)
        speed = raid_speed(split.same_faction, subject, base)
        encounter["ranked_target_shares"] = to_data(
            ranked_target_shares(split.same_faction, subject, base.membership)
        )
        benchmarks["raid_speed"] = to_data(speed)
        benchmarks["excluded"] = {
            "other_faction": len(split.other_faction),
            "unknown_faction": len(split.unknown_faction),
        }
        cohort_rows = list(split.same_faction)
        if cross_faction:
            everyone = boss.cohort
            benchmarks["cross_faction"] = {
                "label": "all recorded top-five entries, any faction; not a realistic "
                "benchmark for the subject",
                "baseline": to_data(baseline(everyone, subject, same_faction=False)),
                "rank_one": everyone[0].participant.player if everyone else None,
            }
            cohort_rows = list(everyone)
        integrity_subject = None
        shares: list[float] = []
        if boss.rules.native_game_ids is not None:
            integrity_subject = _integrity(con, boss, subject)
            for e in split.same_faction:
                ti = _integrity(con, boss, e)
                if ti is not None and ti.foreign_share_pct.value is not None:
                    shares.append(ti.foreign_share_pct.value)
                    encounter["cohort_target_integrity"].append(
                        {"player": e.participant.player, **to_data(ti)}
                    )
            encounter["target_integrity"] = to_data(integrity_subject)
        recommendations = [
            to_data(r)
            for r in recommend(
                boss,
                split,
                base,
                speed,
                raid_utility(subject.hunter),
                integrity_subject,
                shares,
                {i: n.name for i, n in names.items() if n.name},
            )
        ]
        encounter["cohort_median_foreign_share_pct"] = (
            statistics.median(shares) if len(shares) >= 3 else None
        )
        playbook = build_playbook(
            boss,
            split.same_faction,
            split.other_faction,
            base,
            comparator,
            speed,
            raid_utility(subject.hunter),
            integrity_subject,
            encounter["cohort_median_foreign_share_pct"],
        )
    return {
        "encounter_id": boss.encounter_id,
        "boss": boss.boss,
        "rules": rules,
        "subject": None
        if subject is None
        else _entry(
            con, subject, names, detail=True, percent=rank_percent(con, subject.participant)
        ),
        "benchmarks": benchmarks,
        "encounter": encounter,
        "cohort": [_entry(con, e, names, detail=False) for e in cohort_rows],
        # Every recorded leaderboard row, any faction: context only. Baselines,
        # ceilings and recommendations still use the same-faction cohort.
        "overall_cohort": [_entry(con, e, names, detail=False) for e in boss.cohort],
        "playbook": to_data(playbook),
        "recommendations": recommendations,
    }


def _integrity(con: duckdb.DuckDBPyConnection, boss: BossData, entry: Entry) -> Any:
    return target_integrity(
        con, entry.participant, boss.rules, [entry.participant.actor_id], "hunter"
    )


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def build_document(
    con: duckdb.DuckDBPyConnection,
    cross_faction: bool = False,
    role_overrides: dict[tuple[str, int], RoleOverride] | None = None,
) -> dict[str, Any]:
    meta = con.execute(
        """SELECT archive_sha256, scope, format, source_fight_count, selected_fights,
                  subject_id, subject_name, subject_server, subject_region,
                  subject_class_id, zone_id, zone_name, partition_id, cohort, top_n,
                  schema_version, mode, limitations, acquisition FROM snapshot_meta"""
    ).fetchone()
    assert meta is not None
    cov = con.execute(
        """SELECT count(*), count(*) FILTER (WHERE status <> 'complete'),
                  (SELECT count(*) FROM event_anomalies),
                  (SELECT count(*) FROM snapshot_issues) FROM stream_coverage"""
    ).fetchone()
    assert cov is not None
    mode = "live" if meta[16] == "live" else "historical"
    limitations = (
        list(HISTORICAL_LIMITATIONS) if mode == "historical" else list(_json(meta[17]) or [])
    )
    acquisition = _json(meta[18]) if mode == "live" else None
    names = item_catalog(con)
    boss_data = load_bosses(con, GAME, ZONE, role_overrides)
    if meta[9] != 3:
        from functools import partial

        from necropsy.report.combat import boss_section as combat_boss
        from necropsy.report.druid import boss_section as druid_boss

        make_boss = druid_boss if meta[9] == 2 else partial(combat_boss, class_id=meta[9])

        records = {b["encounter_id"]: b for b in (acquisition or {}).get("bosses", [])}
        categories = {
            ((r.get("key") or {}).get("spec") or {}).get("value") for r in records.values()
        } - {None}
        category = (acquisition or {}).get("selected_category")
        if category is None and len(categories) == 1:
            category = next(iter(categories))
        if category is None and meta[9] != 2:
            categories = {
                e.combat.ranking_category.value
                for b in boss_data
                for e in ((b.subject,) if b.subject else ()) + b.cohort
            } - {None}
            if len(categories) == 1:
                category = next(iter(categories))
        if acquisition is not None:
            acquisition = {**acquisition, "selected_category": category}
        present = {b.encounter_id for b in boss_data}
        boss_data += [
            BossData(eid, r["boss"], encounter_rules(GAME, ZONE, eid), None, ())
            for eid, r in records.items()
            if eid not in present
        ]
        order = {
            int(e["id"]): i for i, e in enumerate(load_rules(GAME, f"zones/{ZONE}")["encounters"])
        }
        boss_data.sort(key=lambda b: order.get(b.encounter_id, 999))
        bosses = [
            make_boss(
                con,
                b,
                meta[12],
                ((records.get(b.encounter_id, {}).get("key") or {}).get("metric") or {}).get(
                    "value"
                ),
                category,
                records.get(b.encounter_id),
            )
            for b in boss_data
        ]
    else:
        if acquisition is not None and acquisition.get("selected_category"):
            present = {b.encounter_id for b in boss_data}
            boss_data += [
                BossData(
                    r["encounter_id"],
                    r["boss"],
                    encounter_rules(GAME, ZONE, r["encounter_id"]),
                    None,
                    (),
                )
                for r in acquisition.get("bosses", [])
                if r["encounter_id"] not in present
            ]
        bosses = [_boss(con, b, cross_faction, names) for b in boss_data]
    document = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "necropsy_version": __version__,
        "mode": mode,
        "options": {"cross_faction": cross_faction},
        "snapshot": {
            "archive_sha256": meta[0],
            "scope": meta[1],
            "format": meta[2],
            "source_fight_count": meta[3],
            "selected_fights": meta[4],
            "database_schema_version": meta[15],
        },
        "subject": {
            "id": meta[5],
            "name": meta[6],
            "server": meta[7],
            "region": meta[8],
            "class_id": meta[9],
        },
        "zone": {"id": meta[10], "name": meta[11], "partition": meta[12]},
        "cohort": {
            "kind": meta[13],
            "top_n": meta[14],
            "limitations": limitations,
        },
        "coverage": {
            "streams": cov[0],
            "streams_not_complete": cov[1],
            "event_anomalies": cov[2],
            "snapshot_issues": cov[3],
        },
        "bosses": bosses,
        "overview": to_data(build_overview(boss_data)) if meta[9] == 3 else None,
        "game_data": gamedata.source(),
    }
    if acquisition is not None:
        document["acquisition"] = acquisition
    AnalysisDocument.model_validate(document)
    return document


def dumps(document: dict[str, Any]) -> str:
    return json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def json_schema() -> dict[str, Any]:
    return AnalysisDocument.model_json_schema()
