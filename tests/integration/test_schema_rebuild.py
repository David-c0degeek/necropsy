"""A database from an older schema is rebuilt from the same verified archive, never read."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import duckdb
import pytest

from necropsy.normalize import ingest as ingest_mod
from necropsy.normalize.schema import SCHEMA_VERSION
from necropsy.report.offline import run_offline
from tests.analysis_db import subset_db
from tests.fixture_paths import subset_path


def _old_db(tmp_path: Path) -> Path:
    db = tmp_path / "old.duckdb"
    shutil.copyfile(subset_db(), db)
    con = duckdb.connect(str(db))
    con.execute("UPDATE snapshot_meta SET schema_version = 1")
    con.close()
    return db


def test_an_older_schema_database_is_rebuilt(tmp_path: Path) -> None:
    db = _old_db(tmp_path)
    run_offline(subset_path(), tmp_path / "out", db=db, package=False)
    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute("SELECT schema_version, mode FROM snapshot_meta").fetchone()
    finally:
        con.close()
    assert row == (SCHEMA_VERSION, "historical")
    document = json.loads((tmp_path / "out" / "analysis.json").read_text(encoding="utf-8"))
    assert document["mode"] == "historical" and "acquisition" not in document


def test_a_failed_rebuild_leaves_the_old_database_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = _old_db(tmp_path)
    before = db.read_bytes()

    def broken(*args: object, **kwargs: object) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(ingest_mod, "build_database", broken)
    with pytest.raises(RuntimeError):
        run_offline(subset_path(), tmp_path / "out", db=db, package=False)
    assert db.read_bytes() == before
