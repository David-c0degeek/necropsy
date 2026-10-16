# Lessons

- Inspect the GUI's actual report IPC before inferring stale files cause a stale
  embedded view. It already uses current templates; installed engine version is
  the relevant boundary.

- A frozen one-file engine has a bootloader parent and temporary extraction
  lifetime. Pass the actual shell PID and spawn independent helpers with
  PYINSTALLER_RESET_ENVIRONMENT=1; restore system library search paths before
  launching platform tools. Official reference:
  https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html
- Installation rollback includes OS shortcuts, not only the CLI launcher and
  GUI pointer. Preserve both and avoid rewriting PATH during in-app updates.
- Native Tauri internals deliberately use immutable properties. Windows UI
  fixture checks intercept only the test process's IPC fetch and state explicitly
  which flows use real backend data versus controlled release responses.
- Keep verification claims scoped: real Windows staged install through controlled
  metadata is evidence for installer integration, not a claim that a future
  published release or macOS/Linux GUI update was accepted by a user.
