# 03 - Naxx Captures

## Goal
Real, public, full-raid Naxx actor evidence for every configuration, captured on
Tower from one reviewed queue, copied to the PC with verified hashes, and
registered as actor sources.

## Integration analysis
Verified against the existing queue, runner, image stager and strict snapshot
reader. The runner already passes raid, partition and configuration through.
Queue commands now carry one immutable raid/artifact context; default calls
retain the original 102 MC/BWL/AQ40 runs. Explicit Naxx scope has 34 legal
configurations and 15 encounters, and requires separate research and queue paths.
Other-raid register records are filtered before configuration lookup. A v1 actor
source stays reusable evidence but never suppresses encounter capture. Suppression
requires strict v2 proofs and complete encounter/critical and actor scopes for
the boss, plus a finished capture with its comparison cohort met. All 34 runs
still need capture in the current inventory.

Report mining reads both wrappers, registered class/Druid archives and raid
archives. It requires matching positive fight/kill/partition and metric evidence,
deduplicates copied report witnesses and excludes owner identities before and
after resolution. Research pins every scanned archive by its committed bytes
or hydrated LFS oid. Strict and snapshot verification use the same context and
reconstruct scoped queue entries from their checked plan and caches.

`scripts/check_capture_archive.py` verifies a real output ZIP against its expected
digest, full entries manifest, queue entry, resolved subject and exact selected
report/fight/encounter. It uses the strict v2 reader, requires both complete
encounter scopes and complete actor streams for that fight, and writes a fresh
receipt with Python/tool/package/input digests and page/event counts. Its
synthetic tests are verifier evidence only. A real Tower capture is still needed.

Offline preparation command (options precede the subcommand):

```powershell
uv run python scripts/capture_queue.py --raid naxxramas --research-dir tasks/naxx-completion/research --queue tasks/naxx-completion/capture-queue.json plan
```

Use those same three options with `resolve --budget N`, `leaderboard --budget N`,
`emit`, `verify` and `verify --snapshot`. Resolution/leaderboards wait for WCL
maintenance to finish. Once emitted and verified, stage with explicit `--queue`
and `--queue-pin`; controller results take `check_results.py RESULTS --queue QUEUE`.
The archive verifier separately takes `ARCHIVE --sha256 HASH --entries MANIFEST
--queue QUEUE --entry ID --subject-id ID --report CODE --fight ID --encounter ID
--out FRESH_RECEIPT`. Preserve fresh state/output/cache paths before any live run.

## Boxes
- [ ] **03.1** (agent) Before the bulk queue, one normal v2 capture measures quota with timestamped readings, page and event counts, including a short fight and at least one of the Four Horsemen, Gothik or Kel'Thuzad (`research/quota-estimate.md`). Then the Naxx queue: 34 configurations minus usable existing archives, 1–3 reviewed public candidates each (owner's characters excluded), pinned research, `capture_queue verify` clean. Pair review.
- [ ] **03.2** (agent) Image and smoke: current release wheel (cut a release only if the runner needs a change), smoke with the exact production argv on a Naxx entry. The smoke asserts the produced archive is a v2 snapshot with encounter and critical streams for the entry's fight, not only argv and exit (PM-2).
- [x] **03.3** (product-owner) Approve restarting the Tower runner with the Naxx queue; approval mirrored. Execution and watchdog re-enablement remain in 03.4 after all approval conditions are met.
- [ ] **03.4** (agent) Tower restart per the unraid-tower skill with a change record; monitor; handle attention states.
- [ ] **03.5** (agent) Intake: copy finished archives to the PC, verify hashes, add provenance, register actor sources (`actor_problems` clean). Partial captures classified with evidence; missing configurations stay OPEN with the reason.

