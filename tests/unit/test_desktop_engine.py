"""Desktop boundary checks: cancellation, identity, offline and credential isolation."""

from __future__ import annotations

import io
import json
import threading
from pathlib import Path
from typing import Any

import pytest

from necropsy.desktop.engine import DesktopEngine, describe_character, describe_run, serve
from necropsy.tui.service import AnalysisService, RunLibrary, SavedRun, Stopped
from necropsy.wcl.analyze import Outcome
from tests.unit.test_wcl_acquire import _context


def test_desktop_keeps_combat_preference_separate_from_wcl_dps_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    from necropsy.wcl.context import Field

    context = replace(_context(), class_id=Field(8, "observed", "test"))
    character = describe_character(context)
    assert character["talent_trees"] == ["Assassination", "Combat", "Subtlety"]
    assert character["categories"] == [{"label": "DPS", "value": "Assassination"}]
    engine = DesktopEngine(lambda _: None, RunLibrary(tmp_path))
    engine.context, engine.url = context, "https://vanilla.warcraftlogs.com/character/id/86583560"
    captured: list[SavedRun] = []
    monkeypatch.setattr(engine, "analyze", lambda run: captured.append(run))
    engine.dispatch("analyze", {"category": "Assassination", "talent_tree": "Combat"})
    assert captured[0].options["category"] == "Assassination"
    assert captured[0].options["talent_tree"] == "Combat"
    assert engine.library.load(captured[0].out).options == captured[0].options
    with pytest.raises(ValueError):
        engine.dispatch("analyze", {"category": "Combat", "talent_tree": "Combat"})
    with pytest.raises(ValueError):
        engine.dispatch("analyze", {"category": "Assassination", "talent_tree": "Arcane"})


@pytest.mark.parametrize("status", ["Complete — data notes", "Partial — report ready"])
def test_finished_analysis_with_data_notes_does_not_offer_resume(
    tmp_path: Path, status: str
) -> None:
    library = RunLibrary(tmp_path)
    run = library.create(
        "https://vanilla.warcraftlogs.com/character/id/86583560", "Marksmanship", _context()
    )
    run.store(status, "Saved data notes")
    (run.out / "analysis.json").write_text("{}", encoding="utf-8")
    loaded = library.load(run.out)
    payload = describe_run(loaded)
    assert payload["status"] == "Complete — data notes"
    assert payload["has_report"]
    assert not payload["can_resume"]
    if status == "Partial — report ready":
        assert "No restart is required" in payload["detail"]
    else:
        assert payload["detail"] == "Saved data notes"


@pytest.mark.parametrize("status", ["Stopped — ready to continue", "Waiting", "Needs attention"])
def test_unfinished_analysis_still_offers_resume(tmp_path: Path, status: str) -> None:
    library = RunLibrary(tmp_path)
    run = library.create(
        "https://vanilla.warcraftlogs.com/character/id/86583560", "Marksmanship", _context()
    )
    run.store(status)
    assert describe_run(library.load(run.out))["can_resume"]


class BlockingService(AnalysisService):
    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()

    def run(self, run: SavedRun, stop: threading.Event, *args: Any) -> Outcome:
        run.store("Running")
        self.started.set()
        assert stop.wait(5), "desktop stop never reached the analysis worker"
        run.store("Stopped — ready to continue")
        raise Stopped


def test_stop_is_read_while_analysis_is_running_and_shutdown_waits(tmp_path: Path) -> None:
    messages: list[dict[str, Any]] = []
    service = BlockingService()
    library = RunLibrary(tmp_path)
    run = library.create(
        "https://vanilla.warcraftlogs.com/character/id/86583560", "Marksmanship", _context()
    )
    engine = DesktopEngine(messages.append, library, service)
    engine.handle({"id": 1, "method": "resume", "params": {"id": str(run.out)}})
    assert service.started.wait(5)
    engine.handle({"id": 2, "method": "demo"})
    engine.handle({"id": 3, "method": "stop"})
    engine.shutdown()
    assert any(m.get("id") == 2 and "already running" in m["error"] for m in messages)
    assert any(m.get("id") == 3 and m.get("result") is None for m in messages)
    assert any(m.get("id") == 1 and m.get("result") == {"stopped": True} for m in messages)
    assert library.load(run.out).status == "Stopped — ready to continue"
    assert messages[-1] == {"event": "busy", "data": False}


def test_eof_waits_for_cooperative_save(tmp_path: Path) -> None:
    messages: list[dict[str, Any]] = []
    service = BlockingService()
    library = RunLibrary(tmp_path)
    run = library.create(
        "https://vanilla.warcraftlogs.com/character/id/86583560", "Marksmanship", _context()
    )
    engine = DesktopEngine(messages.append, library, service)
    engine.handle({"id": 1, "method": "resume", "params": {"id": str(run.out)}})
    assert service.started.wait(5)
    engine.shutdown()
    assert not engine.busy
    assert library.load(run.out).status == "Stopped — ready to continue"


def test_bad_url_and_unknown_operations_do_not_open_credential_store(tmp_path: Path) -> None:
    messages: list[dict[str, Any]] = []
    service = AnalysisService()
    engine = DesktopEngine(messages.append, RunLibrary(tmp_path), service)
    engine.handle({"id": 1, "method": "identify", "params": {"url": "file:///etc/passwd"}})
    engine.shutdown()
    engine.handle({"id": 2, "method": "token_for"})
    assert service._auth is None
    assert any(m.get("id") == 1 and "error" in m for m in messages)
    assert messages[-1] == {"id": 2, "error": "Unknown desktop operation."}


def test_character_payload_contains_only_presentation_fields() -> None:
    payload = describe_character(_context())
    assert payload["ready"] is True
    assert payload["class_name"] == "Hunter"
    assert payload["categories"][0]["value"] == "Marksmanship"
    assert "token" not in json.dumps(payload)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://evil.example/report",
        "https://vanilla.warcraftlogs.com.evil.example",
        "https://user:password@warcraftlogs.com",
        "https://warcraftlogs.com:444/",
    ],
)
def test_report_links_cannot_launch_other_schemes_or_hosts(tmp_path: Path, url: str) -> None:
    engine = DesktopEngine(lambda _: None, RunLibrary(tmp_path))
    with pytest.raises(ValueError, match="Only secure"):
        engine.dispatch("open_link", {"url": url})


def test_wire_survives_malformed_requests_without_tracebacks(tmp_path: Path) -> None:
    source = io.StringIO('not-json\n[]\n{"id":1,"method":"hello"}\n')
    target = io.StringIO()
    serve(source, target, tmp_path)
    messages = [json.loads(line) for line in target.getvalue().splitlines()]
    assert len(messages) == 3
    assert messages[-1]["result"]["runs"] == []
    assert "Traceback" not in target.getvalue()
