"""Keep system tools independent of the frozen engine's library search paths."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def external_environment() -> Iterator[dict[str, str]]:
    environment = os.environ.copy()
    if not getattr(sys, "frozen", False):
        yield environment
        return
    environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    for name in ("LD_LIBRARY_PATH", "LIBPATH"):
        original = environment.get(name + "_ORIG")
        if original is None:
            environment.pop(name, None)
        else:
            environment[name] = original
    if sys.platform == "win32":
        import ctypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetDllDirectoryW.argtypes = (ctypes.c_wchar_p,)
        kernel.SetDllDirectoryW.restype = ctypes.c_int
        if not kernel.SetDllDirectoryW(None):
            raise OSError("Could not prepare the update process.")
        try:
            yield environment
        finally:
            kernel.SetDllDirectoryW(getattr(sys, "_MEIPASS", None))
    else:
        yield environment
