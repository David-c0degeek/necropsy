# GUI-first installation

User request: the existing one-line installers and default launchers must open
the new GUI. Explicit terminal and advanced commands remain available.

## Pre-mortem and guardrails

| ID | Failed future and evidence | Guardrail | Resolution |
|---|---|---|---|
| PM-1 | Main installer points at nonexistent native assets. Current v0.2.1 release has wheels only; desktop workflow uploaded no public assets. | Work on a branch; build/test all platform archives, publish versioned release assets before merging raw-main installer changes. Keep old release immutable. | Pending |
| PM-2 | Upgrade replaces a working launcher before a broken GUI can start. Existing scripts stage/verify the wheel before publishing launchers. | Preserve this ordering for GUI and Python together; checksum both, run a headless GUI/engine readiness check, publish pointers/shortcuts last. Test damaged-download rollback. | Pending |
| PM-3 | Desktop shortcut opens a terminal or macOS/Linux packages need the checkout/FUSE. Existing launchers target terminal commands; Linux runtime needs WebKit. | Direct native Windows shortcut, macOS .app shortcut, Linux Terminal=false launcher. Distribute extracted AppImage AppDir with its libraries; native checks run outside checkout on each OS. | Pending |

Proceed with guardrails. New release 0.3.0 keeps the current GUI, vault,
checkpoint and analysis contracts. Bootstrap still supplies the CLI runtime for
explicit advanced commands. Native GUI assets are separate platform archives.

## Work

- [ ] Versioned native portable packages and headless readiness checks.
- [ ] GUI-first bootstrap, shortcuts and CLI default; explicit TUI preserved.
- [ ] Per-OS bootstrap/rollback CI and release asset assembly.
- [ ] Documentation, local checks and cross-platform CI.
- [ ] Publish assets before merging installer switch; verify public downloads.
