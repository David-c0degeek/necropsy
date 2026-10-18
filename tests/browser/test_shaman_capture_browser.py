"""Real Restoration evidence retains support context and unresolved ownership."""

import json
from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import load_entries_manifest

pytestmark = [pytest.mark.golden, pytest.mark.browser]
sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).parents[1] / "golden/raids"


@pytest.fixture(scope="module")
def shaman_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    fixture = next(
        f
        for f in json.loads((ROOT / "provenance.json").read_bytes())["fixtures"]
        if f["label"] == "mc-restoration-shaman-raid-context"
    )
    raw = ROOT / fixture["archive"]
    out = tmp_path_factory.mktemp("shaman-raid")
    run_offline(
        raw,
        out,
        db=out / "analysis.duckdb",
        expected_sha256=fixture["sha256"],
        entries=load_entries_manifest(raw.with_suffix(".entries")),
    )
    doc = json.loads((out / "analysis.json").read_bytes())
    assert len(doc["bosses"]) == 10
    for boss in doc["bosses"]:
        assert boss["subject"]["player"] == "Rumpldoc"
        assert len(boss["overall_cohort"]) == 5
    magmadar = next(b for b in doc["bosses"] if b["encounter_id"] == 50664)
    avaztwo = next(e for e in magmadar["overall_cohort"] if e["player"] == "Avaztwo")
    assert avaztwo["combat"]["pets_known"] is False
    assert avaztwo["combat"]["pets"] == []
    examples = [
        e
        for boss in doc["bosses"]
        for e in boss["playbook"]["healing_context"].get("owned_summon_examples", ())
    ]
    assert len(examples) == 17
    hardzen = next(e for e in examples if e["player"] == "Hardzen")
    assert hardzen["support"]["healing"]["value"] == 683
    assert all(e["support"]["healing"]["value"] is not None for e in examples)
    return out


@pytest.mark.parametrize("width", [1400, 390])
def test_real_shaman_support_keeps_ownership_unknown(shaman_site: Path, width: int) -> None:
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
                page.goto((shaman_site / name).as_uri())
                assert "Rumpldoc" in page.locator("body").inner_text()
                if name == "report.html":
                    page.locator("#analysis-quality > summary").click()
                    assert (
                        "pets unknown for Avaztwo: pet 104 has no valid owner"
                        in page.locator("#analysis-quality").inner_text()
                    )
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
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth + 1"
                )
                summon = page.get_by_text(
                    "Hardzen · zzOLDHealing Stream Totem V (owned unit 64): 683 friendly healing;",
                    exact=False,
                ).first
                summon.scroll_into_view_if_needed()
                assert summon.is_visible()
                assert (
                    "not added to actor support or WCL scores" in page.locator("body").inner_text()
                )
                page.emulate_media(media="print")
                assert summon.is_visible()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth + 1"
                )
                assert not errors and not remote
                page.close()
        finally:
            browser.close()
