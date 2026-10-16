# Necropsy desktop

[Home](../README.md) Â· [Installation](installation.md) Â· [Architecture](architecture.md)

The desktop GUI brings character setup, saved analyses and the existing Playbook
and Report into one window. It uses the same local analysis engine, saved-run
library and operating-system password vault as the terminal app.

![Necropsy desktop with guided character setup and an offline example](images/desktop.png)

Choose a raid before finding your character. Each raid produces a separate
Report and Playbook; **Your analyses** can be filtered by raid. See
[raid modules and validation](raids.md).

## Start here

1. Open **Necropsy** and paste your Warcraft Logs character-page address.
2. Choose **Find my character**. Sign in through your normal browser if asked,
   then return to Necropsy. You never enter a WCL password into the app.
3. Choose the raid history if prompted, optionally declare your talent tree,
   choose the **WCL comparison category**, then select
   **Analyze my character**.
4. Follow the activity panel. The Playbook opens inside Necropsy when ready.

Your declared tree is saved with the run and snapshot. It does not narrow the
leaderboard: a Combat Rogue uses the WCL **DPS** category, while a Fury-heavy
Warrior can choose **Tank**. Recorded talent totals and inferred duty remain
separate per fight. See [class and category choices](class-analysis.md).

To explore without signing in, choose **Try the example**. The bundled Hunter
example contains four encounters and limited comparison data; it is a sample,
not a complete raid or a claim about other classes.

The GUI follows the Playbook's dark iron/sage theme, serif character headings,
original N mark and class accents. **Light theme** switches to the same stone
and ivory palette. Your theme and review marks stay on this computer.

## Return to an analysis

