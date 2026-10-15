"""Capture real self-contained output; no credentials, remote assets or mock data.

Usage: uv run python -m scripts.capture_product workspace/demo/analysis.json
       --out docs/images --render-out workspace/product-capture
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import Request, sync_playwright

from necropsy.report.package import write_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--out", type=Path, default=Path("workspace/product-screens"))
    parser.add_argument("--render-out", type=Path, default=Path("workspace/product-capture"))
    args = parser.parse_args()
    write_outputs(args.analysis.read_bytes(), args.render_out, include_package=False)
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (1440, 1280, 900, 390):
            page = browser.new_page(viewport={"width": width, "height": 1000})
            remote: list[str] = []

            def record_remote(request: Request, *, requests: list[str] = remote) -> None:
                if request.url.startswith("http"):
                    requests.append(request.url)

            page.on("request", record_remote)
            page.goto((args.render_out / "report.html").resolve().as_uri())
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            name = "overview" if width == 1440 else "mobile" if width == 390 else f"width-{width}"
            page.screenshot(path=str(args.out / f"{name}.png"))
            if width == 1440:
                page.locator("#theme-toggle").click()
                page.screenshot(path=str(args.out / "light.png"))
                page.locator("#theme-toggle").click()
                page.locator("#theme-toggle").click()
                page.goto((args.render_out / "playbook.html").resolve().as_uri())
                boss = page.locator("section.boss").first
                boss_id = boss.get_attribute("id")
                page.goto(page.url + "#" + str(boss_id))
                page.locator(f".sidenav a[href='#{boss_id}'][aria-current='location']").wait_for()
                page.screenshot(path=str(args.out / "playbook.png"))
                evidence = boss.locator(".action-evidence > summary").first
                if evidence.count():
                    evidence.click()
                    evidence.locator("..").locator("details > summary").first.click()
                    evidence.scroll_into_view_if_needed()
                    page.screenshot(path=str(args.out / "evidence.png"))
                page.locator(f"#{boss_id}-plan").evaluate("el => el.scrollIntoView()")
                page.screenshot(path=str(args.out / "next-pull.png"))
            assert not remote, remote
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
