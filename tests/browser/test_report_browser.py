"""Headless-browser checks of the rendered report and playbook (uv run pytest -m browser).

Needs Playwright's Chromium (`uv run playwright install chromium`); without it
these tests are skipped with that reason.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from necropsy.report.offline import run_offline
from necropsy.report.package import write_outputs
from tests.analysis_db import subset_db
from tests.fixture_paths import subset_path

pytestmark = pytest.mark.browser

sync_api = pytest.importorskip("playwright.sync_api")

DESKTOP = {"width": 1400, "height": 900}
MOBILE = {"width": 390, "height": 844}


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site")
    run_offline(subset_path(), out, db=subset_db(), package=False)
    return out


@pytest.fixture(scope="module")
def hostile_site(site: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    document = json.loads((site / "analysis.json").read_bytes())
    long_name = "Ünïcødé名" + "W" * 80 + "</script><img src=x>"
    document["subject"]["name"] = long_name
    boss = document["bosses"][0]
    boss["boss"] = long_name
    boss["cohort"][0]["player"] = long_name
    if boss.get("overall_cohort"):
        boss["overall_cohort"][0]["player"] = long_name
    if document.get("overview"):
        document["overview"]["corrections"][0]["rank_one_player"] = long_name
    if boss.get("playbook"):
        boss["playbook"]["context"]["comparator"]["player"] = long_name
    for rec in boss["recommendations"]:
        rec["finding"] = long_name
    out = tmp_path_factory.mktemp("hostile-site")
    write_outputs(json.dumps(document, sort_keys=True).encode("utf-8"), out, include_package=False)
    return out


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    with sync_api.sync_playwright() as p:
        try:
            chromium = p.chromium.launch()
        except Exception as exc:  # Chromium not installed
            pytest.skip(f"Chromium unavailable: {exc}")
        yield chromium
        chromium.close()


class _Watch:
    def __init__(self, page: Any) -> None:
        self.errors: list[str] = []
        self.requests: list[str] = []
        page.on("console", lambda m: self.errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: self.errors.append(str(e)))
        page.on("request", lambda r: self.requests.append(r.url))

    def check(self) -> None:
        assert self.errors == []
        assert [u for u in self.requests if not u.startswith("file:")] == []


@pytest.fixture
def page(browser: Any) -> Iterator[Any]:
    context = browser.new_context(viewport=DESKTOP)
    yield context.new_page()
    context.close()


def test_desktop_navigation_between_report_and_playbook(page: Any, site: Path) -> None:
    watch = _Watch(page)
    page.goto((site / "report.html").as_uri())
    assert page.locator("section.boss").count() == 4
    assert page.locator("nav.sidenav").is_visible()
    page.locator("nav.sidenav a", has_text="Gothik").click()
    assert page.url.endswith("#boss-51109")
    page.locator("nav.switch a", has_text="Playbook").click()
    assert page.url.endswith("playbook.html#boss-51109")
    assert page.locator("h1").inner_text().lower().endswith("playbook")
    page.locator("nav.switch a", has_text="Report").click()
    assert page.url.endswith("report.html#boss-51109")
    watch.check()


def test_keyboard_skip_link_and_disclosures(page: Any, site: Path) -> None:
    page.goto((site / "report.html").as_uri())
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id") == "main"
    summary = page.locator("main details > summary").first
    details = page.locator("main details").first
    summary.focus()
    initial = details.evaluate("d => d.open")
    page.keyboard.press("Enter")
    assert details.evaluate("d => d.open") is not initial


def test_theme_toggle_cycles_and_persists(page: Any, site: Path) -> None:
    page.goto((site / "report.html").as_uri())
    button = page.locator("#theme-toggle")
    assert button.inner_text() == "Theme: dark"
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    button.click()
    assert page.evaluate("document.documentElement.dataset.theme") == "light"
    page.reload()
    assert page.evaluate("document.documentElement.dataset.theme") == "light"
    button.click()
    assert page.evaluate("document.documentElement.dataset.theme") is None
    assert button.inner_text() == "Theme: system"
    page.reload()
    assert page.locator("#theme-toggle").inner_text() == "Theme: system"
    button.click()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"


def test_review_marks_persist_and_reset(page: Any, site: Path) -> None:
    page.goto((site / "playbook.html").as_uri())
    box = page.locator("input[data-review-key]").first
    box.check()
    page.reload()
    assert page.locator("input[data-review-key]").first.is_checked()
    assert "only in this browser" in page.locator("#review-status").inner_text()
    page.locator("#reset-reviews").click()
    page.reload()
    assert not page.locator("input[data-review-key]").first.is_checked()


def test_print_opens_disclosures_and_restores_them(page: Any, site: Path) -> None:
    page.goto((site / "report.html").as_uri())
    first = page.locator("main details").first
    first.evaluate("d => { d.open = true; }")
    before = page.evaluate("[...document.querySelectorAll('main details')].map(d => d.open)")
    page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
    assert page.evaluate("[...document.querySelectorAll('details')].every(d => d.open)")
    page.evaluate("window.dispatchEvent(new Event('afterprint'))")
    states = page.evaluate("[...document.querySelectorAll('main details')].map(d => d.open)")
    assert states == before
    page.emulate_media(media="print")
    assert not page.locator("#theme-toggle").is_visible()
    assert page.locator(".severity-label").first.evaluate(
        "el => getComputedStyle(el).color"
    ) == "rgb(34, 34, 34)"


def test_compact_picker_works_without_a_select(browser: Any, site: Path) -> None:
    context = browser.new_context(viewport=MOBILE)
    page = context.new_page()
    watch = _Watch(page)
    page.goto((site / "report.html").as_uri())
    assert not page.locator("nav.sidenav").is_visible()
    page.locator("#boss-picker > summary").click()
    page.locator("#boss-picker a", has_text="Kel'Thuzad").click()
    assert page.url.endswith("#boss-51114")
    assert not page.locator("#boss-picker").evaluate("d => d.open")
    page.wait_for_function("document.activeElement.id === 'boss-51114-title'")
    watch.check()
    context.close()


def test_side_navigation_marks_the_current_boss(page: Any, site: Path) -> None:
    page.goto((site / "report.html").as_uri() + "#boss-51109")
    current = page.locator(".sidenav a[aria-current='location']")
    assert current.count() == 1 and "Gothik" in current.inner_text()
    assert page.locator(".sidenav .sr").first.inner_text().strip().startswith("finding")


@pytest.mark.parametrize("viewport", [DESKTOP, MOBILE])
def test_boss_search_keeps_overview_and_truth_links(
    browser: Any, site: Path, viewport: dict[str, int]
) -> None:
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    page.goto((site / "playbook.html").as_uri())
    nav = "nav.sidenav" if viewport == DESKTOP else "#boss-picker"
    if viewport == MOBILE:
        page.locator("#boss-picker > summary").click()
    page.get_by_role("searchbox", name="Filter bosses").fill("  GoThIk  ")
    assert page.locator(f"{nav} li[data-boss-name]:visible").count() == 1
    assert page.locator(f"{nav} a[href='#overview']").is_visible()
    truth = page.locator(f"{nav} a[href='#truth-model']")
    assert truth.is_visible()
    assert page.locator("section.boss").count() == 4
    truth.click()
    page.wait_for_function("document.activeElement.id === 'truth-model-title'")
    page.get_by_role("searchbox", name="Filter bosses").fill("")
    if viewport == MOBILE:
        page.locator("#boss-picker > summary").click()
    assert page.locator(f"{nav} li[data-boss-name]:visible").count() == 4
    context.close()


@pytest.mark.parametrize("width", [320, 390, 768])
@pytest.mark.parametrize("name", ["report.html", "playbook.html"])
def test_no_horizontal_page_scroll(browser: Any, hostile_site: Path, width: int, name: str) -> None:
    context = browser.new_context(viewport={"width": width, "height": 800})
    page = context.new_page()
    page.goto((hostile_site / name).as_uri())
    page.evaluate("document.querySelectorAll('details').forEach(d => { d.open = true; })")
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1, (name, width, overflow)
    context.close()


def test_storage_blocked_still_works(browser: Any, site: Path) -> None:
    context = browser.new_context(viewport=DESKTOP)
    context.add_init_script(
        "Object.defineProperty(window, 'localStorage', {get() { throw new Error('blocked'); }});"
    )
    page = context.new_page()
    watch = _Watch(page)
    page.goto((site / "playbook.html").as_uri())
    assert "does not allow saving" in page.locator("#review-status").inner_text()
    page.locator("input[data-review-key]").first.check()
    page.locator("#theme-toggle").click()
    watch.check()
    context.close()


@pytest.mark.parametrize("name", ["report.html", "playbook.html"])
def test_definitive_sections_full_cohort_and_equipment(page: Any, site: Path, name: str) -> None:
    document = json.loads((site / "analysis.json").read_bytes())
    watch = _Watch(page)
    page.goto((site / name).as_uri())
    page.locator("details.raid-reference > summary").click()
    for heading in (
        "Global setup",
        "Corrections that matter after faction normalization",
        "Truth model / what every label means",
        "At-a-glance raid sheet",
    ):
        assert page.get_by_role("heading", name=heading, exact=True).count() == 1
    columns = [
        "#",
        "Hunter",
        "Faction",
        "Race evidence",
        "WF procs",
        "DPS",
        "Spec",
        "Trinkets",
        "Weapons",
        "Raptor",
        "White",
        "Pet",
        "Pet DPS",
    ]
    for boss in document["bosses"]:
        section = page.locator(f"#boss-{boss['encounter_id']}")
        # Detailed contracts remain available through native disclosures.
        section.evaluate("s => s.querySelectorAll('details').forEach(d => d.open = true)")
        for heading in (
            "Benchmark context",
            "Loadout plan",
            "Execution plan",
            "Do not",
            "Raid help",
        ):
            assert section.get_by_role("heading", name=heading, exact=True).count() == 1
        assert section.locator(".quick-plan .plan-lines > dt").all_text_contents() == [
            "Recommended opener",
            "Rapid Fire",
            "Notes",
        ]
        assert section.locator(".grid.two .plan-lines > dt").all_text_contents() == [
            "Weapons",
            "Trinkets",
            "Pet",
            "Weaving",
            "Opener",
            "Rapid Fire",
            "Refocus",
        ]
        assert section.locator(".cohort-table thead th").all_text_contents() == columns
        assert section.locator(".cohort-table tbody > tr").count() == len(boss["overall_cohort"])
        assert section.locator(".full-gear .gear-grid > div").count() == 17
        cards = section.locator(".hunter-card")
        assert cards.count() == len(boss["overall_cohort"])
        for card in cards.all():
            assert card.locator(".gear-grid > div").count() == 17
    watch.check()


def test_product_priorities_filters_and_boss_review(page: Any, site: Path) -> None:
    page.goto((site / "playbook.html").as_uri())
    assert page.locator("html").get_attribute("data-class") == "hunter"
    assert page.locator("html").get_attribute("data-raid") == "naxxramas"
    assert page.locator(".priority-list > li").count() == 3
    assert page.locator(".raid-reference").evaluate("d => !d.open")
    assert page.locator(".cohort-details[open]").count() == 0
    first_boss = page.locator("section.boss").first
    assert first_boss.locator(".boss-actions > .cards > .card").count() == 2
    first_boss.locator(".done input").check()
    page.locator("#boss-filter").select_option("reviewed")
    assert page.locator(".sidenav li[data-boss-name]:visible").count() == 1
    assert "Reviewed locally" in page.locator(".triage-row").first.inner_text()
    page.reload()
    assert first_boss.locator(".done input").is_checked()
    page.locator("#boss-filter").select_option("unreviewed")
    assert page.locator(".sidenav li[data-boss-name]:visible").count() == 3
    page.locator("#boss-filter").select_option("limited")
    assert page.locator(".sidenav li[data-boss-name]:visible").count() == 3
    page.locator("#boss-search").fill("no such boss")
    assert "No matching bosses" in page.locator("#nav-results").inner_text()
    assert page.locator("section.boss").count() == 4  # Filters never remove evidence.


@pytest.mark.parametrize("width", [390, 900, 1280, 1440])
def test_product_light_reduced_motion_and_expanded_layout(
    browser: Any, site: Path, width: int
) -> None:
    context = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce")
    page = context.new_page()
    watch = _Watch(page)
    page.goto((site / "report.html").as_uri())
    page.locator("#theme-toggle").click()
    assert page.locator("html").get_attribute("data-theme") == "light"
    assert page.locator(".character-name").is_visible()
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    watch.check()
    context.close()


def test_no_javascript_preserves_coaching_and_native_evidence(browser: Any, site: Path) -> None:
    context = browser.new_context(java_script_enabled=False, viewport=MOBILE)
    page = context.new_page()
    page.goto((site / "playbook.html").as_uri())
    assert page.locator(".priority-list").is_visible()
    boss = page.locator("section.boss").first
    disclosure = boss.locator(".action-evidence").first
    disclosure.locator(":scope > summary").click()
    assert disclosure.get_attribute("open") is not None
    assert boss.locator(".quick-plan").is_visible()
    assert page.locator(".switch a").count() == 2
    context.close()


def test_keyboard_reveals_nested_evidence_destination(page: Any, site: Path) -> None:
    page.goto((site / "report.html").as_uri())
    link = page.locator(".sidenav a[href='#truth-model']")
    link.focus()
    page.keyboard.press("Enter")
    assert page.locator(".raid-reference").evaluate("d => d.open")
    assert page.locator("#truth-model-title").is_visible()
    assert page.evaluate("document.activeElement.id") == "truth-model-title"
    action_link = page.locator(".boss-jumps a[href$='-actions']").first
    action_link.focus()
    page.keyboard.press("Enter")
    assert page.locator(".boss-actions h3").first.evaluate(
        "el => document.activeElement === el"
    )


def test_all_class_accents_have_readable_dark_and_light_contrast(page: Any, site: Path) -> None:
    page.goto((site / "report.html").as_uri())
    ratios = page.evaluate("""() => {
      const root = document.documentElement;
      const probe = document.createElement('span');
      probe.style.background = 'var(--surface-panel)';
      document.body.appendChild(probe);
      function luminance(color) {
        const values = color.match(/[\\d.]+/g).slice(0,3).map(Number).map(v => {
          v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
        });
        return values[0] * .2126 + values[1] * .7152 + values[2] * .0722;
      }
      const results = [];
      for (const mode of ['dark','light']) {
        root.dataset.theme = mode;
        for (const cls of ['hunter','druid','mage','warrior','paladin','priest',
                           'shaman','rogue','warlock','unrecognized']) {
          root.dataset.class = cls;
          const character = document.querySelector('.character-name');
          const foreground = luminance(getComputedStyle(character).color);
          const background = luminance(getComputedStyle(probe).backgroundColor);
          results.push([mode,cls,(Math.max(foreground,background)+.05)/(Math.min(foreground,background)+.05)]);
        }
      }
      probe.remove(); return results;
    }""")
    assert all(ratio >= 4.5 for _, _, ratio in ratios), ratios
