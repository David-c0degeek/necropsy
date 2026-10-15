from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

import httpx
import pytest
from textual.widgets import Button, Input, Select

from necropsy.tui.app import NecropsyApp
from necropsy.tui.service import AnalysisService, RunLibrary, SavedRun, Stopped
from necropsy.wcl import acquire as acquire_module
from necropsy.wcl import analyze as analyze_module
from necropsy.wcl.analyze import Outcome
from necropsy.wcl.client import RateLimit, WclClient
from necropsy.wcl.context import CharacterContext
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _context
from tests.wcl_fakes import FakeClock


class FakeService(AnalysisService):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[SavedRun] = []
        self.waiting = threading.Event()

    def identify(self, *args: Any, **kwargs: Any) -> CharacterContext:
        return _context()

    def run(
        self, run: SavedRun, stop: threading.Event, notify: Any, browser: Any, countdown: Any
    ) -> Outcome:
        self.calls.append(run)
        run.store("Waiting")
        notify("Waiting for Warcraft Logs allowance")
        countdown(90)
        self.waiting.set()
        if stop.wait(10):
            run.store("Stopped — ready to continue")
            raise Stopped
        raise AssertionError("test did not stop the worker")


def test_tui_identifies_creates_stops_and_reloads_a_run(tmp_path: Path) -> None:
    async def scenario() -> None:
        library = RunLibrary(tmp_path)
        service = FakeService()
        app = NecropsyApp(library, service, opener=lambda _: True)
        async with app.run_test(size=(100, 45)) as pilot:
            app.query_one(
                "#character-url", Input
            ).value = "https://vanilla.warcraftlogs.com/character/id/86583560"
            await pilot.click("#find")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app.query_one("#analyze").display
            assert app.query_one("#spec", Select).value == "Marksmanship"
            await pilot.click("#analyze")
            for _ in range(100):
                if service.waiting.is_set():
                    break
                await pilot.pause(0.01)
            assert service.waiting.is_set()
            assert app.busy and app.query_one("#continue", Button).disabled
            app.action_stop()
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert not app.busy
            assert len(library.discover()) == 1
            assert not app.query_one("#continue", Button).disabled
        reloaded = NecropsyApp(RunLibrary(tmp_path), FakeService())
        async with reloaded.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert len(reloaded.saved) == 1
            assert "Stopped" in reloaded.saved[0].status
            assert not reloaded.query_one("#continue", Button).disabled

    asyncio.run(scenario())


def test_guided_worker_writes_real_report_and_opens_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = FakeWcl([Player(f"Ally{i}") for i in range(1, 31)], Player("Haplina"))
    monkeypatch.setattr(acquire_module, "boss_order", lambda: (PATCHWERK,))
    monkeypatch.setattr(analyze_module, "resolve", lambda *args, **kwargs: _context())

    class RealAnalysis(AnalysisService):
        def ensure_connected(self, *args: Any) -> None:
            pass

        @property
        def auth(self) -> Any:
            class Tokens:
                @staticmethod
                def token_for(endpoint: str) -> str:
                    return "synthetic-tui-token"

            return Tokens()

        def factory(self, stop: threading.Event) -> Any:
            def client(site: Any, tokens: Any) -> WclClient:
                self.client = WclClient(
                    site, tokens, transport=httpx.MockTransport(server), clock=FakeClock()
                )
                self.client.last_rate = RateLimit(36000, 10, 1800)
                return self.client

            return client

    async def scenario() -> None:
        library = RunLibrary(tmp_path)
        run = library.create(
            "https://vanilla.warcraftlogs.com/character/id/86583560", "Marksmanship", _context()
        )
        opened: list[str] = []

        def open_report(path: str) -> bool:
            opened.append(path)
            return True

        app = NecropsyApp(library, RealAnalysis(), opener=open_report)
        async with app.run_test(size=(100, 45)) as pilot:
            app.start_operation("run", run)
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert (run.out / "report.html").is_file()
            assert (run.out / "playbook.html").is_file()
            assert library.load(run.out).status == "Complete"
            assert opened == [(run.out / "playbook.html").as_uri()]
            assert not app.busy
            assert app.query_one("#continue", Button).disabled
            assert not app.query_one("#report", Button).disabled

    asyncio.run(scenario())
