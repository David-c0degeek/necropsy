# Necropsy

A Warcraft performance coach for all nine Classic Era classes in Naxxramas, AQ40, BWL and Molten Core.

## Install and open

The installer handles the graphical app and its runtime, then opens the GUI.
No Git, GitHub account or Python experience is required.

Windows PowerShell:

```powershell
& { $ErrorActionPreference = 'Stop'; $setup = Join-Path $env:TEMP ('necropsy-setup-' + [guid]::NewGuid() + '.ps1'); Invoke-WebRequest -UseBasicParsing https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.ps1 -OutFile $setup -ErrorAction Stop; powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $setup; if ($LASTEXITCODE -ne 0) { throw 'Necropsy setup failed. See the message above.' } }
```

macOS Terminal:

```sh
curl -fsSL https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.sh | sh
```

Linux desktop:

```sh
sh -c 'u=https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.sh; if command -v curl >/dev/null; then curl -fsSL "$u"; else wget -qO- "$u"; fi' | sh
```

Paste your Warcraft Logs character link, sign in in your browser and choose your
spec. The app handles paths and connection settings and opens the Playbook.
When the hourly API allowance is exhausted, it saves, sleeps and retries after
the reset. Stop whenever needed; choose a previous run and Continue later.
Saved reports open offline. New analyses use the redesigned coaching interface.

The app uses Windows Credential Manager, macOS Keychain or Linux Secret
Service/KWallet. Linux needs a normal desktop/user D-Bus and password-vault
session and curl or wget for the download. No plaintext credential fallback is
used. Private/archived WCL reports still depend on your account's permissions.

Setup creates an app shortcut/launcher. Next time open it, or run `necropsy`.
Repeating setup updates the app while preserving saved data and sign-in.
Version 0.3.0 makes the graphical app the default. Use `necropsy tui` for the
terminal interface. Version 0.2.1 corrects the Windows setup command; 0.2.0 introduced the TUI and
installers. The v0.1.0 release predates the redesign; locally built 0.1.1 added CLI resume/progress. Published artifacts are
listed on the [releases page](https://github.com/David-c0degeek/necropsy/releases).

Advanced CLI commands remain available through `necropsy --help`, including
`analyze --resume`, offline snapshot replay and rendering from saved JSON.
Public login uses the included registered PKCE app and no shared client secret.
Tokens are stored only in an approved OS vault. Reports/caches may contain
player identities; retain them privately unless sharing is authorized.

See the [installation guide](https://github.com/David-c0degeek/necropsy/blob/main/docs/installation.md)
for data locations, recovery, manual wheel installation and removal. Local
logout/uninstall does not revoke the server-side WCL authorization.
