"""Public sign-in preserves personal credentials and never uses a shared secret."""

from __future__ import annotations

import json
import re
import time
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from typer.testing import CliRunner

from necropsy.cli import app
from necropsy.wcl import cli as wcl_cli
from necropsy.wcl.auth import PUBLIC_CLIENT_ID, AuthError, AuthMode, LoginNeeded, PkceAttempt, Token
from necropsy.wcl.client import RATE_FIELDS, PermissionDenied, WclClient
from necropsy.wcl.credentials import CredentialStoreError
from necropsy.wcl.sites import VANILLA
from tests.unit.test_wcl_auth import (
    ACCESS,
    CODE,
    REFRESH,
    ROTATED,
    SECRET,
    _auth,
    _clean,
    _cli_auth,
    _Listener,
    _token_ok,
)
from tests.wcl_fakes import Script


def test_rfc_s256_vector_and_fresh_attempts() -> None:
    vector = PkceAttempt("app", verifier="dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")
    assert vector.challenge == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    first, second = PkceAttempt("app"), PkceAttempt("app")
    assert first.state != second.state and first.verifier != second.verifier
    assert re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", first.verifier)
    assert first.verifier not in repr(first) and first.state not in repr(first)


def test_public_exchange_and_user_query_preserve_legacy_record() -> None:
    script = Script(
        _token_ok(),
        httpx.Response(
            200,
            json={
                "data": {
                    "rateLimitData": {
                        "limitPerHour": 3600,
                        "pointsSpentThisHour": 1,
                        "pointsResetIn": 60,
                    }
                }
            },
        ),
    )
    auth, _ = _auth(script, expires_at=99999)
    legacy = auth.store.get("client:cid")
    # Pin compatibility with pre-tag personal JSON, including the same client id.
    old = json.loads(legacy or "{}")
    old.pop("mode")
    auth.store.set("client:cid", json.dumps(old))
    attempt = PkceAttempt("cid")
    params = parse_qs(
        urlsplit(auth.authorize_url("cid", attempt.state, challenge=attempt.challenge)).query
    )
    assert params["code_challenge"] == [attempt.challenge]
    assert params["code_challenge_method"] == ["S256"]
    assert attempt.verifier not in str(params)
    auth.complete_public_sign_in(attempt, CODE)
    request = script.requests[0]
    form = parse_qs(request.content.decode())
    assert "authorization" not in request.headers
    assert form == {
        "client_id": ["cid"],
        "grant_type": ["authorization_code"],
        "code": [CODE],
        "redirect_uri": ["http://localhost:8765/callback"],
        "code_verifier": [attempt.verifier],
    }
    record = auth.record()
    assert record and record.mode is AuthMode.PUBLIC and record.secret is None
    assert auth.store.get("client:cid") == json.dumps(old)
    assert auth.record("cid", mode=AuthMode.PERSONAL).secret == SECRET  # type: ignore[union-attr]
    client = WclClient(VANILLA, auth.token_for, transport=script.transport)
    try:
        client.query(f"query {{ {RATE_FIELDS} }}", endpoint="user")
    finally:
        client.close()
    assert script.requests[-1].url.path == "/api/v2/user"
    assert script.requests[-1].headers["Authorization"] == f"Bearer {ACCESS}"
    with pytest.raises(AuthError, match="--endpoint user"):
        auth.token_for("client")
    with pytest.raises(AuthError, match="endpoint must"):
        auth.token_for("typo")
    assert len(script.requests) == 2
    _clean(repr(auth) + repr(record))


@pytest.mark.parametrize("expired", [False, True])
def test_attempt_is_single_use_and_expires_before_http(expired: bool) -> None:
    script = Script(_token_ok())
    auth, _ = _auth(script)
    attempt = PkceAttempt("app")
    if expired:
        attempt.started_at = time.monotonic() - 301
    else:
        auth.complete_public_sign_in(attempt, CODE)
    with pytest.raises(AuthError, match="expired or already used"):
        auth.complete_public_sign_in(attempt, CODE)
    assert len(script.requests) == (0 if expired else 1)


@pytest.mark.parametrize("error", ["invalid_grant", "access_denied", "invalid_client"])
def test_failed_public_exchange_preserves_personal_sign_in(error: str) -> None:
    script = Script(httpx.Response(400, json={"error": error, "error_description": SECRET}))
    auth, memory = _auth(script, expires_at=99999)
    before = dict(memory.data)
    attempt = PkceAttempt("cid")
    with pytest.raises(AuthError, match=error) as raised:
        auth.complete_public_sign_in(attempt, CODE)
    assert before == memory.data and auth.mode() is AuthMode.PERSONAL
    _clean(str(raised.value))
    with pytest.raises(AuthError, match="already used"):
        auth.complete_public_sign_in(attempt, CODE)


