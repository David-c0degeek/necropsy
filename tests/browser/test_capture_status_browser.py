"""The committed capture status page, fed by the real runner's public status for
the production queue: search, filters, inert markup, feed loss and recovery, and
a stale heartbeat that drops the live claim."""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts import capture_runner as cr
from scripts import visual_check as vc

pytestmark = pytest.mark.browser
sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "tasks" / "raid-completion" / "capture-queue.json"


def status(tmp_path: Path, *, heartbeat_age: timedelta = timedelta(0)) -> dict[str, Any]:
    """The runner's public status for the real queue, with some runs deferred."""
    paths = cr.Paths(
        QUEUE, tmp_path / "state", tmp_path / "out", tmp_path / "cache", tmp_path / "w"
    )
    for directory in (paths.state, paths.out, paths.cache, paths.www):
        directory.mkdir(parents=True, exist_ok=True)
    now = cr.utcnow() - heartbeat_age
    runner = cr.Runner(paths, now=lambda: now, free_floor_bytes=0)
    runner.load()
    for entry in runner.entries[:5]:
        info = runner.state["entries"][entry.entry_id]
        info.update(state=cr.DEFERRED, reason="quota-reset stop", retry_at=cr.iso(now))
    runner.state["inflight"] = {
        "entry": runner.entries[5].entry_id,
        "attempt": 1,
        "candidate": 0,
    }
    return runner.status()


@pytest.fixture
def page(tmp_path: Path) -> Iterator[tuple[Any, Path, str]]:
    site = tmp_path / "site"
    shutil.copytree(ROOT / "capture" / "www", site)
    server, base = vc.serve(site)
    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as error:
            pytest.skip(f"Chromium unavailable: {error}")
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.route(
            "**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort()
        )
        tab = context.new_page()
        try:
            yield tab, site, base
        finally:
            browser.close()
            server.shutdown()


def load(page: tuple[Any, Path, str], data: dict[str, Any]) -> None:
    tab, site, base = page
    (site / "status.json").write_text(json.dumps(data), encoding="utf-8")
    tab.goto(base + "index.html")
    tab.wait_for_function("document.querySelectorAll('#runs tr').length > 1")


def rows(tab: Any) -> int:
    return int(tab.locator("#runs tr").count())


def test_search_filters_and_feed_loss_keep_the_last_snapshot(
    page: tuple[Any, Path, str], tmp_path: Path
) -> None:
    tab, site, _ = page
    data = status(tmp_path)
    load(page, data)
    total = len(data["entries"])
    assert rows(tab) == total == 93
    assert tab.locator("#state").inner_text() == "Running"
    bwl = sum(e["raid"] == "bwl" for e in data["entries"])
    tab.fill("#search", "bwl")
    tab.wait_for_timeout(200)
    assert rows(tab) == bwl
    tab.fill("#search", "<img src=x onerror=alert(1)>")
    tab.wait_for_timeout(200)
    assert tab.locator("#runs img").count() == 0
    assert "No runs match these filters." in tab.locator("#runs").inner_text()
    tab.fill("#search", "")
    tab.select_option("#filter", "deferred")
    tab.wait_for_timeout(200)
    assert rows(tab) == 5
    tab.select_option("#filter", "all")
    (site / "status.json").unlink()
    tab.click("#refresh")
    tab.wait_for_timeout(1500)
    assert tab.locator("#connection-text").inner_text().startswith("Cannot reach the status feed")
    assert "Last known Running" in tab.locator("#snapshot-time").inner_text()
    assert rows(tab) == total
    (site / "status.json").write_text(json.dumps(data), encoding="utf-8")
    tab.click("#refresh")
    tab.wait_for_timeout(1500)
    assert tab.locator("#connection-text").inner_text().startswith("Worker reported")


def test_a_stale_heartbeat_drops_the_live_claim(
    page: tuple[Any, Path, str], tmp_path: Path
) -> None:
    tab = page[0]
    load(page, status(tmp_path, heartbeat_age=timedelta(hours=1)))
    assert tab.locator("#state").inner_text() == "Worker offline"
    assert "heartbeat is stale" in tab.locator("#connection-text").inner_text()
    assert "Last saved snapshot" in tab.locator("#table-summary").inner_text()
