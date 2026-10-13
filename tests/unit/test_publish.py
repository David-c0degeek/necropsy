"""Publishing a set of output files together."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from necropsy.report import publish as publish_module
from necropsy.report.publish import BACKUP_PREFIX, STAGING_PREFIX, PublishError, publish

OLD = {"analysis.json": b"old-json", "report.html": b"old-report", "pkg.zip": b"old-zip"}
NEW = {"analysis.json": b"new-json", "report.html": b"new-report", "pkg.zip": b"new-zip"}


def _seed(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in OLD.items():
        (out / name).write_bytes(data)
    (out / "notes.txt").write_bytes(b"user file")


def _state(out: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}


def _leftovers(out: Path) -> list[str]:
    return [p.name for p in out.iterdir() if p.name.startswith((STAGING_PREFIX, BACKUP_PREFIX))]


def test_success_replaces_only_owned_files(tmp_path: Path) -> None:
    _seed(tmp_path)
    publish(tmp_path, NEW)
    assert _state(tmp_path) == {**NEW, "notes.txt": b"user file"}
    assert _leftovers(tmp_path) == []


def test_none_removes_a_stale_file(tmp_path: Path) -> None:
    _seed(tmp_path)
    publish(tmp_path, {**NEW, "pkg.zip": None})
    assert "pkg.zip" not in _state(tmp_path)
    assert _state(tmp_path)["analysis.json"] == b"new-json"


def test_failure_while_staging_keeps_the_previous_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed(tmp_path)
    real = Path.write_bytes
    calls = {"n": 0}

    def flaky(self: Path, data: Any) -> int:
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk full")
        return real(self, data)

    monkeypatch.setattr(Path, "write_bytes", flaky)
    with pytest.raises(OSError, match="disk full"):
        publish(tmp_path, NEW)
    monkeypatch.undo()
    assert _state(tmp_path) == {**OLD, "notes.txt": b"user file"}
    assert _leftovers(tmp_path) == []


def test_failure_during_publication_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed(tmp_path)
    real = Path.replace
    calls = {"n": 0}

    def flaky(self: Path, target: Any) -> Path:
        calls["n"] += 1
        if calls["n"] == 4:  # after the first file was swapped in
            raise OSError("locked")
        return real(self, target)

    monkeypatch.setattr(Path, "replace", flaky)
    with pytest.raises(OSError, match="locked"):
        publish(tmp_path, NEW)
    monkeypatch.undo()
    assert _state(tmp_path) == {**OLD, "notes.txt": b"user file"}
    assert _leftovers(tmp_path) == []


def test_failed_rollback_keeps_the_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(tmp_path)
    real = Path.replace
    calls = {"n": 0}

    def flaky(self: Path, target: Any) -> Path:
        calls["n"] += 1
        if calls["n"] >= 4:  # publication fails, and so does every restore
            raise OSError("locked")
        return real(self, target)

    monkeypatch.setattr(Path, "replace", flaky)
    with pytest.raises(PublishError) as raised:
        publish(tmp_path, NEW)
    monkeypatch.undo()
    backup = raised.value.backup
    assert backup is not None and backup.is_dir()
    saved = {p.name: p.read_bytes() for p in backup.iterdir()}
    assert saved == {"analysis.json": b"old-json", "pkg.zip": b"old-zip"}
    assert str(backup) in str(raised.value)
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(STAGING_PREFIX)]


def test_a_new_output_directory_is_removed_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "fresh"
    monkeypatch.setattr(publish_module, "_swap", _boom)
    with pytest.raises(RuntimeError):
        publish(out, NEW)
    assert not out.exists()


def test_an_existing_directory_is_never_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "existing"
    out.mkdir()
    monkeypatch.setattr(publish_module, "_swap", _boom)
    with pytest.raises(RuntimeError):
        publish(out, NEW)
    assert out.is_dir() and list(out.iterdir()) == []


def _boom(*_args: Any) -> None:
    raise RuntimeError("publish failed")


@pytest.mark.parametrize("name", ["../x.json", "sub/x.json", ".hidden", "a\\b"])
def test_only_plain_file_names(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError, match="plain output file name"):
        publish(tmp_path, {name: b"x"})


@pytest.mark.parametrize("name", ["report.html", "pkg.zip"])
def test_refuses_a_directory_with_an_artifact_name(tmp_path: Path, name: str) -> None:
    _seed(tmp_path)
    (tmp_path / name).unlink()
    (tmp_path / name).mkdir()
    (tmp_path / name / "important.txt").write_bytes(b"keep me")
    before = _state(tmp_path)
    files = {**NEW, "pkg.zip": None} if name == "pkg.zip" else NEW
    with pytest.raises(PublishError, match="not a regular file"):
        publish(tmp_path, files)
    assert (tmp_path / name / "important.txt").read_bytes() == b"keep me"
    assert _state(tmp_path) == before
    assert _leftovers(tmp_path) == []


def test_refuses_a_symlink_with_an_artifact_name(tmp_path: Path) -> None:
    _seed(tmp_path)
    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere.write_bytes(b"target")
    (tmp_path / "report.html").unlink()
    try:
        (tmp_path / "report.html").symlink_to(elsewhere)
    except OSError:
        pytest.skip("symbolic links are not available here")
    with pytest.raises(PublishError, match="not a regular file"):
        publish(tmp_path, NEW)
    assert elsewhere.read_bytes() == b"target"
    assert (tmp_path / "report.html").is_symlink()
