# Install the local CLI

[Documentation](README.md) · [Sign in](warcraft-logs.md) · [Live acceptance](live-acceptance.md)

The Python wheel is an installable CLI, including all class rules and report
templates/assets. It requires Python **3.14 or newer**. Windows is the first
supported release target. Version0.1.0 is available through the private
[GitHub release](https://github.com/David-c0degeek/necropsy/releases/tag/v0.1.0)
to authorized collaborators; no PyPI availability is claimed. The product owner
confirmed an independent account/machine test passed and approved publication. The platform evidence is:

| Platform | Installation evidence | Real credential store / public account |
|---|---|---|
| Windows | Clean Python 3.14.6 wheel install, public mock flow and offline replay | WinVault, public sign-in/callback, refresh rotation and query access observed; independent account/machine acceptance confirmed by product owner |
| Linux (Ubuntu CI) | Installed wheel, public mock flow and offline replay passed | Real desktop credential store and user-account flow unverified; no end-user support claim |
| macOS | Unverified | Unverified |

## Install and run

Download the wheel and SHA256SUMS from the release above. Compare its
digest before installation, for example in PowerShell:

```powershell
Get-FileHash .\necropsy-0.1.0-py3-none-any.whl -Algorithm SHA256
uv tool install --python 3.14 .\necropsy-0.1.0-py3-none-any.whl
necropsy --version
necropsy auth login
necropsy auth status --check
necropsy resolve "YOUR_CHARACTER_URL" --endpoint user
necropsy analyze "YOUR_CHARACTER_URL" --endpoint user --cache .\wcl-cache --out .\analysis
```

The package includes Necropsy's registered public client ID. `auth login` uses it
automatically. For another app registration, override with `--client-id` or
`NECROPSY_WCL_CLIENT_ID`. [Live validation](live-validation.md) records the
registered callback and account-specific query/refresh observations.
The ID identifies the app; your browser authorization identifies your account.
Public login never asks for a shared secret. If it is cancelled or rejected, the
previous successful sign-in stays selected. Keep the terminal open during login.

The default API endpoint remains `client` for compatibility with personal
clients. Public sign-in always requires explicit `--endpoint user`. An incorrect
choice fails before an API request; Necropsy never silently switches endpoints.
Public login is the default; owners of confidential personal clients instead use
`necropsy auth login --mode personal --client-id YOUR_PERSONAL_CLIENT_ID`.

For a saved supported snapshot, no login or network is needed:

```powershell
necropsy offline .\snapshot.zip --out .\offline-analysis
```

Open `report.html` and `playbook.html` under the output directory. `analysis.json`
and the shareable ZIP retain evidence and coverage limits. Raw logs, snapshots,
caches and generated reports can contain player identities; keep them private
unless their owners authorize sharing. They are not included in the CLI wheel.

## Recovery and removal

- Expired access refreshes using the saved refresh token when issued. Without a
  refresh token, or if WCL rejects it, run `auth login` again. Refresh rotation
  is saved through the OS store. WCL's actual public-client refresh behavior
  has an observed Windows receipt; other accounts retain their own permissions.
- HTTP 401: sign in again. HTTP 403: verify account access, report privacy and
  archive subscription. The CLI keeps the requested endpoint. It cannot grant
  permissions your WCL account lacks.
- Quota stop: retain the cache and retry into a fresh output directory after the
  observed hourly reset, or explicitly allow one bounded `--wait-for-reset` wait.
  Exit 4 means partial output; read the coverage notes before using advice.
- Port 8765 in use: close the conflicting application and retry. Without a
  browser launch, use `auth login --no-browser` and open the printed URL on the
  same computer. Incorrect state or denied authorization requires a new attempt.
- An unavailable/unapproved credential store is an error. No plaintext fallback
  exists. Only Windows WinVault has current real-store evidence.
- Upgrade from a newly reviewed wheel with
  `uv tool install --force --python 3.14 .\necropsy-VERSION-py3-none-any.whl`.
  Keep raw snapshots; use fresh result directories. Before downgrading to a
  version without PKCE support, select your personal client again with
  `auth login --mode personal`.
- Run `necropsy auth logout --forget-secret` **before**
  `uv tool uninstall necropsy`. This removes the active mode/client record and
  selection. Other saved clients/modes require separate logout. Normal logout
  removes only the active user tokens; personal client secrets remain available.
  Local logout is not server revocation: revoke app access in WCL account settings
  if required. Uninstall leaves your caches, snapshots and reports for you to keep
  or remove deliberately.

## Build verification for contributors

```powershell
uv build
uv run python scripts/check_distribution.py --snapshot tests/fixtures/haplina_naxx_subset.zip --receipt workspace/distribution-check.json --probe-os-store
```

The script scans every extracted wheel/sdist member with the installed gitleaks
tool (unlimited member size), creates a temporary clean environment outside the
checkout, installs the wheel, exercises the entry point and synthetic public
CLI/user API flow, and replays the supplied snapshot. `--probe-os-store` writes
and removes synthetic chunked values under a unique temporary OS-store service;
it never reads or modifies your saved WCL credentials. Omit the flag on machines
without an approved credential backend. The receipt records skipped probes and
does not certify live WCL access or another person/machine.

Keep only the current wheel/sdist pair in `dist` for the command. Installation
can fetch dependencies; subsequent offline replay does not. The built artifacts
exclude tests, private fixtures, workspace, caches and plans. Package metadata uses PACKAGE.md with generic installed commands; repository
samples and player-specific references are excluded. Repository documentation
is intentionally not bundled in the minimal sdist. A clean heuristic scan is a gate, not proof that no secret exists.
