"""Real owned control and curse observations support review with unknown totals."""

import json
from pathlib import Path

import pytest

from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import load_entries_manifest

pytestmark = [pytest.mark.golden, pytest.mark.browser]
sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).parents[1] / "golden/raids"


@pytest.fixture(scope="module")
def control_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    fixture = next(
        f
        for f in json.loads((ROOT / "provenance.json").read_bytes())["fixtures"]
        if f["label"] == "mc-garr-control-warlock"
    )
    raw = ROOT / fixture.get("archive", f"raw/{fixture['label']}.zip")
    out = tmp_path_factory.mktemp("owned-control")
    run_offline(
        raw,
        out,
        db=out / "analysis.duckdb",
        expected_sha256=fixture["sha256"],
        entries=load_entries_manifest(raw.with_suffix(".entries")),
    )
    doc = json.loads((out / "analysis.json").read_bytes())
    (control,) = doc["bosses"][0]["playbook"]["control_applications"]
    assert control["applications"]["value"] is None
    assert control["observations"]["value"] == [[4.258, 100, 8, 18647]]
    assert len(control["review"]) == 1
    (curse,) = doc["bosses"][0]["playbook"]["curse_applications"]
    assert curse["applications"]["value"] is None
    assert curse["observations"]["value"] == [[5.764, 101, None, 17937]]
    assert len(curse["review"]) == 1
    return out


@pytest.mark.parametrize("width", [1400, 390])
def test_owned_control_review_survives_unknown_total(control_site: Path, width: int) -> None:
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
                page.goto((control_site / name).as_uri())
                boss = page.locator("#boss-50666")
                review = boss.get_by_text(
                    "Recorded Banish on Firesworn 100, instance 8, at 4.26s.", exact=False
                )
                assert review.count() == 1
                review.scroll_into_view_if_needed()
                assert review.is_visible()
                text = boss.inner_text()
                for expected in (
                    "Recorded Firesworn Banish applications: Unknown.",
                    "Confirm whether you should maintain control on this add",
                    "not an assignment, maintained uptime or proof that control was needed",
                    "who provides backup when it ends",
                    "Recorded Garr Recklessness/Elements/Shadow curse applications: Unknown.",
                    "5.76s · Curse ability 17937 applied; target actor 101, instance unrecorded.",
                    "Confirm which curse your raid assigned you before copying a reference "
                    "curse choice.",
                    "not an assignment, uptime or a recommendation to change curses",
                ):
                    assert expected in text
                curse_review = boss.get_by_text(
                    "Recorded Curse of Shadow on Garr 101, instance unrecorded, at 5.76s.",
                    exact=False,
                )
                assert curse_review.count() == 1
                curse_review.scroll_into_view_if_needed()
                assert curse_review.is_visible()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth + 1"
                )
                page.emulate_media(media="print")
                assert review.is_visible()
                assert curse_review.is_visible()
                assert not errors and not remote
                page.close()
        finally:
            browser.close()
