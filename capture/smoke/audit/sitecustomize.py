"""Smoke-only instrumentation, never part of the image.

Loaded through PYTHONPATH into every Python process of a smoke container. It
records each socket attempt and refuses all of them except the loopback
Notifiarr fake, and routes the Notifiarr passthrough URL to that fake. Each
process also records that the hook loaded, so an empty socket log is evidence
rather than a missing hook.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

LOG = os.environ.get("SMOKE_NET_LOG")
FAKE = os.environ.get("SMOKE_NOTIFIARR_FAKE")  # "127.0.0.1:5454" or unset
ALLOWED: tuple[str, int] | None = None
if FAKE:
    host, port = FAKE.rsplit(":", 1)
    ALLOWED = (host, int(port))
PREFIX = "https://notifiarr.com/api/v1/notification/passthrough/"


def _record(event: str, detail: Any, allowed: bool) -> None:
    if LOG:
        entry = {
            "t": time.time(),
            "pid": os.getpid(),
            "argv": sys.argv[:3],
            "event": event,
            "detail": repr(detail)[:200],
            "allowed": allowed,
        }
        with Path(LOG).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")


def _hook(event: str, args: tuple[Any, ...]) -> None:
    if event in ("socket.connect", "socket.connect_ex", "socket.sendto", "socket.sendmsg"):
        address = args[1] if len(args) > 1 else None
        ok = ALLOWED is not None and isinstance(address, tuple) and address[:2] == ALLOWED
        _record(event, address, ok)
        if not ok:
            raise ConnectionRefusedError("smoke network denial")
    elif event == "socket.getaddrinfo":
        ok = ALLOWED is not None and args[0] == ALLOWED[0]
        _record(event, args[:2], ok)
        if not ok:
            raise OSError("smoke DNS denial")


sys.addaudithook(_hook)
_record("audit.loaded", sys.executable, True)

if FAKE:
    import urllib.request

    _urlopen = urllib.request.urlopen

    def _routed(request: Any, *args: Any, **kwargs: Any) -> Any:
        is_request = isinstance(request, urllib.request.Request)
        url = request.full_url if is_request else request
        if isinstance(url, str) and url.startswith(PREFIX):
            routed = f"http://{FAKE}/passthrough/" + url[len(PREFIX) :]
            _record("notifiarr.route", PREFIX + "<key>", True)
            if is_request:
                request.full_url = routed
            else:
                request = routed
        return _urlopen(request, *args, **kwargs)

    urllib.request.urlopen = _routed  # type: ignore[assignment]
