"""Druid pages keep their evidence usable at desktop and phone widths."""

from __future__ import annotations

from copy import deepcopy
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
    if not missing:
        boss = doc["bosses"][0]
        leader = deepcopy(boss["subject"])
        leader["player"] = "Sparse healer"
        leader["leaderboard_position"] = 1
        boss["playbook"]["reference"] = leader
        boss["playbook"]["comparisons"] = [
            {
                "player": "Sparse healer",
                "leaderboard_position": 1,
                "report_code": "REPORT1",
                "fight_id": 7,
                "build": {"value": "1/0/50", "level": "observed"},
                "kill_duration_s": 100,
                "metrics": {
                    "effective_healing_per_second": {
                        "yours": 3,
                        "reference": 6,
                        "difference": -3,
                        "difference_pct": -50,
                    }
                },
                "spells": [
                    {
                        "spell": "Healing Touch",
                        "counts": {"yours": 3, "reference": 6},
                        "per_minute": {"yours": 1.8, "reference": 3.6},
                    }
                ],
            }
        ]
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
            else:
                text = page.locator("main").inner_text()
                assert "Limited sample: only 1 source" in text
                assert "Sparse healer" in text and "-50.0%" in text
                assert "Your uses/min" in text
            assert page.locator("#boss-51118").count() == 1
            assert page.locator("section.boss .boss-head .metrics").count() == 1
            assert page.locator("#raid-sheet").count() == 1
            assert (
                page.locator("section.boss .grid.two article h3", has_text="Loadout plan").count()
                == 1
            )
            assert (
                page.locator("section.boss .grid.two article h3", has_text="Execution plan").count()
                == 1
            )
            assert page.locator("input[data-review-key]").count() == 1
            assert page.locator("details.overall-comparison[open]").count() == 0
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
