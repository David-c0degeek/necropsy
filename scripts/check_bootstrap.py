"""Exercise a fresh private bootstrap and failed-upgrade rollback on this OS."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import httpx

from necropsy import __version__
from necropsy.desktop import updates
from necropsy.desktop.installer import AppUpdater, verify_installed_gui


def check_app_update(root: Path, bundle: Path, env: dict[str, str]) -> None:
    """Use real packages/installers with a local future-release transport fixture."""
    old_gui = verify_installed_gui(root, __version__)
    engine = old_gui.with_name("necropsy-engine.exe" if os.name == "nt" else "necropsy-engine")
    platform_asset = updates.platform_archive(sys.platform, platform.machine())
    assert platform_asset is not None
    script = "install.ps1" if os.name == "nt" else "install.sh"
    repository = Path(__file__).resolve().parents[1]
    installer = (repository / script).read_bytes()
    if os.name == "nt":
        # Suppress personal shortcuts/PATH only; keep the production install steps.
        installer = installer.replace(b"[switch]$NoShortcuts,", b"[switch]$NoShortcuts = $true,")
        installer = installer.replace(
            b"[switch]$NoPathChange\n", b"[switch]$NoPathChange = $true\n"
        )
    files = {
        script: installer,
        f"necropsy-{__version__}-py3-none-any.whl": (
            bundle / f"necropsy-{__version__}-py3-none-any.whl"
        ).read_bytes(),
        f"necropsy-desktop-{__version__}-{platform_asset}": (
            bundle / f"necropsy-desktop-{__version__}-{platform_asset}"
        ).read_bytes(),
    }
    files["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in files.items()
    ).encode()
    release = {
        "tag_name": f"v{__version__}",
        "draft": False,
        "prerelease": False,
        "html_url": f"{updates.REPOSITORY}/releases/tag/v{__version__}",
        "body": "Isolated installer verification",
        "assets": [
            {
                "id": index,
                "name": name,
                "size": len(data),
                "state": "uploaded",
                "browser_download_url": (
                    f"{updates.REPOSITORY}/releases/download/v{__version__}/{name}"
                ),
                "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
            for index, (name, data) in enumerate(files.items(), 1)
        ],
    }

    def handle(request: httpx.Request) -> httpx.Response:
        if str(request.url) == updates.LATEST_RELEASE:
            return httpx.Response(200, json=release)
        return httpx.Response(200, content=files[request.url.path.rsplit("/", 1)[-1]])

    with patch.dict(
        os.environ,
        {**env, "NECROPSY_NO_SHORTCUTS": "1", "NECROPSY_NO_PATH_CHANGE": "1"},
        clear=True,
    ):
        updater = AppUpdater(
            "0.0.0", engine, lambda: httpx.Client(transport=httpx.MockTransport(handle))
        )
        assert updater.check()["can_install"]
        gui = updater.install(lambda _: None, lambda: None)
        assert gui != old_gui and old_gui.is_file()
        assert verify_installed_gui(root, __version__) == gui
    print("PASS: app updater, verified downloads, real staged installer and new GUI readiness.")


def documented_command(repository: Path) -> str:
    commands = []
    for name in ("README.md", "PACKAGE.md", "docs/installation.md"):
        text = (repository / name).read_text(encoding="utf-8")
        match = re.search(r"```powershell\n([^\n]+)\n```", text)
        if match is None:
            raise ValueError(f"missing Windows setup command in {name}")
        commands.append(match[1])
    if len(set(commands)) != 1:
        raise ValueError("Windows setup commands differ between installation guides")
    command = commands[0]
    if "-File $setup" not in command or "iex" in command.lower() or "bypass" in command.lower():
        raise ValueError("Windows setup must run a saved file without IEX or Bypass")
    return command


@contextlib.contextmanager
def downloaded_setup(repository: Path, content: bytes) -> Iterator[str]:
    """Substitute only the download origin; keep the advertised PowerShell syntax."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/install.ps1":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format: str, *args: object) -> None:
            pass

    command = documented_command(repository)
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield command.replace(
                "https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.ps1",
                f"http://127.0.0.1:{server.server_port}/install.ps1",
            )
        finally:
            server.shutdown()
            thread.join()


