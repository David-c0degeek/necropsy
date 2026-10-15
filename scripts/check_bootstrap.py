"""Exercise a fresh private bootstrap and failed-upgrade rollback on this OS."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from necropsy import __version__


def check(bundle: Path, receipt: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="necropsy-bootstrap-") as temporary:
        root = Path(temporary) / "fresh app with spaces"
        env = {k: v for k, v in os.environ.items() if not k.startswith("NECROPSY_")}
        env["UV_PYTHON_INSTALL_DIR"] = str(root / "runtime/python")
        if os.name == "nt":
            command = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(repository / "install.ps1"),
                "-InstallRoot",
                str(root),
                "-BundleDirectory",
                str(bundle),
                "-NoLaunch",
                "-NoShortcuts",
                "-NoPathChange",
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
        saved_launcher = launcher.read_bytes()
        python_pointer = root / "python-path"
        saved_pointer = python_pointer.read_bytes() if python_pointer.exists() else None
        bad = Path(temporary) / "bad bundle"
        bad.mkdir()
        wheel_name = f"necropsy-{__version__}-py3-none-any.whl"
        (bad / wheel_name).write_bytes(b"damaged download")
        (bad / "SHA256SUMS").write_bytes((bundle / "SHA256SUMS").read_bytes())
        if os.name == "nt":
            failed_command = command.copy()
            failed_command[failed_command.index("-BundleDirectory") + 1] = str(bad)
        else:
            failed_command = command
            env["NECROPSY_BUNDLE_DIR"] = str(bad)
        failed = subprocess.run(failed_command, env=env, capture_output=True, text=True, timeout=60)
        if failed.returncode == 0:
            raise RuntimeError("damaged download was accepted")
        if launcher.read_bytes() != saved_launcher:
            raise RuntimeError("failed upgrade modified the working launcher")
        if saved_pointer is not None and python_pointer.read_bytes() != saved_pointer:
            raise RuntimeError("failed upgrade changed the active interpreter")
        data = dict(
            platform=os.name,
            version=version,
            private_runtime="passed",
            fresh_bootstrap="passed",
            launcher="passed",
            checksum_refusal="passed",
            failed_upgrade_preserves_launcher="passed",
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
