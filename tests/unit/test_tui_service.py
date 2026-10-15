from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

from necropsy.tui import service as module
from necropsy.tui.service import AnalysisService, RunLibrary, SavedRun, StopClock, Stopped
from necropsy.wcl.acquire import Acquisition
from necropsy.wcl.analyze import AnalyzeError, Outcome
from necropsy.wcl.checkpoint import Checkpoint
from tests.unit.test_wcl_acquire import PATCHWERK, _context


def new_run(tmp_path: Path) -> tuple[RunLibrary, SavedRun]:
    library = RunLibrary(tmp_path)
    run = library.create(
        "https://vanilla.warcraftlogs.com/character/id/86583560", "Marksmanship", _context()
    )
    return library, run


class Scripted(AnalysisService):
    def __init__(self, answers: list[Outcome | Exception]) -> None:
        super().__init__()
        self.answers = answers
        self.attempts = 0

    def ensure_connected(self, *args: Any) -> None:
        pass

    def attempt(self, run: SavedRun, stop: threading.Event, notify: module.Notify) -> Outcome:
        self.attempts += 1
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def reset_delay(self) -> int:
        return 2


def test_quota_waits_repeatedly_and_finishes_without_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, run = new_run(tmp_path)
    acquisition = Acquisition("user", False, _context(), (PATCHWERK,))
    acquisition.stopped = "BudgetExceeded: account allowance exhausted"
    service = Scripted(
        [
            Outcome(4, acquisition=acquisition),
            AnalyzeError("stopped: RateLimited during finalization", code=3),
            Outcome(0),
        ]
    )
    clock = [0.0]

    class FastStop(threading.Event):
        def wait(self, timeout: float | None = None) -> bool:
            clock[0] += timeout or 0
            return self.is_set()

    monkeypatch.setattr("necropsy.tui.service.time.monotonic", lambda: clock[0])
    countdowns: list[int] = []
    messages: list[str] = []
    result = service.run(run, FastStop(), messages.append, lambda _: None, countdowns.append)
    assert result.code == 0 and service.attempts == 3
    assert countdowns == [2, 1, 0, 2, 1, 0]
    assert library.load(run.out).status == "Complete"
    assert sum("waiting to continue" in message for message in messages) == 2


def test_stop_during_quota_wait_is_saved_and_can_be_reloaded(tmp_path: Path) -> None:
    library, run = new_run(tmp_path)
    stop = threading.Event()
    service = Scripted([AnalyzeError("BudgetExceeded during finalization", code=3)])
    with pytest.raises(Stopped):
        service.run(run, stop, lambda _: None, lambda _: None, lambda _: stop.set())
    loaded = library.discover()
    assert len(loaded) == 1
    assert loaded[0].status == "Stopped — ready to continue"
    assert loaded[0].options == run.options


def test_partial_coverage_without_quota_does_not_sleep(tmp_path: Path) -> None:
    _, run = new_run(tmp_path)
    service = Scripted([Outcome(4)])
    result = service.run(
        run,
        threading.Event(),
        lambda _: None,
        lambda _: None,
        lambda _: pytest.fail("partial coverage must not wait"),
    )
    assert result.code == 4 and service.attempts == 1
    assert run.status == "Partial — report ready"


def test_other_errors_are_saved_without_an_automatic_retry(tmp_path: Path) -> None:
    library, run = new_run(tmp_path)
    service = Scripted([AnalyzeError("choose a partition", code=2)])
    with pytest.raises(AnalyzeError):
        service.run(run, threading.Event(), lambda _: None, lambda _: None, lambda _: None)
    assert service.attempts == 1
    assert library.load(run.out).status == "Needs attention"


def test_existing_cli_checkpoint_is_imported_without_changing_outputs(tmp_path: Path) -> None:
    library = RunLibrary(tmp_path / "library")
    out = tmp_path / "cli-run"
    out.mkdir()
    options = dict(
        url="https://vanilla.warcraftlogs.com/character/id/86583560",
        cache=str(library.cache),
        partition=None,
        endpoint="user",
        cross_faction=False,
        name=None,
        package=True,
        category="Balance",
        metric=None,
        faction="Alliance",
    )
    Checkpoint(out, options, False)
    imported = library.import_run(str(out))
    assert imported.resumable and imported.options == options
    assert library.discover()[0].out == out
    assert not (out / module.SESSION).exists()


def test_crash_status_reloads_as_interrupted(tmp_path: Path) -> None:
    library, run = new_run(tmp_path)
    run.store("Running")
    assert library.discover()[0].status == "Interrupted — ready to continue"


def test_stop_interrupts_long_retry_sleep_immediately() -> None:
    stop = threading.Event()
    stop.set()
    with pytest.raises(Stopped):
        StopClock(stop).sleep(3600)
