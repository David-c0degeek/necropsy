"""Apply checked app releases using the existing staged, per-user installer."""

from __future__ import annotations

import hashlib
import os
import platform
import re
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from necropsy import __version__
from necropsy.desktop import updates
from necropsy.desktop.runtime import external_environment
from necropsy.desktop.updates import Asset, Release
from necropsy.wcl.analyze import plain_dir
from necropsy.wcl.cache import is_link, item_lock

Notify = Callable[[str], None]


def _read_gui(root: Path) -> Path:
    pointer = root / "gui-path"
    if is_link(pointer) or not pointer.is_file() or pointer.stat().st_size > 16384:
        raise ValueError("This app installation has no usable launcher information.")
    gui = Path(pointer.read_text(encoding="utf-8-sig").strip())
    if (
        not gui.is_absolute()
        or not gui.resolve().is_relative_to(root.resolve())
        or not gui.is_file()
    ):
        raise ValueError("The app launcher does not point inside its installation.")
    return gui


def managed_root(executable: Path) -> Path | None:
    executable = executable.resolve()
    for root in executable.parents:
        if not (root / "gui-path").exists():
            continue
        try:
            gui = _read_gui(root)
            companion = gui.resolve().with_name(
                "necropsy-engine.exe" if sys.platform == "win32" else "necropsy-engine"
            )
            if companion == executable and any(
                p.name == "gui" for p in executable.relative_to(root).parents
            ):
                return root
        except OSError, ValueError:
            continue
    return None


def _process_options() -> dict[str, Any]:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}


def verify_installed_gui(root: Path, version: str) -> Path:
    gui = _read_gui(root)
    with external_environment() as environment:
        result = subprocess.run(  # noqa: S603 -- installation-owned executable, no shell
            [str(gui), "--check-install"],
            capture_output=True,
            text=True,
            timeout=60,
            env=environment,
            **_process_options(),
        )
    if result.returncode or result.stdout.strip() != f"necropsy {version}":
        raise ValueError("The updated app could not start. Your previous app is preserved.")
    return gui


def run_installer(script: Path, bundle: Path, root: Path) -> None:
    with external_environment() as environment:
        _run_installer(script, bundle, root, environment)


def _run_installer(script: Path, bundle: Path, root: Path, environment: dict[str, str]) -> None:
    if sys.platform == "win32":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "RemoteSigned",
            "-File",
            str(script),
            "-InstallRoot",
            str(root),
            "-BundleDirectory",
            str(bundle),
            "-NoLaunch",
            "-NoPathChange",
        ]
    else:
        environment.update(
            NECROPSY_INSTALL_ROOT=str(root),
            NECROPSY_BUNDLE_DIR=str(bundle),
            NECROPSY_NO_LAUNCH="1",
            NECROPSY_NO_PATH_CHANGE="1",
        )
        command = ["sh", str(script)]
    # Once installation starts, let its staged readiness/activation step finish.
    # Closing the app waits for this worker rather than killing the installer.
    with (root / "last-update.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(  # noqa: S603 -- verified release installer and structured arguments
            command, env=environment, stdout=log, stderr=subprocess.STDOUT, **_process_options()
        )
    if result.returncode:
        raise ValueError(
            f"The update could not finish. Your current app is still available. "
            f"Try again; details are in {root / 'last-update.log'}."
        )


def _download(
    connection: httpx.Client, asset: Asset, destination: Path, check: Callable[[], None]
) -> str:
    limit = (
        1024 * 1024
        if asset.name == "SHA256SUMS"
        else 2 * 1024 * 1024
        if asset.name.startswith("install.")
        else updates.MAX_ASSET_SIZE
    )
    if asset.size > limit:
        raise ValueError("An update asset is too large. Nothing was installed.")
    size = 0
    digest = hashlib.sha256()
    with (
        updates.stream_response(connection, asset.url) as response,
        destination.open("xb") as target,
    ):
        updates.check_response(response)
        for chunk in response.iter_bytes(chunk_size=64 * 1024):
            check()
            size += len(chunk)
            if size > asset.size:
                raise ValueError(
                    "An update download exceeds its expected size. Nothing was installed."
                )
            digest.update(chunk)
            target.write(chunk)
    actual = digest.hexdigest()
    if size != asset.size or (asset.sha256 is not None and actual != asset.sha256):
        raise ValueError("An update download is incomplete or damaged. Nothing was installed.")
    return actual


