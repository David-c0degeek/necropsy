"""Druid pages keep their evidence usable at desktop and phone widths."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from necropsy.report.analysis_json import dumps
from necropsy.report.package import write_outputs
from tests.druid_fixture import document

pytestmark = pytest.mark.browser
sync_api = pytest.importorskip("playwright.sync_api")


@pytest.mark.parametrize("width", [1400, 390])
@pytest.mark.parametrize("page_name", ["report", "playbook"])
@pytest.mark.parametrize("missing", [False, True])
def test_druid_pages_preserve_roles_and_evidence_offline(
    tmp_path: Path,
    width: int,
    page_name: str,
    missing: bool,
) -> None:
    doc = document(tmp_path, ["Healing Touch"] * 3)
    doc["subject"]["name"] = "<script>window.injected=true</script>"
    if missing:
        boss = doc["bosses"][0]
        reference = boss["subject"]
        reference["player"] = "Example healer"
        reference["leaderboard_position"] = 2
        boss["subject"] = None
        boss["playbook"]["reference"] = reference
        boss["playbook"]["personal_data"] = {
            "message": "Not enough personal data in Restoration for this encounter."
        }
        boss["playbook"]["reference_note"] = "Recorded learning example; assignments may differ."
    out = tmp_path / "pages"
    write_outputs(dumps(doc).encode(), out)
    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except sync_api.Error as error:
            if "Executable doesn't exist" in str(error):
                pytest.skip("Playwright Chromium needed")
            raise
        try:
            page = browser.new_page(viewport={"width": width, "height": 900})
            requests: list[str] = []
            errors: list[Any] = []
            page.on("request", lambda r: requests.append(r.url))
            page.on("pageerror", lambda error: errors.append(error))
            page.goto((out / f"{page_name}.html").as_uri())
            assert "restoration" in page.locator("main").inner_text()
            if missing:
                text = page.locator("main").inner_text()
                assert "Example healer" in text and "leaderboard #2" in text
                assert "Your measurements" not in text
                assert "Rank #1 recorded example" not in text
            assert page.locator("#boss-51118").count() == 1
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            assert page.evaluate("window.injected === undefined")
            assert not errors
            assert not any(r.startswith(("http:", "https:")) for r in requests)
            page.locator("#theme-toggle").click()
            page.locator("#boss-search").fill("unmatched")
            assert page.locator(".sidenav li[data-boss-name]").evaluate_all(
                "(rows) => rows.every(r => r.hidden)"
            )
        finally:
            browser.close()
