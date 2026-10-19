"""Screenshot static pages at several widths and colour schemes and report layout,
network and console problems.

    uv run python scripts/visual_check.py SITE_DIR --page report.html [--page playbook.html]
        --out DIR [--browser chromium|msedge] [--widths 1440,390] [--schemes dark,light]
        [--print] [--max-height 20000]

A temporary copy of SITE_DIR is served on 127.0.0.1 and the network is closed:
every request to another origin is refused before it is sent, a same-origin
response that redirects is refused rather than followed (the browser never
connects to the redirect target), WebSockets and service workers are blocked.
Each screen records its page, width, scheme, the files of its pictures,
horizontal overflow, elements past the right edge that are not inside a
horizontally scrollable container, console and page errors, refused requests
and failed requests.

Pictures keep the real viewport (width x 1000): a page up to --max-height is
taken whole, a longer one as viewport tiles down to that height, so the picture
shows the same layout the checks measured; the record says when it stops short
of the page end. `--print` adds print-media screens.

The exit code is 1 when any screen has a finding. A clean run is layout,
network and console evidence only: it is not visual, domain or print approval
(a print-media screenshot does not prove PDF pagination), and the pictures are
there for a person or the peer reviewer to look at.
"""

from __future__ import annotations

import argparse
import http.server
import json
import math
import re
import shutil
import sys
import tempfile
import threading
from functools import partial
from pathlib import Path
from typing import Any

from playwright.sync_api import (
    Browser,
    ConsoleMessage,
    Error,
    Page,
    Request,
    Route,
    WebSocketRoute,
    sync_playwright,
)

VIEWPORT_HEIGHT = 1000
PAST_EDGE = """() => [...document.querySelectorAll('body *')]
  .filter(e => {
    const box = e.getBoundingClientRect();
    if (box.width <= 0 || box.right <= innerWidth + 1) return false;
    for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) {
      const x = getComputedStyle(a).overflowX;
      if (x === 'auto' || x === 'scroll') return false;
    }
    return true;
  })
  .slice(0, 10)
  .map(e => {
    const classes = typeof e.className === 'string' ? e.className.trim() : '';
    return e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
      (classes ? '.' + classes.split(/\\s+/).join('.') : '');
  })"""


class SiteError(ValueError):
    """The site or output directory cannot be used safely."""


