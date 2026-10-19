"""The explicit credential file (ADR 0023): fail closed, private, atomic, never a fallback."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from necropsy.wcl import credentials
from necropsy.wcl.credentials import (
    BACKEND_ENV,
    FILE_ENV,
    CredentialStore,
    CredentialStoreError,
    FileCredentialStore,
    file_payload,
)

posix = pytest.mark.skipif(sys.platform == "win32", reason="the credential file is POSIX-only")

SECRET = "SENTINEL-REFRESH-TOKEN-7"


def _private(tmp_path: Path) -> Path:
    directory = tmp_path / "secrets"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    return directory / "credentials.json"


def _write(path: Path, values: dict[str, str], mode: int = 0o600) -> None:
    path.write_text(json.dumps({"version": 1, "values": values}), encoding="utf-8")
    path.chmod(mode)


def test_both_selectors_are_refused_before_any_store_is_touched(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(FILE_ENV, str(tmp_path / "credentials.json"))
    monkeypatch.setenv(BACKEND_ENV, "keyring.backends.Windows.WinVaultKeyring")

    def untouched(*_: Any, **__: Any) -> Any:
        raise AssertionError("the OS store must not be selected")

    monkeypatch.setattr(credentials, "select_backend", untouched)
    with pytest.raises(CredentialStoreError, match="both set"):
        CredentialStore.open()


def test_without_the_file_selector_the_os_store_path_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(FILE_ENV, raising=False)
    seen = []

    def fake(configured: Any, allowed: Any) -> object:
        seen.append((configured, allowed))
        return object()

    monkeypatch.setattr(credentials, "select_backend", fake)
    store = CredentialStore.open()
    assert type(store) is CredentialStore and seen == [(None, credentials.APPROVED)]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows refusal only")
def test_the_file_store_is_refused_on_windows(tmp_path: Path) -> None:
    with pytest.raises(CredentialStoreError, match="POSIX"):
        FileCredentialStore(tmp_path / "credentials.json")


@posix
def test_round_trip_keeps_mode_0600_and_never_leaves_a_temporary_file(tmp_path: Path) -> None:
    path = _private(tmp_path)
    store = FileCredentialStore(path)
    assert store.get("client-id") is None
    store.set("client-id", "abc")
    store.set("public-client:abc", SECRET)
    assert store.get("public-client:abc") == SECRET
    assert (path.stat().st_mode & 0o777) == 0o600
    assert sorted(p.name for p in path.parent.iterdir()) == ["credentials.json"]
    assert store.delete("client-id") is True and store.delete("client-id") is False
    assert json.loads(path.read_text(encoding="utf-8"))["values"] == {"public-client:abc": SECRET}
    assert SECRET not in repr(store)


@posix
@pytest.mark.parametrize("mode", [0o644, 0o640, 0o604, 0o700, 0o400])
def test_a_file_that_is_not_exactly_0600_is_refused(tmp_path: Path, mode: int) -> None:
    path = _private(tmp_path)
    _write(path, {"client-id": "abc"}, mode)
    with pytest.raises(CredentialStoreError, match="0600") as raised:
        FileCredentialStore(path).get("client-id")
    assert SECRET not in str(raised.value)


@posix
@pytest.mark.parametrize("mode", [0o755, 0o750, 0o711])
def test_a_directory_that_is_not_0700_is_refused(tmp_path: Path, mode: int) -> None:
    path = _private(tmp_path)
    path.parent.chmod(mode)
    with pytest.raises(CredentialStoreError, match="0700"):
        FileCredentialStore(path)


@posix
def test_a_linked_credential_file_is_refused(tmp_path: Path) -> None:
    path = _private(tmp_path)
    real = path.parent / "real.json"
    _write(real, {"client-id": "abc"})
    path.symlink_to(real)
    with pytest.raises(CredentialStoreError, match="could not be opened"):
        FileCredentialStore(path).get("client-id")


@posix
def test_a_linked_directory_is_refused(tmp_path: Path) -> None:
    path = _private(tmp_path)
    link = tmp_path / "linked"
    link.symlink_to(path.parent, target_is_directory=True)
    with pytest.raises(CredentialStoreError, match="plain directory"):
        FileCredentialStore(link / "credentials.json")


@posix
def test_a_file_owned_by_another_user_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _private(tmp_path)
    _write(path, {"client-id": "abc"})
    store = FileCredentialStore(path)
    real = path.stat().st_uid
    monkeypatch.setattr(os, "getuid", lambda: real + 1)
    with pytest.raises(CredentialStoreError, match="owned by this user"):
        store.get("client-id")


@posix
@pytest.mark.parametrize(
    "raw",
    [b"not json", b'{"version": 2, "values": {}}', b'{"version": 1, "values": {"a": 1}}', b"[]"],
)
def test_an_unreadable_file_is_refused_without_its_content(tmp_path: Path, raw: bytes) -> None:
    path = _private(tmp_path)
    path.write_bytes(raw)
    path.chmod(0o600)
    with pytest.raises(CredentialStoreError, match="unreadable") as raised:
        FileCredentialStore(path).get("a")
    assert raised.value.__cause__ is None


@posix
def test_a_failed_save_raises_and_keeps_the_previous_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _private(tmp_path)
    store = FileCredentialStore(path)
    store.set("public-client:abc", "old")
    before = path.read_bytes()

    def full(*_: Any) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "fsync", full)
    with pytest.raises(CredentialStoreError, match="could not be saved") as raised:
        store.set("public-client:abc", SECRET)
    assert raised.value.__cause__ is None and SECRET not in str(raised.value)
    assert path.read_bytes() == before
    assert sorted(p.name for p in path.parent.iterdir()) == ["credentials.json"]


@posix
def test_an_interrupted_rename_leaves_the_previous_value_readable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _private(tmp_path)
    store = FileCredentialStore(path)
    store.set("public-client:abc", "old")

    def interrupted(self: Path, target: Any) -> Path:
        raise OSError(5, "I/O error")

    monkeypatch.setattr(Path, "replace", interrupted)
    with pytest.raises(CredentialStoreError):
        store.set("public-client:abc", SECRET)
    monkeypatch.undo()
    assert FileCredentialStore(path).get("public-client:abc") == "old"
    assert sorted(p.name for p in path.parent.iterdir()) == ["credentials.json"]


@posix
def test_open_selects_the_file_store_only_when_named(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _private(tmp_path)
    monkeypatch.setenv(FILE_ENV, str(path))
    monkeypatch.delenv(BACKEND_ENV, raising=False)
    store = CredentialStore.open()
    assert isinstance(store, FileCredentialStore) and store.backend_name == "credential-file"


TOKEN = {"access": "ACCESS-SENTINEL", "refresh": SECRET, "expires_at": 4102444800.0}


def _record(mode: str, secret: str | None, token: dict[str, Any] | None = TOKEN) -> str:
    return json.dumps({"mode": mode, "secret": secret, "token": token})


class _Memory(CredentialStore):
    def __init__(self, values: dict[str, str]) -> None:
        self.values = dict(values)

    def get(self, name: str) -> str | None:
        return self.values.get(name)


def _imported(values: dict[str, str]) -> Any:
    from necropsy.wcl.auth import Auth
    from necropsy.wcl.sites import VANILLA

    return Auth(VANILLA, _Memory(values))


PUBLIC_POINTER = json.dumps({"mode": "public", "client_id": "pub"})


@pytest.mark.parametrize(
    ("stored", "override", "expected_pointer", "expected_record"),
    [
        ({"client-id": "cid", "client:cid": _record("personal", "s")}, None, "cid", "client:cid"),
        (
            {"client-id": PUBLIC_POINTER, "public-client:pub": _record("public", None)},
            None,
            PUBLIC_POINTER,
            "public-client:pub",
        ),
        (
            {
                "client-id": "saved",
                "client:saved": _record("personal", "s"),
                "client:override": _record("personal", "t"),
            },
            "override",
            "override",
            "client:override",
        ),
        ({"client:override": _record("personal", "t")}, "override", "override", "client:override"),
    ],
    ids=["personal", "public", "override", "override-without-pointer"],
)
def test_export_is_a_self_contained_selection_that_imports_cleanly(
    monkeypatch: pytest.MonkeyPatch,
    stored: dict[str, str],
    override: str | None,
    expected_pointer: str,
    expected_record: str,
) -> None:
    from necropsy.wcl.auth import CLIENT_ID_ENV, validate_import

    if override:
        monkeypatch.setenv(CLIENT_ID_ENV, override)
    else:
        monkeypatch.delenv(CLIENT_ID_ENV, raising=False)
    exported = _imported(stored).export_values()
    assert exported == {"client-id": expected_pointer, expected_record: stored[expected_record]}
    monkeypatch.delenv(CLIENT_ID_ENV, raising=False)
    validate_import(exported)
    record = _imported(exported).record()
    assert record is not None and record.token is not None
    assert record.token.refresh_token == SECRET


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"client-id": "cid"},
        {"client-id": "cid", "client:other": _record("personal", "s")},
        {"client-id": "cid", "client:cid": _record("personal", "s", None)},
        {"client-id": "cid", "client:cid": "not json"},
        {"client-id": "cid", "client:cid": _record("personal", "s"), "extra": "x"},
    ],
    ids=["empty", "pointer-only", "mismatched", "no-token", "unreadable", "extra"],
)
def test_import_refuses_anything_but_one_complete_sign_in(values: dict[str, str]) -> None:
    from necropsy.wcl.auth import AuthError, validate_import

    with pytest.raises(AuthError) as raised:
        validate_import(values)
    assert SECRET not in str(raised.value)


def _cli_auth(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    from necropsy.wcl import cli

    monkeypatch.setattr(cli, "_auth", lambda: _imported(values))


def test_auth_export_writes_the_effective_sign_in_only(monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from necropsy.cli import app

    record = _record("personal", "client-secret")
    monkeypatch.delenv("NECROPSY_WCL_CLIENT_ID", raising=False)
    _cli_auth(monkeypatch, {"client-id": "cid", "client:cid": record, "client:other": "x"})
    result = CliRunner().invoke(app, ["auth", "export"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == json.loads(
        file_payload({"client-id": "cid", "client:cid": record})
    )


def test_auth_export_refuses_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from necropsy.cli import app

    _cli_auth(monkeypatch, {"client-id": "cid"})
    from necropsy.wcl import cli

    monkeypatch.setattr(cli, "_stdout_is_terminal", lambda: True)
    result = CliRunner().invoke(app, ["auth", "export"])
    assert result.exit_code == 2 and "pipe" in result.output


def test_auth_export_without_a_sign_in_fails_without_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from typer.testing import CliRunner

    from necropsy.cli import app

    _cli_auth(monkeypatch, {})
    result = CliRunner().invoke(app, ["auth", "export"])
    assert result.exit_code == 1 and result.stdout == ""


def test_auth_import_needs_the_file_selector(monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from necropsy.cli import app

    monkeypatch.delenv(FILE_ENV, raising=False)
    result = CliRunner().invoke(app, ["auth", "import"], input="{}")
    assert result.exit_code == 2


GOOD = {"client-id": "cid", "client:cid": _record("personal", "s")}


@posix
@pytest.mark.parametrize(
    "payload",
    [b"", file_payload(GOOD).encode()[:40], b"garbage", file_payload({"client-id": "x"}).encode()],
    ids=["empty", "truncated", "garbage", "incomplete"],
)
def test_auth_import_keeps_the_previous_file_on_bad_input(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, payload: bytes
) -> None:
    from typer.testing import CliRunner

    from necropsy.cli import app

    path = _private(tmp_path)
    FileCredentialStore(path).replace_all(GOOD)
    before = path.read_bytes()
    monkeypatch.setenv(FILE_ENV, str(path))
    monkeypatch.delenv(BACKEND_ENV, raising=False)
    result = CliRunner().invoke(app, ["auth", "import"], input=payload)
    assert result.exit_code != 0
    assert path.read_bytes() == before and SECRET not in result.output
    assert sorted(p.name for p in path.parent.iterdir()) == ["credentials.json"]


@posix
def test_auth_import_replaces_the_file_with_a_valid_export(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from typer.testing import CliRunner

    from necropsy.cli import app

    path = _private(tmp_path)
    monkeypatch.setenv(FILE_ENV, str(path))
    monkeypatch.delenv(BACKEND_ENV, raising=False)
    result = CliRunner().invoke(app, ["auth", "import"], input=file_payload(GOOD))
    assert result.exit_code == 0, result.output
    assert FileCredentialStore(path).get("client:cid") == GOOD["client:cid"]
    assert (path.stat().st_mode & 0o777) == 0o600 and SECRET not in result.output


FIFO_PROBE = """
import sys
from pathlib import Path
from necropsy.wcl.credentials import CredentialStoreError, FileCredentialStore
try:
    FileCredentialStore(Path(sys.argv[1])).get("x")