def _checksums(path: Path, names: tuple[str, ...]) -> dict[str, str]:
    values: dict[str, list[str]] = {name: [] for name in names}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-fA-F0-9]{64})\s+\*?(.+)", line)
        if match and match[2] in values:
            values[match[2]].append(match[1].lower())
    if any(len(found) != 1 for found in values.values()):
        raise ValueError("The update checksums are missing or ambiguous. Nothing was installed.")
    return {name: found[0] for name, found in values.items()}


def _shortcuts() -> tuple[Path, ...]:
    if sys.platform == "win32":
        import ctypes

        shell = ctypes.WinDLL("shell32")
        shell.SHGetFolderPathW.argtypes = (
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_wchar_p,
        )
        paths = []
        for folder in (2, 16):  # Current user's Programs and Desktop directories.
            buffer = ctypes.create_unicode_buffer(260)
            if shell.SHGetFolderPathW(None, folder, None, 0, buffer) != 0:
                raise ValueError("Could not preserve your app shortcuts. Update manually.")
            paths.append(Path(buffer.value) / "Necropsy.lnk")
        return tuple(paths)
    if sys.platform == "darwin":
        return (Path.home() / "Applications/Necropsy.app",)
    return (
        Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
        / "applications/necropsy.desktop",
    )


ActiveFiles = dict[Path, tuple[bytes | None, int, str | None]]


def _active_files(root: Path) -> ActiveFiles:
    names = (
        ("gui-path", "necropsy.cmd")
        if sys.platform == "win32"
        else ("gui-path", "python-path", "necropsy")
    )
    saved: ActiveFiles = {}
    for name in names:
        path = root / name
        if is_link(path) or not path.is_file() or path.stat().st_size > 1024 * 1024:
            raise ValueError(
                "This installation's launcher cannot be safely updated. Reinstall manually."
            )
        saved[path] = path.read_bytes(), stat.S_IMODE(path.stat().st_mode), None
    for path in _shortcuts():
        if path.is_symlink():
            saved[path] = None, 0, str(path.readlink())
        elif not path.exists():
            saved[path] = None, 0, None
        elif path.is_file() and path.stat().st_size <= 1024 * 1024:
            saved[path] = path.read_bytes(), stat.S_IMODE(path.stat().st_mode), None
        elif sys.platform != "darwin" or not path.is_dir():
            raise ValueError("Could not preserve your app shortcuts. Update manually.")
        # A real macOS application directory is deliberately left alone by install.sh.
    return saved


def _restore_active(saved: ActiveFiles) -> None:
    for path, (data, mode, link) in saved.items():
        if data is None:
            path.unlink(missing_ok=True)
            if link is not None:
                path.symlink_to(link, target_is_directory=True)
            continue
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".restore-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        try:
            temporary.chmod(mode)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


