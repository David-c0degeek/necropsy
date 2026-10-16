"""Launch the installed GUI; terminal mode remains an explicit CLI command."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


def executable() -> Path:
    configured = os.environ.get("NECROPSY_GUI_PATH")
    if configured:
        target = Path(configured)
        if target.is_file():
            return target
        raise ValueError("The desktop app is missing. Run the one-line installer again.")
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Necropsy/app"
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support/Necropsy/app"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "necropsy/app"
    pointer = root / "gui-path"
    if pointer.is_file():
        target = Path(pointer.read_text(encoding="utf-8").strip())
        if target.is_file():
            return target
    # Source checkouts may already have a native build; no build tools run on launch.
    checkout = Path(__file__).resolve().parents[3]
    name = "necropsy-desktop.exe" if sys.platform == "win32" else "necropsy-desktop"
    machine = "aarch64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
    suffix = {"win32": "pc-windows-msvc", "darwin": "apple-darwin"}.get(
        sys.platform, "unknown-linux-gnu"
    )
    for folder in ("release", f"{machine}-{suffix}/release"):
        target = checkout / "desktop/src-tauri/target" / folder / name
        if target.is_file():
            return target
    raise ValueError(
        "The graphical app is not installed. Run the one-line installer from the README, "
        "or use 'necropsy tui' for the terminal interface."
    )


def launch() -> None:
    target = executable()
    subprocess.Popen(  # noqa: S603 -- user-installed app path; no log data or shell execution
        [str(target)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=0x208 if os.name == "nt" else 0,
        start_new_session=os.name != "nt",
    )
