"""The capture image context holds only checked files: the release wheel that
matches its published SHA256SUMS, the pinned queue and the locked requirements."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import stage_capture_image as stage

VERSION = "9.9.9"
WHEEL = f"necropsy-{VERSION}-py3-none-any.whl"


@pytest.fixture(autouse=True)
def _locked(monkeypatch: pytest.MonkeyPatch) -> None:
    # The real check runs `uv export`; the committed file stands in for it here.
    committed = (stage.CAPTURE / "requirements.txt").read_bytes()
    monkeypatch.setattr(stage, "lock_requirements", lambda: committed)


def _release(tmp_path: Path, *, digest: str | None = None, marker: str = "  ") -> Path:
    release = tmp_path / "release"
    release.mkdir()
    (release / WHEEL).write_bytes(b"wheel-bytes")
    actual = hashlib.sha256(b"wheel-bytes").hexdigest()
    (release / "SHA256SUMS").write_text(
        f"{digest or actual}{marker}{WHEEL}\n0000  install.sh\n", encoding="utf-8"
    )
    return release


def test_a_staged_context_lists_every_file_and_pins_the_queue(tmp_path: Path) -> None:
    out = tmp_path / "context"
    staged = stage.stage(_release(tmp_path), out, VERSION)

    manifest = json.loads((out / "manifest.json").read_bytes())
    assert manifest["files"] == staged
    for name, digest in staged.items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    pin = (stage.CAPTURE / "queue.sha256").read_text(encoding="ascii").strip()
    assert manifest["queue_sha256"] == pin
    assert staged["queue/capture-queue.json"] == pin
    assert (out / "queue" / "capture-queue.sha256").read_bytes() == pin.encode() + b"\n"
    assert (out / "SHA256SUMS").read_bytes().endswith(f"  {WHEEL}\n".encode())
    assert (out / "wheel" / WHEEL).read_bytes() == b"wheel-bytes"
    assert b"\r" not in (out / "entrypoint.sh").read_bytes()


def test_a_binary_marker_in_the_checksum_list_is_accepted(tmp_path: Path) -> None:
    stage.stage(_release(tmp_path, marker=" *"), tmp_path / "context", VERSION)


def test_a_wheel_that_does_not_match_the_release_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not match the release"):
        stage.stage(_release(tmp_path, digest="0" * 64), tmp_path / "context", VERSION)


def test_a_wheel_of_another_version_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"no necropsy-1.0.0"):
        stage.stage(_release(tmp_path), tmp_path / "context", "1.0.0")


def test_requirements_that_drift_from_the_lock_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stage, "lock_requirements", lambda: b"other==1.0\n")
    with pytest.raises(ValueError, match=r"does not match uv.lock"):
        stage.stage(_release(tmp_path), tmp_path / "context", VERSION)


def test_a_queue_that_does_not_match_its_pin_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue = tmp_path / "queue.json"
    queue.write_bytes(b"{}")
    monkeypatch.setattr(stage, "QUEUE", queue)
    with pytest.raises(ValueError, match=r"does not match capture/queue.sha256"):
        stage.stage(_release(tmp_path), tmp_path / "context", VERSION)


def test_a_non_empty_output_directory_is_refused(tmp_path: Path) -> None:
    out = tmp_path / "context"
    out.mkdir()
    (out / "old").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="not empty"):
        stage.stage(_release(tmp_path), out, VERSION)
