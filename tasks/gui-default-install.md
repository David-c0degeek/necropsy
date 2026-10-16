# GUI-first installation

User request: the existing one-line installers and default launchers must open
the new GUI. Explicit terminal and advanced commands remain available.

## Pre-mortem and guardrails

| ID | Failed future and evidence | Guardrail | Resolution |
|---|---|---|---|
| PM-1 | Main installer points at nonexistent native assets. Current v0.2.1 release has wheels only; desktop workflow uploaded no public assets. | Work on a branch; build/test all platform archives, publish versioned release assets before merging raw-main installer changes. Keep old release immutable. | Resolved: all nine public assets downloaded and hash-verified before PR merge; raw-main scripts then matched the release. |
| PM-2 | Upgrade replaces a working launcher before a broken GUI can start. Existing scripts stage/verify the wheel before publishing launchers. | Preserve this ordering for GUI and Python together; checksum both, run a headless GUI/engine readiness check, publish pointers/shortcuts last. Test damaged-download rollback. | Resolved: all four native CI jobs passed readiness and corrupt-wheel/corrupt-GUI rollback. |
| PM-3 | Desktop shortcut opens a terminal or macOS/Linux packages need the checkout/FUSE. Existing launchers target terminal commands; Linux runtime needs WebKit. | Direct native Windows shortcut, macOS .app shortcut, Linux Terminal=false launcher. Distribute extracted AppImage AppDir with its libraries; native checks run outside checkout on each OS. | Implemented and native bootstrap checked on all targets; actual offline GUI flow checked on Windows. Manual desktop acceptance on Mac/Linux remains separate. |

Proceed with guardrails. New release 0.3.0 keeps the current GUI, vault,
checkpoint and analysis contracts. Bootstrap still supplies the CLI runtime for
explicit advanced commands. Native GUI assets are separate platform archives.

## Work

- [x] Versioned native portable packages and headless readiness checks.
- [x] GUI-first bootstrap, shortcuts and CLI default; explicit TUI preserved.
- [x] Per-OS bootstrap/rollback CI and release asset assembly.
- [x] Documentation, local checks and cross-platform CI.
- [x] Publish assets before merging installer switch; verify public downloads.

## Completion evidence

- [Release 0.3.0](https://github.com/David-c0degeek/necropsy/releases/tag/v0.3.0)
  targets `99aa435`; [PR #3](https://github.com/David-c0degeek/necropsy/pull/3)
  merged as `ae67939` after publication and public checksum verification.
- [Desktop CI](https://github.com/David-c0degeek/necropsy/actions/runs/38874925377)
  passed Windows, Linux, Apple Silicon and Intel Mac builds, offline engine checks,
  fresh bootstrap and failed-upgrade recovery.
- [Python CI](https://github.com/David-c0degeek/necropsy/actions/runs/38874925379)
  passed lint, types and fast tests on all three OS families. Final assembled
  distribution passed installed replay, package integrity and secret scanning.
- The exact CI Windows archive passed native-window offline example, report
  navigation, review persistence, library and save-before-quit checks.
- After merge, the public raw-main Windows script installed into an isolated
  directory using public release downloads. GUI/engine readiness, CLI version and
  explicit terminal help passed; user shortcuts and PATH were left untouched.
- Checks caught macOS `/var` aliasing in temporary test paths and asynchronous
  GUI invocation in Windows PowerShell. Canonical test paths and a waited native
  process fixed those failures without weakening engine path validation.
- Windows setup verifies Microsoft's runtime installer signature before using
  it when WebView2 is absent. Mocked tests cover reuse, trusted setup and refusal
  of an untrusted download.
- Real-account GUI acquisition, OS-vault variations and manual desktop acceptance
  remain separate from automated installation readiness. Signing and notarization
  are not included in this release.
