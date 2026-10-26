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
synthetic tests are verifier evidence only. The real0.6.1 Tower capture and
short/complex smoke passed2026-10-23 as recorded below.

Offline preparation command (options precede the subcommand):

```powershell
uv run python scripts/capture_queue.py --raid naxxramas --research-dir tasks/naxx-completion/research --queue tasks/naxx-completion/capture-queue.json plan
```

Use those same three options with `resolve --budget N`, `leaderboard --budget N`,
`emit`, `verify` and `verify --snapshot`. Candidate research has completed. Tower owns the API during production capture;
do not run concurrent PC resolution/leaderboard calls. Once emitted and verified, stage with explicit `--queue`
and `--queue-pin`; controller results take `check_results.py RESULTS --queue QUEUE`.
The archive verifier separately takes `ARCHIVE --sha256 HASH --entries MANIFEST
--queue QUEUE --entry ID --subject-id ID --report CODE --fight ID --encounter ID
--out FRESH_RECEIPT`. Preserve fresh state/output/cache paths before any live run.

## Boxes
- [ ] **03.1** (agent) Before the bulk queue, one normal v2 capture measures quota with timestamped readings, page and event counts, including a short fight and at least one of the Four Horsemen, Gothik or Kel'Thuzad (`research/quota-estimate.md`). Then the Naxx queue: 34 configurations minus usable existing archives, 1–3 reviewed public candidates each (owner's characters excluded), pinned research, `capture_queue verify` clean. Pair review.
- [x] **03.2** (agent) Image and smoke: current release wheel (cut a release only if the runner needs a change), smoke with the exact production argv on a Naxx entry. The smoke asserts the produced archive is a v2 snapshot with encounter and critical streams for the entry's fight, not only argv and exit (PM-2). Real released0.6.1 capture and selected short/complex scope checks passed2026-10-23; bulk queue and production remain open.
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
2026-10-26 · Shared quota controller fix prepared · Reproduced both production
incident orderings offline: the old per-entry scheduler launches a different
entry before the known account reset, then pauses on its reset-less 429. The
controller now persists a shared deadline and migrates only future known waits,
without changing entry records or clearing attention. The pinned pre-clear
state passes a two-clock migration proof in research/quota-gate-20261026/.
Review and the eight-worker full gate precede push. The owner approved the fixes,
release and Tower image rollout (mailbox claude:42); Claude retains live probing
and incident recovery until the reviewed fixed image is ready. Fight-centric
capture and report batching are the next unit, after this fix and release.

2026-10-26 · Partial production intake classification · The October24 production
archive (SHA256 837485a99ae96dfd644d410933f64947a0b4b236f47cd3dbff6cda5e6f293f5b,
55,832,205 bytes) is retained on Tower and in the ignored intake workspace.
All917 member paths match the registered measurement archive:724 members are
byte-identical and193 wrappers change. Player-role arrays match by unique actor
ID; report/user rankings and leaderboard rows have refreshed metadata. No event
member or strict scope improves. Existing sources, dependent facts and all cell
statuses remain unchanged; missing pet ownership and primary KelThuzad faction
remain refusals. Reproducible classification and exact input pins are in
research/production-intake-20261026/. The duplicate payload is not added to LFS.
03.5 remains open. Claude independently reproduced the comparison and approved
the original candidate, then verified an on-NAS retention copy outside every
container mount (maintenance commit74cbbb4, mailboxclaude:25). This is not an
off-server backup. Revised explicit checker guards preserve verification under
Python optimization. At09:44UTC Claude cleared queue-scoped attention under the
owner's delegated recovery decision after preserving state; the Horde Balance
capture child started. Production owns WCL; no competing PC calls. Final revised
review and eight-worker full gate precede this intake checkpoint's push.

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

## Latest isolated measurement follow-up

