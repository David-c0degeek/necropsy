# 04 - Verification and documentation

## Goal

Verify complete saved-run and app-update user flows, document boundaries and deliver.

## Integration analysis

Extend existing native window, frozen-engine and bootstrap smoke checks. Reuse current test fixtures and private temporary install roots; never upgrade the personal installation as a test.

## Boxes

- [x] **04.1** (agent) Exercise native UI refresh and update states plus backend successful/failing install paths; record observed behavior and platform boundaries.
- [x] **04.2** (agent) Update desktop/install guides, README and architecture decision; reconcile lessons and retained risks with Captain Hindsight.
- [x] **04.3** (agent) Run required checks, review diff, commit/push main and verify remote/working-tree state.

## Hindsight checkpoint

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log

2026-10-16 · 04.1-04.2 implemented and verified. 1,189 fast tests passed
(251 excluded; workspace/desktop-updates-fast.log). After later review fixes,
63 focused desktop/update/refresh tests and 11 launcher/bootstrap tests passed.
Ruff lint/format, strict mypy (190 files), uv build, npm build/format, cargo
fmt/clippy/build passed. Latest frozen-engine and real staged-bootstrap receipts
are workspace/desktop-updates-frozen-check.log and desktop-updates-bootstrap.json.
Native WebView2 checks and screenshots are workspace/desktop-updates-native.
README, desktop/install guides, architecture map and ADR 0013 cover the feature.
No dependency changes or public release. macOS/Linux checks are wired to the
existing four-platform workflow and are not claimed locally passed.
2026-10-16 · 04.3 implementation pushed as 1f16cbd. git status --porcelain
was empty and origin/main exactly matched 1f16cbd7c4cf3664c9ee58966a64069aedd321ba.
GitHub CI and Desktop packages runs were queued for that commit; their completion
is not claimed as local platform acceptance. This close-out record is a separate
documentation checkpoint; no release publication or personal installation occurred.

## Captain Hindsight

Keep: refreshed outputs use the existing renderer/publisher/checkpoint boundary;
updates use the existing staged installers and four-platform distribution. Native
checks distinguish real saved-run behavior from controlled release responses.
Fix before closing: none. The runtime/shortcut issues found during review were
fixed and rechecked before 1f16cbd. Code/type/build checks pass; native refresh,
controlled update states, frozen refresh/export, real staged installation and
failed-download preservation all produced the expected observable results.
Record: ADR 0013, D001-D005, lessons, PM-1..3 terminal resolutions/calibrations and
CH-MISS-1 are reconciled. Manual actions explicitly exclude public publication.
Risk: new macOS/Linux runtime flows and real future-release restart need release
acceptance. Existing crash recovery and unsigned release trust remain explicit.
No claim of completed CI on the new commit or of a released binary is made.
Verdict: CLOSE.
