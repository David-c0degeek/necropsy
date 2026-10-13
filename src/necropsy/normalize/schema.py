"""DuckDB schema for normalized snapshots. Every column type is declared.

The database is always rebuilt from the raw snapshot; there are no in-place
migrations. Bump SCHEMA_VERSION whenever a table or column changes.
"""

from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION = 2


@dataclass(frozen=True)
class Table:
    name: str
    columns: tuple[tuple[str, str], ...]

    def ddl(self) -> str:
        cols = ",\n  ".join(f"{name} {sql_type}" for name, sql_type in self.columns)
        return f"CREATE TABLE {self.name} (\n  {cols}\n)"

    def column_types(self) -> dict[str, str]:
        return dict(self.columns)


SNAPSHOT_META = Table(
    "snapshot_meta",
    (
        ("schema_version", "INTEGER"),
        ("format", "VARCHAR"),
        ("archive_sha256", "VARCHAR"),
        ("scope", "VARCHAR"),
        ("subject_id", "BIGINT"),
        ("subject_name", "VARCHAR"),
        ("subject_class_id", "INTEGER"),
        ("subject_server", "VARCHAR"),
        ("subject_region", "VARCHAR"),
        ("zone_id", "INTEGER"),
        ("zone_name", "VARCHAR"),
        ("partition_id", "INTEGER"),
        ("cohort", "VARCHAR"),
        ("top_n", "INTEGER"),
        ("selected_fights", "INTEGER"),
        ("source_fight_count", "INTEGER"),
        ("source_errors", "JSON"),
        ("necropsy_version", "VARCHAR"),
        ("mode", "VARCHAR"),
        ("limitations", "JSON"),
        ("acquisition", "JSON"),
    ),
)

SNAPSHOT_ISSUES = Table("snapshot_issues", (("issue", "VARCHAR"),))

BENCHMARK_PARTICIPANTS = Table(
    "benchmark_participants",
    (
        ("report_code", "VARCHAR"),
        ("fight_id", "INTEGER"),
        ("kind", "VARCHAR"),
        ("boss", "VARCHAR"),
        ("encounter_id", "INTEGER"),
        ("player", "VARCHAR"),
        ("server", "VARCHAR"),
        ("leaderboard_position", "INTEGER"),
        ("total", "DOUBLE"),
        ("duration_ms", "BIGINT"),
        ("spec", "VARCHAR"),
    ),
)

REPORTS = Table(
    "reports",
    (
        ("report_code", "VARCHAR"),
        ("title", "VARCHAR"),
        ("start_time", "BIGINT"),
        ("end_time", "BIGINT"),
        ("revision", "INTEGER"),
        ("visibility", "VARCHAR"),
        ("is_archived", "BOOLEAN"),
        ("zone_id", "INTEGER"),
        ("log_version", "INTEGER"),
        ("game_version", "INTEGER"),
    ),
)

FIGHTS = Table(
    "fights",
    (
        ("report_code", "VARCHAR"),
        ("fight_id", "INTEGER"),
        ("encounter_id", "INTEGER"),
        ("name", "VARCHAR"),
        ("start_time", "BIGINT"),
        ("end_time", "BIGINT"),
        ("kill", "BOOLEAN"),
        ("difficulty", "INTEGER"),
        ("size", "INTEGER"),
        ("average_item_level", "DOUBLE"),
        ("friendly_players", "JSON"),
        ("enemy_npcs", "JSON"),
        ("friendly_pets", "JSON"),
    ),
)

ACTORS = Table(
    "actors",
    (
        ("report_code", "VARCHAR"),
        ("actor_id", "INTEGER"),
        ("name", "VARCHAR"),
        ("type", "VARCHAR"),
        ("sub_type", "VARCHAR"),
        ("server", "VARCHAR"),
        ("game_id", "BIGINT"),
        ("pet_owner", "INTEGER"),
        ("icon", "VARCHAR"),
    ),
)

ABILITIES = Table(
    "abilities",
    (
        ("report_code", "VARCHAR"),
        ("game_id", "BIGINT"),
        ("name", "VARCHAR"),
        ("type", "VARCHAR"),
        ("icon", "VARCHAR"),
    ),
)

PLAYER_DETAILS = Table(
    "player_details",
    (
        ("report_code", "VARCHAR"),
        ("role", "VARCHAR"),
        ("actor_id", "INTEGER"),
        ("name", "VARCHAR"),
        ("server", "VARCHAR"),
        ("class", "VARCHAR"),
        ("icon", "VARCHAR"),
        ("specs", "JSON"),
        ("faction_id", "INTEGER"),
        ("combatant_info", "JSON"),
    ),
)

REPORT_RANKINGS = Table(
    "report_rankings",
    (
        ("report_code", "VARCHAR"),
        ("fight_id", "INTEGER"),
        ("encounter_id", "INTEGER"),
        ("partition_id", "INTEGER"),
        ("duration_ms", "BIGINT"),
        ("raw", "JSON"),
    ),
)

RANKINGS = Table(
    "rankings",
    (
        ("source", "VARCHAR"),
        ("kind", "VARCHAR"),
        ("encounter_id", "INTEGER"),
        ("encounter_name", "VARCHAR"),
        ("page", "INTEGER"),
        ("row_index", "INTEGER"),
        ("player", "VARCHAR"),
        ("amount", "DOUBLE"),
        ("report_code", "VARCHAR"),
        ("fight_id", "INTEGER"),
        ("raw", "JSON"),
    ),
)