2026-10-22 · Attempt 004 ended 19:20:27 UTC on database-points refusal during
the same first combined-report finalization. No archive/report was written.
The retained journal now contains 288 successful acquisition responses,
45 new; every response-data digest checks and every prior request is unchanged.
`research/capture-attempt-004-20261022.json` binds the private journal digest,
controller receipt and limits. The last returned hourly reading, 393/3000,
does not establish database readiness or an exact cost for the failed request.
Next bounded retry is 20:20:08 UTC / 22:20 Amsterdam, with attempts 005–006
remaining. Coordinator owns the API; production stays parked and local AI off.
No v2 smoke, quota-throughput measurement or new capture eligibility is claimed.

Public official-source follow-up in
`research/wcl-quota-source-followup-20261022.json` records Archon's September
API-cost announcement, Vanilla caching/reset guidance and the documented
Warcraft `currentRequest` field. Direct opens returned 403; retrieval uses
indexed official text. These sources do not diagnose this credential or
establish a Vanilla database budget/reset. No new schema/data query, alternate
endpoint, finalization bypass or in-place image change was made. Endpoint
confirmation and separately validated telemetry remain possible follow-up
after the bounded measurement releases API ownership.

2026-10-22 · Offline resume correction · A synthetic database allowance can
exhaust while the returned hourly reading still has headroom. The original
resume then starts new acquisition events before finalizing saved complete
entries and fails again. The new regression reproduces this without WCL or
credentials. Resume now reconstructs saved entries under a zero-new-request
client guard, finalizes them through the existing independent report scope,
then continues normal acquisition and finalization. The preliminary pass
publishes nothing, changes no checkpoint/options schema and never copies
acquisition answers into finalization.

Both legacy and v2 regressions now produce a structurally valid partial archive
after that repeated quota scenario; source/cohort completeness stays false.
Missing cache requests, exception recovery and changed-report invalidation are
covered. This demonstrates a client scheduling failure and its offline fix,
not the exact database budget or guaranteed success on the real account.
PM-14–PM-16 guardrails remain in `pre-mortem.md`. The current released Tower
measurement and its remaining attempt are unchanged; release/image validation
and real smoke are still required before using the fix operationally.
`research/resume-finalization-priority-20261022.json` records the before/after
reproduction and all 57 unchanged legacy output hashes. Forty-five focused
client/replay/failure checks pass, and the scoped Naxx inventory remains clean
at 26 IN_PROGRESS/484 TODO. Full gate and browser receipts are retained under
the ignored `workspace/codex-naxx/finalization-priority-*` logs.

2026-10-22 · Bounded run collected, fixed release deployed · All six 0.6.0
attempts stopped on database quota without an archive; 693 acquisition responses
are retained with all digests and prior bytes verified. The completed controller
was collected, privately archived and removed. `research/capture-attempt-006-20261022.json`
records that historical outcome. Offline replay of a copy reused all 693 answers
with HTTP/tokens forbidden, reconstructing 74 complete acquisition entries that
need 59 independent report finalizations (`research/saved-journal-replay-20261022.json`).
A first replay without the context-resolution meter stopped safely before reuse;
the successful replay explicitly seeds the last historical meter, not a live reading.

Version 0.6.1 is now published at c10c461 after the immutable full gate, installed
three-window recovery, real Windows credential-backend probe and all four native
bootstrap checks. All release assets passed fresh-download digest comparison;
main's installers advanced only after publication. This is an operational patch,
not final Naxx content acceptance. The release-bound isolated image passed
network-disabled version/UID/manifest/queue/checkpoint/seed checks. Attempts
007–008 are bounded to four hours overall/two hours each with a 50 GiB floor,
waiting until 22:24:12 UTC / October23 00:24 Amsterdam. The same cache/checkpoint
and private file-mode session remain; no new API request has occurred at this
checkpoint. The exact-container collector verifies outputs and has guarded
private archival/removal after collection. Production remains parked, local AI
off and smoke/cost/bulk-queue review open. Full provenance, limits and cancel
identity are in `research/capture-fixed-release-20261022.json`.

2026-10-23 · Collected fixed-version progress and continued supervision ·
Attempts 007/008 again stopped on database quota without archives, but retained
4 and 9 independent finalization answers respectively. All 693 earlier
acquisition request bytes are unchanged; all 706 response-data digests pass.
`research/capture-attempt-008-20261023.json` records the 13 saved finalizations,
outcomes and successful guarded controller retirement at 23:28:38 UTC. The
two-attempt bound had ended; no capture worker was active until continuation.

