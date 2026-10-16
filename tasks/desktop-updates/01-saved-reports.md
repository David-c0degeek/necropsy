# 01 - Saved reports

## Goal

Persist current templates into a known saved analysis without a new run or API calls.

## Integration analysis

Extend DesktopEngine and report publisher; use RunLibrary/SavedRun, existing output lock and Checkpoint ownership. Preserve analysis bytes, session status, source snapshot and review keys. Report opening already renders trusted templates; this action persists derived files.

## Boxes

- [x] **01.1** (agent) Validate selected run, preserve identity/data and serialize refresh with the existing output lock.
- [x] **01.2** (agent) Publish regenerated HTML/package with checkpoint finalization and rollback on render/write/metadata failure; exercise resumed ownership validation.
- [x] **01.3** (agent) Add Update reports to library rows and active-report controls with offline success/error feedback and busy handling.

## Hindsight checkpoint

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log

2026-10-16 Â· 01.1-01.3 implemented. Targeted backend checks pass; the actual
Windows GUI refreshed its one known run, retained identical analysis bytes and
review marks across reload, and persisted current HTML. Frozen-engine IPC also
refreshed the same run and exported its package. Checkpoint reconstruction after
refresh succeeds; injected metadata/render failures restore previous outputs;
edited owned files and concurrent acquisition are refused. The no-package option
removes obsolete ZIP ownership without changing analysis data.

## Captain Hindsight

Keep: shared output lock, validated JSON renderer, publisher rollback and saved
checkpoint contract. No analytical recomputation or duplicate run.
Fix before closing: none; test_report_refresh.py, native and frozen smoke outputs
confirm the changed behavior rather than only compilation.
Record: D002 and ADR 0013 distinguish render refresh from analysis production;
PM-1 calibration is recorded in pre-mortem.md.
Risk: existing crash-interruption recovery remains necessary; no stronger
transaction claim is made. Older JSON still has to pass existing validation.
Verdict: CLOSE.

Checkpoint: implementation and verification pushed as 1f16cbd.
