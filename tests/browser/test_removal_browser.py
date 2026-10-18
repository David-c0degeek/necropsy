"""Real Priest removal effects and their limits remain visible on both pages."""

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
        if f["label"] == "bwl-holy-raid-context"
    )
    raw = ROOT / fixture["archive"]
    out = tmp_path_factory.mktemp("priest-removals")
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
def test_real_owned_removals_and_opportunity_limit_remain_visible(
    priest_site: Path, width: int
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
                page.goto((priest_site / name).as_uri())
                boss = page.locator("#boss-50616")
                for count in (0, 1, 2):
                    finding = boss.get_by_text(
                        f"Brood Affliction Blue removals: {count} recorded successful effects.",
                        exact=False,
                    ).first
                    finding.scroll_into_view_if_needed()
                    assert finding.is_visible()
                assert (
                    "Missing opportunity evidence cannot support a utility score."
                    in boss.inner_text()
                )
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                page.emulate_media(media="print")
                assert finding.is_visible()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                assert errors == [] and remote == []
                page.close()
        finally:
            browser.close()
