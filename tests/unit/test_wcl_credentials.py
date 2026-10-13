"""Credential store selection never touches an unapproved backend."""

from __future__ import annotations

from typing import Any

import pytest
from keyring.backends.chainer import ChainerBackend

from necropsy.wcl import credentials
from necropsy.wcl.credentials import CHUNK, CredentialStore, CredentialStoreError, select_backend


class _Memory:
    """In-memory backend that records every call."""

    def __init__(self, preset: dict[str, str] | None = None) -> None:
        self.data: dict[tuple[str, str], str] = {
            (credentials.SERVICE, k): v for k, v in (preset or {}).items()
        }
        self.calls: list[str] = []

    def get_password(self, service: str, name: str) -> str | None:
        self.calls.append(f"get {name}")
        return self.data.get((service, name))

    def set_password(self, service: str, name: str, value: str) -> None:
        self.calls.append(f"set {name}")
        self.data[(service, name)] = value

    def delete_password(self, service: str, name: str) -> None:
        self.calls.append(f"delete {name}")
        if (service, name) not in self.data:
            import keyring.errors

            raise keyring.errors.PasswordDeleteError(name)
        del self.data[(service, name)]


class Secure(_Memory):
    """Stands in for an approved OS store (only in the test's own allow list)."""


class Insecure(_Memory):
    """A positive-priority plaintext-style backend that must never be used."""

    priority = 10


class WinVaultKeyring(_Memory):
    """Spoofs the name of an approved class; must still be refused."""


ALLOWED = (Secure,)


class _FakeChain(ChainerBackend):
    """A chaining backend over test backends only (the real chain is never built)."""

    def __init__(self, members: list[Any]) -> None:
        self._members = members

    @property
    def backends(self) -> list[Any]:
        return self._members


def _chain(*backends: Any) -> ChainerBackend:
    return _FakeChain(list(backends))


def test_secure_first_empty_never_falls_through_to_an_insecure_store() -> None:
    insecure = Insecure({"client-id": "leaked"})
    secure = Secure()
    store = CredentialStore.open(_chain(secure, insecure), ALLOWED)
    assert store.get("client-id") is None
    assert insecure.calls == []


def test_an_insecure_only_configuration_is_refused_before_any_access() -> None:
    insecure = Insecure({"client-id": "x"})
    with pytest.raises(CredentialStoreError, match="no approved OS credential store"):
        CredentialStore.open(_chain(insecure), ALLOWED)
    with pytest.raises(CredentialStoreError):
        CredentialStore.open(insecure, ALLOWED)
    assert insecure.calls == []


def test_a_spoofed_class_name_is_refused() -> None:
    spoof = WinVaultKeyring()
    with pytest.raises(CredentialStoreError):
        select_backend(spoof)  # the real allow list holds the real class only
    assert spoof.calls == []


def test_two_approved_stores_need_an_explicit_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    class Secure2(_Memory):
        pass

    a, b = Secure(), Secure2()
    allowed = (Secure, Secure2)
    with pytest.raises(CredentialStoreError, match="several approved"):
        select_backend(_chain(a, b), allowed)
    monkeypatch.setenv(credentials.BACKEND_ENV, f"{Secure2.__module__}.{Secure2.__qualname__}")
    assert select_backend(_chain(a, b), allowed) is b


class Flaky(Secure):
    """Fails the n-th write, or every delete, on demand."""

    def __init__(self) -> None:
        super().__init__()
        self.fail_on_set: int | None = None
        self.fail_deletes = False
        self.set_count = 0

    def set_password(self, service: str, name: str, value: str) -> None:
        self.set_count += 1
        if self.fail_on_set is not None and self.set_count == self.fail_on_set:
            raise RuntimeError(f"disk full while writing {value}")
        super().set_password(service, name, value)

    def delete_password(self, service: str, name: str) -> None:
        if self.fail_deletes:
            raise RuntimeError("locked")
        super().delete_password(service, name)


A = "A" * (CHUNK * 2)
B = "B" * (CHUNK * 2)


def _store_with_a() -> tuple[CredentialStore, Flaky]:
    backend = Flaky()
    store = CredentialStore(backend)
    store.set("user-token:c", A)
    backend.set_count = 0
    return store, backend


