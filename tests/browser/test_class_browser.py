"""All new class/category playbooks expose real execution rows at both sizes."""

from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from tests.class_fixture import CASES, snapshot

pytestmark = pytest.mark.browser
sync_api = pytest.importorskip("playwright.sync_api")


@pytest.mark.parametrize(("class_id", "category", "ability", "role"), CASES)
def test_class_pages_have_ability_execution_sources_and_shared_interactions(
    tmp_path: Path,
    class_id: int,
    category: str,
    ability: str,
    role: str,
) -> None:
    archive = snapshot(tmp_path, class_id, category, ability, role)
    out = tmp_path / "pages"
    run_offline(archive, out)
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as error:
            pytest.skip(f"Chromium unavailable: {error}")
        for width in (1400, 390):
            for name in ("report", "playbook"):
                page = browser.new_page(viewport={"width": width, "height": 1000})
                errors: list[str] = []
                remote: list[str] = []
                page.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
                page.on(
                    "request",
                    lambda r, remote=remote: (
                        remote.append(r.url) if r.url.startswith(("https:", "http:")) else None
                    ),
                )
                page.goto((out / (name + ".html")).as_uri())
                boss = page.locator("section.boss")
                preparation = boss.locator("details.preparation-details")
                if not preparation.evaluate("d => d.open"):
                    preparation.locator(":scope > summary").click()
                execution = boss.locator(".grid.two").first.locator("article").nth(1)
                assert "Opener" in execution.locator("dt").all_text_contents()
                assert ability in execution.locator("dt").all_text_contents()
                assert "first use" in execution.inner_text()
                assert execution.locator('a[href^="https://"]').count() >= 2
                assert "Ability use vs Leader" in boss.inner_text()
                assert boss.locator("details.overall-comparison[open]").count() == 0
                check = boss.locator("input[data-review-key]")
                check.check()
                page.reload()
                assert check.is_checked()
                check.uncheck()
                page.locator("#theme-toggle").click()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                assert not errors and not remote
                page.close()
        browser.close()
