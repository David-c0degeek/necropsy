"""Wait for the old GUI to close before opening a verified updated installation."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from necropsy.desktop.runtime import external_environment


def wait_for_exit(pid: int, timeout: float = 60) -> None:
    if pid <= 0 or pid == os.getpid():
        raise ValueError("Cannot wait for this application process.")
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
        if not handle:
            if ctypes.get_last_error() == 87:  # Process already exited.
                return
            raise OSError("Could not wait for the previous app to close.")
        try:
            if kernel.WaitForSingleObject(handle, int(timeout * 1000)) != 0:
                raise TimeoutError(
                    "The previous app is still closing. Open Necropsy again manually."
                )
        finally:
            kernel.CloseHandle(handle)
        return
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.kill(pid, 0)  # POSIX-only existence probe; never used on Windows.
        except ProcessLookupError:
            return
        if time.monotonic() >= deadline:
            raise TimeoutError("The previous app is still closing. Open Necropsy again manually.")
        time.sleep(0.1)


def restart_after_exit(pid: int, gui: Path) -> None:
    gui = gui.resolve(strict=True)
    try:
        wait_for_exit(pid)
        with external_environment() as environment:
            subprocess.Popen(  # noqa: S603 -- verified installation GUI from the update manager
                [str(gui)],
                cwd=gui.parent,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=environment,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
    except (OSError, TimeoutError) as error:
        (gui.parent / "restart-error.log").write_text(str(error), encoding="utf-8")
        raise
