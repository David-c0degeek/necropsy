"""Build the DuckDB analysis database from a raw snapshot, atomically.

Event identity: an event is identified within its fight by the SHA-256 of its
canonical JSON. Streams overlap (an event between two exported actors appears
in both actors' streams) and a stream can legitimately contain byte-identical
events, so each identity is stored as many times as it occurs in any single
stream (maximum multiplicity), one row per occurrence. Streams that disagree on
an identity's multiplicity are recorded in `event_anomalies` and mark the
affected streams as untrustworthy for absence claims.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

import duckdb

from necropsy import __version__
from necropsy.normalize import schema
from necropsy.snapshot.archive import EntryDigest, VerifiedArchive
from necropsy.snapshot.canonical import canonical_json, event_uid
from necropsy.snapshot.model import SnapshotDescriptor, StreamRead, StreamRef
from necropsy.snapshot.reader import SnapshotReader
from necropsy.snapshot.v0 import V0Snapshot


class IngestError(Exception):
    """Ingest refused or failed; any existing database is left untouched."""


@dataclass(frozen=True)
class IngestSummary:
    database: Path
    archive_sha256: str
    scope: str
    fights: int
    streams: int
    incomplete_streams: int
    stream_events: int
    events: int
    anomalies: int
    issues: int


@dataclass
class _MergedFight:
    rows: list[tuple[str, str, dict[str, Any], int]]
    anomalies: list[dict[str, Any]]
    mismatches_by_stream: Counter[int]


def merge_streams(report_code: str, fight_id: int, reads: list[StreamRead]) -> _MergedFight:
    """Merge one fight's streams into distinct events with their true multiplicity."""
    counts: list[Counter[str]] = []
    first: dict[str, dict[str, Any]] = {}
    for read in reads:
        counter: Counter[str] = Counter()
        for event in read.events:
            key = canonical_json(event)
            counter[key] += 1
            first.setdefault(key, event)
        counts.append(counter)
    seen: dict[str, set[int]] = defaultdict(set)
    holders: dict[str, list[int]] = defaultdict(list)
    for index, counter in enumerate(counts):
        for key, n in counter.items():
            seen[key].add(n)
            holders[key].append(index)
    rows: list[tuple[str, str, dict[str, Any], int]] = []
    anomalies: list[dict[str, Any]] = []
    mismatches: Counter[int] = Counter()
    for key, multiplicities in seen.items():
        uid = event_uid(key)
        if len(multiplicities) > 1:
            anomalies.append(
                {
                    "report_code": report_code,
                    "fight_id": fight_id,
                    "kind": "multiplicity-mismatch",
                    "event_uid": uid,
                    "detail": f"multiplicities {sorted(multiplicities)} across streams",
                }
            )
            for index in holders[key]:
                mismatches[index] += 1
        rows.append((uid, key, first[key], max(multiplicities)))
    rows.sort(key=lambda r: (r[2].get("timestamp", 0), r[0]))
    return _MergedFight(rows, anomalies, mismatches)


def _event_row(
    report_code: str,
    fight_id: int,
    uid: str,
    event: dict[str, Any],
    copy_index: int,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "report_code": report_code,
        "fight_id": fight_id,
        "event_uid": uid,
        "copy_index": copy_index,
    }
    for field, column in schema.EVENT_FIELDS:
        row[column] = event.get(field)
    row["raw"] = event
    return row


def _talent_points(talents: Any) -> str | None:
    if (
        isinstance(talents, list)
        and talents
        and all(isinstance(t, dict) and isinstance(t.get("id"), int) for t in talents)
    ):
        return "/".join(str(t["id"]) for t in talents)
    return None


class _Loader:
    """Collects rows per table into NDJSON files, then bulk-loads them.

    DuckDB's executemany is far too slow for millions of rows; read_json with
    declared column types is fast and keeps every type explicit.
    """

    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir
        self._files: dict[str, IO[str]] = {}
        self._counts: Counter[str] = Counter()

    def add(self, table: schema.Table, rows: Iterable[dict[str, Any]]) -> None:
        handle = self._files.get(table.name)
        if handle is None:
            handle = (self._workdir / f"{table.name}.ndjson").open("w", encoding="utf-8")
            self._files[table.name] = handle
        columns = [name for name, _ in table.columns]
        for row in rows:
            missing = set(columns) ^ set(row)
            if missing:
                raise IngestError(f"{table.name}: row keys differ from schema: {sorted(missing)}")
            handle.write(json.dumps({c: row[c] for c in columns}, ensure_ascii=False))
            handle.write("\n")
            self._counts[table.name] += 1

    def load(self, con: duckdb.DuckDBPyConnection) -> None:
        for handle in self._files.values():
            handle.close()
        for table in schema.ALL_TABLES:
            con.execute(table.ddl())
            if not self._counts[table.name]:
                continue
            path = str(self._workdir / f"{table.name}.ndjson")
            columns = (
                "{" + ", ".join(f"'{name}': '{sql_type}'" for name, sql_type in table.columns) + "}"
            )
            # Table and column names come from the fixed schema module, never from input.
            con.execute(
                f"INSERT INTO {table.name} SELECT * FROM read_json(?, "  # noqa: S608
                f"format='newline_delimited', columns={columns})",
                [path],
            )

    def close(self) -> None:
        for handle in self._files.values():
            if not handle.closed:
                handle.close()


