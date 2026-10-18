"""Partial Elemental evidence cannot turn ranking labels into personal duty."""

import json
from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import load_entries_manifest

pytestmark = [pytest.mark.golden, pytest.mark.browser]
sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).parents[1] / "golden/raids"


@pytest.fixture(
    scope="module",
    params=("mc-elemental-shaman-initial-raid-context", "mc-elemental-shaman-raid-context"),
)
def elemental_site(
    tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest
) -> tuple[Path, str]:
    fixture = next(
        f
        for f in json.loads((ROOT / "provenance.json").read_bytes())["fixtures"]
        if f["label"] == request.param
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
        assert len(boss["overall_cohort"]) == fixture["cohort_counts"][str(boss["encounter_id"])]
        assert (
            len(boss["cohort"])
            == fixture.get("eligible_cohort_counts", fixture["cohort_counts"])[
                str(boss["encounter_id"])
            ]
        )
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
    if fixture["label"] == "mc-elemental-shaman-raid-context":
        assert sum(len(b["cohort"]) for b in doc["bosses"]) == 49
        golemagg = next(b for b in doc["bosses"] if b["encounter_id"] == 50670)
        uncertain = next(e for e in golemagg["overall_cohort"] if e["player"] == "Pythón")
        assert uncertain["combat"]["role"]["value"] is None
        assert all(e["player"] != "Pythón" for e in golemagg["cohort"])
        sulfuron = next(b for b in doc["bosses"] if b["encounter_id"] == 50669)
        assert len(sulfuron["playbook"]["raid_interrupt_contexts"]) == 6
        assert (
            sum(c["interrupts"]["value"] for c in sulfuron["playbook"]["raid_interrupt_contexts"])
            == 2
        )
    return out, fixture["label"]


@pytest.mark.parametrize("width", [1400, 390])
def test_real_elemental_partial_keeps_unknown_duty_and_confirmed_pets(
    elemental_site: tuple[Path, str],
    width: int,
) -> None:
    site, label = elemental_site
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
                page.goto((site / name).as_uri())
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
                if label == "mc-elemental-shaman-raid-context":
                    sulfuron = page.locator("#boss-50669")
                    for text in ("Enoset (raid Shaman 19)", "Shocknlawl (raid Shaman 59)"):
                        effect = sulfuron.get_by_text(text, exact=False).first
                        effect.scroll_into_view_if_needed()
                        assert effect.is_visible()
                    assert "not credited to the selected player" in sulfuron.inner_text()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.emulate_media(media="print")
                assert notice.is_visible()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                assert not errors and not remote
                page.close()
        finally:
            browser.close()
