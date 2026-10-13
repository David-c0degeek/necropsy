"""Sign-in never leaks a secret and never loses a working sign-in."""

from __future__ import annotations

import base64
import socket
import threading
import time
import traceback
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from necropsy.cli import app
from necropsy.wcl import auth as auth_module
from necropsy.wcl import cli as wcl_cli
from necropsy.wcl.auth import (
    Auth,
    AuthError,
    AuthState,
    CallbackListener,
    ClientRecord,
    LoginNeeded,
    Token,
)
from necropsy.wcl.credentials import CredentialStore
from necropsy.wcl.sites import VANILLA
from tests.wcl_fakes import Script

SECRET = "SENTINEL-CLIENT-SECRET-7f3a"
NEW_SECRET = "SENTINEL-NEW-SECRET-1b2c"
ACCESS = "SENTINEL-ACCESS-TOKEN-91bc"
REFRESH = "SENTINEL-REFRESH-TOKEN-55de"
ROTATED = "SENTINEL-ROTATED-REFRESH-0aa1"
CODE = "SENTINEL-OAUTH-CODE-3c3c"
BASIC = base64.b64encode(f"cid:{SECRET}".encode()).decode()
SENTINELS = (SECRET, NEW_SECRET, ACCESS, REFRESH, ROTATED, CODE, BASIC)


class Memory:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.fail_set_after: int | None = None
        self.sets = 0

    def get_password(self, service: str, name: str) -> str | None:
        return self.data.get(name)

    def set_password(self, service: str, name: str, value: str) -> None:
        self.sets += 1
        if self.fail_set_after is not None and self.sets > self.fail_set_after:
            raise RuntimeError(f"store unavailable {value}")
        self.data[name] = value

    def delete_password(self, service: str, name: str) -> None:
        import keyring.errors

        if name not in self.data:
            raise keyring.errors.PasswordDeleteError(name)
        del self.data[name]


def _auth(
    script: Script | None = None, now: float = 1000.0, expires_at: float | None = None
) -> tuple[Auth, Memory]:
    memory = Memory()
    store = CredentialStore(memory)
    token = None if expires_at is None else Token(ACCESS, REFRESH, expires_at)
    store.set("client:cid", ClientRecord("cid", SECRET, token).to_json())
    store.set("client-id", "cid")
    auth = Auth(
        VANILLA, store, transport=None if script is None else script.transport, now=lambda: now
    )
    memory.sets = 0
    return auth, memory


def _clean(text: str) -> None:
    for sentinel in SENTINELS:
        assert sentinel not in text, sentinel


def _all_text(exc: BaseException) -> str:
    return str(exc) + repr(exc) + "".join(traceback.format_exception(exc))


def _token_ok(**extra: Any) -> httpx.Response:
    return httpx.Response(
        200, json={"access_token": ACCESS, "refresh_token": REFRESH, "expires_in": 3600, **extra}
    )


def test_sign_in_stores_the_token_and_redacts_it() -> None:
    script = Script(_token_ok())
    auth, _ = _auth(script)
    token = auth.complete_sign_in("cid", None, CODE)
    assert token.access_token == ACCESS
    request = script.requests[0]
    assert request.headers["Authorization"] == f"Basic {BASIC}"
    assert CODE.encode() in request.content
    _clean(repr(token))
    stored = auth.stored_token()
    assert stored is not None and stored.refresh_token == REFRESH
    assert auth.state() is AuthState.SIGNED_IN


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            {"error": "invalid_client", "error_description": f"bad {SECRET} {CODE}"},
            "invalid_client",
        ),
        ({"error": f"weird-{ACCESS}", "error_description": BASIC}, "unrecognised error"),
        ({"message": f"oops {REFRESH}"}, "unrecognised error"),
    ],
)
def test_token_endpoint_errors_show_only_a_recognised_code(
    body: dict[str, Any], expected: str
) -> None:
    auth, _ = _auth(Script(httpx.Response(400, json=body)))
    with pytest.raises(AuthError) as raised:
        auth.complete_sign_in("cid", None, CODE)
    assert expected in str(raised.value)
    _clean(_all_text(raised.value))


def test_network_failures_do_not_chain_secrets() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot connect {request.headers['Authorization']}")

    auth, _ = _auth(Script(boom))
    with pytest.raises(AuthError) as raised:
        auth.complete_sign_in("cid", None, CODE)
    _clean(_all_text(raised.value))


def test_invalid_grant_means_login_needed() -> None:
    auth, _ = _auth(Script(httpx.Response(400, json={"error": "invalid_grant"})))
    with pytest.raises(LoginNeeded, match="necropsy auth login"):
        auth.complete_sign_in("cid", None, CODE)


def test_failed_sign_in_with_a_new_secret_keeps_the_old_sign_in() -> None:
    auth, memory = _auth(
        Script(httpx.Response(401, json={"error": "invalid_client"})), expires_at=99_999.0
    )
    before = dict(memory.data)
    with pytest.raises(AuthError):
        auth.complete_sign_in("cid", NEW_SECRET, CODE)
    assert memory.data == before
    assert auth.state() is AuthState.SIGNED_IN


