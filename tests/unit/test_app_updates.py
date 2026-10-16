"""Public release discovery, verified staged installs and preserved working launchers."""

from __future__ import annotations

import copy
import hashlib
import os
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from necropsy.desktop import installer, restart, runtime, updates
from necropsy.desktop.engine import DesktopEngine
from necropsy.desktop.installer import AppUpdater
from necropsy.tui.service import RunLibrary


@pytest.fixture(autouse=True)
def isolated_shortcuts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installer, "_shortcuts", lambda: (tmp_path / "Necropsy.shortcut",))


def release_fixture(version: str = "0.4.0") -> tuple[dict[str, Any], dict[str, bytes]]:
    files = {
        "install.ps1": b"# versioned Windows installer fixture\n",
        "install.sh": b"# versioned POSIX installer fixture\n",
        f"necropsy-{version}-py3-none-any.whl": b"wheel fixture",
        **{
            f"necropsy-desktop-{version}-{suffix}": suffix.encode()
            for suffix in (
                "windows-x86_64.zip",
                "macos-arm64.tar.gz",
                "macos-x86_64.tar.gz",
                "linux-x86_64.tar.gz",
            )
        },
    }
    files["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in files.items()
    ).encode()
    raw = {
        "tag_name": f"v{version}",
        "draft": False,
        "prerelease": False,
        "html_url": f"{updates.REPOSITORY}/releases/tag/v{version}",
        "body": "Release notes <script>do not execute this</script>",
        "assets": [
            {
                "id": index,
                "name": name,
                "state": "uploaded",
                "size": len(data),
                "browser_download_url": f"{updates.REPOSITORY}/releases/download/v{version}/{name}",
                "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
            for index, (name, data) in enumerate(files.items(), 1)
        ],
    }
    return raw, files


def connection_factory(
    raw: dict[str, Any], files: dict[str, bytes], calls: list[httpx.Request]
) -> Callable[[], httpx.Client]:
    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert "Authorization" not in request.headers
        if str(request.url) == updates.LATEST_RELEASE:
            return httpx.Response(200, json=raw)
        assert str(request.url).startswith(f"{updates.REPOSITORY}/releases/download/")
        return httpx.Response(200, content=files[request.url.path.rsplit("/", 1)[-1]])

    return lambda: httpx.Client(transport=httpx.MockTransport(handle), trust_env=False)


def managed_install(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "app with spaces and 'quote $literal"
    folder = root / "versions" / "old" / "gui" / "Necropsy"
    folder.mkdir(parents=True)
    gui = folder / ("necropsy-desktop.exe" if sys.platform == "win32" else "necropsy-desktop")
    engine = folder / ("necropsy-engine.exe" if sys.platform == "win32" else "necropsy-engine")
    gui.write_bytes(b"old gui")
    engine.write_bytes(b"old engine")
    (root / "gui-path").write_text(str(gui), encoding="utf-8")
    for name in ("necropsy.cmd",) if sys.platform == "win32" else ("python-path", "necropsy"):
        (root / name).write_bytes(b"old launcher")
    return root, engine


def manager(
    tmp_path: Path,
) -> tuple[AppUpdater, dict[str, Any], dict[str, bytes], list[httpx.Request]]:
    root, executable = managed_install(tmp_path)
    raw, files = release_fixture()
    calls: list[httpx.Request] = []
    updater = AppUpdater("0.3.1", executable, connection_factory(raw, files, calls))
    assert updater.root == root
    return updater, raw, files, calls


@pytest.mark.parametrize(
    ("current", "latest", "available"),
    [
        ("0.3.1", "0.4.0", True),
        ("0.4.0", "0.4.0", False),
        ("0.5.0", "0.4.0", False),
        ("0.4.0-rc.1", "0.4.0", True),
        ("0.9.0", "0.10.0", True),
    ],
)
def test_check_compares_semantic_versions_without_downloading_assets(
    tmp_path: Path, current: str, latest: str, available: bool
) -> None:
    raw, files = release_fixture(latest)
    calls: list[httpx.Request] = []
    updater = AppUpdater(
        current, tmp_path / "portable-engine", connection_factory(raw, files, calls)
    )
    info = updater.check()
    assert info["available"] is available and info["latest_version"] == latest
    assert not info["can_install"]
    assert len(calls) == 1 and str(calls[0].url) == updates.LATEST_RELEASE


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("win32", "AMD64", "windows-x86_64.zip"),
        ("darwin", "arm64", "macos-arm64.tar.gz"),
        ("darwin", "x86_64", "macos-x86_64.tar.gz"),
        ("linux", "x86_64", "linux-x86_64.tar.gz"),
        ("linux", "arm64", None),
    ],
)
def test_platform_packages_match_existing_distribution(
    system: str, machine: str, expected: str | None
) -> None:
    assert updates.platform_archive(system, machine) == expected


