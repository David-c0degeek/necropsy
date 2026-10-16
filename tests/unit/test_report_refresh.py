"""Refreshing known analyses preserves data, ownership and recoverable old outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from necropsy import __version__
from necropsy.desktop.engine import DesktopEngine
from necropsy.report import refresh as refresh_module
from necropsy.report.analysis_json import dumps
from necropsy.report.package import write_outputs
from necropsy.report.refresh import refresh_saved_reports
from necropsy.tui.service import RunLibrary
from necropsy.wcl.analyze import LOCK
from necropsy.wcl.cache import CacheError, item_lock
from necropsy.wcl.checkpoint import Checkpoint, saved_options
from tests.druid_fixture import document


@pytest.fixture(scope="module")
def analysis(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    return dumps(
        document(tmp_path_factory.mktemp("refresh-source"), ["Healing Touch"] * 3)
    ).encode()


def seed(tmp_path: Path, analysis: bytes, *, managed: bool = True) -> tuple[RunLibrary, Path]:
    library = RunLibrary(tmp_path / "library")
    out = library.runs / "saved"
    write_outputs(analysis, out)
    (out / "report.html").write_bytes(b"old report")
    (out / "playbook.html").write_bytes(b"old playbook")
    (out / "notes.txt").write_bytes(b"personal notes")
    if managed:
        run = library.load(out)
        run.store("Stopped — ready to continue", "Keep this status and detail")
        checkpoint = Checkpoint(out, run.options, resume=False)
        checkpoint.record(
            [p for p in out.iterdir() if p.suffix in (".html", ".zip") or p.name == "analysis.json"]
        )
    return library, out


def contents(out: Path) -> dict[str, bytes]:
    return {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob("*") if p.is_file()}


@pytest.mark.parametrize("managed", [False, True])
def test_refresh_keeps_the_same_run_source_and_status(
    tmp_path: Path, analysis: bytes, managed: bool
) -> None:
    library, out = seed(tmp_path, analysis, managed=managed)
    before = library.load(out)
    stamp = (out / "analysis.json").stat().st_mtime_ns
    engine = DesktopEngine(lambda _: None, library)
    result = engine.dispatch("refresh_reports", {"id": str(out)})
    assert result["run"]["id"] == str(out) and result["refreshed"]
    after = library.load(out)
    assert (after.title, after.status, after.detail, after.options) == (
        before.title,
        before.status,
        before.detail,
        before.options,
    )
    assert (out / "analysis.json").read_bytes() == analysis
    assert (out / "analysis.json").stat().st_mtime_ns == stamp
    assert b"Before the pull" in (out / "playbook.html").read_bytes()
    assert b"Evidence and details" in (out / "report.html").read_bytes()
    assert (out / "notes.txt").read_bytes() == b"personal notes"
    assert len(library.discover()) == 1
    if managed:
        Checkpoint(out, saved_options(out), resume=True)


def test_refresh_rolls_back_outputs_when_checkpoint_commit_fails(
    tmp_path: Path, analysis: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, out = seed(tmp_path, analysis)
    before = contents(out)

    def fail(_: Checkpoint) -> None:
        raise OSError("checkpoint storage unavailable")

    monkeypatch.setattr(Checkpoint, "flush", fail)
    with pytest.raises(OSError, match="storage unavailable"):
        refresh_saved_reports(out)
    after = contents(out)
    after.pop(LOCK)
    assert after == before
    Checkpoint(out, saved_options(out), resume=True)
    assert not list(out.glob(".necropsy-backup-*"))


def test_render_failure_preserves_every_existing_file(
    tmp_path: Path, analysis: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, out = seed(tmp_path, analysis)
    before = contents(out)

    def fail(*_: Any, **__: Any) -> Any:
        raise ValueError("cannot render this document")

    monkeypatch.setattr(refresh_module, "build_outputs", fail)
    with pytest.raises(ValueError, match="cannot render"):
        refresh_saved_reports(out)
    after = contents(out)
    after.pop(LOCK)
    assert after == before


def test_refresh_refuses_changed_owned_outputs_before_overwriting(
    tmp_path: Path, analysis: bytes
) -> None:
    _, out = seed(tmp_path, analysis)
    (out / "report.html").write_bytes(b"edited report")
    with pytest.raises(CacheError, match="saved output changed"):
        refresh_saved_reports(out)
    assert (out / "report.html").read_bytes() == b"edited report"
    assert (out / "playbook.html").read_bytes() == b"old playbook"


def test_refresh_shares_the_acquisition_output_lock(tmp_path: Path, analysis: bytes) -> None:
    _, out = seed(tmp_path, analysis)
    with item_lock(out / LOCK), pytest.raises(CacheError):
        refresh_saved_reports(out)
    assert (out / "playbook.html").read_bytes() == b"old playbook"


def test_refresh_never_creates_a_missing_analysis(tmp_path: Path) -> None:
    out = tmp_path / "missing"
    with pytest.raises(ValueError, match="no longer available"):
        refresh_saved_reports(out)
    assert not out.exists()


def test_refresh_respects_saved_no_package_option_and_removes_stale_ownership(
    tmp_path: Path, analysis: bytes
) -> None:
    _, out = seed(tmp_path, analysis)
    checkpoint = Checkpoint(out, saved_options(out), resume=True)
    checkpoint.state["options"]["package"] = False
    checkpoint.flush()
    assert list(out.glob("*.zip"))
    refresh_saved_reports(out)
    assert not list(out.glob("*.zip"))
    resumed = Checkpoint(out, saved_options(out), resume=True)
    assert all(not name.endswith(".zip") for name in resumed.allowed)
    assert (out / "analysis.json").read_bytes() == analysis


def test_refreshed_pages_distinguish_renderer_version_from_recorded_analysis(
    tmp_path: Path, analysis: bytes
) -> None:
    old = json.loads(analysis)
    old["necropsy_version"] = "0.1.1"
    data = json.dumps(old).encode()
    _, out = seed(tmp_path, data, managed=False)
    refresh_saved_reports(out)
    for name in ("playbook.html", "report.html"):
        html = (out / name).read_text(encoding="utf-8")
        assert f"Reports rendered by Necropsy {__version__}" in html
        assert "Analysis produced by Necropsy 0.1.1" in html
    assert (out / "analysis.json").read_bytes() == data
