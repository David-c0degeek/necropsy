"""`necropsy offline`: snapshot -> database -> analysis.json, with no network access."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import duckdb

from necropsy.normalize.ingest import IngestError, ingest
from necropsy.normalize.schema import SCHEMA_VERSION
from necropsy.report.analysis_json import build_document, dumps
from necropsy.snapshot.archive import EntryDigest, VerifiedArchive

ANALYSIS_FILE = "analysis.json"


@dataclass(frozen=True)
class OfflineResult:
    analysis: Path
    bosses: int
    recommendations: int


def _reusable(db: Path, archive_sha256: str) -> bool:
    """True when `db` was built by this schema from exactly this archive."""
    if not db.exists() or db.with_name(db.name + ".wal").exists():
        return False
    try:
        con = duckdb.connect(str(db), read_only=True)
    except duckdb.Error:
        return False
    try:
        row = con.execute("SELECT archive_sha256, schema_version FROM snapshot_meta").fetchone()
    except duckdb.Error:
        row = None
    finally:
        con.close()
    return row is not None and row[0] == archive_sha256 and row[1] == SCHEMA_VERSION


def _verified_sha256(
    snapshot: Path, expected_sha256: str | None, entries: dict[str, EntryDigest] | None
) -> str:
    """Run the same archive checks ingest runs, and return the archive's real digest.

    A reused database must never vouch for an archive that was not checked: the
    whole-archive digest is always computed, and with an entries manifest every
    member is read and checked against it.
    """
    with VerifiedArchive(snapshot, expected_sha256=expected_sha256, entries=entries) as archive:
        if entries is not None:
            for name in archive.names():
                archive.read_bytes(name)
        assert archive.sha256 is not None
        return archive.sha256


def _write_atomically(path: Path, text: str) -> None:
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    try:
        tmp.write_text(text, encoding="utf-8", newline="\n")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _analyze(db: Path, out_dir: Path, cross_faction: bool) -> OfflineResult:
    con = duckdb.connect(str(db), read_only=True)
    try:
        document = build_document(con, cross_faction=cross_faction)
    finally:
        con.close()
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / ANALYSIS_FILE
    _write_atomically(target, dumps(document))
    return OfflineResult(
        analysis=target,
        bosses=len(document["bosses"]),
        recommendations=sum(len(b["recommendations"]) for b in document["bosses"]),
    )


def run_offline(
    snapshot: Path,
    out_dir: Path,
    *,
    db: Path | None = None,
    cross_faction: bool = False,
    expected_sha256: str | None = None,
    entries: dict[str, EntryDigest] | None = None,
    replace: bool = False,
) -> OfflineResult:
    """Analyze a snapshot offline and write analysis.json into `out_dir`.

    The archive is always verified first (digest, member safety, and the entries
    manifest when given). With `db`, an existing database built by this schema
    from the same archive is then reused; otherwise it is rebuilt under the usual
    ingest safety rules. Without `db`, a temporary database is used and removed
    afterwards. analysis.json is written atomically, so a failed run never leaves
    a partial file.
    """
    if db is not None:
        if not _reusable(db, _verified_sha256(snapshot, expected_sha256, entries)):
            ingest(snapshot, db, expected_sha256=expected_sha256, entries=entries, replace=replace)
        return _analyze(db, out_dir, cross_faction)
    with tempfile.TemporaryDirectory(prefix="necropsy-offline-") as work:
        temp_db = Path(work) / "analysis.duckdb"
        ingest(snapshot, temp_db, expected_sha256=expected_sha256, entries=entries)
        return _analyze(temp_db, out_dir, cross_faction)


__all__ = ["ANALYSIS_FILE", "IngestError", "OfflineResult", "run_offline"]
