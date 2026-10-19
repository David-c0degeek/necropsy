"""Credential storage in exactly one approved OS credential store.

The `keyring` facade can be configured with any backend, including plaintext or
file backends, and a chaining backend can read from a later store when an
earlier one has no value. Necropsy therefore never calls the facade: it picks
exactly one backend instance whose concrete type is an approved OS store and
sends every read, write and delete to that instance. There is no file fallback.

Values are written in chunks (Windows Credential Locker holds at most 1,280
characters per entry) under a fresh generation, and the head entry that points
at a generation is written last: a failed write leaves the previous value
readable. Backend failures surface as fixed CredentialStoreError messages that
never carry the backend's own text.

An unattended POSIX server has no OS store. Setting `NECROPSY_CREDENTIAL_FILE`
selects an explicit private file instead (ADR 0023); it is never a fallback.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import stat
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TypeVar

import keyring
from keyring.backend import KeyringBackend
from keyring.backends import SecretService, Windows, kwallet, macOS
from keyring.backends.chainer import ChainerBackend

SERVICE = "necropsy-wcl"
BACKEND_ENV = "NECROPSY_KEYRING_BACKEND"
FILE_ENV = "NECROPSY_CREDENTIAL_FILE"
FILE_VERSION = 1
CHUNK = 1000
_HEAD = "necropsy-v1:"

APPROVED: tuple[type[KeyringBackend], ...] = (
    Windows.WinVaultKeyring,
    macOS.Keyring,
    SecretService.Keyring,
    kwallet.DBusKeyring,
)
"""OS credential stores Necropsy accepts. Matched by class identity, not by name."""

T = TypeVar("T")


class CredentialStoreError(Exception):
    """The OS credential store is unavailable, unapproved or failed."""


def _label(backend: Any) -> str:
    cls = type(backend)
    return f"{cls.__module__}.{cls.__qualname__}"


def _chain(backend: Any) -> list[Any]:
    if isinstance(backend, ChainerBackend):
        return list(backend.backends)
    return [backend]


def select_backend(configured: Any = None, allowed: Sequence[type[Any]] = APPROVED) -> Any:
    """The one approved backend to use, or CredentialStoreError.

    `configured` defaults to keyring's active backend; a chaining backend is
    expanded into its ordered members. Exactly one member must be of an allowed
    class (or `NECROPSY_KEYRING_BACKEND` must name one of several).
    """
    try:
        candidates = _chain(keyring.get_keyring() if configured is None else configured)
    except Exception:
        raise CredentialStoreError("could not inspect the OS credential store setup") from None
    approved = [b for b in candidates if type(b) in allowed]
    if not approved:
        found = ", ".join(_label(b) for b in candidates) or "none"
        raise CredentialStoreError(
            "no approved OS credential store is available (found: "
            f"{found}); Necropsy stores WCL credentials only in the Windows Credential "
            "Locker, macOS Keychain, Secret Service or KWallet"
        )
    if len(approved) > 1:
        wanted = os.environ.get(BACKEND_ENV)
        chosen = [b for b in approved if wanted and _label(b) == wanted]
        if len(chosen) != 1:
            names = ", ".join(_label(b) for b in approved)
            raise CredentialStoreError(
                f"several approved credential stores are configured ({names}); "
                f"set {BACKEND_ENV} to the one to use"
            )
        return chosen[0]
    return approved[0]


class CredentialStore:
    """Read, write and delete secrets in one selected backend only."""

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    @classmethod
    def open(
        cls, configured: Any = None, allowed: Sequence[type[Any]] = APPROVED
    ) -> CredentialStore:
        path = selected_file()
        if path is not None:
            return FileCredentialStore(path)
        return cls(select_backend(configured, allowed))

    @property
    def backend_name(self) -> str:
        return _label(self._backend)

    def _call(self, what: str, operation: Callable[[], T]) -> T:
        try:
            return operation()
        except Exception:
            # The backend's own message could quote stored values: never pass it on.
            raise CredentialStoreError(f"the OS credential store could not {what}") from None

    def _raw_get(self, name: str) -> str | None:
        value = self._call("read a saved value", lambda: self._backend.get_password(SERVICE, name))
        return None if value is None else str(value)

    def _raw_set(self, name: str, value: str) -> None:
        self._call("save a value", lambda: self._backend.set_password(SERVICE, name, value))

    def _raw_delete(self, name: str) -> bool:
        """True if removed, False if it was already absent; otherwise CredentialStoreError.

        Some backends report any failure as PasswordDeleteError, so "not found"
        is only accepted after the store confirms the entry is really gone.
        """

        def run() -> bool:
            try:
                self._backend.delete_password(SERVICE, name)
            except keyring.errors.PasswordDeleteError:
                if self._backend.get_password(SERVICE, name) is None:
                    return False
                raise
            return True

        return self._call("remove a saved value", run)

    def _head(self, name: str) -> tuple[str, int] | None:
        head = self._raw_get(name)
        if head is None or not head.startswith(_HEAD):
            return None
        generation, _, count = head[len(_HEAD) :].partition(":")
        try:
            return generation, int(count)
        except ValueError:
            return None

    def get(self, name: str) -> str | None:
        head = self._head(name)
        if head is None:
            return None
        generation, count = head
        parts = []
        for i in range(count):
            part = self._raw_get(f"{name}@{generation}#{i}")
            if part is None:
                raise CredentialStoreError("a saved credential is incomplete; sign in again")
            parts.append(part)
        return "".join(parts)

    def set(self, name: str, value: str) -> None:
        """Write a new generation, then switch the head to it; old chunks go last."""
        old = self._head(name)
        generation = secrets.token_hex(4)
        parts = [value[i : i + CHUNK] for i in range(0, len(value), CHUNK)] or [""]
        written: list[str] = []
        try:
            for i, part in enumerate(parts):
                key = f"{name}@{generation}#{i}"
                self._raw_set(key, part)
                written.append(key)
            self._raw_set(name, f"{_HEAD}{generation}:{len(parts)}")
        except CredentialStoreError:
            for key in written:
                with contextlib.suppress(CredentialStoreError):
                    self._raw_delete(key)
            raise
        if old is not None:
            for i in range(old[1]):
                with contextlib.suppress(CredentialStoreError):
                    self._raw_delete(f"{name}@{old[0]}#{i}")

    def delete(self, name: str) -> bool:
        """Remove a value; the head must go first, or nothing else is touched."""
        head = self._head(name)
        found = self._raw_delete(name)
        if head is not None:
            for i in range(head[1]):
                with contextlib.suppress(CredentialStoreError):
                    self._raw_delete(f"{name}@{head[0]}#{i}")
        return found

    def __repr__(self) -> str:
        return f"CredentialStore({self.backend_name})"


def selected_file() -> Path | None:
    """The credential file `NECROPSY_CREDENTIAL_FILE` names, or None when unset.

    Naming it together with `NECROPSY_KEYRING_BACKEND` is refused before any
    store is opened.
    """
    path = os.environ.get(FILE_ENV)
    if not path:
        return None
    if os.environ.get(BACKEND_ENV):
        raise CredentialStoreError(
            f"{FILE_ENV} and {BACKEND_ENV} are both set; choose one credential store"
        )
    return Path(path)


class FileCredentialStore(CredentialStore):
    """Values in one private JSON file, selected only by `NECROPSY_CREDENTIAL_FILE`.

    POSIX only. The file must be a regular file (not a link) with mode exactly
    0600, and it and its directory must belong to this process's user; the
    directory must be 0700. Anything else is refused, with no fallback. Every
    write replaces the whole file through a private temporary file in the same
    directory, synced before and after the rename. A failure before the rename
    leaves the previous file intact; a failure syncing the directory after it
    leaves either the previous or the new complete file. Both raise.
    """

    def __init__(self, path: Path) -> None:
        if sys.platform == "win32":
            raise CredentialStoreError(f"{FILE_ENV} is supported only on POSIX systems")
        # absolute(), not resolve(): a link in the path must stay visible to the checks.
        self._path: Path = path.absolute()
        self._check_dir()

    @property
    def backend_name(self) -> str:
        return "credential-file"

    def _check_dir(self) -> None:
        if sys.platform == "win32":
            raise CredentialStoreError(f"{FILE_ENV} is supported only on POSIX systems")
        try:
            info = os.lstat(self._path.parent)
        except OSError:
            raise CredentialStoreError("the credential file directory is missing") from None
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise CredentialStoreError(
                "the credential file directory must be a plain directory owned by this user"
            )
        if stat.S_IMODE(info.st_mode) != 0o700:
            raise CredentialStoreError("the credential file directory must have mode 0700")

    def _read(self) -> dict[str, str]:
        if sys.platform == "win32":
            raise CredentialStoreError(f"{FILE_ENV} is supported only on POSIX systems")
        self._check_dir()
        try:
            # Non-blocking: a FIFO or device must reach the type check, not hang the open.
            fd = os.open(self._path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return {}
        except OSError:
            raise CredentialStoreError("the credential file could not be opened") from None
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise CredentialStoreError(
                    "the credential file must be a regular file owned by this user"
                )
            if stat.S_IMODE(info.st_mode) != 0o600:
                raise CredentialStoreError("the credential file must have mode 0600")
            raw = handle.read()
        try:
            return parse_file_payload(raw)
        except ValueError:
            raise CredentialStoreError("the credential file is unreadable") from None

    def _write(self, values: dict[str, str]) -> None:
        payload = json.dumps({"version": FILE_VERSION, "values": values}, sort_keys=True)
        directory = self._path.parent
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(prefix=".credentials-", dir=directory)
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload.encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            Path(tmp).replace(self._path)
            tmp = None
            dir_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            raise CredentialStoreError("the credential file could not be saved") from None
        finally:
            if tmp is not None:
                with contextlib.suppress(OSError):
                    Path(tmp).unlink()

    def replace_all(self, values: dict[str, str]) -> None:
        """Replace every stored value at once, with the same failure guarantees as a write."""
        self._read()
        self._write(dict(values))

    def get(self, name: str) -> str | None:
        return self._read().get(name)

    def set(self, name: str, value: str) -> None:
        values = self._read()
        values[name] = value
        self._write(values)

    def delete(self, name: str) -> bool:
        values = self._read()
        if name not in values:
            return False
        del values[name]
        self._write(values)
        return True

    def __repr__(self) -> str:
        return "FileCredentialStore()"


def file_payload(values: dict[str, str]) -> str:
    """Values as credential-file JSON."""
    return json.dumps({"version": FILE_VERSION, "values": values}, sort_keys=True)


def parse_file_payload(raw: bytes) -> dict[str, str]:
    """The values of credential-file JSON, or ValueError (never echoing content)."""
    try:
        data = json.loads(raw)
        values = data["values"]
        if data.get("version") != FILE_VERSION or not isinstance(values, dict):
            raise ValueError
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
            raise ValueError
    except ValueError, KeyError, TypeError, AttributeError:
        raise ValueError("not a credential file") from None
    return dict(values)


__all__ = [
    "APPROVED",
    "BACKEND_ENV",
    "CHUNK",
    "FILE_ENV",
    "SERVICE",
    "CredentialStore",
    "CredentialStoreError",
    "FileCredentialStore",
    "file_payload",
    "parse_file_payload",
    "select_backend",
    "selected_file",
]