@pytest.mark.parametrize(
    "change", ["draft", "prerelease", "url", "asset_url", "duplicate", "missing"]
)
def test_bad_or_incomplete_releases_never_become_installable(tmp_path: Path, change: str) -> None:
    updater, raw, _, calls = manager(tmp_path)
    if change in ("draft", "prerelease"):
        raw[change] = True
    elif change == "url":
        raw["html_url"] = "https://evil.example/releases/tag/v0.4.0"
    elif change == "asset_url":
        raw["assets"][0]["browser_download_url"] = "file:///installer.ps1"
    elif change == "duplicate":
        raw["assets"].append(copy.deepcopy(raw["assets"][0]))
    else:
        raw["assets"] = [a for a in raw["assets"] if a["name"] != "SHA256SUMS"]
    with pytest.raises(ValueError):
        updater.check()
    assert updater.checked is None and len(calls) == 1


@pytest.mark.parametrize("status", [404, 403, 429])
def test_no_release_and_rate_limit_results_are_clear(tmp_path: Path, status: int) -> None:
    updater = AppUpdater(
        connection=lambda: httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(status))
        )
    )
    if status == 404:
        assert updater.check()["latest_version"] is None
    else:
        with pytest.raises(ValueError, match="limiting update checks"):
            updater.check()


def test_offline_check_has_retry_guidance() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    updater = AppUpdater(connection=lambda: httpx.Client(transport=httpx.MockTransport(fail)))
    with pytest.raises(ValueError, match="Check your connection"):
        updater.check()


def test_redirects_are_checked_before_contacting_an_untrusted_host() -> None:
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host)
        return httpx.Response(302, headers={"Location": "https://evil.example/stolen"})

    updater = AppUpdater(connection=lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    with pytest.raises(ValueError, match="outside GitHub"):
        updater.check()
    assert calls == ["api.github.com"]


def test_verified_install_uses_the_existing_installer_and_keeps_the_old_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    updater, _, files, calls = manager(tmp_path)
    assert updater.check()["can_install"]
    root = updater.root
    assert root is not None
    old_gui = Path((root / "gui-path").read_text())
    installed = []

    def install(script: Path, bundle: Path, target: Path) -> None:
        assert target == root and script.read_bytes() == files[script.name]
        assert updater.checked is not None
        assert {p.name for p in bundle.iterdir()} == {
            *updater._names(updater.checked),
            "SHA256SUMS",
        }
        gui = root / "versions" / "new" / "gui" / "Necropsy" / old_gui.name
        gui.parent.mkdir(parents=True)
        gui.write_bytes(b"new gui")
        (root / "gui-path").write_text(str(gui), encoding="utf-8")
        installed.append(gui)

    monkeypatch.setattr(installer, "run_installer", install)
    monkeypatch.setattr(
        installer,
        "verify_installed_gui",
        lambda root, version: Path((root / "gui-path").read_text()),
    )
    result = updater.install(lambda _: None, lambda: None)
    assert result == installed[0] and updater.installed_version == "0.4.0"
    assert old_gui.read_bytes() == b"old gui"
    assert len(calls) == 6  # check, recheck, sums, script, wheel, matching GUI
    assert not list(root.glob(".update-*"))


@pytest.mark.parametrize(
    "failure", ["download", "checksum", "installer", "readiness", "changed_release"]
)
def test_failed_update_preserves_the_active_launchers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    updater, raw, files, _ = manager(tmp_path)
    updater.check()
    root = updater.root
    assert root is not None and updater.checked is not None
    before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    shortcut = installer._shortcuts()[0]
    shortcut.write_bytes(b"old shortcut")
    calls = []
    if failure == "download":
        name = updater._names(updater.checked)[1]
        files[name] = b"x" * len(files[name])
    elif failure == "checksum":
        name = updater._names(updater.checked)[1]
        files[name] = b"x" * len(files[name])
        next(a for a in raw["assets"] if a["name"] == name)["digest"] = None
        updater.checked = updates.parse_release(raw)
    elif failure == "changed_release":
        raw["assets"][0]["id"] += 9999

    def install(*_: Any) -> None:
        calls.append("install")
        (root / "gui-path").write_bytes(b"bad new pointer")
        shortcut.write_bytes(b"new shortcut")
        if failure == "installer":
            raise ValueError("installer failed")

    def readiness(*_: Any) -> Path:
        raise ValueError("readiness failed")

    monkeypatch.setattr(installer, "run_installer", install)
    monkeypatch.setattr(installer, "verify_installed_gui", readiness)
    with pytest.raises(ValueError):
        updater.install(lambda _: None, lambda: None)
    for name, data in before.items():
        assert (root / name).read_bytes() == data
    assert bool(calls) is (failure in ("installer", "readiness"))
    assert updater.installed_gui is None
    assert shortcut.read_bytes() == b"old shortcut"


def test_update_operations_do_not_start_auth_or_accept_arbitrary_links(tmp_path: Path) -> None:
    raw, files = release_fixture()
    engine = DesktopEngine(lambda _: None, RunLibrary(tmp_path))
    calls: list[httpx.Request] = []
    engine.updater = AppUpdater(connection=connection_factory(raw, files, calls))
    result = engine.dispatch("check_updates", {})
    assert result["available"] and engine.service._auth is None
    with pytest.raises(ValueError, match="manual update"):
        engine.dispatch("install_update", {})
    with pytest.raises(ValueError, match="Only secure Warcraft Logs"):
        engine.dispatch("open_link", {"url": updates.REPOSITORY})


def test_restart_waits_for_the_old_gui_before_launching_the_verified_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gui = tmp_path / "gui.exe"
    gui.write_bytes(b"gui")
    steps = []
    monkeypatch.setattr(restart, "wait_for_exit", lambda pid: steps.append(("wait", pid)))
    monkeypatch.setattr(
        subprocess, "Popen", lambda command, **kwargs: steps.append(("launch", command[0]))
    )
    restart.restart_after_exit(12345, gui)
    assert steps == [("wait", 12345), ("launch", str(gui))]


def test_restart_waits_for_a_real_child_process_to_exit() -> None:
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(0.1)"],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    reaper = threading.Thread(target=child.wait)
    reaper.start()
    try:
        restart.wait_for_exit(child.pid, timeout=10)
    finally:
        reaper.join(timeout=10)
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=5)
    assert child.returncode == 0


