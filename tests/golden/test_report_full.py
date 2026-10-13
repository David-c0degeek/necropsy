"""Full export end to end: offline analysis to report, playbook and package (golden + browser)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from necropsy.report.package import package_name, write_outputs
from necropsy.report.render import build_view, load_document
from tests.analysis_db import full_db
from tests.fixture_paths import is_lfs_pointer, raw_export_path

pytestmark = pytest.mark.golden


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    raw = raw_export_path()
    if not raw.is_file() or is_lfs_pointer(raw):
        pytest.fail(f"{raw.name} is missing or an LFS pointer. Run `git lfs pull` first.")
    out = tmp_path_factory.mktemp("full-site")
    run_offline(raw, out, db=full_db())
    return out


def test_full_export_produces_the_package(site: Path) -> None:
    analysis = (site / "analysis.json").read_bytes()
    document = json.loads(analysis)
    package = site / package_name(document)
    with zipfile.ZipFile(package) as zf:
        assert zf.read("analysis.json") == analysis
        assert len([n for n in zf.namelist() if n.startswith("evidence/")]) == 15
    for name in ("report.html", "playbook.html"):
        html = (site / name).read_text(encoding="utf-8")
        assert html.count('<section class="boss"') == 15


def test_rerendering_the_full_analysis_is_byte_identical(site: Path, tmp_path: Path) -> None:
    write_outputs((site / "analysis.json").read_bytes(), tmp_path)
    for path in tmp_path.iterdir():
        assert path.read_bytes() == (site / path.name).read_bytes(), path.name


@pytest.mark.browser
def test_full_report_in_a_browser(site: Path) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        errors: list[str] = []
        requests: list[str] = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: requests.append(r.url))
        for name in ("report.html", "playbook.html"):
            page.goto((site / name).as_uri())
            assert page.locator("section.boss").count() == 15
            links = page.locator("nav.sidenav a")
            assert links.count() == 17
            for i in range(17):
                href = links.nth(i).get_attribute("href")
                assert href is not None and page.locator(href).count() == 1
        browser.close()
        assert errors == []
        assert [u for u in requests if not u.startswith("file:")] == []


def test_sapphiron_fill_is_considered_not_used(site: Path) -> None:
    document, sha = load_document((site / "analysis.json").read_bytes())
    view = build_view(document, sha)
    sapphiron = next(b for b in view.bosses if b.name == "Sapphiron")
    assert sapphiron.fill is not None and not sapphiron.fill.applied
    assert sapphiron.fill.eligible == ()
    assert any("no other-faction entry qualified" in limit for limit in sapphiron.limits)
    razuvious = next(b for b in view.bosses if b.name == "Instructor Razuvious")
    explosives = next(f for f in razuvious.cooldowns if f.label == "Explosives used")
    assert explosives.typical is not None and explosives.typical.level == "inferred"