def test_failed_sign_in_with_another_client_id_keeps_the_current_one() -> None:
    auth, memory = _auth(
        Script(httpx.Response(401, json={"error": "invalid_client"})), expires_at=99_999.0
    )
    before = dict(memory.data)
    with pytest.raises(AuthError):
        auth.complete_sign_in("other", NEW_SECRET, CODE)
    assert memory.data == before and auth.client_id() == "cid"


def test_failed_save_after_a_good_exchange_keeps_the_old_sign_in() -> None:
    auth, memory = _auth(Script(_token_ok()), expires_at=99_999.0)
    memory.fail_set_after = 1  # the first new chunk lands, the next write fails
    with pytest.raises(Exception) as raised:
        auth.complete_sign_in("cid", NEW_SECRET, CODE)
    _clean(_all_text(raised.value))
    memory.fail_set_after = None
    record = auth.record()
    assert record is not None and record.secret == SECRET
    assert record.token is not None and record.token.access_token == ACCESS


def test_refresh_keeps_an_omitted_refresh_token() -> None:
    script = Script(httpx.Response(200, json={"access_token": "new-access", "expires_in": 3600}))
    auth, _ = _auth(script, now=10_000.0, expires_at=100.0)
    assert auth.state() is AuthState.EXPIRED
    assert auth.user_token() == "new-access"
    stored = auth.stored_token()
    assert stored is not None and stored.refresh_token == REFRESH


def test_refresh_replaces_a_rotated_refresh_token() -> None:
    script = Script(
        httpx.Response(
            200, json={"access_token": "new", "refresh_token": ROTATED, "expires_in": 60}
        )
    )
    auth, _ = _auth(script, now=10_000.0, expires_at=100.0)
    auth.refresh()
    stored = auth.stored_token()
    assert stored is not None and stored.refresh_token == ROTATED


def test_failed_refresh_keeps_the_stored_token() -> None:
    auth, memory = _auth(
        Script(httpx.Response(500, json={"error": "server_error"})),
        now=10_000.0,
        expires_at=100.0,
    )
    before = dict(memory.data)
    with pytest.raises(AuthError):
        auth.refresh()
    assert memory.data == before


def test_client_token_is_kept_in_memory_only() -> None:
    script = Script(httpx.Response(200, json={"access_token": ACCESS, "expires_in": 3600}))
    auth, memory = _auth(script)
    assert auth.token_for("client") == ACCESS
    assert auth.token_for("client") == ACCESS
    assert len(script.requests) == 1
    assert all(ACCESS not in v for v in memory.data.values())
    _clean(repr(auth))


def test_not_signed_in() -> None:
    auth, _ = _auth()
    assert auth.state() is AuthState.LOGIN_NEEDED
    with pytest.raises(LoginNeeded):
        auth.user_token()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_listener_is_bound_before_the_browser_opens() -> None:
    port = _free_port()
    got: dict[str, str] = {}
    with CallbackListener("good", port=port) as listener:
        # A callback arriving before wait() is queued by the bound socket.
        def hit() -> None:
            got["page"] = httpx.get(
                f"http://127.0.0.1:{port}/callback?state=good&code={CODE}", timeout=5
            ).text

        thread = threading.Thread(target=hit)
        thread.start()
        time.sleep(0.2)
        assert listener.wait(timeout_s=5) == CODE
        thread.join(timeout=5)
    assert "Authorization received. Return to Necropsy to finish signing in." in got["page"]
    assert "Signed in" not in got["page"]


@pytest.mark.parametrize(
    ("query", "outcome"),
    [
        (f"state=bad&code={CODE}", "state"),
        (f"state=good&error=access_denied&error_description={SECRET}", "access_denied"),
        (f"state=good&error={ACCESS}", "unrecognised error"),
    ],
)
def test_callback_errors(query: str, outcome: str, capsys: pytest.CaptureFixture[str]) -> None:
    port = _free_port()
    with CallbackListener("good", port=port) as listener:
        thread = threading.Thread(
            target=lambda: httpx.get(f"http://127.0.0.1:{port}/callback?{query}", timeout=5)
        )
        thread.start()
        with pytest.raises(AuthError) as raised:
            listener.wait(timeout_s=5)
        thread.join(timeout=5)
    assert outcome in str(raised.value)
    _clean(_all_text(raised.value))
    captured = capsys.readouterr()
    _clean(captured.out + captured.err)


def test_a_silent_client_cannot_hold_the_listener(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_module._Handler, "timeout", 0.5)
    port = _free_port()
    start = time.monotonic()
    with CallbackListener("good", port=port) as listener:
        idle = socket.create_connection(("127.0.0.1", port))
        with pytest.raises(AuthError, match="timed out"):
            listener.wait(timeout_s=2)
        idle.close()
    assert time.monotonic() - start < 6


