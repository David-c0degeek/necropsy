"""Real AQ40 summon observations remain readable on desktop, mobile and print."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import load_entries_manifest

pytestmark = [pytest.mark.golden, pytest.mark.browser]
sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).parents[1] / "golden/raids"


@pytest.fixture(
    scope="module", params=["aq40-holy-complete-context", "aq40-hunter-expanded-context"]
)
def summon_site(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    fixture = next(
        f
        for f in json.loads((ROOT / "provenance.json").read_bytes())["fixtures"]
        if f["label"] == request.param
    )
    raw = ROOT / fixture["archive"]
    out = tmp_path_factory.mktemp(fixture["label"])
    run_offline(
        raw,
        out,
        db=out / "analysis.duckdb",
        expected_sha256=fixture["sha256"],
        entries=load_entries_manifest(raw.with_suffix(".entries")),
        package=False,
    )
    return out


@pytest.mark.parametrize("width", [1400, 390])
def test_real_summon_observations_have_visible_bounds_and_limits_without_overflow(
    summon_site: Path,
    width: int,
) -> None:
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as error:
            pytest.skip(f"Chromium unavailable: {error}")
        try:
            for name in ("report.html", "playbook.html"):
                page = browser.new_page(viewport={"width": width, "height": 1000})
                errors: list[str] = []
                remote: list[str] = []
                page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
                page.on(
                    "request",
                    lambda request, remote=remote: (
                        remote.append(request.url)
                        if request.url.startswith(("http:", "https:"))
                        else None
                    ),
                )
                page.goto((summon_site / name).as_uri())
                boss = page.locator("#boss-50709")
                heading = boss.get_by_text("Observed summon event bounds.", exact=False).first
                heading.scroll_into_view_if_needed()
                assert heading.is_visible()
                text = boss.inner_text()
                assert "Groups can overlap." in text
                assert "does not establish lifetime, continuous attackability" in text
                assert "from summon to first positive-overkill marker." in text
                assert "In " in text and "'s fight: Summon Images:" in text
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                page.emulate_media(media="print")
                assert heading.is_visible()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                assert errors == [] and remote == []
                page.close()
        finally:
            browser.close()
