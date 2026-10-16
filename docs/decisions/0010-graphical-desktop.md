# Graphical desktop with the existing Python engine

Status: Implemented in development; platform and real-account acceptance remain
bounded by the desktop guide.
Date: 2026-10-16

Use Tauri 2 and React/TypeScript for the graphical desktop shell. Bundle the
Python engine as a separate executable, built for each OS and architecture.
Keep the CLI and guided terminal app available with their existing installers.

Reuse `AnalysisService`, `RunLibrary`, the quota supervisor, run locks and
checkpoint formats. Their current module is terminal-independent; moving it
solely for the GUI would add churn. The sidecar accepts allowlisted JSON-lines
requests over stdin/stdout. It has one acquisition/offline worker; the input
reader can still deliver a stop while work runs. EOF requests cooperative stop
and waits for the worker. Native window close and application quit follow the
same save-before-exit path. No local application HTTP server is required.

Credentials and all analytical computation remain in Python. The frontend gets
presentation fields and outcomes, not token records or auth objects. Sign-in
uses the existing external-browser PKCE flow and OS vault.

Regenerate the embedded Playbook/Report from validated analysis JSON using the
existing templates. Imported HTML is never executed. The shell imports the
report stylesheet for its theme tokens and adds desktop layouts. The report
frame has an opaque origin and its own CSP denying network requests. Parent
messages accept only current-frame navigation, WCL links and review keys from
the displayed analysis. Python independently validates outgoing link hosts.
Personal review annotations stay in shell storage, separate from analytical
truth and exported packages.

The existing report scripts are inline, so permit inline scripts and disable
Tauri's automatic script-src hash modification for that directive. Keep remote
scripts, object content and report network requests blocked. This is an explicit
compatibility decision; adding externally supplied HTML or JS would require
revisiting the boundary.

Build desktop packages in a per-OS CI matrix and exercise each frozen engine
outside the checkout. A successful Windows offline check does not establish
macOS/Linux GUI acceptance, real-account GUI acceptance, signing or publication.
See [desktop operations and verification](../desktop.md).
