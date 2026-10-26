# Shared capture quota deadline

The October 24 and 26 incidents have the same sequence: one capture reports a
known quota reset, then a different due entry starts before that reset and gets
a 429 without reset metadata. The old controller paused in attention even
though another entry already held an observed account deadline. Two synthetic
regressions reproduce those incident timings, including the three-minute gap
on October 24. Both failed against the prior runner.

The runner now persists `quota_until_utc` with the verified outcome in the
existing atomic state commit. Every entry waits for that deadline, retaining
any later individual retry delay. Unknown-reset quota receipts can reuse a
future known deadline without extending it; absent/expired deadlines,
authentication errors and invalid receipts still require attention. A completed
queue is never held open by a stale gate. The existing public status schema
shows the actual next retry and remains quietly `waiting` during the gate.

State version 2 is retained. Loading an old state adds only the gate field and
reconstructs it from exact known quota-reset/quota-reserve reasons whose retry
times are future. Expired historical waits do not invent a deadline, malformed
quota timestamps fail closed, and loading never clears an attention incident.
Older code can read the additive field but does not honor it; stop the worker
and preserve state before rollback. This is a shared gate within one runner
using one configured WCL identity, not coordination across independent runners.

## Real-state migration proof

The protected Tower evidence copy is
`/mnt/user/appdata/necropsy-naxx-evidence-20261026/state-before-clear-20261026T1345.json`.
The ignored local copy is
`workspace/quota-gate-20261026/state-before-clear-20261026T1345.json`, SHA-256
`9dd2a0ffdc7f031f9e8e1797a2e69adf056a5daa74b148e196e314b2146a5dfa`.
This is on-NAS retention, not an off-server backup. A clean checkout needs that
exact private input restored to the local path before replay.

```powershell
uv run python tasks/naxx-completion/research/quota-gate-20261026/check.py
```

The checker uses two frozen clocks. At `2026-10-26T12:41:46Z` it reconstructs
`13:40:47Z`; at the supplied pre-clear time `13:43:54Z`, every known deadline
has expired and it reconstructs none. Every other state field remains exactly
equal, including all 34 entry records, 33 deferred/one partial statuses, incident
2 and the inflight record. It writes no live state and makes no WCL call.

The initial migration test tried to call the current status publisher after
removing its newly initialized field. It was corrected to write the legacy
fixture directly, as an older writer would. A test callback annotation caused
a mypy failure and was corrected; neither is counted as a successful run.
The publication-level regression also caught a brief startup `running` state
before a scheduled wait. Startup now chooses `waiting` before any publication,
so the watchdog cannot mistake old progress for a stalled active capture.
Code review and the full eight-worker gate precede push. Release and fixed-image
rollout are owner-authorized and follow verified artifacts/state preservation;
Claude retains live Tower operations until that handover.