**Your analyses** lists saved runs with their status. **Open Playbook** renders
the saved analysis offline with the installed app's current templates. It does
not execute previously saved HTML. **Update reports**, available on a saved-run
row or the open report toolbar, also saves refreshed Report/Playbook HTML and the
configured ZIP package in that same analysis folder. It keeps the analytical
data, run identity, review keys and resume options unchanged; it does not fetch
logs or create another analysis. Changed owned files are refused rather than
silently overwritten, and ordinary publication/metadata failures restore the
previous outputs. Existing [output recovery](getting-started.md#output-recovery)
guidance applies to an interrupted publication.

**Continue analysis** resumes saved acquisition and may
require sign-in. Use **Add folder** for an analysis saved elsewhere, or
**Open snapshot** to analyze a saved snapshot ZIP without WCL access.

The Playbook and Report keep the established boss navigation, explanation and
evidence controls. **Export package** saves both pages, analysis data and evidence
as a shareable ZIP. Packages may contain player identities. Local review marks
are personal annotations; they are not added to exported analytical findings.

## Update the app

Choose **Check for updates** in the sidebar. Necropsy checks the latest published
stable release on GitHub and shows your installed version, the latest version
and release notes. Checks happen only when requested and do not use your WCL
credentials. Finish or stop an active analysis before checking.

For a copy installed by the one-line installer, choose **Update and restart**.
Necropsy verifies the release downloads, installs into a fresh version folder,
checks that the new GUI and engine start together, then restarts. Your analyses,
review marks and password-vault sign-in remain on this computer. Previous version
folders remain available. If installation fails, the active launcher is restored;
retry the check or inspect `last-update.log` inside the app installation folder.
If automatic restart fails, use **Restart now** or open your usual shortcut.

Source checkouts, portable archives and other unmanaged copies offer **Open
release page** for manual download. They are not modified by the updater. Older
app versions without these controls need one manual update first; after that,
future published releases can be installed from the app.

## Waiting and closing

When WCL's hourly allowance is exhausted, the app saves progress and shows the
observed reset countdown. Leave it open to continue automatically, or choose
**Stop and save** and continue later from the library.

Closing an active window offers **Keep working** or **Save and quit**. Saving
waits for the current request or offline stage to finish safely. An HTTP request
can take up to 30 seconds; large offline analyses may take longer. A forced OS
shutdown can retain only work already checkpointed.

During an app installation, closing offers **Close when finished**. Necropsy
waits for the installer rather than interrupting activation. Reopen the app from
its usual shortcut afterward.

## Build and run from source

The one-line installers open this GUI by default. They install the native package
and retain a private Python runtime for explicit CLI commands. `necropsy` or
`necropsy gui` opens the GUI; `necropsy tui` opens the terminal interface. A manual
wheel install supplies the CLI, not the native desktop binary.

Install Node.js 24, a stable Rust toolchain and the
[Tauri platform prerequisites](https://v2.tauri.app/start/prerequisites/).
Then, from the repository root:

```sh
uv sync --locked --group desktop-build
uv run --group desktop-build python scripts/build_desktop.py
cd desktop
npm ci
npm run desktop
```

The engine build is required before the first native build because Tauri checks
the bundled binary. Development uses the checkout's `.venv`; packaging uses the
frozen engine. The example is bundled from the committed subset fixture.

To produce an installer on its target OS:

```sh
cd desktop
npm run package
```

Windows produces a per-user installer; macOS produces an application bundle/DMG;
Linux packaging includes Debian and AppImage targets. The
[desktop workflow](../.github/workflows/desktop.yml) builds Windows x64, Linux
x64, macOS Apple Silicon and macOS Intel artifacts and exercises each frozen
engine offline. It also creates portable archives for the one-line installers
and exercises fresh setup and damaged-download recovery on each OS.
Signing/notarization remains separate release work.

## Verification and platform boundaries

Windows has local frozen-engine and native-window offline verification. The
window check uses the actual engine and IPC: example analysis, both views, local
review persistence across reload, boss links, invalid-link recovery, library
navigation, saved-report refresh and save-before-quit during offline work. Update
dialog checks use controlled current/offline/manual/damaged-download responses;
backend tests separately verify release policy, checksums and launcher rollback.
The bootstrap smoke check also feeds real packages through a controlled release
transport into the updater and existing installer in a temporary app root. It
verifies new GUI readiness and retention of the previous version; personal
shortcuts and PATH changes are suppressed for that check.
Existing service tests cover repeated
quota waits, cancellation and checkpoint recovery. A real-account GUI sign-in
and acquisition is a separate acceptance check; prior terminal acceptance does
not establish GUI acceptance.

For [0.3.0](https://github.com/David-c0degeek/necropsy/releases/tag/v0.3.0),
[native CI](https://github.com/David-c0degeek/necropsy/actions/runs/38874925377)
passed on Windows x64, Linux x64 and both Mac architectures: packaging,
frozen-engine offline replay, fresh installation, GUI/engine readiness and
damaged-download rollback. The exact published Windows binary also passed the
native-window check above. OS vault access, native dialogs, real-account sign-in,
keyboard access, scaling and close/resume still need manual acceptance on each
target platform; automated packaging checks do not establish those results.

[0.3.1](https://github.com/David-c0degeek/necropsy/releases/tag/v0.3.1)
passed the same [four-platform native checks](https://github.com/David-c0degeek/necropsy/actions/runs/38895236316)
and [three-platform Python checks](https://github.com/David-c0degeek/necropsy/actions/runs/38895236311).
The exact Windows package passed the native-window smoke test and replayed the
reported Restoration snapshot with the corrected Loatheb and missing-talent
comparisons. All nine public assets were downloaded and checksum-verified before
updating the installers on main.

[0.4.0](https://github.com/David-c0degeek/necropsy/releases/tag/v0.4.0)
adds saved-report refresh, explicit app updates and the clearer Playbook. Its
[four-platform native checks](https://github.com/David-c0degeek/necropsy/actions/runs/38964392126)
passed frozen-engine replay, packaging, fresh setup, staged app updates and
damaged-download recovery. Its
[three-platform Python checks](https://github.com/David-c0degeek/necropsy/actions/runs/38964395667)
also passed. The exact Windows archive passed the native-window flow, including
report refresh, review persistence and controlled update-dialog states. All nine
public files were downloaded without authentication and checksum-verified before
switching the one-line installers to this version.

To check a frozen engine outside the checkout, pass its executable to:

```sh
uv run python scripts/check_desktop_engine.py PATH_TO_ENGINE
```

On Windows, `scripts/check_desktop_window.py PATH_TO_APP` exercises a built
WebView2 window with an isolated library/profile and writes screenshots under
`workspace/desktop-screenshots`. A debug build requires the Vite server
(`npm run dev`); a release build serves bundled assets. The check enables remote
debugging only for its own temporary test process.

If your global Cargo configuration sets a default target, pass it explicitly to
Tauri (for example `npm run desktop -- --target x86_64-pc-windows-msvc` or
`npm run package -- --target x86_64-pc-windows-msvc` on Windows x64), so launching
and bundling search the same target directory as Cargo.

## Desktop boundary

React controls workflow and presentation. The Python sidecar owns credentials,
WCL access, checkpoints, analysis and export. It accepts a fixed set of JSON-line
operations over process pipes; it opens no application HTTP server.

The embedded pages are regenerated from validated `analysis.json` using the real
Jinja templates, rather than executing imported HTML. An opaque-origin sandbox
and a restrictive report CSP isolate them from the shell. Only current-frame
navigation, approved review keys and explicit WCL links cross the parent-message
boundary. WCL links are independently checked by Python before browser launch.
Inline scripts are allowed for the existing offline report code; automatic
Tauri script hash injection is disabled for that directive so it does not break
the frame. The report's CSP denies network requests.

`NECROPSY_DESKTOP_DATA_DIR` optionally chooses a separate run library for
verification. Leave it unset for normal use so the GUI and TUI share saved runs.
