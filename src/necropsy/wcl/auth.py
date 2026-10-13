"""Personal-use Warcraft Logs sign-in with a confidential client.

The client secret and the user token live only in the selected OS credential
store (see `credentials`), together in one record per client id, so a single
write switches both. Sign-in is staged: a new client id or secret is used for
the browser authorization and the token exchange first, and is saved only when
the whole sign-in succeeds. A failed or cancelled sign-in leaves the previous
working credentials untouched.

Nothing secret is ever printed, logged, put in an exception message or kept in
an exception chain: token-endpoint failures report only a recognised OAuth
error code, and reprs are redacted. This flow is for the account owner's own
machine; a distributed app must use a public PKCE client instead.
"""

from __future__ import annotations

import base64
import http.server
import json
import os
import secrets
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx

from necropsy.wcl.credentials import CredentialStore
from necropsy.wcl.sites import Site, require_supported

CLIENT_ID_ENV = "NECROPSY_WCL_CLIENT_ID"
REDIRECT_HOST = "127.0.0.1"
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
EXPIRY_MARGIN_S = 120
REQUEST_READ_TIMEOUT_S = 10.0
OAUTH_ERRORS = frozenset(
    {
        "invalid_request",
        "invalid_client",
        "invalid_grant",
        "unauthorized_client",
        "unsupported_grant_type",
        "invalid_scope",
        "access_denied",
        "server_error",
        "temporarily_unavailable",
    }
)
_POINTER = "client-id"


def _record_name(client_id: str) -> str:
    return f"client:{client_id}"


class AuthError(Exception):
    """Sign-in failed. The message never contains a secret."""


class LoginNeeded(AuthError):
    """No usable user token: run `necropsy auth login`."""


class AuthState(StrEnum):
    SIGNED_IN = "signed-in"
    EXPIRED = "expired"
    LOGIN_NEEDED = "login-needed"