@pytest.mark.parametrize("fail_after", [0, 1, 2, 3])
def test_partial_store_write_keeps_personal_selection(fail_after: int) -> None:
    auth, memory = _auth(Script(_token_ok()), expires_at=99999)
    old = auth.store.get("client:cid")
    memory.fail_set_after = fail_after
    with pytest.raises(CredentialStoreError):
        auth.complete_public_sign_in(PkceAttempt("cid"), CODE)
    memory.fail_set_after = None
    assert auth.mode() is AuthMode.PERSONAL and auth.client_id() == "cid"
    assert auth.store.get("client:cid") == old


@pytest.mark.parametrize("refresh", [None, ROTATED])
def test_public_refresh_rotation_and_logout(refresh: str | None) -> None:
    body: dict[str, object] = {"access_token": "renewed", "expires_in": 3600}
    if refresh is not None:
        body["refresh_token"] = refresh
    script = Script(_token_ok(), httpx.Response(200, json=body))
    auth, _ = _auth(script)
    auth.complete_public_sign_in(PkceAttempt("cid"), CODE)
    legacy = auth.store.get("client:cid")
    auth.now = lambda: 10000
    assert auth.user_token() == "renewed"
    assert auth.stored_token() == Token("renewed", refresh or REFRESH, 13600)
    assert parse_qs(script.requests[-1].content.decode()) == {
        "client_id": ["cid"],
        "grant_type": ["refresh_token"],
        "refresh_token": [REFRESH],
    }
    assert "authorization" not in script.requests[-1].headers
    auth.logout()
    assert auth.stored_token() is None
    auth.logout(forget_secret=True)
    assert auth.store.get("public-client:cid") is None
    assert auth.store.get("client:cid") == legacy


def test_public_refresh_failure_keeps_stored_record() -> None:
    script = Script(_token_ok(), httpx.Response(400, json={"error": "invalid_grant"}))
    auth, memory = _auth(script)
    auth.complete_public_sign_in(PkceAttempt("cid"), CODE)
    before = dict(memory.data)
    auth.now = lambda: 10000
    with pytest.raises(LoginNeeded):
        auth.user_token()
    assert before == memory.data


@pytest.mark.parametrize(
    "body",
    [
        {"access_token": None},
        {"access_token": ""},
        {"access_token": ACCESS, "expires_in": "NaN"},
        {"access_token": ACCESS, "expires_in": -1},
        {"access_token": ACCESS, "refresh_token": []},
    ],
)
def test_malformed_token_cannot_commit(body: dict[str, object]) -> None:
    auth, memory = _auth(Script(httpx.Response(200, json=body)), expires_at=99999)
    before = dict(memory.data)
    with pytest.raises(AuthError, match="invalid token response"):
        auth.complete_public_sign_in(PkceAttempt("cid"), CODE)
    assert before == memory.data


@pytest.mark.parametrize("explicit_id", [None, "app"])
def test_cli_public_login_never_prompts_for_secret(
    monkeypatch: pytest.MonkeyPatch,
    explicit_id: str | None,
) -> None:
    script = Script(_token_ok())
    auth, _ = _auth(script)
    _cli_auth(monkeypatch, auth)
    monkeypatch.setattr(wcl_cli, "CallbackListener", _Listener(CODE))
    monkeypatch.delenv("NECROPSY_WCL_CLIENT_ID", raising=False)
    args = ["auth", "login"]
    if explicit_id:
        args += ["--client-id", explicit_id]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert "secret" not in result.output.lower()
    assert "code_challenge_method=S256" in result.output
    _clean(result.output)
    assert auth.mode() is AuthMode.PUBLIC
    assert parse_qs(script.requests[0].content.decode())["client_id"] == [
        explicit_id or PUBLIC_CLIENT_ID
    ]


@pytest.mark.parametrize(
    "outcome",
    [
        AuthError("sign-in failed (state)"),
        AuthError("sign-in failed (access_denied)"),
        AuthError("timed out"),
    ],
)
def test_cancelled_public_cli_preserves_selection(
    monkeypatch: pytest.MonkeyPatch,
    outcome: AuthError,
) -> None:
    auth, memory = _auth(expires_at=99999)
    before = dict(memory.data)
    _cli_auth(monkeypatch, auth)
    monkeypatch.setattr(wcl_cli, "CallbackListener", _Listener(outcome))
    result = CliRunner().invoke(app, ["auth", "login", "--client-id", "app"])
    assert result.exit_code == 1 and memory.data == before
    _clean(result.output)


def test_public_permission_denial_never_falls_back() -> None:
    script = Script(_token_ok(), httpx.Response(403))
    auth, _ = _auth(script)
    auth.complete_public_sign_in(PkceAttempt("app"), CODE)
    client = WclClient(VANILLA, auth.token_for, transport=script.transport)
    try:
        with pytest.raises(PermissionDenied):
            client.query(f"query {{ {RATE_FIELDS} }}", endpoint="user")
    finally:
        client.close()
    assert len(script.requests) == 2
    assert script.requests[-1].url.path == "/api/v2/user"