def _cli_auth(monkeypatch: pytest.MonkeyPatch, auth: Auth) -> None:
    monkeypatch.setattr(wcl_cli, "_auth", lambda: auth)
    monkeypatch.setattr("webbrowser.open", lambda url: True)


class _Listener:
    def __init__(self, outcome: str | Exception) -> None:
        self.outcome = outcome

    def __call__(self, state: str) -> _Listener:
        return self

    def __enter__(self) -> _Listener:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def wait(self, timeout_s: float = 300.0) -> str:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def test_status_prints_no_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    auth, _ = _auth(expires_at=999_999.0)
    _cli_auth(monkeypatch, auth)
    result = CliRunner().invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "signed-in" in result.output and "client id:        set" in result.output
    _clean(result.output)


def test_login_prompts_for_the_secret_without_echo(monkeypatch: pytest.MonkeyPatch) -> None:
    memory = Memory()
    auth = Auth(
        VANILLA, CredentialStore(memory), transport=Script(_token_ok()).transport, now=lambda: 1.0
    )
    _cli_auth(monkeypatch, auth)
    monkeypatch.setattr(wcl_cli, "CallbackListener", _Listener(CODE))
    result = CliRunner().invoke(app, ["auth", "login", "--client-id", "cid"], input=f"{SECRET}\n")
    assert result.exit_code == 0, result.output
    assert "Signed in to vanilla.warcraftlogs.com" in result.output
    _clean(result.output)
    record = auth.record("cid")
    assert record is not None and record.secret == SECRET


def test_cancelled_login_with_a_new_secret_changes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth, memory = _auth(expires_at=999_999.0)
    before = dict(memory.data)
    _cli_auth(monkeypatch, auth)
    monkeypatch.setattr(
        wcl_cli, "CallbackListener", _Listener(AuthError("sign-in failed (access_denied)"))
    )
    result = CliRunner().invoke(app, ["auth", "login", "--new-secret"], input=f"{NEW_SECRET}\n")
    assert result.exit_code == 1
    assert "auth failed: sign-in failed (access_denied)" in result.output
    assert memory.data == before
    _clean(result.output)


class _Broken:
    def get_password(self, service: str, name: str) -> str | None:
        raise RuntimeError(f"backend exploded holding {SECRET}")

    def set_password(self, service: str, name: str, value: str) -> None:
        raise RuntimeError(f"backend exploded holding {value}")

    def delete_password(self, service: str, name: str) -> None:
        raise RuntimeError(f"backend exploded holding {ACCESS}")


@pytest.mark.parametrize(
    "command", [["auth", "status"], ["auth", "status", "--check"], ["auth", "logout"]]
)
def test_backend_failures_are_sanitised_in_the_cli(
    monkeypatch: pytest.MonkeyPatch, command: list[str]
) -> None:
    auth = Auth(VANILLA, CredentialStore(_Broken()), now=lambda: 1000.0)
    _cli_auth(monkeypatch, auth)
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 1
    assert "auth failed: the OS credential store could not" in result.output
    _clean(result.output)


def test_auth_module_has_no_file_fallback() -> None:
    text = Path(auth_module.__file__ or "").read_text(encoding="utf-8")
    for forbidden in ("open(", "write_text", ".wcl_user_token", "Path("):
        assert forbidden not in text


def test_logout_removes_the_token_and_keeps_the_client(monkeypatch: pytest.MonkeyPatch) -> None:
    auth, _ = _auth(expires_at=999_999.0)
    _cli_auth(monkeypatch, auth)
    result = CliRunner().invoke(app, ["auth", "logout"])
    assert result.exit_code == 0 and result.output.strip() == "Signed out."
    record = auth.record()
    assert record is not None and record.token is None and record.secret == SECRET
    assert auth.state() is AuthState.LOGIN_NEEDED


def test_logout_forget_secret_removes_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    auth, memory = _auth(expires_at=999_999.0)
    _cli_auth(monkeypatch, auth)
    result = CliRunner().invoke(app, ["auth", "logout", "--forget-secret"])
    assert result.exit_code == 0 and "Client id and secret removed." in result.output
    assert memory.data == {}


class _RefusesDelete(Memory):
    def delete_password(self, service: str, name: str) -> None:
        import keyring.errors

        raise keyring.errors.PasswordDeleteError(f"denied {SECRET}")


def test_forget_secret_does_not_claim_success_when_removal_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = _RefusesDelete()
    store = CredentialStore(memory)
    store.set("client:cid", ClientRecord("cid", SECRET, Token(ACCESS, REFRESH, 9e9)).to_json())
    store.set("client-id", "cid")
    before = dict(memory.data)
    auth = Auth(VANILLA, store, now=lambda: 1000.0)
    _cli_auth(monkeypatch, auth)
    result = CliRunner().invoke(app, ["auth", "logout", "--forget-secret"])
    assert result.exit_code == 1
    assert "auth failed: the OS credential store could not remove a saved value" in result.output
    assert "Signed out" not in result.output
    assert memory.data == before
    _clean(result.output)
