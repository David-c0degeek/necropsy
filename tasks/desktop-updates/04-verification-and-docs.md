# 04 - Verification and documentation

## Goal

Verify complete saved-run and app-update user flows, document boundaries and deliver.

## Integration analysis

Extend existing native window, frozen-engine and bootstrap smoke checks. Reuse current test fixtures and private temporary install roots; never upgrade the personal installation as a test.

## Boxes

- [x] **04.1** (agent) Exercise native UI refresh and update states plus backend successful/failing install paths; record observed behavior and platform boundaries.
- [x] **04.2** (agent) Update desktop/install guides, README and architecture decision; reconcile lessons and retained risks with Captain Hindsight.
- [ ] **04.3** (agent) Run required checks, review diff, commit/push main and verify remote/working-tree state.

## Hindsight checkpoint

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

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
04.3 remains pending commit/push and remote/clean-state verification.
