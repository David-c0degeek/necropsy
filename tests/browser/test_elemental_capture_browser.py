"""Partial Elemental evidence cannot turn ranking labels into personal duty."""

import json
from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import load_entries_manifest

pytestmark = [pytest.mark.golden, pytest.mark.browser]
sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).parents[1] / "golden/raids"


@pytest.fixture(scope="module")
def elemental_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    fixture = next(
        f
        for f in json.loads((ROOT / "provenance.json").read_bytes())["fixtures"]
        if f["label"] == "mc-elemental-shaman-initial-raid-context"
    )
    raw = ROOT / fixture["archive"]
    out = tmp_path_factory.mktemp("elemental-raid")
    run_offline(
        raw,
        out,
        db=out / "analysis.duckdb",
        expected_sha256=fixture["sha256"],
        entries=load_entries_manifest(raw.with_suffix(".entries")),
    )
    doc = json.loads((out / "analysis.json").read_bytes())
    assert len(doc["bosses"]) == 10 and all(b["subject"] is None for b in doc["bosses"])
    for boss in doc["bosses"]:
        assert boss["recommendations"] == []
        if boss["encounter_id"] in fixture["excluded_subject_encounters"]:
            excluded = boss["playbook"]["excluded_subject"]
            assert excluded["player"] == "Rumpldoc"
            assert excluded["combat"]["role"]["value"] is None
        else:
            assert len(boss["cohort"]) == 5
    majordomo = next(b for b in doc["bosses"] if b["encounter_id"] == 50671)
    owner = next(e for e in majordomo["overall_cohort"] if e["player"] == "Bushmilfs")
    assert owner["combat"]["pets_known"] is False
    assert {p["actor_id"]: p["damage"]["value"] for p in owner["combat"]["pets"]} == {
        48: 10843,
        106: 8174,
    }
    return out


@pytest.mark.parametrize("width", [1400, 390])
def test_real_elemental_partial_keeps_unknown_duty_and_confirmed_pets(
    elemental_site: Path,
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
                page.goto((elemental_site / name).as_uri())
                for encounter in range(50663, 50673):
                    boss = page.locator(f"#boss-{encounter}")
                    notice = boss.get_by_text(
                        (
                            "Your performance is not assessed for this boss in the selected spec."
                            if name == "report.html"
                            else "No matching personal fight is available. This is a practice "
                            "reference, not an assessment of your performance. Confirm assignments "
                            "before copying an example."
                        ),
                        exact=True,
                    ).first
                    notice.scroll_into_view_if_needed()
                    assert notice.is_visible()
                majordomo = page.locator("#boss-50671")
                assert "Stormstrike" in majordomo.inner_text()
                if name == "report.html":
                    panel = majordomo.locator(".pet-evidence")
                    panel.locator("summary").click()
                    text = panel.inner_text().replace(",", "")
                    assert "Bushmilfs" in text and "owned-pet listing is incomplete" in text
                    assert "10843" in text and "8174" in text
                else:
                    assert "cannot establish all-summon totals" in majordomo.inner_text()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.emulate_media(media="print")
                assert notice.is_visible()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                assert not errors and not remote
                page.close()
        finally:
            browser.close()
