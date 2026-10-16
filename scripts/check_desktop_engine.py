"""Exercise a real or frozen engine outside the checkout, entirely offline."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any


def check(command: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="necropsy-desktop-check-") as directory:
        root = Path(directory).resolve()
        process = subprocess.Popen(
            [*command, "--data-dir", str(root / "library")],
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        assert process.stdin is not None and process.stdout is not None
        next_id = 0

        def request(method: str, **params: Any) -> Any:
            nonlocal next_id
            next_id += 1
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(
                json.dumps({"id": next_id, "method": method, "params": params}) + "\n"
            )
            process.stdin.flush()
            for line in process.stdout:
                message = json.loads(line)
                if message.get("id") == next_id:
                    assert "error" not in message, message
                    return message.get("result")
            stderr = process.stderr.read() if process.stderr else ""
            raise AssertionError(f"Engine exited without a response: {stderr}")

        try:
            assert request("hello")["runs"] == []
            result = request("demo")
            run = result["run"]
            assert run["has_report"] and not run["can_resume"]
            assert "Example" in run["title"]
            # Wait for the worker's final busy notification before another operation.
            for line in process.stdout:
                message = json.loads(line)
                if message == {"event": "busy", "data": False}:
                    break
            for view in ("playbook", "report"):
                rendered = request("report", id=run["id"], view=view)
                assert "<html" in rendered["html"] and "Haplina" in rendered["html"]
                assert rendered["class_key"] == "hunter"
            exported = root / "shared.zip"
            request("export", id=run["id"], path=str(exported))
            with zipfile.ZipFile(exported) as archive:
                assert {"playbook.html", "report.html", "analysis.json", "manifest.json"} <= set(
                    archive.namelist()
                )
            assert len(request("list")) == 1
            print(
                "PASS: isolated example, saved library, both report views, ZIP export; no sign-in."
            )
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise
            assert process.returncode == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("engine", type=Path, help="Frozen engine executable")
    args = parser.parse_args()
    check([str(args.engine.resolve())])