def test_restart_rejects_waiting_for_itself() -> None:
    with pytest.raises(ValueError):
        restart.wait_for_exit(os.getpid())


def test_restart_helper_uses_the_window_pid_and_independent_frozen_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    updater, _, _, _ = manager(tmp_path)
    assert updater.root is not None
    gui = Path((updater.root / "gui-path").read_text())
    updater.installed_gui, updater.installed_version = gui, "0.4.0"
    monkeypatch.setattr(installer, "verify_installed_gui", lambda *_: gui)
    monkeypatch.setenv("NECROPSY_GUI_PID", "12345")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    started: list[tuple[list[str], dict[str, Any]]] = []

    def launch(command: list[str], **options: Any) -> Any:
        started.append((command, options))
        return None

    monkeypatch.setattr(subprocess, "Popen", launch)
    updater.restart()
    command, options = started[0]
    assert command == [sys.executable, "--restart-pid", "12345", "--restart-gui", str(gui)]
    assert options["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    monkeypatch.delenv("NECROPSY_GUI_PID")
    with pytest.raises(ValueError, match="usual shortcut"):
        updater.restart()


def test_shutdown_finishes_installation_without_starting_a_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = DesktopEngine(lambda _: None, RunLibrary(tmp_path))
    started, finish = threading.Event(), threading.Event()
    completed: list[str] = []

    def install(*_: Any) -> Path:
        started.set()
        assert finish.wait(5)
        completed.append("installed")
        return tmp_path

    monkeypatch.setattr(engine.updater, "install", install)
    monkeypatch.setattr(engine.updater, "restart", lambda: completed.append("restart"))
    engine.handle({"id": 1, "method": "install_update"})
    assert started.wait(5)
    closer = threading.Thread(target=engine.shutdown)
    closer.start()
    assert engine.stop.wait(5)
    assert closer.is_alive() and completed == []
    finish.set()
    closer.join(5)
    assert not closer.is_alive() and completed == ["installed"]


def test_system_tools_use_the_original_library_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/temporary/frozen/libs")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/system/libs")
    with runtime.external_environment() as environment:
        assert environment["LD_LIBRARY_PATH"] == "/system/libs"
        assert environment["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert os.environ["LD_LIBRARY_PATH"] == "/temporary/frozen/libs"


def test_failed_restart_keeps_the_installed_app_available_for_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    updater, _, _, _ = manager(tmp_path)
    assert updater.root is not None
    gui = Path((updater.root / "gui-path").read_text())
    updater.installed_gui, updater.installed_version = gui, "0.4.0"
    monkeypatch.setattr(installer, "verify_installed_gui", lambda *_: gui)
    monkeypatch.setenv("NECROPSY_GUI_PID", "12345")

    def fail(*_: Any, **__: Any) -> Any:
        raise OSError("cannot start restart helper")

    monkeypatch.setattr(subprocess, "Popen", fail)
    with pytest.raises(OSError, match="restart helper"):
        updater.restart()
    assert updater.installed_gui == gui and gui.is_file()
    assert updater.restart_process is None
