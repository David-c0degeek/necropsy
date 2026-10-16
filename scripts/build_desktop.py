"""Freeze the Python engine for the host platform, ready for Tauri bundling.

Run with: uv run --group desktop-build python scripts/build_desktop.py
Then: cd desktop && npm ci && npm run package
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    work = ROOT / "workspace/desktop-build"
    work.mkdir(parents=True, exist_ok=True)
    assets = work / "assets"
    assets.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "tests/fixtures/haplina_naxx_subset.zip", assets / "demo.zip")
    host = subprocess.run(
        ["rustc", "--print", "host-tuple"], check=True, capture_output=True, text=True
    ).stdout.strip()
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--noupx",
        "--name",
        "necropsy-engine",
        "--distpath",
        str(work / "dist"),
        "--workpath",
        str(work / "build"),
        "--specpath",
        str(work),
        "--collect-data",
        "necropsy",
        "--collect-all",
        "duckdb",
        "--collect-submodules",
        "keyring.backends",
        "--copy-metadata",
        "keyring",
        "--add-data",
        f"{assets}:necropsy/desktop/assets",
        str(ROOT / "src/necropsy/desktop/engine.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    extension = ".exe" if sys.platform == "win32" else ""
    destination = ROOT / "desktop/src-tauri/binaries" / f"necropsy-engine-{host}{extension}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(work / "dist" / f"necropsy-engine{extension}", destination)
    print(f"Desktop engine: {destination}")


if __name__ == "__main__":
    main()
