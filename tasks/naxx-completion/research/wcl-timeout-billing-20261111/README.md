# Timed-out rankings queries billed repeatedly — 11 November 2026

## Problem

The owner asked whether the Tower capture was stuck. It was not stuck, but it was
finalizing only one or two reports per hour. Entry
`naxxramas-warrior-protection-dps-alliance` had 20 of 58 evidence reports left
to finalize after 20 hourly attempts.

## Evidence

Source: `.necropsy-run/usage.jsonl` of that entry on Tower, 04:00–09:35 UTC.
In every hour, one finalization `NecropsyReport` query (rankings-bearing)
ended in client `ReadTimeout` after 30 s, one to four times. The
retry then succeeded with a small reported cost. The next response's
`database_points_spent` was far above the sum of the costs reported so far:

| Hour | Timeouts before success | Reported cost of success | Spent before → after |
|---|---:|---:|---:|
| 04 | 2 | 286 | 12 → 1,896 |
| 05 | 2 | 220 | 0 → 1,673 |
| 07 | 2 | 29 | 61 → 1,165 |
| 09 | 2 | 139 | 20 → 1,446 |

The hourly database allowance is 1,050, so each hour ended in
`no database points remaining` after one or two reports. Attempts 028 and 043
ended in `network error: ReadTimeout` alone and wasted the whole hour.

Inference (not confirmed by WCL documentation): abandoning a request does not stop
WCL's server-side work, so each timed-out attempt is billed, and the retry pays for
the same work again. The cheap successful retry fits a server-side cache filled by
the abandoned attempt.

## Change

`src/necropsy/wcl/client.py`: queries containing `rankings(`,
`characterRankings(` or `encounterRankings(` get a 240 s per-request read
timeout (other queries keep 30 s). Their call deadline is widened to at least
270 s, enough for one full slow attempt plus one retry. Retry counts, error
classification, journal identities and evidence are unchanged.

Tests: two new cases in `tests/unit/test_wcl_client.py`; unit + integration suites
2,819 passed, 29 skipped; ruff, format and mypy clean.

## Deployment

The local checkout's `wcl/*.py` matched the running image byte for byte before the
edit. The child image `necropsy-capture:0.7.1-timeout-fix-20261111` (`e2c7a72c…`) is
`FROM 0.7.1-rankings-recovery-20261106` with only `client.py` replaced
(sha256 `bda7b53d…`). The swap ran at 09:47:45 UTC while the runner was waiting for
the quota reset. The prior worker is kept as `necropsy-capture-before-timeout-20261111`.
Tower record: unraid-tower `changes/2026-11-11-necropsy-timeout-fix.md`.

## First production hour (attempt 045, 10:35 UTC)

WCL's gateway answered the slow queries with HTTP 504 after about 60 s and a
120 s Retry-After, so the 240 s client wait is never reached. The retry after 120 s
returned the cached answer for 2 points. Each slow report was billed once:
database spent 19 → 894 and 894 → 1,506. Previously, two 30 s timeouts per report
cost about 1,600 points. Two reports finalized this hour, against one or two before.

The gain comes from not re-requesting while WCL is still computing. It does not
come from the longer read timeout itself. A slow rankings report still costs about
600–900 database points, so the 1,050 hourly allowance remains the limit. Expect
roughly two slow reports per hour, not a large speedup.