Under standing autopilot, the same released image/cache/checkpoint/checked
one-entry queue now continues with fresh attempts 009–014, at most six attempts
in eight hours (two hours each, 50 GiB floor). Network-disabled seed/version/
wheel/queue/checkpoint preflight passed; collector PID30316 pins the exact
container/image and verifies outputs before guarded private archival/removal.
First attempt is due 07:58:44 UTC / 09:58 Amsterdam. No production restart or
model use. `research/capture-resume-20261023.json` binds limits, scripts and
current status/cancel identity. No archive/smoke or completed cell is claimed.

2026-10-23 · Continued quota progress · Attempts009–012 all stopped on
database quota, with seven additional independent finalization answers saved
since008 (20 in total). The new records were copied and canonical data/record
hashes checked; their exact report/fight sets match the prior59-set replay.
The full706-request check retains its historical timestamp; incremental checks
do not claim a fresh blanket rehash. Attempt012 ended11:06:43UTC, no snapshot;
next retry12:06:51UTC /14:06 Amsterdam, attempts013/014 remain under the same
bound. Research receipts cover010/011 and012 separately. No competing PC WCL
request, production restart or model use. Archive/smoke/cost gates stay open.

2026-10-23 · Bounded controller finished with attention required · Attempt013
saved one more verified finalization, now21, before four request attempts ended
in ReadTimeout. Attempt014 then received HTTP429 during character resolution;
no reset time was available, so shipped policy stopped with needs-attention
rather than inventing a retry. Collector copied logs/outcomes and privately
archived/removed the exact exited controller at12:15:13UTC, preserving mounted
state/images. No worker remains; production is still parked. The stale collector
TimeoutExpired key is historical after a recovered inspection timeout, not an
uncollected-output or cleanup failure. `research/capture-attempts-013-014-20261023.json`
records outcomes, one new digest-checked response and successful retirement.
No archive/smoke exists. Inspect rate-limit state before any further measured
retry; sole ownership and bounded operation still apply.

2026-10-23 · API recovered; fresh bounded resume · An isolated budget recheck
succeeded at13:15:12UTC (1/3000 hourly points, reset displayed60 minutes).
That is endpoint health, not database readiness. Under standing autopilot a
network-disabled preflight verified the same released image/wheel, checked
queue/checkpoint, saved012 seed and recent successful probe before a new
six-attempt/eight-hour coordinator started13:18:06UTC (015–020). Existing
two-hour child limit,50GiB floor, shared lock, default reserve, attention stops
and mounted state apply. First not-before13:18:38UTC. Exact-ID/image collector
PID17404 verifies outputs before guarded retirement; transformed metadata
accepts only expected exited/zero-layer/binds and refuses running, altered ID,
layer or mount. Waiting cleanup refuses before SSH. Current inspection errors
are cleared on recovery while historical errors remain recorded.

Attempt015 ended13:21:11UTC on quota-reset without archive, but saved13 more
independent finalization responses, now34. Each copied data/record hash and exact
report/fight set was checked against the earlier59-set replay. Next known retry
14:17:15UTC /16:17 Amsterdam; five bounded attempts remain. No PC WCL calls
while it owns the API, no production restart or model use. Provenance/cancel and
limits: `research/capture-recovery-20261023.json`; actual additions:
`research/capture-attempt-015-20261023.json`. Neither count is a completeness
percentage, archive certificate or cell closure.

2026-10-23 · First real v2 archive, smoke and partial intake · Attempt017
finished15:30:08UTC/source-limit after writing the55,836,308-byte archive
`tests/golden/raids/raw/naxx-balance-v2-measurement/77619978-2006-20261023T152230.zip`.
Whole digestcaa199389d11dab0d3c0678d086a352fb679d3e3cd133e62f2da0ecfef86dcb5
and all 917 member digests pass. All89 encounter scopes,89 critical scopes,
178 player streams and16 known-pet streams are complete;14 unresolved pet
scopes remain explicitly missing. Selected25.598s Sapphiron and303.964s Gothik
smoke checks pass, including three-page All scope.03.2 is complete on observed
archive behavior, not on exit code alone.