def _describe(loader: _Loader, d: SnapshotDescriptor, issues: list[str]) -> None:
    loader.add(
        schema.SNAPSHOT_META,
        [
            {
                "schema_version": schema.SCHEMA_VERSION,
                "format": d.format,
                "archive_sha256": d.archive_sha256,
                "scope": d.scope.value,
                "subject_id": d.subject.id,
                "subject_name": d.subject.name,
                "subject_class_id": d.subject.class_id,
                "subject_server": d.subject.server,
                "subject_region": d.subject.region,
                "zone_id": d.zone.id,
                "zone_name": d.zone.name,
                "partition_id": d.zone.partition,
                "cohort": d.cohort,
                "top_n": d.top_n,
                "selected_fights": len(d.fights),
                "source_fight_count": d.source_fight_count,
                "source_errors": list(d.source_errors),
                "necropsy_version": __version__,
            }
        ],
    )
    loader.add(schema.SNAPSHOT_ISSUES, ({"issue": i} for i in issues))
    loader.add(
        schema.BENCHMARK_PARTICIPANTS,
        (
            {
                "report_code": f.report_code,
                "fight_id": f.fight_id,
                "kind": p.kind,
                "boss": p.boss,
                "encounter_id": p.encounter_id,
                "player": p.player,
                "server": p.server,
                "leaderboard_position": p.leaderboard_position,
                "total": p.total,
                "duration_ms": p.duration_ms,
                "spec": p.spec,
            }
            for f in d.fights
            for p in f.participants
        ),
    )


def _load_reports(loader: _Loader, reader: SnapshotReader, wanted: set[tuple[str, int]]) -> None:
    for report in reader.reports():
        code = report["code"]
        master = report.get("masterData") or {}
        loader.add(
            schema.REPORTS,
            [
                {
                    "report_code": code,
                    "title": report.get("title"),
                    "start_time": report.get("startTime"),
                    "end_time": report.get("endTime"),
                    "revision": report.get("revision"),
                    "visibility": report.get("visibility"),
                    "is_archived": (report.get("archiveStatus") or {}).get("isArchived"),
                    "zone_id": (report.get("zone") or {}).get("id"),
                    "log_version": master.get("logVersion"),
                    "game_version": master.get("gameVersion"),
                }
            ],
        )
        loader.add(
            schema.FIGHTS,
            (
                {
                    "report_code": code,
                    "fight_id": f["id"],
                    "encounter_id": f.get("encounterID"),
                    "name": f.get("name"),
                    "start_time": f.get("startTime"),
                    "end_time": f.get("endTime"),
                    "kill": f.get("kill"),
                    "difficulty": f.get("difficulty"),
                    "size": f.get("size"),
                    "average_item_level": f.get("averageItemLevel"),
                    "friendly_players": f.get("friendlyPlayers"),
                    "enemy_npcs": f.get("enemyNPCs"),
                    "friendly_pets": f.get("friendlyPets"),
                }
                for f in report.get("fights") or []
                if (code, f["id"]) in wanted
            ),
        )
        loader.add(
            schema.ACTORS,
            (
                {
                    "report_code": code,
                    "actor_id": a["id"],
                    "name": a.get("name"),
                    "type": a.get("type"),
                    "sub_type": a.get("subType"),
                    "server": a.get("server"),
                    "game_id": a.get("gameID"),
                    "pet_owner": a.get("petOwner"),
                    "icon": a.get("icon"),
                }
                for a in master.get("actors") or []
            ),
        )
        loader.add(
            schema.ABILITIES,
            (
                {
                    "report_code": code,
                    "game_id": a.get("gameID"),
                    "name": a.get("name"),
                    "type": a.get("type"),
                    "icon": a.get("icon"),
                }
                for a in master.get("abilities") or []
            ),
        )
        details = ((report.get("playerDetails") or {}).get("data") or {}).get("playerDetails")
        loader.add(
            schema.PLAYER_DETAILS,
            (
                {
                    "report_code": code,
                    "role": role,
                    "actor_id": p.get("id"),
                    "name": p.get("name"),
                    "server": p.get("server"),
                    "class": p.get("type"),
                    "icon": p.get("icon"),
                    "specs": p.get("specs"),
                    "faction_id": _int_or_none((p.get("combatantInfo") or {}).get("factionID")),
                    "combatant_info": p.get("combatantInfo"),
                }
                for role, players in (details or {}).items()
                for p in players or []
            ),
        )
        loader.add(
            schema.REPORT_RANKINGS,
            (
                {
                    "report_code": code,
                    "fight_id": r.get("fightID"),
                    "encounter_id": (r.get("encounter") or {}).get("id"),
                    "partition_id": r.get("partition"),
                    "duration_ms": r.get("duration"),
                    "raw": r,
                }
                for r in (report.get("rankings") or {}).get("data") or []
                if (code, r.get("fightID")) in wanted
            ),
        )


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except TypeError, ValueError:
        return None


