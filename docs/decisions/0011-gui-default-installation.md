# GUI-first bootstrap and launch

Status: Implemented for 0.3.0.
Date: 2026-10-16

The public one-line commands keep their existing raw-main URLs, but install a
versioned native GUI archive alongside the private Python/CLI runtime. Bare
`necropsy` and OS shortcuts open the graphical app. `necropsy gui`, `necropsy tui`
and all advanced commands remain explicit. A wheel-only install cannot supply
native desktop binaries and explains recovery rather than silently opening TUI.

Verify checksums for both downloads and run the GUI's headless `--check-install`
before changing active launchers. That check verifies the bundled engine's exact
version without an interactive window, credentials or network access. Stage each
upgrade in a fresh directory; preserve prior versions and the separate data/vault
locations. Failed wheel/GUI downloads must leave active pointers unchanged.

Windows shortcuts target the native executable directly. macOS gets an `.app`
symlink, replacing only the old bootstrap-owned `.command` symlink. Linux uses a
Terminal=false launcher and an archive of the extracted AppImage runtime; users
need no FUSE mount or system-wide package installation to launch the bundled app.

Build, package and verify bootstrap/rollback on each target OS. Publish all
versioned native archives, CLI artifacts and checksums before merging the raw-main
installer switch. This ordering prevents a valid existing install command from
pointing at downloads that have not yet been published. Old releases stay intact.

Signing/notarization and real-account GUI acceptance remain distinct from
automated native readiness, offline analysis and bootstrap checks.
