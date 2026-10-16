"""Exercise our own Windows WebView2 window against the real engine, offline.

Requires a built desktop executable. Debug builds also need `npm run dev`.
Uses an isolated library and a temporary WebView2 profile, not a personal browser.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright


def check_update_controls(page: Page, screenshots: Path) -> None:
    """Exercise UI states using release fixtures; actual update policy has backend tests."""
    page.evaluate("""() => {
      const original = window.__TAURI_INTERNALS__.invoke;
      const originalFetch = window.fetch;
      window.necropsyUpdateFixture = 'current';
      window.fetch = async function(address, options) {
        const isRequest = String(address) === 'http://ipc.localhost/engine_request';
        const message = isRequest ? JSON.parse(options.body)?.message : null;
        const update = ['check_updates', 'install_update'].includes(message?.method);
        if (update) {
          const mode = window.necropsyUpdateFixture;
          const failure = message.method === 'install_update'
            ? 'An update checksum did not match. Nothing was installed.'
            : mode === 'offline' ? 'Could not check for updates. '
              + 'Check your connection and try again.' : null;
          const result = {
            installed_version:'0.3.1', latest_version:mode === 'current' ? '0.3.1' : '0.4.0',
            available:mode !== 'current', can_install:mode === 'future', restart_required:false,
            release_url:'https://github.com/David-c0degeek/necropsy/releases/tag/v0.4.0',
            notes:'<script>window.updateInjected = true</script>',
            message:mode === 'current' ? 'You are using the latest available version.'
              : 'An update is available.'
          };
          await original('plugin:event|emit', {event:'engine-message', payload:{
            id:message.id, ...(failure ? {error:failure} : {result})
          }});
          return new Response('null', {headers:{
            'Tauri-Response':'ok', 'Content-Type':'application/json'
          }});
        }
        return originalFetch(address, options);
      };
    }""")
    page.get_by_role("button", name="Check for updates", exact=True).click()
    dialog = page.get_by_role("dialog", name="App updates")
    expect(dialog.get_by_role("status")).to_have_text("You are using the latest available version.")
    assert dialog.get_by_role("button", name="Update and restart").count() == 0
    dialog.get_by_text("Release notes", exact=True).click()
    assert "window.updateInjected" in dialog.locator("pre").inner_text()
    assert page.evaluate("window.updateInjected === undefined")
    page.screenshot(path=str(screenshots / "desktop-update-current-fixture.png"))
    page.evaluate("window.necropsyUpdateFixture = 'offline'")
    dialog.get_by_role("button", name="Check again").click()
    expect(dialog.get_by_role("alert")).to_contain_text("Check your connection")
    page.evaluate("window.necropsyUpdateFixture = 'manual'")
    dialog.get_by_role("button", name="Check again").click()
    expect(dialog.get_by_role("button", name="Open release page")).to_be_visible()
    assert dialog.get_by_role("button", name="Update and restart").count() == 0
    page.evaluate("window.necropsyUpdateFixture = 'future'")
    dialog.get_by_role("button", name="Check again").click()
    dialog.get_by_role("button", name="Update and restart").click()
    expect(dialog.get_by_role("alert")).to_contain_text("Nothing was installed")
    expect(dialog.get_by_role("button", name="Check again")).to_be_enabled()
    dialog.get_by_role("button", name="Close", exact=True).click()
    assert not page.get_by_role("dialog").count()


def check(executable: Path, screenshots: Path) -> None:
    screenshots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="necropsy-window-check-", ignore_cleanup_errors=True
    ) as directory:
        root = Path(directory)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        env = {
            **os.environ,
            "NECROPSY_DESKTOP_DATA_DIR": str(root / "library"),
            "WEBVIEW2_USER_DATA_FOLDER": str(root / "webview"),
            "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": f"--remote-debugging-port={port}",
        }
        process = subprocess.Popen([str(executable.resolve())], env=env, cwd=root)
        try:
            with sync_playwright() as playwright:
                deadline = time.monotonic() + 45
                while True:
                    try:
                        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                        break
                    except Exception:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.2)
                page = browser.contexts[0].pages[0]
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "console",
                    lambda message: print(message.text) if message.type == "error" else None,
                )
                page.get_by_role("button", name="Try the example").wait_for(state="visible")
                expect(page.get_by_role("button", name="Try the example")).to_be_enabled(
                    timeout=30000
                )
                assert not page.get_by_role("alert").count(), page.locator("body").inner_text()
                page.screenshot(path=str(screenshots / "desktop-home-dark.png"))
                page.get_by_role("button", name="Light theme").click()
                page.wait_for_timeout(200)  # let the deliberate CSS color transition settle
                page.screenshot(path=str(screenshots / "desktop-home-light.png"))
                page.get_by_role("button", name="Dark theme").click()
                page.get_by_role("textbox", name="Warcraft Logs character link").fill(
                    "https://example.com/character/test"
                )
                page.get_by_role("button", name="Find my character").click()
                expect(page.get_by_role("alert")).to_be_visible()
                page.get_by_role("button", name="Dismiss error").click()
                page.get_by_role("button", name="Try the example").click()
                page.locator("iframe").wait_for(state="visible", timeout=60000)
                frame = page.frame_locator("iframe")
                frame.locator("section.boss").first.wait_for(state="visible")
                assert frame.locator("section.boss").count() == 4
                assert "Haplina" in frame.locator("body").inner_text()
                # Report JS executed inside an opaque-origin sandbox.
                expect(frame.locator("#review-status")).to_have_text(
                    "Review marks are saved on this computer, for this exact analysis."
                )
                assert frame.locator("#theme-toggle").is_hidden()
                inner = page.locator("iframe").element_handle().content_frame()
                assert inner is not None
                denied = inner.evaluate("""async () => Promise.race([
                  (async function() {
                    try {
                      await window.__TAURI_INTERNALS__.invoke('engine_request', {
                        message:{id:-1,method:'hello'}
                      });
                      return 'ALLOWED';
                    }
                    catch(e) { return String(e); }
                  })(), new Promise(resolve => setTimeout(() => resolve('blocked'), 500))
                ])""")
                assert denied != "ALLOWED", "The report frame gained desktop command access."
                local_link = frame.locator(".boss-jumps a").first
                anchor = local_link.get_attribute("href")
                assert anchor is not None
                local_link.click()
                expect(frame.locator(anchor)).to_be_in_viewport()
                assert page.locator("iframe").get_attribute("srcdoc")
                box = frame.locator("input[data-review-key]").first
                box.check()
                frame.locator('a[href^="report.html#"]:visible').first.click()
                expect(page.get_by_role("button", name="Report", exact=True)).to_have_attribute(
                    "aria-pressed", "true"
                )
                page.get_by_role("status").filter(has_text="Opening your analysis").wait_for(
                    state="hidden"
                )
                page.get_by_role("button", name="Playbook", exact=True).click()
                expect(page.get_by_role("button", name="Playbook", exact=True)).to_have_attribute(
                    "aria-pressed", "true"
                )
                page.get_by_role("status").filter(has_text="Opening your analysis").wait_for(
                    state="hidden"
                )
                expect(frame.locator("input[data-review-key]").first).to_be_checked()
                frame.locator("#overview").scroll_into_view_if_needed()
                page.screenshot(path=str(screenshots / "desktop-playbook.png"))
                page.get_by_role("button", name="Your analyses", exact=True).first.click()
                assert page.get_by_role("heading", name="Your analyses", exact=True).is_visible()
                assert page.get_by_role("button", name="Open Playbook").count() == 1
                saved = next((root / "library/runs").glob("*/analysis.json"))
                original_analysis = saved.read_bytes()
                page.get_by_role("button", name="Update reports", exact=True).click()
                expect(page.locator("iframe")).to_be_visible()
                expect(page.get_by_role("status")).to_contain_text(
                    "Saved reports updated", timeout=30000
                )
                assert saved.read_bytes() == original_analysis
                assert len(list((root / "library/runs").glob("*/analysis.json"))) == 1
                assert "Reports rendered by Necropsy" in (saved.parent / "playbook.html").read_text(
                    encoding="utf-8"
                )
                page.get_by_role("button", name="Your analyses", exact=True).first.click()
                check_update_controls(page, screenshots)
                page.get_by_role("textbox", name="Search saved analyses").fill("no-such-character")
                assert page.get_by_role("heading", name="No matching analyses").is_visible()
                page.get_by_role("button", name="Clear search").click()
                page.get_by_role("button", name="Open Playbook").click()
                expect(frame.locator("input[data-review-key]").first).to_be_checked()
                page.reload()
                page.get_by_role("button", name="Your analyses").first.click()
                page.get_by_role("button", name="Open Playbook").click()
                expect(frame.locator("input[data-review-key]").first).to_be_checked()
                assert errors == [], errors
                page.get_by_role("button", name="New analysis", exact=True).click()
                page.get_by_role("button", name="Try the example").click()
                # Deliver the same close event emitted by the native titlebar.
                page.evaluate("""window.__TAURI_INTERNALS__.invoke('plugin:event|emit', {
                  event:'desktop-close', payload:null
                })""")
                expect(page.get_by_role("dialog")).to_be_visible()
                page.get_by_role("button", name="Save and quit", exact=True).click()
                process.wait(timeout=45)
                assert process.returncode == 0
                assert len(list((root / "library/runs").glob("*/analysis.json"))) == 2
                print(
                    "PASS: native window, real IPC, offline example, report scripts, "
                    "review persistence, library, save-before-quit."
                    " Saved-report refresh and controlled update-dialog states passed."
                )
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--screenshots", type=Path, default=Path("workspace/desktop-screenshots"))
    args = parser.parse_args()
    check(args.executable, args.screenshots)
