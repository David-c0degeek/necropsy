"""The visual check reports overflow, past-edge elements, page errors and refused
requests per screen, keeps the network closed (no redirect or WebSocket
escapes), pictures the real viewport, and never writes into or over output."""

from __future__ import annotations

import http.server
import json
import socket
import struct
import threading
from pathlib import Path
from typing import Any

import pytest

from scripts import visual_check as vc

pytestmark = pytest.mark.browser
sync_api = pytest.importorskip("playwright.sync_api")

PAGES = {
    "clean.html": "<h1>Clean</h1><p>Fits the screen.</p>",
    "wide.html": "<h1>Wide</h1><div id='slab' style='width:2000px;height:10px'></div>",
    "framed.html": (
        "<h1>Framed</h1><div style='overflow-x:auto'>"
        "<table style='width:2000px'><tr><td>scrolls inside its frame</td></tr></table></div>"
    ),
    "error.html": "<h1>Error</h1><script>throw new Error('boom')</script>",
    "offsite.html": "<h1>Offsite</h1><img src='http://example.invalid/x.png' alt=''>",
    "socket.html": "<h1>Socket</h1><script>new WebSocket('ws://127.0.0.1:9/feed')</script>",
}


@pytest.fixture(scope="module")
def browser_available() -> None:
    """Skip only when no browser can start; tool failures afterwards fail the test."""
    with sync_api.sync_playwright() as playwright:
        try:
            playwright.chromium.launch().close()
        except Exception as error:
            pytest.skip(f"Chromium unavailable: {error}")


def html(body: str) -> str:
    return f"<!doctype html><html><head><title>t</title></head><body>{body}</body></html>"


def site(tmp_path: Path, pages: dict[str, str] = PAGES) -> Path:
    root = tmp_path / "site"
    for name, body in pages.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(html(body), encoding="utf-8")
    return root


def run(root: Path, out: Path, pages: list[str], *extra: str) -> tuple[int, dict[str, Any]]:
    args = [str(root), "--out", str(out), "--widths", "800", "--schemes", "light"]
    for name in pages:
        args += ["--page", name]
    code = vc.main([*args, *extra])
    report: dict[str, Any] = json.loads((out / "findings.json").read_text(encoding="utf-8"))
    return code, report


def png_size(path: Path) -> tuple[int, int]:
    width, height = struct.unpack(">II", path.read_bytes()[16:24])
    return width, height


def test_each_screen_reports_only_its_own_problems(tmp_path: Path, browser_available: None) -> None:
    code, report = run(site(tmp_path), tmp_path / "out", list(PAGES))
    assert code == 1
    screens = {s["page"]: s for s in report["screens"]}
    clean = screens["clean.html"]
    assert [clean[k] for k in ("overflow_px", "past_edge", "errors", "blocked", "failed")] == [
        0,
        [],
        [],
        [],
        [],
    ]
    assert screens["wide.html"]["past_edge"] == ["div#slab"]
    assert screens["framed.html"]["overflow_px"] == 0
    assert screens["framed.html"]["past_edge"] == []
    assert any("boom" in e for e in screens["error.html"]["errors"])
    assert screens["offsite.html"]["blocked"] == ["http://example.invalid/x.png"]
    assert screens["offsite.html"]["failed"] == []
    assert screens["socket.html"]["blocked"] == ["ws://127.0.0.1:9/feed"]
    assert clean["pictures"] == ["clean.html-800-light.png"]
    assert clean["viewport"] == [800, 1000]
    assert report["browser"]["name"] == "chromium" and report["browser"]["version"]


class Redirect(http.server.BaseHTTPRequestHandler):
    """A site whose image redirects to another origin."""

    sink = ""

    def do_GET(self) -> None:
        if self.path == "/page.html":
            body = html("<h1>Redirect</h1><img src='/hop.png' alt=''>").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(302)
            self.send_header("Location", self.sink + "escaped.png")
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


