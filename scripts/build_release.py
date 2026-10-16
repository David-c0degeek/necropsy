"""Build a version-matched public installer bundle and checksums."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path

from necropsy import __version__


def build(out: Path, desktop_bundles: Path | None = None, *, require_all: bool = False) -> None:
    repository = Path(__file__).resolve().parents[1]
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    expected = {f"necropsy-{__version__}-py3-none-any.whl", f"necropsy-{__version__}.tar.gz"}
    native_names = {
        f"necropsy-desktop-{__version__}-{platform}{extension}"
        for platform, extension in (
            ("windows-x86_64", ".zip"),
            ("macos-arm64", ".tar.gz"),
            ("macos-x86_64", ".tar.gz"),
            ("linux-x86_64", ".tar.gz"),
        )
    }
    if any(
        p.name not in expected | native_names
        for p in out.iterdir()
        if p.suffix in (".whl", ".gz", ".zip")
    ):
        raise ValueError("output contains another release; choose a fresh bundle directory")
    for name, marker in (
        ("install.ps1", f"$necropsyVersion = '{__version__}'"),
        ("install.sh", f"version={__version__}\n"),
    ):
        if marker not in (repository / name).read_text(encoding="utf-8"):
            raise ValueError(f"{name} does not match package version {__version__}")
    subprocess.run(["uv", "build", "--out-dir", str(out)], cwd=repository, check=True)
    for name in ("install.ps1", "install.sh"):
        # A Windows checkout may contain CRLF despite the repository's LF policy.
        # In particular, sh must receive executable Unix line endings.
        (out / name).write_bytes((repository / name).read_text(encoding="utf-8").encode("utf-8"))
    if desktop_bundles is not None:
        for name in native_names:
            source = desktop_bundles / name
            if source.is_file():
                shutil.copyfile(source, out / name)
    available = {name for name in native_names if (out / name).is_file()}
    if require_all and available != native_names:
        raise ValueError(f"Missing desktop packages: {sorted(native_names - available)}")
    assets = [out / name for name in sorted(expected | available | {"install.ps1", "install.sh"})]
    (out / "SHA256SUMS").write_text(
        "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in assets),
        encoding="utf-8",
    )
    print(f"Release bundle ready: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("dist"))
    parser.add_argument("--desktop-bundles", type=Path)
    parser.add_argument("--require-all-desktop", action="store_true")
    args = parser.parse_args()
    build(args.out, args.desktop_bundles, require_all=args.require_all_desktop)


if __name__ == "__main__":
    main()