def copy_site(site: Path, target: Path) -> None:
    """Copy SITE into TARGET, refusing links that could lead outside it."""
    for path in [site, *site.rglob("*")]:
        if path.is_symlink() or path.is_junction():
            raise SiteError(f"{path} is a link; the site must be plain files")
    shutil.copytree(site, target, symlinks=False)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def serve(root: Path) -> tuple[http.server.ThreadingHTTPServer, str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


def stem(page_name: str) -> str:
    """A file-name-safe, unique stem for a page path inside the site."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", page_name.replace("/", "__"))


def screen(
    browser: Browser, base: str, page_name: str, width: int, scheme: str, media: str
) -> tuple[Page, dict[str, list[str]]]:
    context = browser.new_context(
        viewport={"width": width, "height": VIEWPORT_HEIGHT},
        color_scheme=scheme,  # type: ignore[arg-type]
        service_workers="block",
    )
    seen: dict[str, list[str]] = {"errors": [], "blocked": [], "failed": []}

    def refuse(url: str) -> None:
        if url not in seen["blocked"]:
            seen["blocked"].append(url)

    def route(r: Route) -> None:
        if not r.request.url.startswith(base):
            refuse(r.request.url)
            r.abort("blockedbyclient")
            return
        # Fetch here without following redirects, so a redirect target is never
        # contacted; a static site has no reason to redirect.
        response = r.fetch(max_redirects=0)
        if 300 <= response.status < 400:
            refuse(f"{r.request.url} -> redirect {response.headers.get('location', '?')}")
            r.abort("blockedbyclient")
            return
        r.fulfill(response=response)

    def socket(ws: WebSocketRoute) -> None:
        # Never calling connect_to_server keeps the socket mocked: it reaches no server.
        refuse(ws.url)

    def console(message: ConsoleMessage) -> None:
        if message.type == "error":
            seen["errors"].append(message.text)

    def page_error(error: Error) -> None:
        seen["errors"].append(str(error))

    def failed(r: Request) -> None:
        if r.url.startswith(base) and r.failure != "net::ERR_BLOCKED_BY_CLIENT":
            seen["failed"].append(f"{r.url} {r.failure}")

    context.route("**/*", route)
    context.route_web_socket("**/*", socket)
    page = context.new_page()
    page.on("console", console)
    page.on("pageerror", page_error)
    page.on("requestfailed", failed)
    if media == "print":
        page.emulate_media(media="print")
    page.goto(base + page_name)
    page.wait_for_load_state("networkidle")
    return page, seen


def pictures(page: Page, out: Path, name: str, max_height: int) -> tuple[list[str], int]:
    """Screenshots at the real viewport: whole page, or viewport tiles down to max_height."""
    height = int(page.evaluate("document.documentElement.scrollHeight"))
    if height <= max_height:
        page.screenshot(path=str(out / f"{name}.png"), full_page=True, timeout=120_000)
        return [f"{name}.png"], height
    files = []
    for tile in range(math.ceil(max_height / VIEWPORT_HEIGHT)):
        page.evaluate(f"window.scrollTo(0, {tile * VIEWPORT_HEIGHT})")
        page.wait_for_timeout(50)
        files.append(f"{name}-tile{tile + 1:02d}.png")
        page.screenshot(path=str(out / files[-1]))
    page.evaluate("window.scrollTo(0, 0)")
    return files, height


def check(args: argparse.Namespace) -> dict[str, Any]:
    site, out = args.site.resolve(), args.out.resolve()
    if not site.is_dir():
        raise SiteError(f"{site} is not a directory")
    if out == site or site in out.parents:
        raise SiteError("the output directory must be outside the site")
    if out.exists() and any(out.iterdir()):
        raise SiteError(f"{out} is not empty; choose a new output directory")
    if len({stem(p) for p in args.page}) != len(args.page):
        raise SiteError("each page may be named once, and page names must map to distinct files")
    for name in args.page:
        if not (site / name).is_file():
            raise SiteError(f"{name} is not a file in the site")
    out.mkdir(parents=True, exist_ok=True)
    screens: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
        root = Path(tmp) / "site"
        copy_site(site, root)
        server, base = serve(root)
        launch = {"channel": "msedge"} if args.browser == "msedge" else {}
        browser = playwright.chromium.launch(**launch)  # type: ignore[arg-type]
        try:
            plan = [
                (name, width, scheme, "screen")
                for name in args.page
                for width in args.widths
                for scheme in args.schemes
            ]
            if args.print:
                plan += [(name, args.widths[0], "light", "print") for name in args.page]
            for name, width, scheme, media in plan:
                page, seen = screen(browser, base, name, width, scheme, media)
                shot = f"{stem(name)}-{width}-{scheme}" + ("-print" if media == "print" else "")
                heading = page.locator("h1").first
                record: dict[str, Any] = {
                    "page": name,
                    "width": width,
                    "scheme": scheme,
                    "media": media,
                    "viewport": [width, VIEWPORT_HEIGHT],
                    "title": page.title(),
                    "h1": heading.inner_text() if heading.count() else None,
                    "overflow_px": page.evaluate(
                        "document.documentElement.scrollWidth - innerWidth"
                    ),
                    "past_edge": page.evaluate(PAST_EDGE),
                }
                files, height = pictures(page, out, shot, args.max_height)
                record |= {
                    "page_height_px": height,
                    "pictures": files,
                    "pictures_stop_short": height > args.max_height,
                    **seen,
                }
                screens.append(record)
                page.context.close()
            version = browser.version
        finally:
            browser.close()
            server.shutdown()
    findings = [
        s
        for s in screens
        if s["overflow_px"] > 0 or s["past_edge"] or s["errors"] or s["blocked"] or s["failed"]
    ]
    report = {
        "browser": {"name": args.browser, "version": version},
        "site": site.as_posix(),
        "screens": screens,
        "findings": len(findings),
    }
    (out / "findings.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("site", type=Path)
    parser.add_argument("--page", action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", choices=("chromium", "msedge"), default="chromium")
    parser.add_argument(
        "--widths", type=lambda v: [int(w) for w in v.split(",")], default=[1440, 390]
    )
    parser.add_argument("--schemes", type=lambda v: v.split(","), default=["dark", "light"])
    parser.add_argument("--print", action="store_true", help="add print-media screens")
    parser.add_argument(
        "--max-height",
        type=int,
        default=20_000,
        help="picture longer pages as viewport tiles down to this height",
    )
    args = parser.parse_args(argv)
    if not set(args.schemes) <= {"dark", "light"}:
        parser.error("schemes are dark and light")
    if len(set(args.schemes)) != len(args.schemes) or len(set(args.widths)) != len(args.widths):
        parser.error("each width and scheme may be named once")
    if min(args.widths) <= 0 or args.max_height <= 0:
        parser.error("widths and --max-height must be positive")
    try:
        report = check(args)
    except SiteError as error:
        print(f"visual check refused: {error}", file=sys.stderr)
        return 2
    for s in report["screens"]:
        flags = [
            f"{key}={s[key]}"
            for key in ("overflow_px", "past_edge", "errors", "blocked", "failed")
            if s[key]
        ]
        if s["pictures_stop_short"]:
            flags.append(f"pictures stop at {args.max_height} of {s['page_height_px']} px")
        print(f"{s['pictures'][0]:44} {' '.join(flags) or 'ok'}")
    print(f"{len(report['screens'])} screens, {report['findings']} with findings")
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