def test_long_values_are_chunked_within_the_one_store() -> None:
    store, backend = _store_with_a()
    assert all(len(v) <= CHUNK for v in backend.data.values())
    assert store.get("user-token:c") == A


@pytest.mark.parametrize("failing_write", [1, 2, 3])
def test_a_failed_replacement_keeps_the_previous_value(failing_write: int) -> None:
    # writes 1-2 are the new chunks, write 3 is the head
    store, backend = _store_with_a()
    backend.fail_on_set = failing_write
    with pytest.raises(CredentialStoreError) as raised:
        store.set("user-token:c", B)
    assert "B" * 10 not in str(raised.value) and raised.value.__cause__ is None
    backend.fail_on_set = None
    assert store.get("user-token:c") == A
    assert not any(v.startswith("B") for v in backend.data.values())


def test_shrinking_removes_the_old_generation() -> None:
    store, backend = _store_with_a()
    store.set("user-token:c", "short")
    assert store.get("user-token:c") == "short"
    assert len([k for _, k in backend.data if k.startswith("user-token:c@")]) == 1


def test_a_failed_cleanup_cannot_undo_a_successful_write() -> None:
    store, backend = _store_with_a()
    backend.fail_deletes = True
    store.set("user-token:c", B)
    assert store.get("user-token:c") == B


def test_delete_removes_head_and_chunks() -> None:
    store, backend = _store_with_a()
    assert store.delete("user-token:c")
    assert backend.data == {}


class Exploding(Secure):
    def get_password(self, service: str, name: str) -> str | None:
        raise RuntimeError("read failed: SENTINEL-SECRET-1")

    def set_password(self, service: str, name: str, value: str) -> None:
        raise RuntimeError(f"write failed: {value}")

    def delete_password(self, service: str, name: str) -> None:
        raise RuntimeError("delete failed: SENTINEL-SECRET-2")


@pytest.mark.parametrize("operation", ["get", "set", "delete"])
def test_backend_failures_never_carry_backend_text(operation: str) -> None:
    import traceback

    store = CredentialStore(Exploding())
    with pytest.raises(CredentialStoreError) as raised:
        if operation == "get":
            store.get("x")
        elif operation == "set":
            store.set("x", "SENTINEL-SECRET-3")
        else:
            store.delete("x")
    error = raised.value
    assert "SENTINEL" not in str(error) and "SENTINEL" not in repr(error)
    assert error.__cause__ is None and error.__suppress_context__
    # The formatted traceback shows no chained backend exception.
    assert "RuntimeError" not in "".join(traceback.format_exception(error))


def test_backend_discovery_failure_is_sanitised(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> Any:
        raise RuntimeError("SENTINEL-SECRET-4")

    monkeypatch.setattr("keyring.get_keyring", broken)
    with pytest.raises(CredentialStoreError) as raised:
        select_backend()
    assert "SENTINEL" not in str(raised.value) and raised.value.__cause__ is None


def test_repr_names_only_the_backend() -> None:
    assert "Secure" in repr(CredentialStore(Secure({"client-secret:c": "s3cret"})))
    assert "s3cret" not in repr(CredentialStore(Secure({"client-secret:c": "s3cret"})))


class RefusesDelete(Secure):
    """Reports every delete failure as PasswordDeleteError, like some OS backends."""

    def delete_password(self, service: str, name: str) -> None:
        import keyring.errors

        raise keyring.errors.PasswordDeleteError("permission denied: SENTINEL-SECRET-5")


def test_a_refused_delete_is_an_error_and_keeps_the_active_value() -> None:
    backend = RefusesDelete()
    store = CredentialStore(backend)
    store.set("user-token:c", A)
    before = dict(backend.data)
    with pytest.raises(CredentialStoreError) as raised:
        store.delete("user-token:c")
    assert "SENTINEL" not in str(raised.value) and raised.value.__cause__ is None
    assert backend.data == before
    assert store.get("user-token:c") == A


def test_deleting_an_absent_value_is_not_an_error() -> None:
    assert CredentialStore(Secure()).delete("nothing-here") is False