class AppUpdater:
    def __init__(
        self,
        version: str = __version__,
        executable: Path | None = None,
        connection: Callable[[], httpx.Client] = updates.client,
    ) -> None:
        self.version = version
        self.executable = executable or Path(sys.executable)
        self.connection = connection
        self.root = managed_root(self.executable)
        self.platform = updates.platform_archive(sys.platform, platform.machine())
        self.checked: Release | None = None
        self.installed_gui: Path | None = None
        self.installed_version: str | None = None
        self.restart_process: subprocess.Popen[bytes] | None = None

    def _names(self, release: Release) -> tuple[str, ...]:
        names: tuple[str, ...] = (
            "install.ps1" if sys.platform == "win32" else "install.sh",
            f"necropsy-{release.version}-py3-none-any.whl",
        )
        if self.platform:
            names += (f"necropsy-desktop-{release.version}-{self.platform}",)
        if any(name not in release.assets for name in (*names, "SHA256SUMS")):
            raise ValueError(
                "The new release is still being prepared for your computer. Check again later."
            )
        return names

    def check(self) -> dict[str, Any]:
        self.checked = None
        try:
            with self.connection() as connection:
                release = updates.latest_release(connection)
        except httpx.HTTPError as error:
            raise ValueError(
                "Could not check for updates. Check your connection and try again."
            ) from error
        available = release is not None and updates.version_key(
            release.version
        ) > updates.version_key(self.version)
        if available:
            assert release is not None
            self._names(release)
            self.checked = release
        return {
            "installed_version": self.version,
            "latest_version": release.version if release else None,
            "available": available,
            "can_install": available and self.root is not None and self.platform is not None,
            "restart_required": self.installed_gui is not None,
            "release_url": release.url if release else f"{updates.REPOSITORY}/releases",
            "notes": release.notes if release else "No published release is available yet.",
            "message": "An update is available."
            if available
            else "You are using the latest available version."
            if release
            else "No published release is available yet.",
        }

    def install(self, notify: Notify, check: Callable[[], None]) -> Path:
        release = self.checked
        if release is None:
            raise ValueError("Check for an available app update first.")
        if self.root is None or self.platform is None:
            raise ValueError("This copy needs a manual update. Download the release instead.")
        root = plain_dir(self.root, "app installation")
        if managed_root(self.executable) != root:
            raise ValueError(
                "The active app installation changed. Restart and check for updates again."
            )
        names = self._names(release)
        with item_lock(root / ".necropsy-update.lock"), self.connection() as connection:
            latest = updates.latest_release(connection)
            if (
                latest is None
                or latest.version != release.version
                or any(
                    latest.assets.get(name) != release.assets.get(name)
                    for name in (*names, "SHA256SUMS")
                )
            ):
                self.checked = None
                raise ValueError(
                    "The available release changed. Check for updates again before installing."
                )
            with tempfile.TemporaryDirectory(prefix=".update-", dir=root) as directory:
                bundle = Path(directory)
                check()
                notify("Verifying the app update…")
                _download(connection, release.assets["SHA256SUMS"], bundle / "SHA256SUMS", check)
                expected = _checksums(bundle / "SHA256SUMS", names)
                for name in names:
                    notify("Downloading " + name + "…")
                    if (
                        _download(connection, release.assets[name], bundle / name, check)
                        != expected[name]
                    ):
                        raise ValueError("An update checksum did not match. Nothing was installed.")
                check()
                saved = _active_files(root)
                notify(
                    "Installing the update. The current app stays available "
                    "until the new version is ready…"
                )
                try:
                    run_installer(bundle / names[0], bundle, root)
                    gui = verify_installed_gui(root, release.version)
                except BaseException:
                    _restore_active(saved)
                    raise
        self.installed_gui = gui
        self.installed_version = release.version
        notify("Update installed. Ready to restart Necropsy.")
        return gui

    def restart(self) -> None:
        if self.root is None or self.installed_gui is None or self.installed_version is None:
            raise ValueError("Install an app update before restarting into it.")
        if verify_installed_gui(self.root, self.installed_version) != self.installed_gui:
            raise ValueError("The installed app changed. Open Necropsy from its usual shortcut.")
        if self.restart_process is not None and self.restart_process.poll() is None:
            return
        command = [sys.executable]
        if not getattr(sys, "frozen", False):
            command += ["-m", "necropsy.desktop.engine"]
        gui_pid = os.environ.get("NECROPSY_GUI_PID", "")
        if not gui_pid.isdecimal() or int(gui_pid) <= 0:
            raise ValueError("Open Necropsy from its usual shortcut to finish updating.")
        command += ["--restart-pid", gui_pid, "--restart-gui", str(self.installed_gui)]
        options = _process_options() if sys.platform == "win32" else {"start_new_session": True}
        self.restart_process = subprocess.Popen(  # noqa: S603 -- current engine and verified GUI
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"},
            **options,
        )
