"""Exercise a fresh private bootstrap and failed-upgrade rollback on this OS."""

from __future__ import annotations

import argparse
import contextlib
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

from necropsy import __version__


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
        root = Path(temporary) / "fresh app with spaces"
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
