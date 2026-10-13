# Sign in to Warcraft Logs

[Home](../README.md) · [Documentation](README.md) · [Getting started](getting-started.md)

Necropsy can sign in, resolve a Warcraft Logs character URL, and acquire a snapshot
for a report and playbook. The CLI flow is verified with synthetic responses;
authenticated live validation remains pending. The [offline sample](getting-started.md)
already produces a report and playbook without signing in.

The current connection supports **Classic Era on `vanilla.warcraftlogs.com`**
and the Naxxramas context. Other Warcraft Logs game sites are recognized and
refused with an explanation before Necropsy accesses saved credentials.

For storage, token lifecycle and distribution limits, see
[Authentication boundaries](auth.md).

## Set up your personal API client

This sign-in flow uses your own confidential Warcraft Logs API client on your
own computer. In your Warcraft Logs API client settings, register this exact
redirect URL:

```text
http://localhost:8765/callback
```

Keep your client ID and client secret available. The ID identifies the client;
the secret is entered at a hidden prompt. Follow the
[Warcraft Logs API documentation](https://www.warcraftlogs.com/api/docs)
for client setup. The current confidential-client flow is for personal use;
a distributed application needs a public-client flow with PKCE first.

## Sign in

From the repository root:

```sh
uv run necropsy auth login
```

On your first sign-in, enter your client ID and secret when prompted. Necropsy
opens the authorization page in your browser and waits up to five minutes.
After you authorize access, the browser asks you to return to Necropsy.
The terminal confirms success once the token is received and saved:

```text
Signed in to vanilla.warcraftlogs.com; token valid until … UTC.
```

Your client secret and sign-in token are saved in your operating system's
credential store: Windows Credential Locker, macOS Keychain, Secret Service,
or KWallet. Necropsy selects one approved store and uses it directly.
It does not fall back to a credentials file or print the token.

Subsequent sign-ins reuse the saved client ID and secret. To enter a replacement
secret, use:

```sh
uv run necropsy auth login --new-secret
```

The replacement is retained only when sign-in succeeds. A cancelled sign-in
or failed token exchange preserves the previous working credentials.
To switch clients, add `--client-id YOUR_CLIENT_ID`; the secret is still prompted
for privately. The client ID can also come from `NECROPSY_WCL_CLIENT_ID`.
Selection order is the command option, environment variable, saved ID, then prompt.

If the browser does not open automatically, run `auth login --no-browser` and
open the printed URL yourself on the same computer. Keep the terminal running
while you authorize access.

## Check the connection

```sh
uv run necropsy auth status
```

This checks saved state locally and shows the selected credential store,
whether a client ID is set, the sign-in state, and token expiry. It does not
prove the API is reachable. To make a WCL request and see the current hourly
points budget:

```sh
uv run necropsy auth status --check
```

That request uses your user token and can refresh it when needed. If refresh
is unavailable or rejected, sign in again. Budget figures describe the API's
current account reading, rather than an exact cost for a future analysis.

## Resolve a character URL

```sh
uv run necropsy resolve "https://vanilla.warcraftlogs.com/character/eu/REALM/CHARACTER"
```

Replace `REALM` and `CHARACTER` with the values in your WCL character URL.
An ID URL, such as `https://vanilla.warcraftlogs.com/character/id/12345`, is also
accepted. Resolution shows the character, server, region, faction, zone, and
partition. Use `analyze` below to acquire fights and build the pages.

If several partitions are possible, the command lists the choices and exits
with status 2. Repeat with the ID you want:

```sh
uv run necropsy resolve "YOUR_CHARACTER_URL" --partition 1
```

Faction remains **unknown** when the returned name cannot be reliably
identified. Necropsy keeps that uncertainty rather than guessing a faction
from an API ID. Same-faction acquisition cannot use an unknown faction.

## Acquire an analysis

After signing in, run:

```sh
uv run necropsy analyze "YOUR_CHARACTER_URL" --cache workspace/wcl-cache --out workspace/my-run
```

Both directories can be created by the command. Reuse the cache across runs;
choose an output directory without earlier analysis files or snapshots. The
command refuses existing results before accessing credentials or making requests.
It also refuses paths through symlinks or junctions and prevents simultaneous
`analyze` runs in one output directory. The offline and render commands retain
their existing replacement behavior.

If several partitions are possible, read the listed choices and repeat with
`--partition ID`. Only an observed faction and Hunter character are supported.
Every request uses `--endpoint client` by default; `--endpoint user` selects the
user API for the whole run. Permission failures never switch endpoints.

Acquisition seeks five verified same-faction event samples and up to 25 metadata
entries per boss. Metadata-only rows are context, not extra event samples.
`--cross-faction` adds the verified other-faction overall #1 as separate context;
it does not replace the same-faction baseline. `--no-package` skips the shareable
ZIP. `--name STEM` names the raw snapshot without its extensions; the default
uses the character, zone and UTC time.

Results include `analysis.json`, `report.html`, `playbook.html`, the optional
package, and `snapshot/STEM.zip` with its `.entries` and `.sha256` companions.
Read **Live acquisition coverage** in either page before interpreting results.
An overall #1 comparison stays unknown when that fight was not acquired.
The points summary describes an account-wide change between observed readings;
it can include other activity and stays unknown when the accounting period
cannot be established.

| Exit status | Result and next step |
|---|---|
| `0` | Report written with complete requested acquisition coverage |
| `4` | Report written with partial coverage; inspect the boss coverage notes |
| `2` | A partition choice is needed; repeat with one of the listed IDs |
| `3` | Finalization stopped before a snapshot or report was written; fetched data remains in the cache for a later run |
| `1` | Input, authentication, acquisition or output failure; follow the printed error |

A report with complete acquisition coverage can still contain unknown analysis
values. If report generation fails after saving the snapshot, the command prints
its path and an offline recovery command. Keep the snapshot and its manifest
together. Replaying it requires no WCL credentials or network access; the pages
do not update their rankings while you read them.

## Sign out

```sh
uv run necropsy auth logout
```

This removes the selected client's saved user token and keeps its client
secret for your next sign-in. To remove that client's record and saved ID too:

```sh
uv run necropsy auth logout --forget-secret
```

These commands affect the selected client. An environment override selects
the client it names; credentials previously saved for other client IDs are
separate records.

## When sign-in needs attention

| What you see | What to do |
|---|---|
| No approved credential store | Enable an OS credential store supported above, then retry; Necropsy will not use a file fallback |
| Several approved stores | Set `NECROPSY_KEYRING_BACKEND` to one of the exact backend names printed by the error |
| Credential store could not read, save, or remove a value | Unlock or repair access to the selected OS store, then retry; a removal failure is reported instead of claiming success |
| Port 8765 is in use | Close the application using the local callback port, then sign in again |
| Sign-in timed out or access was denied | Keep Necropsy running, retry, and finish authorization in the browser |
| `invalid_client` | Check the client ID and use `--new-secret` to re-enter the matching secret |
| `invalid_grant` or login needed | Run `auth login` again |
| Unsupported site | Use a Classic Era character URL on `vanilla.warcraftlogs.com`; fresh and other game families are not supported yet |

[Return to the offline workflow →](getting-started.md)
