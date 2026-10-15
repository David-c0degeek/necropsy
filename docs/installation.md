# Install and open Necropsy

[Home](../README.md) · [First analysis](getting-started.md) · [Connect Warcraft Logs](warcraft-logs.md)

## One command

Run the command for your computer. It installs a private uv runtime, a managed
Python 3.14 environment and the versioned Necropsy wheel, verifies the download
checksum and installed version, creates a launcher and opens the guided TUI.
No Git, GitHub account, preinstalled Python or uv is needed. Downloads are public.
You need an internet connection, a terminal and a normal desktop session.

**Windows (PowerShell)**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.ps1 | iex"
```

**macOS (Terminal)**

```sh
curl -fsSL https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.sh | sh
```

**Linux desktop (curl or wget is selected automatically)**

```sh
sh -c 'u=https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.sh; if command -v curl >/dev/null; then curl -fsSL "$u"; else wget -qO- "$u"; fi' | sh
```

Linux desktops need at least one standard HTTPS downloader (curl or wget).
A stripped-down/headless system may require its package manager to provide one;
there is no portable way for a shell without any downloader to fetch an installer.
The app and Python dependencies install per-user and need no administrator rights.

## Next time

| Computer | Open Necropsy |
|---|---|
| Windows | Desktop or Start menu **Necropsy** shortcut |
| macOS | `Applications/Necropsy.command` in your home folder |
| Linux desktop | **Necropsy** in your applications menu |
| Any supported terminal | `necropsy` (in a new terminal after setup) |

The first launch needs no shell restart: setup opens the app directly.
Tab moves between controls; Enter activates a control; the mouse also works.
Ctrl+C stops and saves an active operation. Ctrl+Q saves/stops and quits.
An in-flight network request can take up to 30 seconds to stop. Report generation
may finish its current offline stage before stopping. Closing the terminal
abruptly still retains requests already checkpointed to disk.

## Sign in and analyze

Paste your character link, choose **Find my character** and authorize Necropsy
in your browser. Return to the app, choose a spec and **Analyze my character**.
The app checks the observed faction and offers a partition choice only when WCL
needs one. It uses the user endpoint automatically. Tokens stay in your OS vault.
The report opens automatically; **Open report** opens it again later.

An unlocked OS password vault is required: Windows Credential Manager, macOS
Keychain, or a desktop Secret Service/KWallet on Linux. Linux needs a running
user D-Bus/password-wallet session; a bare server or locked/unavailable vault
cannot securely save a sign-in. Necropsy explains this in the app and never
falls back to plaintext credentials. An OS vault prompt is part of sign-in.

## Saved analyses and automatic continuation

**Your saved analyses** shows prior runs and their status. Select a run to
**Continue analysis** or **Open report**. Add an analysis saved elsewhere using
**Find an older analysis saved elsewhere** and its containing folder. CLI runs
with `.necropsy-run/run.json` can resume in place. Older live runs recover completed
cached streams into a new run, preserving the old report/snapshots.

Quota exhaustion saves the current request/page checkpoint and displays a
countdown. The app sleeps and retries after WCL's observed reset, repeating as
needed until done or stopped. Partial coverage caused by inaccessible/missing
logs finishes with coverage notes; it does not trigger endless quota retries.
A subscription is not needed to retain progress across hourly resets; private
or subscription-gated archived reports still require WCL permission.

Data lives in your per-user application-data folder: `%LOCALAPPDATA%\Necropsy`
on Windows, `~/Library/Application Support/Necropsy` on macOS, and
`$XDG_DATA_HOME/Necropsy` (usually `~/.local/share/Necropsy`) on Linux. The
`runs` folder holds sessions, snapshots, reports and `.necropsy-run` checkpoints.
Keep the cache and run folder together for continuation. Existing
`~/necropsy/wcl-cache` is reused when present; older runs under `~/necropsy` are
automatically listed by the default app. Reports may contain player identities.

## Updates and older versions

Run the same install command again to update. The installer switches the launcher
only after the new environment starts successfully. A failed download or checksum
check preserves the previous launcher, sign-in and saved analyses. Existing HTML
pages keep their original design until regenerated from their snapshot/JSON.

Version 0.1.0 predates the redesigned report. Version 0.1.1 added progress and
CLI checkpoints and was built locally. Version 0.2.0 adds the guided app and
cross-platform bootstrap. See [releases](https://github.com/David-c0degeek/necropsy/releases)
for published artifacts; historical release receipts describe their own versions.

## Advanced CLI and contributor installation

The guided app is the default; `necropsy tui` opens it explicitly. All advanced
commands remain available through `necropsy --help`. Scripted `analyze` still
uses explicit `--cache`, `--out` and `--endpoint user`; after a quota stop repeat
with `--resume`. Its optional `--wait-for-reset` permits one bounded wait per
invocation. The TUI supervisor supports repeated quota windows.

From a checkout:

```sh
uv sync --locked
uv run necropsy
```

Build a wheel with `uv build`. Manual wheel users can use
`uv tool install --force --python 3.14 dist/necropsy-0.2.0-py3-none-any.whl`.
This path assumes uv exists; it is not the normal first-time install path.
Saved snapshots replay offline with `necropsy offline SNAPSHOT.zip --out FOLDER`.
Rendering existing JSON uses `necropsy render analysis.json --out FOLDER`.

## Verification and removal

Automation verifies the TUI, bootstrap/private runtime, installed version,
checksum refusal, preservation of the launcher after a failed upgrade, offline
report generation and current embedded assets. Real WCL account/vault validation
is recorded separately in [live validation](live-validation.md); synthetic tests
and CI do not certify every desktop/password-wallet configuration.

For maintainers:

```sh
uv run python scripts/build_release.py --out workspace/release
uv run python scripts/check_bootstrap.py --bundle workspace/release --receipt workspace/bootstrap.json
uv run python scripts/check_distribution.py --dist workspace/release --snapshot tests/fixtures/haplina_naxx_subset.zip --receipt workspace/distribution.json
```

Before uninstalling, use `necropsy auth logout --forget-secret` to remove the
active saved sign-in. Other saved personal clients/modes need their own logout.
The bootstrap installs into a per-user app directory, not uv's global tool list.
Remove its app directory and launcher/shortcuts to uninstall; retain the separate
run/cache data if you want to keep reports. A manual `uv tool install` is removed
with `uv tool uninstall necropsy`. Local logout/uninstall does not revoke WCL's
server-side browser grant.
