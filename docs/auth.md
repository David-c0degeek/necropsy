# Authentication boundaries

[Home](../README.md) · [Documentation](README.md) · [Sign-in guide](warcraft-logs.md)

**The current connection is for personal use with your own confidential WCL
client. A distributed application requires a public-client flow with PKCE before
distribution.** That flow is deferred; it is not implemented by the current CLI.

For client setup, the callback URI, sign-in commands and troubleshooting, follow
the [Warcraft Logs guide](warcraft-logs.md). This page describes what the local
implementation stores and which boundaries it enforces. Authentication logic has
synthetic tests; authenticated live acquisition and real credential-store
acceptance remain pending.

## Credentials and tokens

Necropsy selects exactly one approved operating-system credential backend:
Windows Credential Locker, macOS Keychain, Secret Service or KWallet. Selection
uses the concrete backend class. Reads, writes and deletes go directly to that
instance, rather than through a chaining facade. File, plaintext, null and
unrecognized backends are refused. There is no credentials-file fallback.

The confidential client secret and user-token state share one record per client
ID. Values are chunked under a fresh generation, with the head pointer written
last; a failed write preserves the previous readable generation. Sign-in stages
new credentials until token exchange succeeds. A cancelled or failed sign-in
preserves the previous working record.

The user API uses the saved user access token. An expired token is refreshed when
a refresh token is available. A rotated refresh token replaces the previous one;
an omitted refresh token keeps it. Without a usable sign-in or refresh, the CLI
asks for sign-in again. The client API obtains a client-credentials token from the
saved client record and keeps that token in memory only.

Tokens and secrets are excluded from normal output and representations.
Credential-backend failures use fixed messages rather than printing backend
exception text. The client ID is an identifier, not a secret, and may be selected
through the command option, environment, saved ID or prompt.

## Local sign-in and request boundaries

The registered callback is `http://localhost:8765/callback`. The listener is bound
before the authorization browser opens, checks the returned state and has a
bounded wait. The secret prompt is hidden. Sign-out removes the selected client's
user-token state; `--forget-secret` also removes that client's record and saved
selection. Other client records remain separate.

Supported character URLs use HTTPS and the allowed Warcraft Logs host/path
formats. Acquisition currently supports Classic Era on
`vanilla.warcraftlogs.com`. `analyze` validates its inputs and refuses earlier
outputs before accessing credentials. One endpoint serves the whole acquisition:
`client` by default, or `user` when selected. Permission errors do not switch the
endpoint. HTTP requests do not automatically follow redirects.

Saved snapshot analysis and HTML rendering need no WCL credentials or network.
The acquisition cache contains API data and provenance, not authentication state.
Fetched logs and exported results can still contain player information.

## Implementation references

- [Credential backend selection and generation writes](../src/necropsy/wcl/credentials.py)
- [Client records, token refresh and callback handling](../src/necropsy/wcl/auth.py)
- [Sign-in and acquisition commands](../src/necropsy/wcl/cli.py)
- [HTTP client](../src/necropsy/wcl/client.py), [URL parsing](../src/necropsy/wcl/urls.py)
- [Authentication decision](decisions/0001-personal-authentication.md)