@dataclass(frozen=True)
class Token:
    access_token: str = field(repr=False)
    refresh_token: str | None = field(repr=False)
    expires_at: float

    def __repr__(self) -> str:
        refresh = "yes" if self.refresh_token else "no"
        return f"Token(expires_at={self.expires_at:.0f}, refresh={refresh})"

    def as_dict(self) -> dict[str, Any]:
        return {
            "access": self.access_token,
            "refresh": self.refresh_token,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Token:
        try:
            return cls(str(data["access"]), data.get("refresh"), float(data["expires_at"]))
        except KeyError, TypeError, ValueError, AttributeError:
            raise LoginNeeded(
                "the stored sign-in is unreadable; run `necropsy auth login`"
            ) from None


@dataclass(frozen=True)
class ClientRecord:
    """What is stored for one client id: its secret and, after sign-in, the token."""

    client_id: str
    secret: str = field(repr=False)
    token: Token | None = None

    def to_json(self) -> str:
        return json.dumps(
            {"secret": self.secret, "token": None if self.token is None else self.token.as_dict()}
        )


def _safe_code(value: Any) -> str:
    return str(value) if isinstance(value, str) and value in OAUTH_ERRORS else "unrecognised error"


@dataclass
class Auth:
    site: Site
    store: CredentialStore
    transport: httpx.BaseTransport | None = None
    now: Callable[[], float] = time.time
    _client_token: Token | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        require_supported(self.site)

    # -- stored values ----------------------------------------------------
    def client_id(self) -> str | None:
        return os.environ.get(CLIENT_ID_ENV) or self.store.get(_POINTER)

    def record(self, client_id: str | None = None) -> ClientRecord | None:
        cid = client_id or self.client_id()
        if not cid:
            return None
        text = self.store.get(_record_name(cid))
        if text is None:
            return None
        try:
            data = json.loads(text)
            secret = str(data["secret"])
            token = None if data.get("token") is None else Token.from_dict(data["token"])
        except ValueError, KeyError, TypeError:
            raise LoginNeeded(
                "the stored sign-in is unreadable; run `necropsy auth login`"
            ) from None
        return ClientRecord(cid, secret, token)

    def stored_token(self) -> Token | None:
        found = self.record()
        return None if found is None else found.token

    def state(self) -> AuthState:
        try:
            token = self.stored_token()
        except LoginNeeded:
            return AuthState.LOGIN_NEEDED
        if token is None:
            return AuthState.LOGIN_NEEDED
        if token.expires_at - EXPIRY_MARGIN_S <= self.now():
            return AuthState.EXPIRED if token.refresh_token else AuthState.LOGIN_NEEDED
        return AuthState.SIGNED_IN

    def logout(self, forget_secret: bool = False) -> None:
        current = self.record()
        if current is None:
            return
        if forget_secret:
            self.store.delete(_record_name(current.client_id))
            self.store.delete(_POINTER)
        else:
            self.store.set(
                _record_name(current.client_id),
                ClientRecord(current.client_id, current.secret).to_json(),
            )

    # -- token endpoint ---------------------------------------------------
    def _token_request(self, client_id: str, secret: str, form: dict[str, str]) -> Token:
        basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode("ascii")
        try:
            with httpx.Client(
                transport=self.transport, timeout=30.0, follow_redirects=False
            ) as http:
                response = http.post(
                    self.site.token_url, data=form, headers={"Authorization": f"Basic {basic}"}
                )
        except httpx.HTTPError:
            raise AuthError("could not reach the WCL sign-in service") from None
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.status_code != 200 or not isinstance(body, dict) or "access_token" not in body:
            code = _safe_code(body.get("error") if isinstance(body, dict) else None)
            if code == "invalid_grant":
                raise LoginNeeded(
                    "WCL rejected the sign-in (invalid_grant); run `necropsy auth login`"
                )
            raise AuthError(f"WCL sign-in failed (HTTP {response.status_code}, {code})")
        try:
            expires_in = float(body.get("expires_in", 3600))
        except TypeError, ValueError:
            expires_in = 3600.0
        refresh = body.get("refresh_token")
        return Token(
            str(body["access_token"]),
            str(refresh) if isinstance(refresh, str) and refresh else None,
            self.now() + expires_in,
        )

    def complete_sign_in(
        self, client_id: str, secret: str | None, code: str, redirect_uri: str = REDIRECT_URI
    ) -> Token:
        """Exchange the code with the given (staged) credentials; save only on success.

        `secret` None means: use the secret already stored for this client id.
        The record (secret + token) is written first, then the pointer to it, so
        a failure at any step leaves the previous working sign-in in place.
        """
        if secret is None:
            existing = self.record(client_id)
            if existing is None:
                raise LoginNeeded("no client secret saved for this client id; enter it to sign in")
            secret = existing.secret
        token = self._token_request(
            client_id,
            secret,
            {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
        )
        self.store.set(_record_name(client_id), ClientRecord(client_id, secret, token).to_json())
        if self.store.get(_POINTER) != client_id:
            self.store.set(_POINTER, client_id)
        return token

    def refresh(self) -> Token:
        current = self.record()
        if current is None or current.token is None or not current.token.refresh_token:
            raise LoginNeeded("no stored sign-in to refresh; run `necropsy auth login`")
        new = self._token_request(
            current.client_id,
            current.secret,
            {"grant_type": "refresh_token", "refresh_token": current.token.refresh_token},
        )
        if new.refresh_token is None:
            new = Token(new.access_token, current.token.refresh_token, new.expires_at)
        self.store.set(
            _record_name(current.client_id),
            ClientRecord(current.client_id, current.secret, new).to_json(),
        )
        return new

    # -- tokens for the API client ------------------------------------------
    def user_token(self) -> str:
        state = self.state()
        if state is AuthState.LOGIN_NEEDED:
            raise LoginNeeded("not signed in to WCL; run `necropsy auth login`")
        token = self.refresh() if state is AuthState.EXPIRED else self.stored_token()
        assert token is not None
        return token.access_token

    def client_token(self) -> str:
        token = self._client_token
        if token is None or token.expires_at - EXPIRY_MARGIN_S <= self.now():
            current = self.record()
            if current is None:
                raise LoginNeeded("no WCL client saved; run `necropsy auth login`")
            token = self._token_request(
                current.client_id, current.secret, {"grant_type": "client_credentials"}
            )
            self._client_token = token  # memory only
        return token.access_token

    def token_for(self, endpoint: str) -> str:
        return self.user_token() if endpoint == "user" else self.client_token()

    def authorize_url(self, client_id: str, state: str, redirect_uri: str = REDIRECT_URI) -> str:
        query = urllib.parse.urlencode(
            {
                "client_id": client_id,
                "state": state,
                "redirect_uri": redirect_uri,
                "response_type": "code",
            }
        )
        return f"{self.site.authorize_url}?{query}"


# -- local callback -----------------------------------------------------------
_PAGE = (
    "<!doctype html><meta charset=utf-8><title>Necropsy</title>"
    "<p>{}</p><p>You can close this window.</p>"
)


class _Handler(http.server.BaseHTTPRequestHandler):
    server_version = "necropsy"
    timeout = REQUEST_READ_TIMEOUT_S  # a slow or idle client cannot hold the listener

    def log_message(self, format: str, *args: Any) -> None:
        return  # never log request lines: they carry the code and state

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        state = params.get("state", [""])[0]
        expected: str = self.server.expected_state  # type: ignore[attr-defined]
        if not secrets.compare_digest(state.encode(), expected.encode()):
            outcome, message = "error:state", "Sign-in failed: the response did not match."
        elif "error" in params:
            outcome = f"error:{_safe_code(params['error'][0])}"
            message = "Sign-in was not completed."
        elif params.get("code", [""])[0]:
            outcome = "code:" + params["code"][0]
            message = "Authorization received. Return to Necropsy to finish signing in."
        else:
            outcome, message = "error:missing-code", "Sign-in failed: no code was returned."
        self.server.result.setdefault("outcome", outcome)  # type: ignore[attr-defined]
        body = _PAGE.format(message).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class CallbackListener:
    """Bound on 127.0.0.1 before the browser opens; serves one sign-in callback."""

    def __init__(self, expected_state: str, port: int = REDIRECT_PORT) -> None:
        try:
            self._server = http.server.HTTPServer((REDIRECT_HOST, port), _Handler)
        except OSError:
            raise AuthError(
                f"port {port} is in use; close the program using it and sign in again"
            ) from None
        self._server.expected_state = expected_state  # type: ignore[attr-defined]
        self._server.result = {}  # type: ignore[attr-defined]
        self._server.timeout = 1.0

    def __enter__(self) -> CallbackListener:
        return self

    def __exit__(self, *_exc: object) -> None:
        self._server.server_close()

    def wait(self, timeout_s: float = 300.0) -> str:
        result: dict[str, str] = self._server.result  # type: ignore[attr-defined]
        deadline = time.monotonic() + timeout_s
        while "outcome" not in result and time.monotonic() < deadline:
            self._server.handle_request()
        outcome = result.get("outcome")
        if outcome is None:
            raise AuthError("timed out waiting for the browser sign-in")
        if outcome.startswith("code:"):
            return outcome[5:]
        raise AuthError(f"sign-in failed ({outcome[6:]})")


def wait_for_code(expected_state: str, timeout_s: float = 300.0, port: int = REDIRECT_PORT) -> str:
    """Bind, then serve one callback and return the authorization code."""
    with CallbackListener(expected_state, port) as listener:
        return listener.wait(timeout_s)


def new_state() -> str:
    return secrets.token_urlsafe(24)


__all__ = [
    "CLIENT_ID_ENV",
    "OAUTH_ERRORS",
    "REDIRECT_URI",
    "Auth",
    "AuthError",
    "AuthState",
    "CallbackListener",
    "ClientRecord",
    "LoginNeeded",
    "Token",
    "new_state",
    "wait_for_code",
]
