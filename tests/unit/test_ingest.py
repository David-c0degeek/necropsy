import os
import sys
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.normalize import ingest as ingest_module
from necropsy.normalize.coverage import has_complete_coverage
from necropsy.normalize.ingest import IngestError, ingest, merge_streams
from necropsy.snapshot.model import (
    ActorRole,
    Direction,
    StreamRead,
    StreamRef,
    StreamStatus,
)
from tests.snapshot_builder import FIGHT, REPORT, SnapshotSpec, build, ev, page

PLAYER = "player_1_Hunter"
PET = "pet_2_Cat"


def _read(events: list[dict[str, Any]], actor: int = 1) -> StreamRead:
    ref = StreamRef(
        report_code=REPORT,
        fight_id=FIGHT,
        actor_id=actor,
        actor_name="a",
        role=ActorRole.PLAYER,
        direction=Direction.SOURCE,
    )
    return StreamRead(ref, StreamStatus.COMPLETE, 1, events, 0)


def test_identical_hits_survive_overlapping_streams() -> None:
    hit = ev(10, source=1, target=2)
    merged = merge_streams(REPORT, FIGHT, [_read([hit, hit, ev(11)]), _read([hit, hit], 2)])
    counts = {row[2]["timestamp"]: row[3] for row in merged.rows}
    assert counts == {10: 2, 11: 1}
    assert merged.anomalies == []


def test_multiplicity_disagreement_is_an_anomaly() -> None:
    hit = ev(10, source=1, target=2)
    merged = merge_streams(REPORT, FIGHT, [_read([hit, hit]), _read([hit], 2)])
    assert [a["kind"] for a in merged.anomalies] == ["multiplicity-mismatch"]
    assert merged.mismatches_by_stream == {0: 1, 1: 1}
    assert merged.rows[0][3] == 2


def _spec(**overrides: Any) -> SnapshotSpec:
    hit = ev(5, source=1, target=2)
    combatant = {
        "timestamp": 0,
        "type": "combatantinfo",
        "sourceID": 1,
        "fight": FIGHT,
        "faction": 1,
        "specID": 0,
        "talents": [{"id": 20}, {"id": 31}, {"id": 0}],
        "gear": [],
        "auras": [],
    }
    streams: dict[str, list[dict[str, Any] | None]] = {
        f"{PLAYER}/source": [page([combatant, ev(1), hit, hit], 6.0), page([hit, ev(7)])],
        f"{PLAYER}/target": [page([ev(3, source=50, target=1)])],
        f"{PET}/source": [page([ev(4, source=2)])],
        f"{PET}/target": [page([hit, hit])],
    }
    return SnapshotSpec(streams=streams, **overrides)


def _count(con: duckdb.DuckDBPyConnection, sql: str) -> Any:
    row = con.execute(sql).fetchone()
    assert row is not None
    return row[0]


def test_ingest_builds_database(tmp_path: Path) -> None:
    path = build(tmp_path / "s.zip", _spec())
    db = tmp_path / "out" / "a.duckdb"
    summary = ingest(path, db)
    assert summary.fights == 1
    assert summary.incomplete_streams == 0
    con = duckdb.connect(str(db), read_only=True)
    try:
        # page-boundary repeat of the hit is kept: three in the player's source
        # stream, which the pet's target stream (two copies) cannot reduce.
        assert _count(con, "SELECT count(*) FROM events WHERE timestamp = 5") == 3
        assert (
            _count(
                con, "SELECT count(*) FROM event_anomalies WHERE kind = 'page-boundary-identical'"
            )
            == 1
        )
        assert (
            _count(con, "SELECT count(*) FROM event_anomalies WHERE kind = 'multiplicity-mismatch'")
            == 1
        )
        assert _count(con, "SELECT talent_points FROM combatant_info") == "20/31/0"
        assert _count(con, "SELECT count(*) FROM events WHERE json_type(raw) <> 'OBJECT'") == 0
        assert (
            _count(con, "SELECT json_extract_string(raw, '$.type') FROM events WHERE timestamp = 7")
            == "damage"
        )
        assert (
            _count(
                con,
                "SELECT json_extract(raw, '$.talents[1].id') FROM events "
                "WHERE type = 'combatantinfo'",
            )
            == "31"
        )
        assert _count(con, "SELECT scope FROM snapshot_meta") == "full"
        assert _count(con, "SELECT count(*) FROM stream_coverage") == 4
        assert not has_complete_coverage(con, REPORT, FIGHT, 1, Direction.SOURCE)
        assert has_complete_coverage(con, REPORT, FIGHT, 1, Direction.TARGET)
        assert not has_complete_coverage(con, REPORT, FIGHT, 999, Direction.SOURCE)
    finally:
        con.close()


def test_rebuild_from_same_snapshot_is_allowed(tmp_path: Path) -> None:
    path = build(tmp_path / "s.zip", _spec())
    db = tmp_path / "a.duckdb"
    ingest(path, db)
    ingest(path, db)
    assert [p.name for p in tmp_path.iterdir() if ".tmp-" in p.name] == []


def test_different_snapshot_requires_replace(tmp_path: Path) -> None:
    first = build(tmp_path / "a.zip", _spec())
    second = build(tmp_path / "b.zip", _spec(extra_members={"notes.txt": b"x"}))
    db = tmp_path / "a.duckdb"
    ingest(first, db)
    before = db.read_bytes()
    with pytest.raises(IngestError, match="--replace"):
        ingest(second, db)
    assert db.read_bytes() == before
    summary = ingest(second, db, replace=True)
    assert summary.issues == 1


