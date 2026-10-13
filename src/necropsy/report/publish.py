"""Publish a set of output files together, keeping the previous set on failure.

Every file is first written into a staging directory inside the output
directory. Only when all of them exist are they moved into place, one by one;
each file it replaces is first moved into a backup directory. If any move
fails, the moves already made are undone and the previous files restored.

This is not a crash-proof transaction: if the process is killed while files are
being moved, the output directory can hold a mix of old and new files, and the
previous files stay in the `.necropsy-backup-*` directory for recovery.
"""

from __future__ import annotations

import contextlib
import secrets
import shutil
from collections.abc import Mapping
from pathlib import Path

STAGING_PREFIX = ".necropsy-staging-"
BACKUP_PREFIX = ".necropsy-backup-"


class PublishError(Exception):
    """Publication failed. `backup` names a directory holding previous files, if one remains."""

    def __init__(self, message: str, backup: Path | None = None) -> None:
        super().__init__(message)
        self.backup = backup


def _remove_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def publish(out_dir: Path, files: Mapping[str, bytes | None]) -> None:
    """Make `out_dir` hold exactly these file contents for these names.

    `files` maps a plain file name to its bytes, or to None to remove an old file
    of that name (a stale artifact). Other files in `out_dir` are never touched.
    """
    for name in files:
        if Path(name).name != name or name.startswith(".") or "/" in name or "\\" in name:
            raise ValueError(f"not a plain output file name: {name!r}")
    # Preflight before any change: only regular files are ever replaced or removed.
    for name in sorted(files):
        target = out_dir / name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise PublishError(
                f"{target} exists and is not a regular file; move it away and run again"
            )
    created = not out_dir.exists()
    out_dir.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(6)
    staging = out_dir / f"{STAGING_PREFIX}{token}"
    backup = out_dir / f"{BACKUP_PREFIX}{token}"
    try:
        staging.mkdir()
        for name, data in sorted(files.items()):
            if data is not None:
                (staging / name).write_bytes(data)
        _swap(out_dir, staging, backup, files)
    except BaseException:
        _remove_tree(staging)
        if created:
            with contextlib.suppress(OSError):
                out_dir.rmdir()  # only succeeds when nothing else is there
        raise
    _remove_tree(staging)
    _remove_tree(backup)


def _swap(out_dir: Path, staging: Path, backup: Path, files: Mapping[str, bytes | None]) -> None:
    placed: list[str] = []
    saved: list[str] = []
    try:
        backup.mkdir()
        for name in sorted(files):
            target = out_dir / name
            if target.exists():
                target.replace(backup / name)
                saved.append(name)
            if files[name] is not None:
                (staging / name).replace(target)
                placed.append(name)
    except BaseException as exc:
        if not _rollback(out_dir, backup, placed, saved):
            raise PublishError(
                f"publishing failed ({exc}) and the previous files could not all be restored; "
                f"they are kept in {backup}",
                backup,
            ) from exc
        _remove_tree(backup)
        raise


def _rollback(out_dir: Path, backup: Path, placed: list[str], saved: list[str]) -> bool:
    ok = True
    for name in reversed(placed):
        try:
            (out_dir / name).unlink(missing_ok=True)
        except OSError:
            ok = False
    for name in reversed(saved):
        try:
            (backup / name).replace(out_dir / name)
        except OSError:
            ok = False
    return ok


__all__ = ["BACKUP_PREFIX", "STAGING_PREFIX", "PublishError", "publish"]
