# 03 - Install and restart

## Goal

Install a verified update for managed apps and restart only after readiness.

## Integration analysis

Reuse published install.ps1/install.sh, SHA256SUMS and existing fresh version staging. Detect a managed app by its existing gui-path pointer and executable layout; source/portable builds receive a manual download option. Do not add a second updater artifact format.

## Boxes

- [x] **03.1** (agent) Pin the checked release, download/verify installer, wheel, GUI and checksums, and run staged installer with no automatic launch under an install lock.
- [x] **03.2** (agent) Keep GUI responsive, serialize with analysis, honor safe close, preserve current working app on failure and only restart to a validated installed GUI.
- [x] **03.3** (agent) Wire Update and restart plus portable/manual release download through narrow Python operations; test request isolation and restart failures.

## Hindsight checkpoint

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log

2026-10-16 · 03.1-03.3 implemented. Checked assets are revalidated and verified
before the existing installer runs. Active launcher files and OS shortcuts are
restored on ordinary installer/readiness failure; previous versions remain.
Updates do not rewrite PATH. New tests cover shutdown waiting for installation
without restarting, failed restart retry state, window PID selection and frozen
runtime isolation. An isolated real Windows bootstrap ran the updater with real
wheel/GUI packages through a controlled release transport, activated a fresh GUI,
passed --check-install and retained its prior version. Damaged bootstrap inputs
preserved the active launchers. No personal install/shortcuts were modified.

## Captain Hindsight

Keep: one engine worker, app install lock, staged version directories and existing
install scripts. Avoid a second packaging/update system.
Fix before closing: fixed before review completion: use the native window PID
instead of the frozen bootloader parent; independent helper extraction; sanitize
frozen library paths for system tools; restore shortcuts alongside launchers.
Record: ADR 0013, lessons and CH-MISS-1 document the packaged-process boundary;
PM-3 calibration records controlled failure evidence and platform limits.
Risk: macOS/Linux runtime updater and a future public-version automatic restart
need release acceptance; Windows local tests use controlled release metadata.
The Windows PID wait and launch order are tested, but this does not claim a real
future public release was installed into the personal app.
Verdict: CLOSE.