def _load_rankings(loader: _Loader, reader: SnapshotReader) -> None:
    for source, document in reader.rankings():
        encounter = document.get("encounter") or {}
        if source.startswith("leaderboards/"):
            rows = [
                (page.get("page"), i, row)
                for page in document.get("pages") or []
                for i, row in enumerate(
                    ((page.get("characterRankings") or {}).get("rankings")) or []
                )
            ]
            kind = "leaderboard"
        else:
            ranks = (document.get("encounterRankings") or {}).get("ranks") or []
            rows = [(None, i, row) for i, row in enumerate(ranks)]
            kind = "subject"
        loader.add(
            schema.RANKINGS,
            (
                {
                    "source": source,
                    "kind": kind,
                    "encounter_id": encounter.get("id"),
                    "encounter_name": encounter.get("name"),
                    "page": page,
                    "row_index": i,
                    "player": row.get("name")
                    or (document.get("character") if kind == "subject" else None),
                    "amount": row.get("amount"),
                    "report_code": (row.get("report") or {}).get("code"),
                    "fight_id": (row.get("report") or {}).get("fightID"),
                    "raw": row,
                }
                for page, i, row in rows
            ),
        )


def _load_fight_events(
    loader: _Loader, reader: SnapshotReader, refs: list[StreamRef], report_code: str, fight_id: int
) -> tuple[int, int, int, int]:
    reads = [reader.read_stream(ref) for ref in refs]
    merged = merge_streams(report_code, fight_id, reads)
    ambiguity_rows = [
        {
            "report_code": report_code,
            "fight_id": fight_id,
            "kind": "page-boundary-identical",
            "event_uid": None,
            "detail": f"{r.ref.role.value} {r.ref.actor_name} {r.ref.direction.value}: "
            f"{r.boundary_ambiguities} page boundaries start with the previous "
            "page's last event; all occurrences kept",
        }
        for r in reads
        if r.boundary_ambiguities
    ]
    loader.add(schema.EVENT_ANOMALIES, [*merged.anomalies, *ambiguity_rows])
    loader.add(
        schema.STREAM_COVERAGE,
        (
            {
                "report_code": report_code,
                "fight_id": fight_id,
                "actor_id": r.ref.actor_id,
                "actor_name": r.ref.actor_name,
                "role": r.ref.role.value,
                "direction": r.ref.direction.value,
                "owner_actor_id": r.ref.owner_actor_id,
                "status": r.status.value,
                "pages": r.pages,
                "raw_events": len(r.events),
                "boundary_ambiguities": r.boundary_ambiguities,
                "multiplicity_mismatches": merged.mismatches_by_stream[i],
                "detail": r.detail,
            }
            for i, r in enumerate(reads)
        ),
    )
    events = 0
    for uid, _canonical, event, count in merged.rows:
        loader.add(
            schema.EVENTS,
            (_event_row(report_code, fight_id, uid, event, copy) for copy in range(count)),
        )
        events += count
        if event.get("type") == "combatantinfo":
            loader.add(
                schema.COMBATANT_INFO,
                [
                    {
                        "report_code": report_code,
                        "fight_id": fight_id,
                        "actor_id": event.get("sourceID"),
                        "timestamp": event.get("timestamp"),
                        "faction": event.get("faction"),
                        "spec_id": event.get("specID"),
                        "talent_points": _talent_points(event.get("talents")),
                        "talents": event.get("talents"),
                        "gear": event.get("gear"),
                        "auras": event.get("auras"),
                        "event_uid": uid,
                    }
                ],
            )
    incomplete = sum(1 for r in reads if r.status.value != "complete")
    return (
        sum(len(r.events) for r in reads),
        events,
        incomplete,
        len(merged.anomalies) + len(ambiguity_rows),
    )


