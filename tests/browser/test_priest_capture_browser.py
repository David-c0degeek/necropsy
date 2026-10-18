"""Real credited absorption stays distinct from shield casts in both pages."""

import json
from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import load_entries_manifest

pytestmark = [pytest.mark.golden, pytest.mark.browser]
sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).parents[1] / "golden/raids"


@pytest.fixture(scope="module")
def priest_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    fixture = next(
        f
        for f in json.loads((ROOT / "provenance.json").read_bytes())["fixtures"]
        if f["label"] == "mc-holy-raid-context"
    )
    raw = ROOT / fixture["archive"]
    out = tmp_path_factory.mktemp("priest-raid")
    run_offline(
        raw,
        out,
        db=out / "analysis.duckdb",
        expected_sha256=fixture["sha256"],
        entries=load_entries_manifest(raw.with_suffix(".entries")),
    )
    doc = json.loads((out / "analysis.json").read_bytes())
    assert (
        sum(len(b["playbook"]["healing_context"]["absorption_examples"]) for b in doc["bosses"])
        == 60
    )
    return out


@pytest.mark.parametrize("width", [1400, 390])
def test_priest_absorption_context_is_readable(priest_site: Path, width: int) -> None:
    with sync_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
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
                page.goto((priest_site / name).as_uri())
                sulfuron = page.locator("#boss-50669")
                shield = sulfuron.get_by_text(
                    "Power Word: Shield (10901): 2406 credited absorption;", exact=False
                ).first
                shield.scroll_into_view_if_needed()
                assert shield.is_visible()
                text = sulfuron.inner_text()
                for expected in (
                    "Persistent Shield (26470): 4845 credited absorption; 17 absorption effects",
                    "Almsivi",
                    "7HRVn849AKpbGcmv",
                    "Agree shield priorities with your tanks and healers",
                    "not prevented-damage, mana-efficiency or WCL ranking estimates",
                ):
                    assert expected in text
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth + 1"
                )
                page.emulate_media(media="print")
                assert shield.is_visible()
                assert not errors and not remote
                page.close()
        finally:
            browser.close()
