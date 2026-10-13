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
"""

from __future__ import annotations

import contextlib
import os
import secrets
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

import keyring
from keyring.backend import KeyringBackend
from keyring.backends import SecretService, Windows, kwallet, macOS
from keyring.backends.chainer import ChainerBackend

SERVICE = "necropsy-wcl"
BACKEND_ENV = "NECROPSY_KEYRING_BACKEND"
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


__all__ = [
    "APPROVED",
    "BACKEND_ENV",
    "CHUNK",
    "SERVICE",
    "CredentialStore",
    "CredentialStoreError",
    "select_backend",
]
