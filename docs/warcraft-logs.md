# Sign in to Warcraft Logs

[Home](../README.md) · [Documentation](README.md) · [Getting started](getting-started.md)

Necropsy can sign in, resolve a Warcraft Logs character URL, and acquire a snapshot
for a report and playbook. The CLI flow has synthetic tests and an observed signed-in Windows run with
explicit partial pet coverage; see [live validation](live-validation.md). The [offline sample](getting-started.md)
already produces a report and playbook without signing in.

The current connection supports **Classic Era on `vanilla.warcraftlogs.com`**
for Naxxramas, AQ40, BWL and Molten Core. Choose one raid for each analysis.
See [raid support and validation](raids.md). Other Warcraft Logs game sites are recognized and
refused with an explanation before Necropsy accesses saved credentials.

For storage, token lifecycle and distribution limits, see
[Authentication boundaries](auth.md).

## Guided sign-in and recovery

Open **Necropsy**, paste your character link and choose **Find my character**.
Sign in in your browser when prompted. The user endpoint, cache and output
folder are selected for you. Choose a spec and **Analyze my character**.

The app saves each successful request/page. Hourly quota exhaustion shows a
countdown and sleeps until it can automatically continue. **Stop and save**
returns you to your saved runs; select one and **Continue analysis** later.
Missing permissions/archived data finish with coverage notes rather than waiting
indefinitely. **Open report** needs no connection. See [first analysis](getting-started.md).

The commands below are for advanced CLI users and application maintainers.

## What needs a connection?

Sign-in, character resolution and acquisition contact Warcraft Logs. Acquisition
saves the selected fights, ranking context and coverage as a snapshot. The
resulting Playbook and Report are **saved analyses**, not live dashboards.

Opening the HTML, changing theme, reviewing bosses, inspecting evidence and
printing make no automatic network requests. WCL and source-document links go
online only when followed. To refresh rankings or acquire missing evidence,
start a new analysis or continue an incomplete saved run; reopening the HTML
does not fetch anything.

Start with the overview's **How complete is this analysis?** disclosure. A
coverage warning can coexist with usable findings. Requested-boss acquisition
status and source-specific limitations remain in the detailed coverage sections.

## Public application sign-in