def build_database(reader: SnapshotReader, db_path: Path, workdir: Path) -> IngestSummary:
    descriptor = reader.descriptor()
    loader = _Loader(workdir)
    try:
        refs_by_fight: dict[tuple[str, int], list[StreamRef]] = defaultdict(list)
        for ref in reader.expected_streams():
            refs_by_fight[(ref.report_code, ref.fight_id)].append(ref)
        wanted = {(f.report_code, f.fight_id) for f in descriptor.fights}
        _load_reports(loader, reader, wanted)
        _load_rankings(loader, reader)
        stream_events = events = incomplete = anomalies = 0
        for fight in descriptor.fights:
            key = (fight.report_code, fight.fight_id)
            s, e, i, a = _load_fight_events(loader, reader, refs_by_fight[key], *key)
            stream_events += s
            events += e
            incomplete += i
            anomalies += a
        issues = reader.issues()
        _describe(loader, descriptor, issues)
        con = duckdb.connect(str(db_path))
        try:
            loader.load(con)
            con.execute("CHECKPOINT")
        finally:
            con.close()
    finally:
        loader.close()
    return IngestSummary(
        database=db_path,
        archive_sha256=descriptor.archive_sha256,
        scope=descriptor.scope.value,
        fights=len(descriptor.fights),
        streams=sum(len(v) for v in refs_by_fight.values()),
        incomplete_streams=incomplete,
        stream_events=stream_events,
        events=events,
        anomalies=anomalies,
        issues=len(issues),
    )


def _existing_identity(db_path: Path) -> tuple[str, str] | None:
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except duckdb.Error as exc:
        raise IngestError(f"{db_path} exists and is not a readable DuckDB database") from exc
    try:
        row = con.execute("SELECT archive_sha256, scope FROM snapshot_meta").fetchone()
    except duckdb.Error:
        row = None
    finally:
        con.close()
    return (str(row[0]), str(row[1])) if row else None


def _remove_db_files(path: Path) -> None:
    for candidate in (path, path.with_name(path.name + ".wal")):
        candidate.unlink(missing_ok=True)


def _target_state(db_path: Path) -> tuple[int, int] | None:
    """(size, mtime_ns) of the target, or None if it does not exist."""
    try:
        stat = db_path.stat()
    except FileNotFoundError:
        return None
    return (stat.st_size, stat.st_mtime_ns)


def _check_target(db_path: Path, descriptor: SnapshotDescriptor, replace: bool) -> None:
    wal = db_path.with_name(db_path.name + ".wal")
    if wal.exists():
        # A write-ahead log may hold changes not yet in the database file;
        # replacing the file would orphan or lose them.
        raise IngestError(
            f"{wal} exists: the database may be open or was not closed cleanly. "
            "Close every program using it (or open and close it once with DuckDB) "
            "and run ingest again."
        )
    if db_path.exists() and not replace:
        identity = _existing_identity(db_path)
        new_identity = (descriptor.archive_sha256, descriptor.scope.value)
        if identity != new_identity:
            raise IngestError(
                f"{db_path} holds a different snapshot ({identity}); pass --replace to overwrite it"
            )


def ingest(
    snapshot: Path,
    db_path: Path,
    *,
    expected_sha256: str | None = None,
    entries: dict[str, EntryDigest] | None = None,
    replace: bool = False,
) -> IngestSummary:
    """Rebuild `db_path` from `snapshot`. The target only changes if the build succeeds.

    The target must stay closed for the whole ingest. Its state is checked before
    the build and again just before the swap; a target that gained a write-ahead
    log or changed in between is left untouched and the ingest fails. A writer
    that opens the target in the instant between that last check and the swap
    is not detected.
    """
    db_path = db_path.resolve()
    with VerifiedArchive(snapshot, expected_sha256=expected_sha256, entries=entries) as archive:
        reader = V0Snapshot(archive)
        descriptor = reader.descriptor()
        _check_target(db_path, descriptor, replace)
        before = _target_state(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_db = db_path.with_name(f"{db_path.name}.tmp-{os.getpid()}")
        _remove_db_files(tmp_db)
        try:
            with tempfile.TemporaryDirectory(
                dir=db_path.parent, prefix=".necropsy-ingest-"
            ) as workdir:
                summary = build_database(reader, tmp_db, Path(workdir))
            _check_target(db_path, descriptor, replace)
            if _target_state(db_path) != before:
                raise IngestError(f"{db_path} changed while ingest was running; not replaced")
            tmp_db.replace(db_path)
        except BaseException:
            _remove_db_files(tmp_db)
            raise
    return IngestSummary(**{**summary.__dict__, "database": db_path})
