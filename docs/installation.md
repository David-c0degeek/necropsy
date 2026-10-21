# Install and open Necropsy

[Home](../README.md) · [First analysis](getting-started.md) · [Connect Warcraft Logs](warcraft-logs.md)

The installers below open the graphical app by default. The [desktop guide](desktop.md)
describes its controls; `necropsy tui` opens the optional terminal interface.

## One command

Run the command for your computer. It installs a private uv runtime, a managed
Python 3.14 environment, the CLI wheel and a native graphical package. It verifies
both download checksums and the GUI/engine version before switching the launcher,
then opens the GUI. Windows x64, Intel/Apple Silicon macOS and Linux x64 are supported.
Windows setup also checks for WebView2 and, if absent, verifies and runs
Microsoft's signed Evergreen bootstrapper. Existing WebView2 installations are reused.
No Git, GitHub account, preinstalled Python or uv is needed. Downloads are public.
You need an internet connection, a terminal and a normal desktop session.

**Windows** — press Start, type **PowerShell** and open it. Paste and press Enter.

```powershell
& { $ErrorActionPreference = 'Stop'; $setup = Join-Path $env:TEMP ('necropsy-setup-' + [guid]::NewGuid() + '.ps1'); Invoke-WebRequest -UseBasicParsing https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.ps1 -OutFile $setup -ErrorAction Stop; powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $setup; if ($LASTEXITCODE -ne 0) { throw 'Necropsy setup failed. See the message above.' } }
```

**macOS** — press Command+Space, type **Terminal** and open it. Paste and press Return.

```sh
curl -fsSL https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.sh | sh
```

**Linux desktop** — open **Terminal** from the applications menu, paste and press Enter.
The command chooses curl or wget automatically.

```sh
sh -c 'u=https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.sh; if command -v curl >/dev/null; then curl -fsSL "$u"; else wget -qO- "$u"; fi' | sh
```

Linux desktops need at least one standard HTTPS downloader (curl or wget).
A stripped-down/headless system may require its package manager to provide one;
there is no portable way for a shell without any downloader to fetch an installer.
The app and Python dependencies install per-user and need no administrator rights.

## Windows setup errors and security alerts

The Windows command saves a uniquely named `necropsy-setup-*.ps1` in your
Windows temporary folder, then runs that file in a profile-free Windows
PowerShell process. It does not use `Invoke-Expression` or the `Bypass`
execution policy. The saved script remains available for inspection.

The previous `irm ... | iex` command has been withdrawn after a reported
`CmdletBinding` parser error and a Defender command-line detection. Use the
command above. If Defender blocks setup, leave protection enabled and record
its threat name and affected item from **Windows Security → Virus & threat
protection → Protection history**. Do not allow a detection or add an exclusion
to finish installation. Share those details in a bug report; a command-line
detection alone does not establish whether a downloaded file is malicious.

A `PSReadLine` error mentioning `PredictionViewStyle` and
`Microsoft.PowerShell_profile.ps1` comes from your existing terminal profile.
The installer child process uses `-NoProfile`; setup does not edit your profile.

## Next time

| Computer | Open Necropsy |
|---|---|
| Windows | Desktop or Start menu **Necropsy** shortcut |
| macOS | `Applications/Necropsy.app` in your home folder |
| Linux desktop | **Necropsy** in your applications menu |
| Any supported terminal | `necropsy` (in a new terminal after setup) |

The first launch needs no shell restart: setup opens the app directly.
Tab moves between controls; Enter activates a control; the mouse also works.
Choose **Stop and save** to stop an active operation. Closing the window offers
**Save and quit** while work is active. The GUI opens without a terminal window.
An in-flight network request can take up to 30 seconds to stop. Report generation
may finish its current offline stage before stopping. Closing the terminal
abruptly still retains requests already checkpointed to disk.

## Sign in and analyze

Paste your character link, choose **Find my character** and authorize Necropsy
in your browser. Return to the app, optionally declare your talent tree, choose
the WCL comparison category and **Analyze my character**.
The app checks the observed faction and offers a partition choice only when WCL
needs one. It uses the user endpoint automatically. Tokens stay in your OS vault.
The Playbook opens inside the app automatically; **Open Playbook** opens it again later.

An unlocked OS password vault is required: Windows Credential Manager, macOS
Keychain, or a desktop Secret Service/KWallet on Linux. Linux needs a running
user D-Bus/password-wallet session; a bare server or locked/unavailable vault
cannot securely save a sign-in. Necropsy explains this in the app and never
falls back to plaintext credentials. An OS vault prompt is part of sign-in.

## Saved analyses and automatic continuation

**Your analyses** shows prior runs and their status. Select a run to
**Continue analysis** or **Open Playbook**. Add an analysis saved elsewhere using
**Add folder** and its containing folder. CLI runs
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

In a desktop version with **Check for updates**, use the sidebar command and
choose **Update and restart** for an installer-managed copy. Source and portable
copies offer a release-page download. See [app updates](desktop.md#update-the-app).
Older versions need one manual update to acquire these controls.

You can also run the same install command again. The installer switches the launcher
only after the new environment starts successfully. A failed download or checksum
check preserves the previous launcher, sign-in and saved analyses. Existing HTML
pages keep their original design until refreshed. In the GUI, **Update reports**
refreshes a saved analysis's HTML and package without downloading logs or changing
its findings. Updating the app makes its current templates available.

Version 0.3.0 installs and opens the GUI by default; rerun the same command to
upgrade a terminal-only installation. Saved analyses, cache and sign-in stay in
their existing locations. Linux uses an extracted AppImage runtime, so launch
does not require FUSE. Older terminal-only versions remain available as releases.

Version 0.1.0 predates the redesigned report. Version 0.1.1 added progress and
CLI checkpoints and was built locally. Version 0.2.0 adds the guided app and
cross-platform bootstrap. See [releases](https://github.com/David-c0degeek/necropsy/releases)
for published artifacts; historical release receipts describe their own versions.

## Advanced CLI and contributor installation

The GUI is the default; `necropsy gui` opens it explicitly, and `necropsy tui`
opens the terminal interface. All advanced
commands remain available through `necropsy --help`. Scripted `analyze` still
uses explicit `--cache`, `--out` and `--endpoint user`; after a quota stop repeat
with `--resume`. Its optional `--wait-for-reset` permits one bounded wait per
invocation. The TUI supervisor supports repeated quota windows.

From a checkout:

```sh
uv sync --locked
uv run necropsy tui
```

Build a wheel with `uv build`. Manual wheel users can use
`uv tool install --force --python 3.14 dist/necropsy-0.5.2-py3-none-any.whl`.
This path assumes uv exists; it is not the normal first-time install path.
The wheel alone does not contain a GUI binary; use `necropsy tui`, or follow
the [desktop build guide](desktop.md#build-and-run-from-source).
Saved snapshots replay offline with `necropsy offline SNAPSHOT.zip --out FOLDER`.
Rendering existing JSON uses `necropsy render analysis.json --out FOLDER`.

## Verification and removal

Automation verifies the TUI, native GUI/engine readiness, bootstrap/private runtime,
installed version, checksum refusal for both packages, preservation of the
launcher and GUI pointer after a failed upgrade, offline
report generation and current embedded assets. Real WCL account/vault validation
is recorded separately in [live validation](live-validation.md); synthetic tests
and CI do not certify every desktop/password-wallet configuration.

For maintainers:

```sh
uv run python scripts/package_desktop.py --out workspace/desktop-bundle
uv run python scripts/build_release.py --out workspace/release --desktop-bundles workspace/desktop-bundle
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
