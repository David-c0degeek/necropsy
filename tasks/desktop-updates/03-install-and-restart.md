# 03 - Install and restart

## Goal

Install a verified update for managed apps and restart only after readiness.

## Integration analysis

Reuse published install.ps1/install.sh, SHA256SUMS and existing fresh version staging. Detect a managed app by its existing gui-path pointer and executable layout; source/portable builds receive a manual download option. Do not add a second updater artifact format.

## Boxes

- [ ] **03.1** (agent) Pin the checked release, download/verify installer, wheel, GUI and checksums, and run staged installer with no automatic launch under an install lock.
- [ ] **03.2** (agent) Keep GUI responsive, serialize with analysis, honor safe close, preserve current working app on failure and only restart to a validated installed GUI.
- [ ] **03.3** (agent) Wire Update and restart plus portable/manual release download through narrow Python operations; test request isolation and restart failures.

## Hindsight checkpoint

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log

Pending.
