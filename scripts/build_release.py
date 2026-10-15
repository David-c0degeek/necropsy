"""Build a version-matched public installer bundle and checksums."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path

from necropsy import __version__


def build(out: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    expected = {f"necropsy-{__version__}-py3-none-any.whl", f"necropsy-{__version__}.tar.gz"}
    if any(p.name not in expected for p in out.iterdir() if p.suffix in (".whl", ".gz")):
        raise ValueError("output contains another release; choose a fresh bundle directory")
    for name, marker in (
        ("install.ps1", f"$necropsyVersion = '{__version__}'"),
        ("install.sh", f"version={__version__}\n"),
    ):
        if marker not in (repository / name).read_text(encoding="utf-8"):
            raise ValueError(f"{name} does not match package version {__version__}")
    subprocess.run(["uv", "build", "--out-dir", str(out)], cwd=repository, check=True)
    for name in ("install.ps1", "install.sh"):
        shutil.copyfile(repository / name, out / name)
    assets = [out / name for name in sorted(expected | {"install.ps1", "install.sh"})]
    (out / "SHA256SUMS").write_text(
        "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in assets),
        encoding="utf-8",
    )
    print(f"Release bundle ready: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("dist"))
    args = parser.parse_args()
    build(args.out)


if __name__ == "__main__":
    main()