COMBATANT_INFO = Table(
    "combatant_info",
    (
        ("report_code", "VARCHAR"),
        ("fight_id", "INTEGER"),
        ("actor_id", "INTEGER"),
        ("timestamp", "BIGINT"),
        ("faction", "INTEGER"),
        ("spec_id", "INTEGER"),
        ("talent_points", "VARCHAR"),
        ("talents", "JSON"),
        ("gear", "JSON"),
        ("auras", "JSON"),
        ("event_uid", "VARCHAR"),
    ),
)

STREAM_COVERAGE = Table(
    "stream_coverage",
    (
        ("report_code", "VARCHAR"),
        ("fight_id", "INTEGER"),
        ("actor_id", "INTEGER"),
        ("actor_name", "VARCHAR"),
        ("role", "VARCHAR"),
        ("direction", "VARCHAR"),
        ("owner_actor_id", "INTEGER"),
        ("status", "VARCHAR"),
        ("pages", "INTEGER"),
        ("raw_events", "BIGINT"),
        ("boundary_ambiguities", "INTEGER"),
        ("multiplicity_mismatches", "INTEGER"),
        ("detail", "VARCHAR"),
    ),
)

EVENTS = Table(
    "events",
    (
        ("report_code", "VARCHAR"),
        ("fight_id", "INTEGER"),
        ("event_uid", "VARCHAR"),
        ("copy_index", "INTEGER"),
        ("timestamp", "BIGINT"),
        ("type", "VARCHAR"),
        ("source_id", "BIGINT"),
        ("source_instance", "BIGINT"),
        ("source_is_friendly", "BOOLEAN"),
        ("target_id", "BIGINT"),
        ("target_instance", "BIGINT"),
        ("target_is_friendly", "BOOLEAN"),
        ("ability_game_id", "BIGINT"),
        ("extra_ability_game_id", "BIGINT"),
        ("hit_type", "INTEGER"),
        ("amount", "BIGINT"),
        ("unmitigated_amount", "BIGINT"),
        ("absorbed", "BIGINT"),
        ("overheal", "BIGINT"),
        ("overkill", "BIGINT"),
        ("mitigated", "BIGINT"),
        ("resisted", "BIGINT"),
        ("blocked", "BIGINT"),
        ("stack", "INTEGER"),
        ("extra_attacks", "INTEGER"),
        ("is_aoe", "BOOLEAN"),
        ("tick", "BOOLEAN"),
        ("melee", "BOOLEAN"),
        ("killer_id", "BIGINT"),
        ("killing_ability_game_id", "BIGINT"),
        ("resource_actor", "INTEGER"),
        ("hit_points", "BIGINT"),
        ("max_hit_points", "BIGINT"),
        ("x", "BIGINT"),
        ("y", "BIGINT"),
        ("raw", "JSON"),
    ),
)

EVENT_ANOMALIES = Table(
    "event_anomalies",
    (
        ("report_code", "VARCHAR"),
        ("fight_id", "INTEGER"),
        ("kind", "VARCHAR"),
        ("event_uid", "VARCHAR"),
        ("detail", "VARCHAR"),
    ),
)

# Raw event field -> events column, for the typed "hot" columns.
EVENT_FIELDS: tuple[tuple[str, str], ...] = (
    ("timestamp", "timestamp"),
    ("type", "type"),
    ("sourceID", "source_id"),
    ("sourceInstance", "source_instance"),
    ("sourceIsFriendly", "source_is_friendly"),
    ("targetID", "target_id"),
    ("targetInstance", "target_instance"),
    ("targetIsFriendly", "target_is_friendly"),
    ("abilityGameID", "ability_game_id"),
    ("extraAbilityGameID", "extra_ability_game_id"),
    ("hitType", "hit_type"),
    ("amount", "amount"),
    ("unmitigatedAmount", "unmitigated_amount"),
    ("absorbed", "absorbed"),
    ("overheal", "overheal"),
    ("overkill", "overkill"),
    ("mitigated", "mitigated"),
    ("resisted", "resisted"),
    ("blocked", "blocked"),
    ("stack", "stack"),
    ("extraAttacks", "extra_attacks"),
    ("isAoE", "is_aoe"),
    ("tick", "tick"),
    ("melee", "melee"),
    ("killerID", "killer_id"),
    ("killingAbilityGameID", "killing_ability_game_id"),
    ("resourceActor", "resource_actor"),
    ("hitPoints", "hit_points"),
    ("maxHitPoints", "max_hit_points"),
    ("x", "x"),
    ("y", "y"),
)

ALL_TABLES: tuple[Table, ...] = (
    SNAPSHOT_META,
    SNAPSHOT_ISSUES,
    BENCHMARK_PARTICIPANTS,
    REPORTS,
    FIGHTS,
    ACTORS,
    ABILITIES,
    PLAYER_DETAILS,
    REPORT_RANKINGS,
    RANKINGS,
    COMBATANT_INFO,
    STREAM_COVERAGE,
    EVENTS,
    EVENT_ANOMALIES,
)