except CredentialStoreError as error:
    print("refused:", error)
"""


@posix
def test_a_fifo_is_refused_instead_of_blocking(tmp_path: Path) -> None:
    import subprocess

    if sys.platform == "win32":
        pytest.skip("POSIX-only")
    path = _private(tmp_path)
    os.mkfifo(path, 0o600)
    done = subprocess.run(
        [sys.executable, "-c", FIFO_PROBE, str(path)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert "refused:" in done.stdout and "regular file" in done.stdout


@posix
def test_a_failed_directory_sync_reports_an_error_and_leaves_one_complete_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _private(tmp_path)
    store = FileCredentialStore(path)
    store.set("public-client:abc", "old")
    real = os.fsync
    calls: list[int] = []

    def directory_fails(fd: int) -> None:
        calls.append(fd)
        if len(calls) == 2:
            raise OSError(5, "I/O error")
        real(fd)

    monkeypatch.setattr(os, "fsync", directory_fails)
    with pytest.raises(CredentialStoreError, match="could not be saved"):
        store.set("public-client:abc", SECRET)
    monkeypatch.undo()
    assert len(calls) == 2
    assert FileCredentialStore(path).get("public-client:abc") in {"old", SECRET}
    assert sorted(p.name for p in path.parent.iterdir()) == ["credentials.json"]


def test_auth_import_with_both_selectors_fails_before_reading_or_opening(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from typer.testing import CliRunner

    from necropsy.cli import app
    from necropsy.wcl import cli

    monkeypatch.setenv(FILE_ENV, str(tmp_path / "credentials.json"))
    monkeypatch.setenv(BACKEND_ENV, "keyring.backends.SecretService.Keyring")

    def untouched(*_: Any, **__: Any) -> Any:
        raise AssertionError("no credential store may be constructed")

    monkeypatch.setattr(cli, "FileCredentialStore", untouched)
    result = CliRunner().invoke(app, ["auth", "import"], input=file_payload(GOOD))
    assert result.exit_code == 1 and "both set" in result.output