The capture reports10 complete/five incomplete bosses: four ownership-limited
cohorts and Teris's missing-faction Kel'Thuzad fight. Fourteen primary actor
sources plus separately observed Alliance comparison actor Hotsndots at
Kel'Thuzad pass actor_problems and replace the corresponding v1 references.
Previous typed records are retained in tests/golden/raids/naxx-v2-intake.json.
All other records/statuses are unchanged:26 IN_PROGRESS,484 TODO,zero COMPLETE.
Kel'Thuzad's five eligible comparison fights can be reused without inventing
Teris's identity. Actual queue projection recognizes11 bosses and retains
Patchwerk,Loatheb,Maexxna and Razuvious needing capture. Capture dispositions
are not completed configuration policies or cells.

The separate pinned provenance file avoids rewriting107 shared-catalog refs.
Planning now verifies each registered catalog's portable path/digest, merges
only its matching archive fixture and pins those catalogs in generated inputs.
Wrong archive,stale/escaping/absolute paths and duplicate/conflicting fixtures
are refused by seven new cases;75 queue tests,41 coverage tests and mypy pass.
Existing identity/cohort/v2 suppression semantics are unchanged. The initial
five-boss reuse assertion was an incorrect expectation about missing primary
subjects; it led to checking separate comparison evidence, not weakening rules.

Fresh final-journal scan verifies all916 canonical data digests:842 acquisition
and74 finalization records. Timestamped readings and stream page/event counts
are in research/real-v2-measurement-20261023/. Positive adjacent account deltas
sum9524.43 across14 decreases/reset transitions and failed windows: not a
per-stream invoice, cold-capture cost or bulk forecast. The final attempt
reported650 reused requests and402 account points between readings. Collector
copied/verified results and privately archived/removed the exact controller
15:32:24UTC, retaining mounted state/images. No capture worker remains;
production parked/local AI off. Queue research resumed with bounded PC API
calls after Tower released ownership. Full queue verification/independent
review and content/product acceptance remain open.

2026-10-23 · Candidate research completed · After Tower released API ownership,
198 bounded resolution/ranking calls (6+40+62+90) and four leaderboard fetches
produce325 cached resolutions/112 metric checks. All34 configurations have
one to three checked candidates (94 selections); no owner or unknown-faction
exception is made. The plan is regenerated against committed raw evidence and
supplemental provenance. Queue emission/pin verification and independent review
follow before production restart. An expanded856,951,518-byte archive-content
Gitleaks stream scan finds no leaks. Data acquisition cost remains governed by
the measured limits; filled candidate pools do not imply complete captures.

2026-10-23 · Full queue emitted and machine-verified ·
capture-queue.json contains34 runs/94 checked selections; SHA256
888b8d8d0355e985c7d8017f61b3dd864af56fd58d3701771647ce4eb9fc8552.
All75 direct/transitive pins match committed blobs and working bytes; snapshot
verification is intact atbf87149283a8. The author-review packet records every
configuration,candidate and evidence reference; independent review is explicitly
pending. A fresh public0.6.1 wheel download matchesb331510f6ca9e82b7752fa518cde1083b68156b77681d186089cd3f2e42d079e.
The local image context binds that published wheel and eight exact committed
source/queue files. Production is untouched; capture is not started by staging.
Full unchanged-tree gate follows the final evidence commit with eight workers,
logworkspace/codex-naxx/measurement-20261022/real-v2-final-full-gate.log.

2026-10-23 · Independent review and production restart · Owner explicitly
selected a separate Codex reviewer while Claude was unavailable. Read-only
review of5dc4b9a passes for the34-run/94-candidate queue,75 pins, exact image
context/public wheel and raw archive/all 917members. No Claude verdict or cell
acceptance is implied. A separate handover review caught attention-state false
readiness; checks were corrected before execution. The reviewed0.6.1 Naxx image
started20:39UTC in isolatedNaxx paths with fresh state, preservedold MC data/images,
1941 copied/hash-verified cache files and privately copied protected credentials.
Status/watchdog align to new paths; only the existing15-minute schedule restored.
Two exactold containers were privately archived/retired after verification;
only two active Necropsy containers remain. All34 entries subsequently quota-deferred
to21:41:39UTC (23:41Amsterdam). Heartbeats live,0 completed/usable runs; partial
quota artifacts are not accepted evidence. One start alert failure retried and
delivered; pending 0. No local AI or competing PC WCL calls.