## Hindsight checkpoint
Current resumed-checkpoint verification: 92 queue/scope/archive/staging tests
pass; research secret scan finds no leaks. Full unchanged-tree gate runs after
commit, with eight workers; log
`workspace/codex-naxx/measurement-20261022/resumed-capture-full-gate.log`.
These checks do not satisfy the pending real-capture or review conditions.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-22 · WCL resumed, bounded measurement scheduled · Owner confirms WCL is back. Normal user-endpoint quota and character checks succeed; the earlier report candidate times out after the normal retry budget. Candidate verification caches now retain 177 resolved identities and 62 ranking checks: 23 of 34 configurations have checked candidates, 11 remain unfilled, and `emit` correctly refuses to write the bulk queue. The third bounded resolution batch stops on `RateLimited: no database points remaining`; a separate timestamped quota query reads 1230/3000 with 2824 seconds to reset. This is not proof of hourly-point exhaustion or database readiness. No further data calls before that observed reset plus margin.

Published 0.6.0 wheel staged into a separate single-entry measurement image, verified on Tower as UID 99:100 (`sha256:71afa601f60aee4c5e19c75c0cf7f12fa430dee48073330dbe0b94a830dbeb6f`). Teris, Balance DPS Alliance, resolves as character 77619978 and has positive rankings on all 15 bosses. One detached isolated attempt is scheduled no earlier than 2026-10-22 11:36:27 UTC (13:36 Amsterdam), with fresh data/cache/attempt/secrets paths, normal production analyze arguments, unchanged quota reserve, no restart policy or automatic retry, bounded logs and a two-hour timeout. The local collector makes no WCL calls; it will copy any snapshot, compare hashes and attempt strict short/complex fight v2 checks. No real capture or v2 smoke has passed yet. `research/capture-readiness-20261022.json` pins the caches, selection, wheel/image, start/collector scripts and quota evidence. Production runner remains stopped on 0.5.2; watchdog remains off; old state/output/queue untouched. 03.1/03.2/03.4/03.5 stay open. Reserve the single API owner for this attempt until it exits; inspect `workspace/codex-naxx/measurement-20261022/collector-status.json` before issuing other data calls.

2026-10-21 · Offline queue and smoke preparation · Owner confirms WCL is temporarily offline for maintenance; no further WCL requests during maintenance. Generated `research/capture-queue-plan.json`: 34 configurations, 15 bosses/510 cells, all 34 still scheduled for capture; 32 have unverified candidate pools, two Balance-HPS pools need leaderboard discovery after maintenance. It pins 68 inputs, including 64 raw archives. No resolution/ranking caches or emitted Naxx queue are fabricated; `emit` refuses all 34 unchecked runs. Parked queue remains SHA256 `8b3431d0b8aea6c3ec3a0af7126738584ae185b6f06a94f5ca88c3c40643676e`. Strict scoped replay/pins, mixed-raid/owner/duplicate/v1 false-reuse rejection and actual v2 archive checks have targeted coverage. Real image smoke, quota measurement and production restart remain open.
2026-10-21 · Preparation validation · Targeted queue/archive suite: 81 passed. Ruff passes on changed Python; whole-tree mypy passes all 276 configured files; docs checker passes 297 maintained links. The full checkpoint gate is run with eight pytest workers (`PYTEST_ADDOPTS=-n 8 --dist worksteal`, `NECROPSY_GATE_WORKERS=8`) after committing, with unchanged-tree protection; result retained at `workspace/codex-naxx/scoped-capture-full-gate.log`. No engine/rule/render changes or new completion ticks.
2026-10-21 · Preparation · Owner directs Codex to continue while Claude has no usage (D013). Existing pair session parked with pending Claude reviews retained. Fresh read-only SSH at 17:48:59 UTC confirms runner exited on 0.5.2, status server running, parked backup directory present and 305 GiB visible free space. Image staging now accepts an explicit queue/pin pair and retains the old defaults. PM-6 records wrong-queue staging and its guardrails. No image deployed, production restart or watchdog enablement; 03.1/03.2/03.4 remain open.
2026-10-21 · Preparation validation · Eleven staging tests pass, including custom-queue binding, wrong-pin refusal without output, and requiring both custom inputs. Ruff lint/format and targeted mypy pass; `check_docs` checks 297 links. Initial normal user-endpoint quota query failed with HTTP 503 at 17:49:33 UTC (start 17:48:59); no subject/report/event requests or capture followed, and available quota remains unknown. Full checkpoint gate uses eight pytest workers via `PYTEST_ADDOPTS=-n 8 --dist worksteal` and `NECROPSY_GATE_WORKERS=8`; its result is retained in the ignored workspace log, with no completion tick inferred while it runs.
2026-10-21 · 03.3 · Owner approval "Approved" relayed verbatim by Claude in mailbox claude:16, session 20261021T120145Z-a4a14bde. Conditional on all of: released 0.6.0 and Tower image built from its wheel; real 03.2 smoke proving v2 encounter and critical streams; one measured normal v2 capture with a short and complex fight and timestamped quota evidence; Naxx queue passing `capture_queue verify` and pair review. Approval is DONE and mirrored in manual-actions.md. No restart, image deployment or watchdog change has occurred; 03.4 remains open. These records are separate from the frozen release candidate 65b1154.

