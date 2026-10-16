# Pre-Mortem Record

## Failed future

The new selector sends Combat or Arcane as WCL filters, or relabels stored spec fields so old archives stop replaying. Reports claim matching builds/races from unknown or declared values.

## Prediction register

| ID | Predicted severity | Failure | Basis | Predicted detection | Guardrail | Resolution | Plan refs |
|---|---|---|---|---|---|---|---|
| PM-1 | High | Game tree becomes rejected API filter or false narrow leaderboard | [evidence: roles.selected_spec, WCL rejected-filter receipt] | Silent / request failure | Independent validated category and declared tree; disclose broad pool | Pending | 01.1; 02.1; 03.1 |
| PM-2 | High | Existing snapshots or resumes fail after spec semantics change | [evidence: snapshot.v1 strict models; checkpoint exact options] | Before merge if legacy replay exercised | Add optional intent fields; preserve archived category keys and legacy options | Pending | 02.2; 04.1 |
| PM-3 | Medium | Unknown or declared build/race becomes observed or matching | [evidence: report.combat._comparison; environment.talents] | Silent | Three-state match; source-specific triple validation; separate declarations and validity | Pending | 01.2; 03.1; 03.2 |

## Plan guardrails

Preserve these IDs in verification and final review; no current WCL classifier parity claim; no inferred race observation.

## Verdict

PROCEED WITH GUARDRAILS.

## Captain Hindsight calibration

| PM ID | Outcome | Observed impact | Actual detection | Mitigation effectiveness | Severity calibration | Hindsight note / evidence |
|---|---|---|---|---|---|---|

## Misses

| ID | Failure | Observed impact | Actual detection | Why Pre-Mortem missed it | Future lesson | Evidence / refs |
|---|---|---|---|---|---|---|