def test_non_database_target_requires_replace(tmp_path: Path) -> None:
    path = build(tmp_path / "s.zip", _spec())
    db = tmp_path / "a.duckdb"
    db.write_bytes(b"not a database")
    with pytest.raises(IngestError):
        ingest(path, db)
    assert db.read_bytes() == b"not a database"


def test_failed_build_leaves_target_and_no_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = build(tmp_path / "s.zip", _spec())
    db = tmp_path / "a.duckdb"
    ingest(path, db)
    before = db.read_bytes()

    def explode(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(ingest_module, "build_database", explode)
    with pytest.raises(RuntimeError):
        ingest(path, db)
    assert db.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir() if ".tmp-" in p.name] == []


def test_stale_temp_from_another_run_never_becomes_target(tmp_path: Path) -> None:
    path = build(tmp_path / "s.zip", _spec())
    db = tmp_path / "a.duckdb"
    stale = tmp_path / f"a.duckdb.tmp-{os.getpid() + 1}"
    stale.write_bytes(b"stale")
    ingest(path, db)
    assert stale.read_bytes() == b"stale"
    con = duckdb.connect(str(db), read_only=True)
    try:
        assert _count(con, "SELECT count(*) FROM fights") == 1
    finally:
        con.close()


def test_repeated_boundary_group_withholds_coverage(tmp_path: Path) -> None:
    first, second = ev(5, ability=1), ev(5, ability=2)
    streams: dict[str, list[dict[str, Any] | None]] = {
        f"{PLAYER}/source": [page([first, second], 5.0), page([first, second])],
        f"{PLAYER}/target": [page([])],
        f"{PET}/source": [page([])],
        f"{PET}/target": [page([])],
    }
    db = tmp_path / "a.duckdb"
    ingest(build(tmp_path / "s.zip", SnapshotSpec(streams=streams)), db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        assert _count(con, "SELECT count(*) FROM events") == 4
        assert not has_complete_coverage(con, REPORT, FIGHT, 1, Direction.SOURCE)
    finally:
        con.close()


@pytest.mark.parametrize("replace", [False, True])
def test_target_with_write_ahead_log_is_refused(tmp_path: Path, replace: bool) -> None:
    path = build(tmp_path / "s.zip", _spec())
    db = tmp_path / "a.duckdb"
    ingest(path, db)
    wal = tmp_path / "a.duckdb.wal"
    wal.write_bytes(b"pending changes")
    before = db.read_bytes()
    with pytest.raises(IngestError, match="wal"):
        ingest(path, db, replace=replace)
    assert db.read_bytes() == before
    assert wal.read_bytes() == b"pending changes"


@pytest.mark.parametrize("replace", [False, True])
def test_failed_replacement_preserves_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replace: bool
) -> None:
    path = build(tmp_path / "s.zip", _spec())
    db = tmp_path / "a.duckdb"
    ingest(path, db)
    before = db.read_bytes()

    def locked(self: Path, target: Any) -> Path:
        raise PermissionError("target is locked")

    monkeypatch.setattr(Path, "replace", locked)
    with pytest.raises(PermissionError):
        ingest(path, db, replace=replace)
    assert db.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.duckdb", "s.zip"]


@pytest.mark.skipif(sys.platform != "win32", reason="open files block replacement on Windows")
def test_busy_database_is_not_replaced(tmp_path: Path) -> None:
    path = build(tmp_path / "s.zip", _spec())
    db = tmp_path / "a.duckdb"
    ingest(path, db)
    before = db.read_bytes()
    holder = duckdb.connect(str(db))
    try:
        with pytest.raises((PermissionError, IngestError)):
            ingest(path, db, replace=True)
    finally:
        holder.close()
    assert db.read_bytes() == before
    assert not [p for p in tmp_path.iterdir() if ".tmp-" in p.name]


@pytest.mark.parametrize("replace", [False, True])
def test_write_ahead_log_appearing_during_build_blocks_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replace: bool
) -> None:
    path = build(tmp_path / "s.zip", _spec())
    db = tmp_path / "a.duckdb"
    ingest(path, db)
    before = db.read_bytes()
    wal = tmp_path / "a.duckdb.wal"
    real_build = ingest_module.build_database

    def build_then_open_target(*args: Any, **kwargs: Any) -> Any:
        result = real_build(*args, **kwargs)
        wal.write_bytes(b"late writer")
        return result

    monkeypatch.setattr(ingest_module, "build_database", build_then_open_target)
    with pytest.raises(IngestError, match="wal"):
        ingest(path, db, replace=replace)
    assert db.read_bytes() == before
    assert wal.read_bytes() == b"late writer"
    assert not [p for p in tmp_path.iterdir() if ".tmp-" in p.name]


@pytest.mark.parametrize("replace", [False, True])
def test_target_changed_during_build_is_not_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replace: bool
) -> None:
    path = build(tmp_path / "s.zip", _spec())
    db = tmp_path / "a.duckdb"
    ingest(path, db)
    real_build = ingest_module.build_database

    def build_then_touch_target(*args: Any, **kwargs: Any) -> Any:
        result = real_build(*args, **kwargs)
        db.write_bytes(db.read_bytes() + b"x")
        return result

    monkeypatch.setattr(ingest_module, "build_database", build_then_touch_target)
    changed: bytes | None = None
    with pytest.raises(IngestError, match="changed while ingest"):
        try:
            ingest(path, db, replace=replace)
        finally:
            changed = db.read_bytes()
    assert changed is not None and changed.endswith(b"x")
    assert not [p for p in tmp_path.iterdir() if ".tmp-" in p.name]