2026-10-22 · Isolated capture resumed with bounded supervision · Attempt 001
stopped at 11:38:35 UTC with quota-reset/exit 3 and no snapshot. After ordinary
report/quota probes succeeded, attempt 002 resumed the pinned checkpoint and
stopped at 17:18:21 UTC with the same database-points refusal, no snapshot and
no report. Last successful hourly API usage was 1048.15/3000; database readiness
must not be equated with hourly API headroom. Retained successful responses are
usable for explicitly partial positive observations, not smoke acceptance.

A separate isolated coordinator now owns the credential-file session and the
same one-entry queue/image. It uses the shipped runner's receipt verification
and reset decision, unchanged quota reserve, a two-minute reset margin, at most
four further attempts (003–006), a six-hour controller limit, two-hour child
limits and a 50 GiB free-space floor. Network-disabled seed validation passes;
a modified checkpoint digest is rejected. Next eligible attempt is
18:16:03 UTC (20:16 Amsterdam). No candidate switching, model use, notification,
promotion, production restart or watchdog enablement occurs. Stop only
`necropsy-naxx-measurement-autopilot-20261022` to cancel; preserve its cache and
receipts. Do not make competing PC WCL/candidate calls while it owns the API.
The current collector is `bounded-collector-status.json` under the ignored
measurement workspace; the older `collector-status.json` is historical.
See `remaining-work.md` for work that continues independently of the capture.

2026-10-22 · Further capture progress and candidate-pool fix · Attempt 003
ran 18:16–18:18 UTC and stopped on database points during finalization of
report `1fZbDXm4jdat9vnq`, fight 37. It retained 52 additional successful
acquisition responses (243 total), with all response-data digests checked and
no previous request removed. No snapshot/report was written. Last returned
hourly reading is 188/3000, which does not explain database readiness or exact
request costs. The coordinator has three bounded attempts left and next waits
until 19:18:06 UTC / 21:18 Amsterdam. Receipt:
`research/capture-attempt-003-20261022.json`. Model hold remains active.

Offline readiness inspection identifies six configurations with unresolved
identity checks and five with empty/exhausted pools. A regression reproduces
leaderboard discovery stopping on 30 cached candidates already rejected for
the current faction. Both discovery and offline board merge now reuse the
existing per-configuration `check()` before their candidate cap: only explicit
rejections are removed; unknown and accepted candidates remain. Emission still
requires both gates, owner exclusions and scoped pins. Regression cases cover
later-boss discovery, live-call budget, metric/faction boundaries, unresolved
rows, resolved owner exclusion and offline merge. No live discovery request or
parked-queue mutation occurs while the isolated measurement owns the API.
The considered one-candidate target is unnecessary for the current cached
pools and was not added. Source evidence and full gate precede publication.
