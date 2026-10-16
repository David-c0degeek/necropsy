# Desktop GUI implementation

User authorization: build the Windows/macOS/Linux GUI, keep it user friendly,
and carry the existing Playbook/Report identity into the application.

## Integration and approach

Tauri 2 + React/TypeScript, with a bundled Python sidecar communicating over
stdin/stdout. Reuse `tui.service.AnalysisService`, `RunLibrary`, existing
checkpoint formats, OS credential stores and report renderers. Render the real
Playbook/Report in a sandboxed frame; do not recreate analytical findings in JS.
Keep current CLI and terminal installers working. Desktop installers are additive.
The service module has no terminal imports, so moving it is unnecessary churn.

## Pre-mortem

Failed future: closing the new window kills an acquisition before its cooperative
stop completes; saved output becomes confusing. Alternatively imported HTML gains
desktop privileges, or an installer depends on the developer's Python checkout.

| ID | Prediction and basis | Guardrail | Resolution |
|---|---|---|---|
| PM-1 | High: a window close kills work during a request. Evidence: `AnalysisService.run`, `StopClock`, TUI `action_request_quit`; stop is cooperative and may wait for an HTTP deadline. | One operation at a time; stop remains independently readable over stdin; intercept native close, explain saving, wait for worker before exiting; preserve run locks/checkpoints. | Mitigated: cancellation/EOF unit tests preserve saved status; packaged window check requests quit during a second offline example and verifies both analysis files survive. Native application quit is also intercepted. |
| PM-2 | High: report scripts or serialized auth objects gain access to desktop commands. Evidence: existing self-contained reports execute JS, `AnalysisService.auth` owns credentials. | Allowlisted JSON operations, no auth/token serialization; sandbox report with opaque origin and restrictive CSP; validate external WCL links; desktop capabilities only for main window. | Prevented by validated-JSON regeneration, escaping, allowlisted operations, opaque sandbox and report CSP. Packaged-window probe observes frame IPC blocked; bad schemes/hosts and presentation-only payload have unit tests. Tauri initialization globals can exist in frames, so do not rely on absence of that object. |
| PM-3 | High: GUI starts in checkout but installed engine cannot load assets/native DuckDB/keyring. Evidence: Python 3.14, DuckDB, Jinja package resources, keyring discovery. | Bundle engine and assets; exercise frozen sidecar outside checkout; per-OS CI builds and offline replay, distinguish local Windows verification from unrun macOS/Linux evidence. | Mitigated on Windows: frozen engine replay/export outside checkout and release-window checks with Vite stopped pass. CI matrix configured for all requested OSes. Explicitly accepted validation boundary: macOS/Linux execution, native vault/dialog acceptance and real-account GUI acceptance require those environments. No claim of signed/published release. |

Verdict: PROCEED WITH GUARDRAILS.

## Work

- [x] Python JSON sidecar: service reuse, saved library, offline import/demo, report rendering, export, stop and failure behavior.
- [x] GUI: first-run guidance, class/spec selection, honest progress, saved-run recovery, sandboxed report, matching dark/light themes and accessible controls.
- [x] Native shell and packaging: developer launch, bundled engine, Windows/macOS/Linux build workflow.
- [x] Verify Python suite/types/lint, TypeScript build, Rust checks/build, browser flows and frozen engine replay (Windows; other platforms explicitly pending).
- [x] Update installation, architecture, roadmap, contributing and changelog; record actual platform limits.

## Validation and lessons

2026-10-16: 1,039 fast-suite tests pass (251 excluded); desktop/service focused
suite 19/19. Ruff, formatting, mypy, docs links, TypeScript/Vite build, Rust fmt
and Clippy pass. Python sdist/wheel build passes. Npm audit reports zero runtime
dependency vulnerabilities. Frozen engine works from a temporary directory:
bundled sample, saved run, both pages and valid ZIP export, without vault access.

Windows NSIS installer built locally (about 42.8 MiB). Release-window check with
the dev server stopped passes: dark/light home, invalid WCL host recovery,
offline example, actual report scripts, frame IPC blocked, in-page and cross-view
boss links, review persistence across views and shell reload, searchable library,
and closing during offline work only after both analyses are safely stored.
Final package is rebuilt after the final local-storage fallback improvement.

Final rebuilt release-window check PASS, including save-before-quit. Installer
copied to `dist/Necropsy_0.2.1_x64-setup.exe` with a SHA-256 companion for local
delivery. The development server and test windows are stopped. Final Ruff,
formatting, mypy, documentation-link and diff-whitespace checks pass.

Lessons: intercept fragment links inside srcdoc (their default base is the
parent URL); avoid top-level `var status` in injected browser JS (it binds the
special window.status string property); keep inline report scripts compatible
with the parent CSP; pass --target when a global Cargo target config exists.
Never rebuild/copy a sidecar while its Windows executable is running.

Durable architecture: docs/decisions/0010-graphical-desktop.md. Existing terminal
installers are unchanged. User approved the GUI and requested commit/push on
2026-10-16. Signing and release publication remain separate work.
macOS/Linux GUI/installer execution and real-account GUI acceptance remain
explicit follow-up verification, not inferred from a green Windows run.