def test_a_redirect_to_another_origin_never_reaches_it(browser_available: None) -> None:
    hits: list[str] = []

    class Sink(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    servers = []
    for handler in (Sink, Redirect):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
    Redirect.sink = f"http://127.0.0.1:{servers[0].server_address[1]}/"
    base = f"http://127.0.0.1:{servers[1].server_address[1]}/"
    try:
        with sync_api.sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page, seen = vc.screen(browser, base, "page.html", 800, "light", "screen")
            page.context.close()
            browser.close()
    finally:
        for server in servers:
            server.shutdown()
    assert hits == []
    assert seen["blocked"] == [f"{base}hop.png -> redirect {Redirect.sink}escaped.png"]


def test_pages_with_the_same_file_name_get_their_own_pictures(
    tmp_path: Path, browser_available: None
) -> None:
    root = site(tmp_path, {"a/index.html": "<h1>A</h1>", "b/index.html": "<h1>B</h1>"})
    code, report = run(root, tmp_path / "out", ["a/index.html", "b/index.html"])
    assert code == 0
    pictures = [s["pictures"] for s in report["screens"]]
    assert pictures == [["a__index.html-800-light.png"], ["b__index.html-800-light.png"]]
    assert all((tmp_path / "out" / p[0]).is_file() for p in pictures)
    twice = ["--page", "a/index.html", "--page", "a/index.html"]
    assert vc.main([str(root), *twice, "--out", str(tmp_path / "o")]) == 2


def test_pictures_keep_the_measured_viewport(tmp_path: Path, browser_available: None) -> None:
    # A height media query would switch on if the picture used a taller viewport.
    tall = (
        "<style>#big{display:none}@media (min-height:1500px){#big{display:block}}</style>"
        "<h1>Tall</h1><p id='big'>tall viewport</p><div style='height:3000px'></div>"
    )
    root = site(tmp_path, {"tall.html": tall, "short.html": "<h1>Short</h1>"})
    out = tmp_path / "out"
    code, report = run(root, out, ["tall.html", "short.html"], "--max-height", "2500")
    assert code == 0
    tall_screen, short_screen = report["screens"]
    assert tall_screen["pictures_stop_short"] is True
    assert tall_screen["pictures"] == [f"tall.html-800-light-tile{i:02d}.png" for i in (1, 2, 3)]
    assert {png_size(out / name) for name in tall_screen["pictures"]} == {(800, 1000)}
    assert short_screen["pictures_stop_short"] is False
    assert png_size(out / short_screen["pictures"][0])[0] == 800


def test_print_screens_are_added(tmp_path: Path, browser_available: None) -> None:
    root = site(tmp_path, {"clean.html": "<h1>C</h1>"})
    _, report = run(root, tmp_path / "out", ["clean.html"], "--print")
    printed = [s["pictures"] for s in report["screens"] if s["media"] == "print"]
    assert printed == [["clean.html-800-light-print.png"]]


def test_output_must_be_new_and_outside_the_site(tmp_path: Path) -> None:
    root = site(tmp_path)
    used = tmp_path / "used"
    used.mkdir()
    (used / "keep.txt").write_text("keep", encoding="utf-8")
    assert vc.main([str(root), "--page", "clean.html", "--out", str(used)]) == 2
    assert (used / "keep.txt").read_text(encoding="utf-8") == "keep"
    assert vc.main([str(root), "--page", "clean.html", "--out", str(root / "shots")]) == 2
    assert not (root / "shots").exists()
    assert vc.main([str(root), "--page", "missing.html", "--out", str(tmp_path / "o")]) == 2


def test_a_site_with_a_link_is_refused(tmp_path: Path) -> None:
    root = site(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    try:
        (root / "link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links are not available here")
    with pytest.raises(vc.SiteError, match="is a link"):
        vc.copy_site(root, tmp_path / "copy")


def test_a_websocket_never_reaches_its_server(tmp_path: Path, browser_available: None) -> None:
    listener = socket.create_server(("127.0.0.1", 0))
    listener.settimeout(0.2)
    port = listener.getsockname()[1]
    script = f"<h1>Socket</h1><script>new WebSocket('ws://127.0.0.1:{port}/feed')</script>"
    try:
        _, report = run(site(tmp_path, {"ws.html": script}), tmp_path / "out", ["ws.html"])
        with pytest.raises(TimeoutError):
            listener.accept()
    finally:
        listener.close()
    assert report["screens"][0]["blocked"] == [f"ws://127.0.0.1:{port}/feed"]


@pytest.mark.parametrize(
    "options",
    [
        ["--widths", "800,800"],
        ["--schemes", "light,light"],
        ["--widths", "0"],
        ["--widths", "-5"],
        ["--max-height", "0"],
    ],
    ids=["repeated-width", "repeated-scheme", "zero-width", "negative-width", "zero-height"],
)
def test_a_screen_plan_that_would_repeat_or_break_pictures_is_refused(
    tmp_path: Path, options: list[str]
) -> None:
    root = site(tmp_path, {"index.html": "<h1>I</h1>"})
    with pytest.raises(SystemExit) as exit_:
        vc.main([str(root), "--page", "index.html", "--out", str(tmp_path / "out"), *options])
    assert exit_.value.code == 2
    assert not (tmp_path / "out").exists()


def test_every_screen_has_its_own_pictures(tmp_path: Path, browser_available: None) -> None:
    root = site(tmp_path, {"index.html": "<h1>I</h1>"})
    args = [str(root), "--page", "index.html", "--out", str(tmp_path / "out"), "--print"]
    assert vc.main([*args, "--widths", "800,390"]) == 0
    report = json.loads((tmp_path / "out" / "findings.json").read_text(encoding="utf-8"))
    names = [name for s in report["screens"] for name in s["pictures"]]
    assert len(names) == len(set(names)) == 5
    assert all((tmp_path / "out" / name).is_file() for name in names)
