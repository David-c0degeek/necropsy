"""Capture the real empty TUI without credentials, user history or remote fonts."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from necropsy.tui.app import NecropsyApp
from necropsy.tui.service import RunLibrary


async def capture(root: Path) -> str:
    app = NecropsyApp(RunLibrary(root))
    async with app.run_test(size=(100, 35)) as pilot:
        await pilot.pause()
        return app.export_screenshot()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("docs/images/terminal.png"))
    args = parser.parse_args()
    # Show the ordinary color-capable desktop experience, independent of a CI
    # parent process asking its own command output to be monochrome.
    os.environ.pop("NO_COLOR", None)
    with tempfile.TemporaryDirectory(prefix="necropsy-tui-capture-") as temporary:
        svg = asyncio.run(capture(Path(temporary).resolve()))
    svg = re.sub(r"@font-face\s*\{[^}]*\}", "", svg)
    svg = svg.replace("<svg ", '<svg width="1238" height="904" ', 1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 910})
        page.route("**/*", lambda route: route.abort())
        page.set_content('<body style="margin:0;background:#10151b">' + svg)
        page.screenshot(path=str(args.out))
        browser.close()
    print(f"Saved terminal screenshot: {args.out}")


if __name__ == "__main__":
    main()