Actual source/operational receipts live in research/production-promotion-20261023/
and Tower changes/2026-10-23-necropsy-naxx-production-restart.md. Follow-up source
review found due alerts do not retry while a long child runs. Boundedmax1 retry
was implemented,74 runner tests pass/3skip, and4newcases fail againstoldsource.
Independentreview passes the fix; separate image build/full gate/promotion follow
without changing public release wheel, queue or persisted state.03.4 monitoring
and03.5 remaining intake stayopen; full configuration/cell acceptance is separate.

2026-10-23 · Alert supervision deployed during quota wait · Source 920977f
passes the full gate with eight workers: 2714 fast/29 skipped, 74 runner/3 skipped,
lint, format, mypy, docs and unchanged-tree checks. Independent source, context
and rollout reviews pass. New worker image 372d7ecc uses the same public 0.6.1
wheel and queue; network-disabled image checks exercise one-send/stop and actual
active-child retry/cleanup without credentials. Worker-only replacement during
verified no-child wait preserves all 34 deferred entry records, inflight None,
attempt paths/cache/output, and the unchanged www container. Exact predecessor
privately archived/removed after verification; only two active containers remain.
Host watchdog helper matches the new runner and returns 0. Docker process-format
and heartbeat timestamp-precision checks failed safely and were corrected using
actual process/start/mtime evidence; no state was reset. Scheduled retry remains
21:41:39 UTC, pending alerts 0, local AI off. Receipts are retained in
research/production-promotion-20261023/. Full capture/intake remain open.

2026-10-24 · First three production rounds checked · At23:07UTC/01:07Amsterdam,
all102 attempts ended quota-reset and all34 entries remain deferred, next retry
23:45:44UTC/01:45Amsterdam. Thirty-three unique partial archives total46841B;
whole SHA checks pass, but they contain zero fights/actor/encounter streams and
cannot enter intake. The leading run has no finalized archive and did retain26
successful saved requests; every canonical data digest was independently checked.
Its quota stops advance across three different report/fight finalizations.
Stable run.json bytes do not mean the separate request journal is unchanged.
These observations establish saved progress, not a completion ETA or quota-cost
forecast. Pendingalerts0, one historical failure, no attention or active child.
No WCL query, state/queue/image change, localAI or evidence registration in this
follow-up. Full raw/refusal inventory and timestamped readings retained in
research/production-followup-20261024/. Production resumes automatically.

2026-10-26 · Quota controller and compatible reader released · The shared
account quota gate is reviewed and shipped with0.7.0. Committed candidate
e0e2ad2 passed the full eight-worker gate, required peer review, three-OS CI and
four native desktop builds/bootstrap checks. All148 wheel package files match
Git; complete draft hashes and fresh unauthenticated public downloads verify
before main/tag advance. Installed synthetic acquisition/finalization/v3 reader
and CLI offline distribution checks pass. The exact published wheel, reviewed
runner and pinned Naxx queue are staged with manifests and separate offline
image proof for Claude's already-authorized Tower rollout. Claude deployed
image2123ec9c at15:23:05UTC after network-none image/reader/migration checks.
The operator receipt verifies unchanged entries/mounts/web and a passing
watchdog; Codex retrieved/hash-checked it and compared the handover invariants.
The first gated Horde Balance DPS attempt resumed and stopped at15:49:07UTC
on a known finalization quota reset; the entire queue quietly waits until
16:48:15UTC, no other entry/attention. Its82 new journal records include zero
target requests. No new archive exists yet, so strict v3 archive/intake remains
an open03.4 follow-up under Claude's sole operational ownership. See
research/release-0.7.0-20261026.md. No capture/cell or product acceptance follows.