For an installed CLI, follow [installation](installation.md). The application
owner creates a separate public Necropsy client in [WCL client management](https://www.warcraftlogs.com/api/clients),
registering exactly `http://localhost:8765/callback` and enabling the public-client
option. Keep confidential personal clients separate. The registered public client is included; normal users do not register an
application or enter an API secret. Account permissions remain WCL's decision.

```sh
uv run necropsy auth login
```

Necropsy includes its registered public client ID. Override it with `--client-id`
or `NECROPSY_WCL_CLIENT_ID` only when intentionally using a different registration.
It never prompts for a secret in public mode. Your own browser authorization
permits account access; the application ID alone does not authorize a user.

The listener binds loopback before the browser opens. Authorize within five
minutes, then return to the terminal. `--no-browser` prints the URL for manual
opening on the same machine. Wrong state, denied access, expired/consumed attempts
and token failures preserve the previous selected sign-in. Retry with a fresh
login; do not reuse a callback code.

Tokens live only in one approved OS credential store, with no file fallback.
The one exception is an explicit opt-in for unattended POSIX servers, described
below. `auth status` shows the active mode. A received refresh token is reused/rotated;
without one, sign in again at expiry. Public refresh rotation and representative
current/archived query access are observed on Windows; see
[live validation](live-validation.md). Permissions remain account-specific.

## Personal confidential client compatibility

For your own existing confidential client, register the same callback and use:

```sh
uv run necropsy auth login --mode personal --client-id YOUR_PERSONAL_CLIENT_ID
uv run necropsy auth login --mode personal --new-secret
```

Personal mode alone prompts privately for a missing/replacement secret. Existing
personal records remain readable and separate from public-mode records, including
when both use the same client ID. New credentials save only after exchange
succeeds. Client selection uses the option, environment, packaged public ID
(public mode only), saved selection of the same mode, then a prompt.

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
uv run necropsy resolve "https://vanilla.warcraftlogs.com/character/eu/REALM/CHARACTER" --endpoint user
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

Race availability differs by game. During Classic Era validation on 2026-10-14,
the Character API exposed `gameData`, but Haplina's response returned
`This game does not support cached game data.` The saved report/player-details
payloads also contained no race field. Necropsy therefore names race from an
observed racial cast; absence of a cast does not identify a race. This limitation
does not imply the same API behavior for other Warcraft Logs game sites.

Overall-#1 DPS uses an acquired event calculation when available; otherwise it
can show an observed scalar from the verified saved leaderboard. That scalar is
metadata-only context, never a member of the same-faction event sample or its
medians. Its source and capture time are shown; older captures explicitly say
when the time was not recorded. Missing or invalid evidence stays unknown.
Use `--cross-faction` with a fresh output directory to request separately verified
event context. Permission or identity failures can still leave it unavailable.

After signing in, run:

```sh
uv run necropsy analyze "YOUR_CHARACTER_URL" --endpoint user --cache workspace/wcl-cache --out workspace/my-run
```

Add `--wait-for-reset` to allow one wait based on an observed hourly reset,
at most one hour, while retaining the acquisition in memory. The default stops
without waiting. Successful API requests are checkpointed to disk, including
event pages from incomplete streams. A second budget stop ends normally. Cancellation interrupts the wait. The output
lock remains held, and a wait inside an event fetch can also hold that stream's
lock. A second run using the same output or locked stream is refused.

Both directories can be created by the command. Reuse the cache across runs;
choose an output directory without earlier analysis files or snapshots for a new
analysis. After a quota reset or interruption, repeat the command with `--resume`
and the same output directory. Keep `.necropsy-run` alongside the outputs. Saved
spec/faction choices are restored and completed requests cost no new API points.
Finalization is separate from acquisition: each report is verified once for its
exact fight set, with successfully finalized answers retained across attempts.
On resume, complete saved entries are finalized before new acquisition spends
more points. That preliminary acquisition pass reads only saved requests; a
missing request stops the pass locally. Normal acquisition then continues,
followed by finalization of its exact report/fight sets. A partial comparison
cohort remains partial even when its available data can now be written.
A report revision change discards that report's saved requests before retrying.
Snapshots from earlier attempts are preserved. Resume validates options and
owned output digests before credentials are accessed; unrelated/modified files
are refused. Pre-0.1.1 runs have no checkpoint: retain their cache and choose a
fresh output directory once to start the new resumable run.

For unattended runners, `--outcome-json PATH` also writes a small JSON file
after the run, whatever its result. It keeps the native exit code and adds a
`stop_class`: `none` (complete), `source-limit` (a finished report with
incomplete source data, no stop), `quota-reset` or `quota-reserve` (stopped
for points; resume after `reset_at_utc` when it is known), `refused` (this
character or option set can't be analysed as asked), `auth` (sign-in
problem), `transient` (server or rate trouble), `interrupted` or `error`. It
also records the snapshot path and SHA-256 when one was written, including a
saved snapshot whose report then failed (an `error` that can be finished with
`necropsy offline`), the number of incomplete bosses, and the SHA-256 of the run
checkpoint. A quota stop while resolving the character is also `quota-reset`.
Failing to write the outcome file only prints a warning; it never changes the
command's own result. An unknown reset time
is `null`, never a guess. A missing outcome file means the runner must treat
the run as needing attention.
It also refuses paths through symlinks or junctions and prevents simultaneous
`analyze` runs in one output directory. The offline and render commands retain
their existing replacement behavior.

If several partitions are possible, read the listed choices and repeat with
`--partition ID`. An observed faction and a supported Classic Era class/category are required.
Every request uses `--endpoint client` by default; `--endpoint user` selects the
user API for the whole run. Permission failures never switch endpoints.

Archived report content requires user authentication with archive access.
When the selected endpoint cannot read an archived candidate, it is recorded as
inaccessible and later candidates can replace it. To deliberately use the user
API, select `--endpoint user`; Necropsy never makes that switch automatically.
Anonymized report identifiers are currently unsupported for identity-verified
acquisition. They stay visible as inaccessible candidates and do not become
deep samples; later eligible candidates can replace them.
[WCL archive-status schema](https://ru.warcraftlogs.com/v2-api-docs/warcraft/reportarchivestatus.doc.html).

Cache format 2 separates endpoint streams and preserves report metadata as exact
content generations. If an older cache is refused, choose a new `--cache` path;
retain the old directory and any saved snapshots. Do not edit its format marker
to make it appear compatible. Saved snapshots can still be analyzed offline.

Acquisition seeks five verified same-faction event samples and up to 25 metadata
entries per boss. Metadata-only rows are context, not extra event samples.
`--cross-faction` adds the verified other-faction overall #1 as separate context;
it does not replace the same-faction baseline. `--no-package` skips the shareable
ZIP. `--name STEM` names the raw snapshot without its extensions; the default
uses the character, zone and UTC time.

Results include `analysis.json`, `report.html`, `playbook.html`, the optional
package, and `snapshot/STEM.zip` with its `.entries` and `.sha256` companions.
Read **Live acquisition coverage** in either page before interpreting results.
Overall #1 DPS can use verified saved leaderboard metadata without an acquired
event sample; detailed event comparisons still require acquired evidence.
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

## Verify a live acquisition

For an explicit authenticated acquisition check, follow the
[manual live procedure](live-acceptance.md). It verifies saved artifacts and
records coverage and optional historical comparisons; its offline tests do not
complete live acceptance.

## Unattended server credential file

An unattended Linux server without an OS credential store can use one private
file instead ([ADR 0023](decisions/0023-unattended-credential-file.md)). This
is never a fallback: it applies only when `NECROPSY_CREDENTIAL_FILE` names the
file, and setting `NECROPSY_KEYRING_BACKEND` as well is an error. The file
must be a regular file (not a link), mode exactly `0600`, in a directory with
mode `0700`, and both must belong to the user running Necropsy. Anything else
is refused.

Sign in on your own computer, then send the selected sign-in straight to the
server, where `auth import` reads and checks all of it before replacing the
file:

```sh
uv run necropsy auth export | ssh server 'NECROPSY_CREDENTIAL_FILE=/path/to/secrets/credentials.json necropsy auth import'
```

`auth export` refuses to write to a terminal, because its output includes the
refresh token. It exports the sign-in that is in effect, including a client ID
override, as a selection that needs no override on the server. `auth import`
keeps the existing file when the input is empty, cut short or not exactly one
complete sign-in.

The server rewrites the file whenever the token is refreshed. If that write
fails, the command fails rather than continuing with an old token. A failure
after the new file is already in place can leave either the old or the new
sign-in on disk; sign in and export again if later commands report an invalid
sign-in.

Export copies a refresh token that Warcraft Logs may rotate on use. Don't let
your computer and the server refresh the same exported sign-in while a server
run is active: treat the server as its only user until that run stops. If
either copy stops working, sign in again on your computer and export again.

## Sign out of the selected client

```sh
uv run necropsy auth logout
```

This removes the selected mode/client's saved user tokens. Personal mode keeps
its confidential secret for your next sign-in; public mode has no secret. To remove that client's record and saved ID too:

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

## Druid categories

Live acquisition also accepts Classic Era Druids with explicit `--category Balance`, `Feral`, `Guardian` or `Restoration`. Restoration queries HPS; Guardian remains a DPS ranking category and never a tank-quality score. Rows and actor class are checked throughout finalization and snapshot readback. Missing category asks for a choice before acquisition. See [Druid analysis](druid-analysis.md).

`--category Balance --metric hps` selects a Balance-category healing performance.
The selected ranking metric is preserved separately from build and observed duty.

`--spec Tank` selects the Guardian category and requires evidenced tank duty for
personal grading. `--spec Balance` selects the Balance view. Personal fights are
collected across bosses before deep comparison samples in multi-boss Druid runs;
comparison gaps remain explicit when the finalization reserve stops acquisition.

### Faction comparison lists

Interactive character lookup asks for faction and spec. Pass `--faction Alliance`
or `Horde` and `--spec Balance`, `Feral`, `Tank`, `Restoration` or Hunter
`Marksmanship` in scripts. The faction is checked against the resolved character;
it never silently changes the character's identity. The spec prompt's `all`
default retains the legacy Hunter all-spec lookup. Current supported analyzers
include all nine Classic Era classes; the same faction/spec display contract applies to future
class plugins without inventing unsupported class analysis.

The main comparison cohort is your faction. Ranking requests select class and,
for Druids, spec and metric. The authenticated Classic Era Encounter API schema
does not expose a dedicated faction argument. Live probes of `faction=1`/`2`
and dot variants in the advanced filter returned identical mixed-faction rows;
Necropsy does not claim those strings enforce a faction filter. It selects
same-faction candidates locally **before deep report acquisition**: known
other-faction guild rows are skipped, while guildless/unknown candidates and
selected deep entries retain their report faction checks. Guild faction remains
an inference, separately labelled from observed character faction. Global #1 is
separate context, and a best recorded same-faction source is not automatically
claimed as faction rank #1 when earlier identities are unresolved.

Multi-boss selected-spec views collect personal encounters, then first-page ranking
references across the raid before deep examples. One or two acquired event
sources still provide individual comparisons, with limited-sample labels.

Supported class/category choices and role aliases are listed in [class analysis](class-analysis.md). Non-Hunter selected categories retain metric/class/spec/role identity through acquisition and snapshot replay; healer queries use HPS, with ranking scores separate from event throughput.

Public PKCE users must include `--endpoint user` on every `analyze` and `resolve`
command. The default `client` route is retained for confidential personal clients;
permission/expiry errors never trigger endpoint fallback. See
[installation and recovery](installation.md) for upgrade, logout and uninstall.

Era Naxxramas/MC/BWL/AQ40 partitions1/2 collect unrestricted whole-fight and filtered
critical-damage streams alongside selected player/pet directions. These extra
pages use the same quota reserve, cache, endpoint, revision checks and resume
journal. A quota stop retains reusable pages without claiming incomplete
encounter context is complete. Resume creates a new immutable snapshot and
preserves the previous archive. Other partitions keep actor-only collection.
Naxxramas uses the complete fight data for selected actor target observations,
avoiding separate target requests; its new archives use format 3 and require
the compatible reader shipped in 0.7.0. MC/BWL/AQ40 retain format 2.
Existing saved analyses can still be opened without new requests. Avoiding
duplicate event requests does not guarantee a particular quota saving.


## Talent-tree intent and comparison categories

Use `--talent-tree` to declare a game tree independently of the WCL pool selected
by `--category` (or legacy `--spec`). For example, a Warrior can use
`--talent-tree Fury --category Protection` for Tank comparisons, and a Mage can
use `--talent-tree Arcane --category Frost`. These combinations record intent;
they do not assert observed talents or reproduce WCL's classifier.

The declaration is retained in saved runs and snapshots and reused by `--resume`.
Changing it on a resume is refused like other run options. Existing checkpoints
without it remain supported. Reports show the broader WCL category scope and
per-fight recorded evidence. See [class selection](class-analysis.md).
