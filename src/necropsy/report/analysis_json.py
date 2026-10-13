"""Build the versioned analysis.json document from the analysis database.

analysis.json is the only input the report and playbook renderers use. It is
deterministic: the same snapshot and options always produce the same bytes
(no wall-clock time, rounded floats, ordered lists, sorted keys).
"""

from __future__ import annotations

import json
import statistics
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
    load_bosses,
    membership,
    raid_speed,
    ranked_target_shares,
    split_by_faction,
)
from necropsy.analysis.encounters.findings import raid_utility, target_integrity
from necropsy.analysis.evidence import Claim, EvidenceLevel
from necropsy.analysis.generic.catalog import ItemName, item_catalog, rank_percent
from necropsy.analysis.overview import build as build_overview
from necropsy.analysis.playbook import build as build_playbook
from necropsy.analysis.recommendations import Controllability, Tier, recommend
from necropsy.report.serialize import to_data

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
    hunter: EvidenceTree
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
    mode: Literal["historical"]
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


Names = dict[int, ItemName]


def _gear(items: Any, names: Names) -> Any:
    if not isinstance(items, list):
        return items
    out = []
    for g in items:
        if not isinstance(g, dict):
            out.append(g)
            continue
        found = names.get(int(g["item_id"]))
        out.append(
            {
                **g,
                "name": None if found is None else found.name,
                "name_source": "none" if found is None else found.source,
                "name_note": None if found is None else found.note,
                "enchant_name": gamedata.enchant_names().get(int(g.get("permanent_enchant") or 0)),
                "temporary_enchant_name": gamedata.enchant_names().get(
                    int(g.get("temporary_enchant") or 0)
                ),
            }
        )
    return out


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


def _overall_top(boss: BossData) -> dict[str, Any] | None:
    """Rank 1 of the recorded leaderboard, whatever its faction; None if not recorded."""
    first = [e for e in boss.cohort if e.participant.leaderboard_position == 1]
    if len(first) != 1:
        return None
    e = first[0]
    return {
        "player": e.participant.player,
        "leaderboard_position": 1,
        "faction": to_data(e.profile.faction),
        "ranked_dps": None if e.ranked_dps is None else round(e.ranked_dps, 6),
        "kill_duration_s": e.participant.duration_ms / 1000.0,
    }


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


def _entry(e: Entry, names: Names, detail: bool, percent: Any = None) -> dict[str, Any]:
    pf = e.participant
    hunter = to_data(e.hunter)
    hunter.pop("participant", None)
    if not detail:
        hunter.pop("auto_intervals", None)
    gear = to_data(e.profile.gear)
    gear["value"] = _gear(gear["value"], names)
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
            "rank_percent": None if percent is None else to_data(percent),
        },
        "raptor_roles": to_data(e.raptor_roles),
        "pets_listed": e.pets_listed,
        "set_pieces": _set_pieces(e),
        "set_armor": _set_armor(e),
        "hunter": hunter,
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
    benchmarks: dict[str, Any] = {
        "ceiling": None,
        "baseline": None,
        "raid_speed": None,
        "cross_faction": None,
        "excluded": None,
        "overall_top": _overall_top(boss),
        "faction_mix": _faction_mix(boss, split),
    }
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
        else _entry(subject, names, detail=True, percent=rank_percent(con, subject.participant)),
        "benchmarks": benchmarks,
        "encounter": encounter,
        "cohort": [_entry(e, names, detail=False) for e in cohort_rows],
        # Every recorded leaderboard row, any faction: context only. Baselines,
        # ceilings and recommendations still use the same-faction cohort.
        "overall_cohort": [_entry(e, names, detail=False) for e in boss.cohort],
        "playbook": to_data(playbook),
        "recommendations": recommendations,
    }


def _integrity(con: duckdb.DuckDBPyConnection, boss: BossData, entry: Entry) -> Any:
    return target_integrity(
        con, entry.participant, boss.rules, [entry.participant.actor_id], "hunter"
    )


def build_document(con: duckdb.DuckDBPyConnection, cross_faction: bool = False) -> dict[str, Any]:
    meta = con.execute(
        """SELECT archive_sha256, scope, format, source_fight_count, selected_fights,
                  subject_id, subject_name, subject_server, subject_region,
                  subject_class_id, zone_id, zone_name, partition_id, cohort, top_n,
                  schema_version FROM snapshot_meta"""
    ).fetchone()
    assert meta is not None
    cov = con.execute(
        """SELECT count(*), count(*) FILTER (WHERE status <> 'complete'),
                  (SELECT count(*) FROM event_anomalies),
                  (SELECT count(*) FROM snapshot_issues) FROM stream_coverage"""
    ).fetchone()
    assert cov is not None
    names = item_catalog(con)
    boss_data = load_bosses(con, GAME, ZONE)
    bosses = [_boss(con, b, cross_faction, names) for b in boss_data]
    document = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "necropsy_version": __version__,
        "mode": "historical",
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
            "limitations": list(HISTORICAL_LIMITATIONS),
        },
        "coverage": {
            "streams": cov[0],
            "streams_not_complete": cov[1],
            "event_anomalies": cov[2],
            "snapshot_issues": cov[3],
        },
        "bosses": bosses,
        "overview": to_data(build_overview(boss_data)),
        "game_data": gamedata.source(),
    }
    AnalysisDocument.model_validate(document)
    return document


def dumps(document: dict[str, Any]) -> str:
    return json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def json_schema() -> dict[str, Any]:
    return AnalysisDocument.model_json_schema()
