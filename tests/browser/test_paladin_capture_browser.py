"""Real full-MC Paladin support keeps unknown ownership and quality limits."""

import json
from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import load_entries_manifest

pytestmark = [pytest.mark.golden, pytest.mark.browser]
sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).parents[1] / "golden/raids"


@pytest.fixture(scope="module")
def paladin_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    fixture = next(
        f
        for f in json.loads((ROOT / "provenance.json").read_bytes())["fixtures"]
        if f["label"] == "mc-holy-paladin-raid-context"
    )
    raw = ROOT / fixture["archive"]
    out = tmp_path_factory.mktemp("paladin-raid")
    run_offline(
        raw,
        out,
        db=out / "analysis.duckdb",
        expected_sha256=fixture["sha256"],
        entries=load_entries_manifest(raw.with_suffix(".entries")),
        package=False,
    )
    doc = json.loads((out / "analysis.json").read_bytes())
    assert len(doc["bosses"]) == 10
    for boss in doc["bosses"]:
        assert boss["subject"]["player"] == "Resurgance"
        assert len(boss["overall_cohort"]) == 5
        assert "exposure_removal_correlations" not in boss["playbook"]
    ragnaros = next(b for b in doc["bosses"] if b["encounter_id"] == 50672)
    guardian = next(e for e in ragnaros["overall_cohort"] if e["player"] == "Carameyl")
    assert guardian["combat"]["pets_known"] is False
    assert guardian["combat"]["pets"] == []
    geddon = next(b for b in doc["bosses"] if b["encounter_id"] == 50668)
    assert geddon["playbook"]["mechanic_removals"][0]["removals"]["value"] == 3
    [example] = geddon["playbook"]["cohort_exposure_removal_correlations"]
    assert example["player"] == "Anrylla"
    assert example["correlations"][0]["intervals_ms"]["value"] == [[7262, 10144, 2882, 4987]]
    return out


@pytest.mark.parametrize("width", [1400, 390])
def test_real_paladin_healing_context_is_usable_without_quality_claims(
    paladin_site: Path, width: int
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
                page.goto((paladin_site / name).as_uri())
                assert "Resurgance" in page.locator("body").inner_text()
                if name == "report.html":
                    page.locator("#analysis-quality > summary").click()
                    assert (
                        "pets unknown for Carameyl: pet 82 has no valid owner"
                        in page.locator("#analysis-quality").inner_text()
                    )
                    pets = page.locator("#boss-50672 .pet-evidence")
                    pets.locator("summary").click()
                    assert "the owned-pet listing is incomplete." in pets.inner_text()
                for encounter in range(50663, 50673):
                    boss = page.locator(f"#boss-{encounter}")
                    support = boss.get_by_text("friendly healing", exact=False).first
                    support.scroll_into_view_if_needed()
                    assert support.is_visible()
                    assert "credited absorption" in boss.inner_text()
                    assert (
                        "Assignments, pet contributions and WCL ranking policies remain separate."
                        in boss.inner_text()
                    )
                geddon = page.locator("#boss-50668")
                for count in (1, 3):
                    finding = geddon.get_by_text(
                        f"Ignite Mana removals: {count} recorded successful effects.", exact=False
                    ).first
                    finding.scroll_into_view_if_needed()
                    assert finding.is_visible()
                pairing = geddon.get_by_text(
                    "recorded exposure from 7.262s to 10.144s (2.882s)", exact=False
                ).first
                pairing.scroll_into_view_if_needed()
                assert pairing.is_visible()
                assert "backup Cleanse coverage" in geddon.inner_text()
                assert "reaction quality" in geddon.inner_text()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                page.emulate_media(media="print")
                assert support.is_visible()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                assert errors == [] and remote == []
                page.close()
        finally:
            browser.close()
