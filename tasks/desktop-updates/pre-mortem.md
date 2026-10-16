# Pre-Mortem Record

## Failed future

Refreshing a saved report appeared successful but made resume refuse its files.
An available app update then replaced a working launcher before the new engine
was ready, leaving the user unable to open those analyses.

## Prediction register

| ID | Predicted severity | Failure | Basis | Predicted detection | Guardrail | Resolution | Plan refs |
|---|---|---|---|---|---|---|---|
| PM-1 | High | Refresh changes owned outputs without reconciling checkpoint hashes; subsequent resume refuses the run | [evidence: wcl/checkpoint.py Checkpoint.__init__/record; report/publish.py] | Silent until resume | Hold existing output lock, validate ownership before writing, finalize checkpoint within publication rollback; preserve original analysis and session identity | Mitigated: shared lock, ownership validation, source retention and checkpoint finalizer rollback verified | 01.1, 01.2; final refresh gate |
| PM-2 | High | Update installs a downgrade, wrong platform or incomplete/mutated release asset | [evidence: install.ps1/install.sh checksums and readiness; GitHub release assets API]; [inference: new discovery path could bypass them] | Before production with new negative tests; otherwise user install failure | Stable version comparison, fixed repository URLs, required platform asset set, bounded downloads, SHA256 verification, recheck release before installation | Mitigated: semantic versions, complete canonical assets, recheck, bounded SHA256-verified downloads; refusal tests passed | 02.1-02.3, 03.1 |
| PM-3 | High | Installer failure or close during update loses a usable app or interrupts saved work | [evidence: desktop engine worker/shutdown; install scripts staged versions and GUI readiness] | Before production via staged failure/close tests | One worker and install lock; refuse update during analysis; reuse staged installers; wait safely on close; keep old GUI alive and prior versions until readiness and restart | Mitigated within tested Windows scope: real staged install, launcher/shortcut rollback, safe close and independent restart helper; other OS runtime acceptance deferred | 03.1-03.3, 04.1 |

## Captain Hindsight calibration

| PM ID | Outcome | Observed impact | Actual detection | Mitigation effectiveness | Severity calibration | Hindsight note / evidence |
|---|---|---|---|---|---|---|

| PM-1 | Prevented Prediction | Injected metadata failure leaves prior outputs and resumable checkpoint intact; no production impact observed | Targeted refresh rollback tests and native/frozen refresh | Effective for ordinary failures and output ownership | High remains appropriate for lost resumability; crash recovery boundary retained | test_report_refresh.py; native same-run/review persistence |
| PM-2 | Prevented Prediction | Wrong/incomplete/changed release, bad size/digest and unsafe redirects refused before execution | test_app_updates.py plus real-package controlled transport | Effective within verified release contract; no independent signature claim | High remains appropriate for installing unusable code | Current public future-update horizon has not elapsed; malformed input cases are controlled |
| PM-3 | Prevented Prediction | Injected installer/readiness failure restores launchers and shortcut; close waits; real private install retains old GUI | 63 focused tests and desktop-updates-bootstrap.json | Effective in Windows local scope; restart PID/runtime issues fixed during review | High remains appropriate; other OS/public restart acceptance remains uncertain | No personal installation changed; platform limitations recorded in subject 03 |

## Misses

| ID | Failure | Observed impact | Actual detection | Why Pre-Mortem missed it | Future lesson | Evidence / refs |
|---|---|---|---|---|---|---|

| CH-MISS-1 | Frozen restart helper shares the old extraction directory or waits for a bootloader PID | No shipped impact; found before commit during packaged-process review | Checked Python parent/frozen behavior against Rust shell and official PyInstaller documentation | Pre-mortem treated restart as ordinary subprocess launch | Include process topology, temporary runtime lifetime and library search paths in packaged-process reviews | Native GUI PID, PYINSTALLER_RESET_ENVIRONMENT and external_environment; test_app_updates.py |

## Verdict

PROCEED WITH GUARDRAILS. Preserve existing crash/publication recovery boundaries;
verify ordinary write, checkpoint and install failures before final delivery.
