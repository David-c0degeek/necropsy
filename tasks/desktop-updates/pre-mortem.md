# Pre-Mortem Record

## Failed future

Refreshing a saved report appeared successful but made resume refuse its files.
An available app update then replaced a working launcher before the new engine
was ready, leaving the user unable to open those analyses.

## Prediction register

| ID | Predicted severity | Failure | Basis | Predicted detection | Guardrail | Resolution | Plan refs |
|---|---|---|---|---|---|---|---|
| PM-1 | High | Refresh changes owned outputs without reconciling checkpoint hashes; subsequent resume refuses the run | [evidence: wcl/checkpoint.py Checkpoint.__init__/record; report/publish.py] | Silent until resume | Hold existing output lock, validate ownership before writing, finalize checkpoint within publication rollback; preserve original analysis and session identity | Pending | 01.1, 01.2; final refresh gate |
| PM-2 | High | Update installs a downgrade, wrong platform or incomplete/mutated release asset | [evidence: install.ps1/install.sh checksums and readiness; GitHub release assets API]; [inference: new discovery path could bypass them] | Before production with new negative tests; otherwise user install failure | Stable version comparison, fixed repository URLs, required platform asset set, bounded downloads, SHA256 verification, recheck release before installation | Pending | 02.1-02.3, 03.1 |
| PM-3 | High | Installer failure or close during update loses a usable app or interrupts saved work | [evidence: desktop engine worker/shutdown; install scripts staged versions and GUI readiness] | Before production via staged failure/close tests | One worker and install lock; refuse update during analysis; reuse staged installers; wait safely on close; keep old GUI alive and prior versions until readiness and restart | Pending | 03.1-03.3, 04.1 |

## Captain Hindsight calibration

| PM ID | Outcome | Observed impact | Actual detection | Mitigation effectiveness | Severity calibration | Hindsight note / evidence |
|---|---|---|---|---|---|---|

## Misses

| ID | Failure | Observed impact | Actual detection | Why Pre-Mortem missed it | Future lesson | Evidence / refs |
|---|---|---|---|---|---|---|

## Verdict

PROCEED WITH GUARDRAILS. Preserve existing crash/publication recovery boundaries;
verify ordinary write, checkpoint and install failures before final delivery.
