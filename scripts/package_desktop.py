"""Create a versioned portable GUI archive for the current operating system."""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

from necropsy import __version__

ROOT = Path(__file__).resolve().parents[1]


def package(out: Path) -> Path:
    host = subprocess.run(
        ["rustc", "--print", "host-tuple"], check=True, capture_output=True, text=True
    ).stdout.strip()
    target = ROOT / "desktop/src-tauri/target"
    release = target / host / "release"
    if not release.is_dir():
        release = target / "release"
    out.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        result = out / f"necropsy-desktop-{__version__}-windows-x86_64.zip"
        with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in ("necropsy-desktop.exe", "necropsy-engine.exe"):
                archive.write(release / name, f"Necropsy/{name}")
            archive.write(ROOT / "desktop/src-tauri/icons/icon.ico", "Necropsy/icon.ico")
    elif sys.platform == "darwin":
        arch = "arm64" if platform.machine() == "arm64" else "x86_64"
        result = out / f"necropsy-desktop-{__version__}-macos-{arch}.tar.gz"
        app = release / "bundle/macos/Necropsy.app"
        with tarfile.open(result, "w:gz") as archive:
            archive.add(app, arcname="Necropsy.app")
    elif sys.platform == "linux":
        result = out / f"necropsy-desktop-{__version__}-linux-x86_64.tar.gz"
        images = list((release / "bundle/appimage").glob(f"*{__version__}*.AppImage"))
        if len(images) != 1:
            raise ValueError("Build exactly one version-matched AppImage before packaging.")
        with tempfile.TemporaryDirectory(prefix="necropsy-appimage-") as work:
            # Extract once at build time: installation and launch need no FUSE mount.
            subprocess.run([str(images[0].resolve()), "--appimage-extract"], cwd=work, check=True)
            with tarfile.open(result, "w:gz") as archive:
                archive.add(Path(work) / "squashfs-root", arcname="Necropsy")
                archive.add(
                    ROOT / "desktop/src-tauri/icons/128x128.png", arcname="Necropsy/necropsy.png"
                )
    else:
        raise ValueError("Desktop packages support Windows, macOS and Linux.")
    print(f"Portable desktop package: {result}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("workspace/desktop-bundle"))
    args = parser.parse_args()
    package(args.out.resolve())