def check(bundle: Path, receipt: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    with (
        tempfile.TemporaryDirectory(prefix="necropsy-bootstrap-") as temporary,
        contextlib.ExitStack() as stack,
    ):
        root = Path(temporary).resolve() / "fresh app with spaces"
        env = {k: v for k, v in os.environ.items() if not k.startswith("NECROPSY_")}
        env["UV_PYTHON_INSTALL_DIR"] = str(root / "runtime/python")
        if os.name == "nt":
            env.update(
                TEMP=temporary,
                NECROPSY_TEST_ROOT=str(root),
                NECROPSY_TEST_BUNDLE=str(bundle),
            )
            expression = stack.enter_context(
                downloaded_setup(repository, (repository / "install.ps1").read_bytes())
            ).replace(
                "-File $setup",
                "-File $setup -InstallRoot $env:NECROPSY_TEST_ROOT "
                "-BundleDirectory $env:NECROPSY_TEST_BUNDLE "
                "-NoLaunch -NoShortcuts -NoPathChange",
            )
            command = [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                expression,
            ]
            launcher = root / "necropsy.cmd"
        else:
            env.update(
                NECROPSY_INSTALL_ROOT=str(root),
                NECROPSY_BUNDLE_DIR=str(bundle),
                NECROPSY_NO_LAUNCH="1",
                NECROPSY_NO_SHORTCUTS="1",
                NECROPSY_NO_PATH_CHANGE="1",
            )
            command = ["sh", str(repository / "install.sh")]
            launcher = root / "necropsy"
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=600)
        if result.returncode:
            raise RuntimeError(f"fresh bootstrap failed: {result.stdout}\n{result.stderr}")
        runtime = root / "runtime/uv" / ("uv.exe" if os.name == "nt" else "uv")
        if not runtime.is_file():
            raise RuntimeError("bootstrap did not provision its own runtime")
        executable = ["cmd", "/c", str(launcher)] if os.name == "nt" else [str(launcher)]
        version = subprocess.run(
            [*executable, "--version"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
        if version != f"necropsy {__version__}":
            raise RuntimeError(f"launcher version differs: {version}")
        gui_pointer = root / "gui-path"
        gui = Path(gui_pointer.read_text(encoding="utf-8").strip())
        ready = subprocess.run(
            [str(gui), "--check-install"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        ).stdout.strip()
        if ready != version:
            raise RuntimeError(f"GUI/engine readiness differs: {ready}")
        subprocess.run(
            [*executable, "tui", "--help"], env=env, check=True, capture_output=True, timeout=30
        )
        check_app_update(root, bundle, env)
        saved_launcher = launcher.read_bytes()
        python_pointer = root / "python-path"
        saved_pointer = python_pointer.read_bytes() if python_pointer.exists() else None
        saved_gui = gui_pointer.read_bytes()
        wheel_name = f"necropsy-{__version__}-py3-none-any.whl"
        if os.name == "nt":
            gui_name = "windows-x86_64.zip"
        elif sys.platform == "darwin":
            arch = "arm64" if platform.machine() == "arm64" else "x86_64"
            gui_name = f"macos-{arch}.tar.gz"
        else:
            gui_name = "linux-x86_64.tar.gz"
        gui_assets = [bundle / f"necropsy-desktop-{__version__}-{gui_name}"]
        for damaged in (wheel_name, gui_assets[0].name):
            bad = Path(temporary) / f"bad-{damaged}"
            bad.mkdir()
            for source in [bundle / wheel_name, bundle / "SHA256SUMS", *gui_assets]:
                shutil.copyfile(source, bad / source.name)
            (bad / damaged).write_bytes(b"damaged download")
            if os.name == "nt":
                env["NECROPSY_TEST_BUNDLE"] = str(bad)
            else:
                env["NECROPSY_BUNDLE_DIR"] = str(bad)
            failed = subprocess.run(command, env=env, capture_output=True, text=True, timeout=60)
            if failed.returncode == 0:
                raise RuntimeError("damaged download was accepted")
            if launcher.read_bytes() != saved_launcher or gui_pointer.read_bytes() != saved_gui:
                raise RuntimeError("failed upgrade modified the working GUI launcher")
            if saved_pointer is not None and python_pointer.read_bytes() != saved_pointer:
                raise RuntimeError("failed upgrade changed the active interpreter")
        data = dict(
            platform=os.name,
            version=version,
            private_runtime="passed",
            fresh_bootstrap="passed",
            launcher="passed",
            gui_engine_readiness="passed",
            explicit_terminal_mode="passed",
            app_update_staged_install="passed",
            checksum_refusal="passed",
            failed_upgrade_preserves_launcher="passed",
            documented_windows_download_command="passed" if os.name == "nt" else "not applicable",
        )
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Bootstrap checks passed; receipt: {receipt}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    check(args.bundle.resolve(strict=True), args.receipt)


if __name__ == "__main__":
    main()
