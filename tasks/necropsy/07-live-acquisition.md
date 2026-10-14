# 07 — Live Acquisition

## Goal
`necropsy analyze <WCL character URL>`: resolve context, build a same-faction
cohort with pagination, acquire metadata + deep events under rate limits into a
resumable cache and snapshot v1, then reuse the offline pipeline unchanged.

## Integration analysis
> Fill before ticking any box in this subject. Reuse and integrate before
> adding — no new code until this is recorded (§6.17). Build on the prior-art
> map from 00.2 and the architectural direction from 00.1.
>
> **Evidence, not prose.** Each bullet names concrete files/symbols (e.g.
> `necropsy/snapshot/v0.py::read_events`), not "the relevant modules". "None
> found" is a valid answer only when it records the search that proved it (the
> grep/scan run). A generic Integration analysis that names nothing is not
> done — it is how a duplicate parallel system slips past this gate.
>
> - **Existing code found** — relevant modules, services, abstractions, workflows.
> - **Behaviour to preserve** — contracts, public APIs, tests, callers that must keep working.
> - **Reuse / extend** — what is reused, extended, or refactored instead of duplicated.
> - **Do not duplicate** — what already exists and must not be reimplemented.
> - **Integration point + why** — where the change lands and why it is the correct seam.
> - **Vision fit** — supports or conflicts with the project vision/ADRs (00.1); cite drift if any.
> - **Risks** — duplication, architectural drift, or accidental complexity introduced.

- **Existing code found** — no network, auth or URL code in `src` (`rg -n "httpx|keyring|oauth|warcraftlogs" src` before this subject → only docs strings); read-only reference `D:/repos/wcl_access_test/{wcl_auth.py,wcl_hunter_deep_export.py}` (working v6 queries, vanilla endpoints, port 8765). Reused in Necropsy: `necropsy.analysis.evidence.Faction`, the CLI app in `necropsy.cli`.
- **Behaviour to preserve** — offline commands untouched and network-free; secrets never in repo/fixtures/output (§6.22); analysis contracts unchanged.
- **Reuse / extend** — query shapes ported from the exporter (ours to own, re-verified live in 07.7); `Faction` enum for context; typer sub-app for `auth`.
- **Do not duplicate** — no second token/secret store (one `CredentialStore`), no file fallback; one client for /client and /user.
- **Integration point + why** — new package `necropsy.wcl` (sites, urls, credentials, auth, client, context, cli) so acquisition (07.4–07.6) builds on it and the analysis layers stay offline.
- **Vision fit** — spec §5 acquisition, D005 personal-only auth with PKCE gate, D007 httpx, D036–D038, pre-mortem PM-1..PM-3.
- **Risks** — WCL schema drift (queries unverified live until 07.7); Windows credential size limit (chunking); field shapes in tests are synthetic.
- **07.4 extension** — reuses `wcl/client.py::pages` (bool `hasMorePages`, repeat detection; its page-budget stop is now the typed `PageBudgetExhausted` so a budget stop is a partial cohort while malformed pages still fail), `WclClient.ensure_budget`/`last_rate`, `wcl/context.py::CharacterContext` (`same_faction_ready` inputs, `SUPPORTED_ZONE_ID`), `sites.require_supported`, and rule data `rules/classic_era/benchmarks.yaml::live_cohort` (targets, page budget, `guild-faction-v1`). New `wcl/cohort.py` is pure selection with an injected `verify` callback, library-only until 07.5 wires acquisition; the leaderboard query copies the recorded exporter's shape (unverified live until 07.7). Lessons line on `guild.faction` informed the INFERRED-only rule (D041).
- **07.5 extension (slice A: cache and fetch)** — reuses `WclClient.query` (typed errors, endpoint fixed per call, no downgrade), `ensure_budget`, `PageBudgetExhausted`, `sites.SITES` for the canonical supported host, and the recorded exporter's REPORT_QUERY / EVENTS_QUERY shapes (unverified live until 07.7), with `revision` added to every events request. `report/publish.py`'s refusal of links and collisions is the precedent for `wcl/cache.py` (contained paths, no-clobber hard-link publication, OS advisory locks, verified markers). Faction for later verification will reuse `externals.yaml::factions` via playerDetails combatantInfo.factionID (`analysis/generic/environment.py::faction`). Slice B (orchestration) follows in its own work unit; library-only until then (D042, PM-4, PM-5).
- **07.5 extension (slice B: orchestration)** — `wcl/acquire.py` drives `cohort.select_boss` (now with an `endpoint` argument, raw page capture and a tri-state `Verdict` verifier; legacy `Faction | None` verifiers still work, `deep_needs_observed` is opt-in), `fetch.fetch_bundle` / `fetch_stream` and `cache.Cache`; faction codes come from `externals.yaml::factions` as in `analysis/generic/environment.py::faction`; realm matching reuses `analysis/context.py::realm_key`; boss order and the subject rule come from rule data. The result keeps raw subject and leaderboard documents, bundle keys and stream identities for the snapshot writer (07.6); nothing is analysed here (D043).
- **07.6 extension (snapshot v1)** — reuses `snapshot/v0.py::V0Snapshot` through two seams (`_top_level`, `_ranking_scope`) instead of a second parser; `snapshot/archive.py` (`VerifiedArchive`, entries manifest, `EntryOrigin` gains an acquired origin); `snapshot/model.py` (`SnapshotDescriptor` gains mode, limitations and acquisition); `normalize/ingest.py` and `report/offline.py` open archives through one `open_snapshot`; `normalize/schema.py` SCHEMA_VERSION 2 with the existing rebuild rule (`report/offline.py::_reusable`); `report/analysis_json.py::build_document` reads mode/limitations/requested coverage; `wcl/cache.py` publication rules for the combined report and the archive set; acquisition finalization in `wcl/acquire.py`. Presentation and documentation wording stay with Codex (D044, PM-6, PM-7).

## Boxes
> ID = `<subject-id>.<box-number>` (subject index ID · box ordinal). Stable — never
> renumber; mark retired boxes done and struck with `ABANDONED; see D###`
> (see §4), don't delete. A human-owned box recorded `DEFERRED` in
> `manual-actions.md` stays `[ ]` and follows the §5 Done rule.
> Owner MUST be one of the §5 enum:
> agent · release-engineer · product-owner · tech-lead · domain-sme.

- [x] **07.1** (agent) WCL GraphQL client rewritten from v6 learnings: site
      profiles (vanilla first), `/client` vs `/user`, pagination,
      `rateLimitData` read on every call with dynamic pacing, cost estimate
      before the deep pass, retry/backoff; tests use recorded responses.
- [x] **07.2** (agent) Auth per the personal-only confidential-client decision:
      secret and user token in the OS keyring (no token file), auth-code flow on
      `http://localhost:8765/callback` with state check, refresh;
      `necropsy auth login|status|logout`. PKCE stays a distribution gate.
- [x] **07.3** (agent) URL parser (`/character/id/<id>`,
      `/character/<region>/<realm>/<name>`, site family) and character context
      resolver (faction, class, WCL spec/role, zones, partitions, rankings) with
      confidence; user confirms zone/partition when ambiguous.
- [x] **07.4** (agent) Benchmark selector: strict cohort key; pages rankings,
      discards opposite faction, stops at 5 deep + 20–30 metadata same-faction,
      and keeps paging past the overall top five until at least 3 same-faction
      deep entries exist per boss (bounded page budget; D031);
      shortfall and inaccessible archive/private logs yield explicit partial
      coverage, never substitution. Tested with recorded ranking pages.
- [x] **07.5** (agent) Two-pass acquisition (metadata, then deep events for
      subject + 5 same-faction + optional cross-faction #1) into an immutable
      cache keyed site + reportCode + revision + fightID; resumable after
      interrupt.
- [x] **07.6** (agent) Snapshot v1 writer + reader on the 02.1 contract; offline
      pipeline consumes v1 unchanged.
- [x] **07.7** (agent) Manual live end-to-end executed on Haplina's URL:
      original snapshot/receipt retained; artifact and secret checks passed;
      all 15 bosses attempted with 5 usable deep + 25 metadata each; 11 complete,
      4 partial due unassigned pets. Exit 4 is recorded, not promoted to 0.
      All subject selections match history; cohort differences are explained.
      One observed reset wait took 3240.989 s; cross-period account cost unknown.
      Functional execution is complete; acceptance of remaining coverage limits
      is explicitly pending 07.11 (D046), so subject/final CLOSE is not claimed.
- [x] **07.8** (agent) Docs: README quickstart, `docs/auth.md` (personal-only
      warning), `docs/architecture.md`, ADRs promoted from §4.
      Completed with independent factual review: auth/architecture references
      and four ADRs under `docs/decisions/` promote D036–D038 and D041–D044;
      package scope from D035 is retained in the output contract. Operational
      guides and navigation reconciled; authenticated acceptance stays open.
      Validation: 155 relative source/navigation links checked, CLI help compared,
      no plan IDs in new shipped docs; navigator AGREE round 1. Authenticated live
      and real-store acceptance remain open in 07.7/07.9.
- [x] **07.9** (product-owner) Run `necropsy auth login` once to move the user
      token into the keyring; confirm redirect URI 8765 is registered.
      User reported successful login on 2026-10-14. Local `auth status` confirms
      signed-in through Windows WinVault, and authenticated user-endpoint queries
      have succeeded. Successful callback completes the registered redirect check;
      no credential values were printed or copied into project artifacts.
- [ ] **07.10** (release-engineer) Before ANY distribution: register a WCL
      public PKCE client and replace confidential-client auth.
      `DEFERRED — see manual-actions`: never ticked in Milestone A; does not
      block closing this subject (§5 Done rule); remains an open blocker for
      any distribution.

- [ ] **07.11** (product-owner) Accept or reject the proposed personal-use live
      acceptance boundary: exit-4 output with all requested bosses/minimum samples
      and explicit unknown pet ownership, rather than requiring complete pet
      coverage. Concrete evidence/questions in `review-packet.md`; D046.

## Hindsight checkpoint
> Run after all boxes in this subject are complete and before marking
> the subject `DONE` in §5. Use the embedded prompt in "Appendix: Captain
> Hindsight Prompt". Record the review result here. An interim run after
> a large or risky box is allowed and recorded the same way; it does not
> replace the closing run. In this coordinated pair plan, the navigator's
> `VERDICT AGREE` on the subject's diff precedes the Hindsight run.
>
> Required output sections: Keep; Fix before closing; Record; Risk;
> Verdict (`CLOSE` or `DO NOT CLOSE`). If the verdict is `DO NOT CLOSE`,
> leave the subject open, add/reopen boxes or update decisions/lessons,
> and rerun this checkpoint after the fixes.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
2026-10-13 · slice 1 · 07.1–07.3 · design huddle with pre-mortem (PM-1..PM-3, D036–D038), `necropsy.wcl` package: allowlisted single-backend credential store with chunking, personal confidential-client auth with sentinel-tested redaction, bounded client with typed errors/pacing/pagination guards, strict URL parser, graded character context; `necropsy auth login|status|logout`, `necropsy resolve` · unit tests on synthetic shapes (no live calls) · awaiting review
2026-10-13 · slice 2 · 07.1–07.3 · review round 1 fixes: generation-based chunk writes with head committed last, sanitised backend failures, one atomic record per client id with staged sign-in (saved only on success), listener bound before the browser, request deadline bounding requests, malformed URLs refused cleanly · unit tests incl. failure-injection and sentinel scans · awaiting round 2
2026-10-13 · slice 3 · 07.2 · round-2 follow-up: confirmed-absence deletes, logout tests · navigator AGREE round 2 · commit f4ddddc pushed; CI run 38385955588 success
2026-10-13 · slice 4 · 07.4 · `wcl/cohort.py` benchmark selector: dimensional cohort key with refusal before any query, cumulative raw-row positions, duplicate-safe candidates, guild faction INFERRED with observed override and contradiction record, deep ⊂ metadata targets, typed partial stops (page budget, quota, permission) with no endpoint change; `PageBudgetExhausted` in the client; D041 · 24 unit tests on synthetic pages · awaiting review
2026-10-13 · slice 5 · 07.4 · review rounds 1–2 fixes: verified first-row context, shared realm key for subject and duplicates, integer-0 difficulty, positive non-blank report references, full-page fingerprints, canonical key rebuilt and compared on every dimension (value, type, status) before any row is read; supported-encounter check from zone rules · 64 cohort unit tests, full suite 789 passed / 4 xfailed · navigator AGREE round 3 · committed and pushed (see git log)
2026-10-13 · slice 6 · 07.5 (part A) · pre-mortem PM-4/PM-5 appended, D042; `wcl/cache.py` (validated keys, contained link-free paths, fsynced temp + hard-link no-clobber publication, OS-released advisory locks, marker last with canonical identity and page hashes, verified reads) and `wcl/fetch.py` (validated bundle before writing, revision checked on every events page, explicit null terminal cursor, bounded pages, typed inaccessible/revision/permission stops) · 30 cache + 24 fetch unit tests incl. a real killed lock holder, a junction/symlink escape, crash before the marker link, tampered pages and malformed markers · awaiting review; 07.5 stays open until orchestration
2026-10-13 · slice 7 · 07.5 (part A) · review rounds 1–2 fixes: pagination semantics enforced by the cache itself on write and read (at least one page, forward in-bounds cursors, explicit null terminal), complete type-checked identity bound to the storage key before any path is created, dangling and file links refused for locks, names and reads, strict report-code fullmatch, cleanup of owned files only, fetch provenance with observed-timestamp rate readings and an account-wide points delta only when both readings provably share an hourly period · 65 cache + 28 fetch tests, full suite 888 passed / 4 xfailed before the final metadata change, wcl tests 184 passed after it · navigator AGREE round 3 · committed and pushed (see git log); 07.5 stays open until orchestration
2026-10-13 · slice 8 · 07.5 (part B) · design huddle (tri-state verification, endpoint on every request, whole-entry generations, completed-entry coverage); `wcl/acquire.py` subject pick, verifier, generation-restarting entries, replenishment, opt-in cross-faction ceiling, points stop; selector `Verdict`/`endpoint`/raw pages; D043 · 16 orchestration tests against a synthetic WCL server (both endpoints, 403s, contradiction, ambiguous actor, missing faction, wrong class, pets known/unknown, wrong-faction subject, revision change before and after completed streams, twice, cross-faction opt-in, points stop, rerun with zero event requests) plus the recorded 15/15 subject-rule check · awaiting review
2026-10-13 · slice 9 · 07.5 (part B) · review round 1 fixes: pet ownership proven by the fight list and masterData (missing, malformed, duplicate or disagreeing owners stay unknown), metadata target and requested cross-faction ceiling in coverage, a points or rate stop keeps the boss and its completed entries and names the stage, dropped replacement rows keep their reason, observed rows take deep slots even after metadata is full (lowest non-deep metadata row displaced), subject rows validated before any query (genuine int class, report code pattern, finite non-negative amount, unusable tie fields as missing, missing rankings documents with a reason), no plan reference in shipped text · 29 orchestration tests plus the recorded 15/15 subject check · awaiting review
2026-10-13 · slice 10 · 07.5 (part B) · review round 2 fixes: every listed pet reconciled with masterData (owner disagreements either way, duplicate or unusable master records stay unknown; a master record without owner is labelled fight-list-only), the in-run bundle memo re-checks the encounter on every reuse, the cross-faction ceiling is not applicable when the overall #1 is own-faction or already a complete entry (no fetch, no false shortfall) and stays partial when its faction is unresolved or its fetch fails · on the recorded bundles 30 of 163 Hunter fights keep pets unknown because ownerless engineering pets (Battle Chicken, Arcanite Dragonling) are listed · 35 orchestration tests · awaiting review
2026-10-13 · slice 11 · 07.5 · navigator AGREE round 3 on orchestration; 07.5 complete as a library (cache, fetch, orchestration); live schema and real-store behaviour unverified until 07.7 · committed and pushed (see git log)
2026-10-13 · slice 12 · 07.6 (data/reader/contract) · design huddle (PM-6/PM-7, D044); acquisition context/requested scope and `finalize_reports` (one combined same-revision report per code, cached as a report set), `snapshot/v1.py` (strict live descriptor, v6 reader seams, certified page digests), `snapshot/v1_writer.py` (complete entries only, pages byte-for-byte from the verified cache, pets.json only when proven, deterministic ZIP, archive+entries+sha256 published as one set), `open_snapshot` in ingest, DB schema 2 (mode, limitations, acquisition) with rebuild from the same archive, analysis.json mode historical|live with the approved live description and per-boss coverage · 6 live end-to-end + 2 rebuild tests, full suite 933 passed / 4 xfailed; synthetic live artifact in workspace/live-synthetic · presentation wording window handed to Codex
2026-10-13 · slice 13 · 07.6 (part A) · Codex mode-aware presentation window (live labels, unknown rank-one, metadata context, requested-boss coverage), then navigator STEER fixes: strict live descriptor (no type coercion, Hunter/Naxx/cohort/top_n rule checks, participants against the acquired combined report's fights, actors and observed factions), writer refuses entries without exactly their player and pet streams or with mismatched boss/context/bundle/stream bindings, set-level writer lock, link and junction output refusal, rollback only of files still ours, stream identity and fetch provenance plus report-set digests and selection verdicts in the marker, subject rankings returned as text decoded and kept · 22 live snapshot tests, full suite 949 passed / 4 xfailed · awaiting final review
2026-10-13 · slice 14 · 07.6 (part A) · review round 1 fixes: the reader validates each stream's complete typed identity (report-set revision, supported site, the report fight's exact bounds, the supported events request) and its page cursor semantics, binds every participant's actor dir to the report actor and its pet list to the report's proven ownership (unproven pets must have no list); the writer checks context and requested scope, finite ranking numbers and stream bounds against the combined report, and opens the finished archive with the reader before publishing anything · 36 live snapshot tests, full suite passing · awaiting round 2
2026-10-13 · slice 15 · 07.6 (part A) · navigator AGREE round 2 on the whole live snapshot slice (data, reader, writer, schema 2, mode-aware presentation); CLI workflow (part B) still open · committed and pushed (see git log)
2026-10-13 · slice 16 · 07.6 (part A) · shipped 04f2324; CI 38456621414 failed on ubuntu only (rollback by inode deleted a replacement that reused the inode), fixed by also requiring the published bytes, navigator AGREE round 3, shipped 95265b9 with CI 38457488680 green on ubuntu and windows
2026-10-13 · slice 17 · 07.6 (part B) · design huddle (no-clobber output contract, exit codes, run-level points); `wcl/analyze.py` + `necropsy analyze`: offline checks before credentials (URL/site, endpoint, partition, name, plain link-free cache/output dirs, no earlier analysis), output lock for the whole run with the check repeated before the report, one endpoint (resolve gained `endpoint`), partition choice exit 2, finalization stop exit 3, partial exit 4, recovery command when the report fails after the snapshot was saved · 15 CLI tests with a fake token source and the synthetic WCL server · wording/help/docs handed to Codex
2026-10-13 · slice 18 · 07.6 (part B) · Codex wording/help/docs window (README, docs index, getting started, Warcraft Logs guide, roadmap, analysis-json intro, CHANGELOG, analyze/ingest/offline help, points wording), then STEER fixes: --cross-faction forwarded to the offline analysis, the recovery command keeps --cross-faction and --no-package and is PowerShell-safe on Windows (single quotes, apostrophes doubled) and POSIX-safe elsewhere · 26 CLI tests · awaiting final review
2026-10-13 · slice 19 · 07.6 · navigator AGREE round 1 on `necropsy analyze`; 07.6 complete (live snapshot format, reader, pipeline, CLI) on synthetic data; authenticated WCL and real credential-store validation stay with 07.7/07.9 · committed and pushed (see git log)

2026-10-13 · slice 20 · 07.8 · auth.md, current architecture/source map and four accepted ADRs shipped in f3964595d3bb6d2008a109e858f4c48d219f21bf; README/docs/WCL/roadmap navigation reconciled; navigator AGREE round 1 on all 12 file fingerprints; 155 relative links verified and CLI help compared; decision-log rows now link the durable ADR records. CI 38462789103 passed on ubuntu-latest and windows-latest.

Documentation checkpoint close-out: Keep — operational guides and boundary references are separate, evidence/source links resolve, historical/live and personal/distributed status are explicit. Fix before closing — none. Record — implemented auth/acquisition/cache/snapshot choices promoted with plan traceability. Risk — authenticated WCL and actual credential-store behavior are still unverified and cannot be established by these docs. Verdict — CLOSE 07.8 only; subject 07 remains open for 07.7/07.9, distribution gate deferred as recorded.
2026-10-13 · slice 20 · 07.7 (preparation) · opt-in live acceptance harness: `wcl/acceptance.py` (snapshot re-open, analysis/pages/package checks incl. the package's own checksum manifest, credential-field structure check, gitleaks scan when available, history comparison only for a matching historical analysis, no-clobber receipt) and `tests/live/test_live_acceptance.py` (needs both `--run-live` and NECROPSY_LIVE_URL; same code path as `necropsy analyze`) · 8 offline tests incl. a configured shell without the option touching nothing · 07.7 stays open until a signed-in run produces a receipt; procedure wording handed to Codex
2026-10-14 · slice 21 · 07.7 (preparation) · review fixes (resolved-context baseline hook, artifact bindings, same-faction realm-normalised comparison with recorded faction basis, package duplicate/malformed refusal, scanner states) and Codex's docs/live-acceptance.md · navigator AGREE round 1 on the harness and procedure only; 07.7 and 07.9 stay open until a real signed-in run produces a receipt · committed and pushed (see git log)

2026-10-14 · slice 22 · 07.7 live findings / cache format 2 · user sign-in confirmed (WinVault); live context Haplina/Ashbringer/EU/Alliance/Naxxramas partition S0 id 1. Client attempt selected the historical Patchwerk fight but an archived events page failed; user-endpoint retry collided with format-1 cache data. Codex now drives at user request. PM-8 persisted before implementation. Endpoint-specific streams; full-digest bundle/report-set generations with exact read binding and fresh finalization; optional v1 generation provenance; recognized archive-only errors inaccessible, mixed errors invalid. Format 1 refused without changes, pre-generation v1 replay fixture retained. Offline checks and review pending; actual live acceptance remains open.

2026-10-14 · slice 23 · 07.7/07.9 · cache format 2 and unsupported/anonymized report-ID rejection shipped in 8aa4988f762f05fd46ca5a7d3e3a1cd04126fcb4; navigator AGREE rounds 1–2 on every changed-file fingerprint. Full suite 1,018 passed / one deliberately disabled live check / four xfailed before the localized ID guard; 70 fetch/acquisition checks passed after it. CI 38564860073 passed Linux and Windows. First user run discovered an anonymized report ID; second stopped conservatively during fresh finalization at 1,462.31 of 1,800 account points, before publishing a snapshot/report. Cache preserved; new run started after the observed reset at 12:48:54 UTC using the same cache and a new output directory. 07.9 synchronized with successful human login, WinVault status and authenticated queries; 07.7 stays open pending a verified receipt.

2026-10-14 · slice 24 · contributor documentation / final-gate preparation · report-only whole-repo cleanup audit emitted at `cleanup-audit-2026-10-14.md`; all candidates triaged (C1 fix now; C2/C3 retained). C1 contributor instructions and acquisition/query module comments corrected afterward, without runtime changes or a claim of completed live acceptance. Ruff check/format, mypy, relative links and both opt-in safeguard tests passed. Fresh remote clone with full LFS fixture began the independent golden/acceptance replay; review and checkpoint publication pending.

2026-10-14 · slice 25 · final-gate evidence / 07.7 continuation · preceding records shipped in b0a4e22 after navigator AGREE round 3 on all 27 work-unit files. Independent remote clone at 8aa4988 passed 229 golden/acceptance checks with four recorded xfails in 353.81 seconds; actual report/package artifacts and digests retained locally. Build, repo-history and expanded-fixture/generated-package secret scans passed; cleanup triaged and lasting lessons promoted. Live attempt 20261014T124854Z stopped during finalization at 1,458.39/1,800 account points (reported reset 2,817 seconds), with no snapshot/report; 240 completed streams and 344 event pages retained. An ignored, bounded local continuation helper is waiting until 13:49:18 UTC, derived from the latest observed stream timestamp/reset plus 20 seconds. At most two continuations use the same cache, full boss scope, user endpoint, partition 1 and unchanged budget policy with fresh outputs; stop on a receipt or unrecognized failure and notify the pair for actual review. No live receipt or closing Hindsight claimed; 07.7 and subject 07 stay open. Shared final-gate record review/push pending.

Final-gate review clarification: automated historical replay/register checks pass,
but historical sign-off remains open because `sapphiron.weave-verdict` has only
an agent rule-based exclusion, without explicit domain-sme attribution. The
other three disputed resolutions already record user review on 2026-10-13.
Carry the remaining exclusion into the existing 05.7 human review; do not weaken
the acceptance criterion or manufacture approval.

2026-10-14 · slice 26 · 07.7 acquisition budget liveness · observed-reset attempt 134918Z added 45 complete streams / 91 pages (cache now 285 streams / 435 pages) but stopped before the first combined-report request at 1,459.23/1,800 points. No report-set generation existed, disproving the suggested repeated-finalization diagnosis. Measured account deltas inside the new stream intervals sum to 112.8 points; about 1,346.43 points were outside them, so repeating fresh acquisition does not establish end-to-end convergence. Cancelled the next plain retry. Design agreed with navigator; PM-9 recorded before code. Explicit `analyze --wait-for-reset` reuses the existing policy with one run-level wait allowance, observed source, one-hour cap, at-most-30-second chunks, cancellation propagation and recorded elapsed wait; selection remains in memory and combined reports stay fresh. Default stop behavior unchanged. Manual acceptance forwards an explicit environment opt-in and records wait evidence. Targeted client/CLI/offline-acceptance checks passed (79 before the final revision-drift regression); ruff/format/mypy/help clean. Docs/ADR/acceptance procedure updated; verification/review/publication and actual live receipt pending.

Reset-wait verification: latest targeted suite 80 passed in 75.31 seconds,
including fresh revision drift during the wait (all outputs refused). Navigator
AGREE round 1 on runtime; optional shared-factory policy concern resolved with a
dataclass copy and a passing two-run isolation regression. Ruff/format/mypy clean.
Full changed-file documentation/record review and actual live receipt remain open.


2026-10-14 · slice 27 · 07.7 / closing preparation · real original receipt and
verified archive inspected; actual run completed 15:57:33 UTC, user endpoint,
partition 1, all 15 requested bosses / 5 usable deep / 25 metadata, 11 complete
and 4 partial due ownerless pet actors. All subject fight choices match history;
artifact/secret checks passed and account-wide cross-period points remain unknown.
Subsequent archive replay restores 15 headlines without changing primary analyses;
runtime/schema checkpoints 713aa63/0224f91 and Linux/Windows CI green. PM outcomes
calibrated, shipped docs reconciled, proposed partial-live acceptance mirrored as
07.11; broader mechanics and final signoff remain open. Claude review and record
checkpoint pending; no credentials or additional network acquisition required.

### Captain Hindsight — live execution close-out preparation

**Keep:** One endpoint and verified same-faction deep samples; immutable original
archive/receipt; fresh revision-bound finalization; explicit partial ownerless-pet
coverage; bounded observed reset wait; offline replay through one shared pipeline.

**Fix before closing:** Obtain the explicit product-owner decision on 07.11.
This review cannot replace the plan's acceptance of partial coverage. Existing
partial reasons are evidence limitations, not a reason to invent pet owners.

**Record:** Actual live receipt and hashes, comparison differences, Windows-only
real-store evidence, unknown cross-period cost, all remaining PM calibrations,
current docs and durable lessons. Original pending-run entries remain chronology.

**Risk:** Four bosses retain incomplete ownership evidence. Other real credential
stores, future WCL drift and public distribution are not validated by this run.
PKCE remains deferred and is owned by the new distribution plan.

**Verdict:** DO NOT CLOSE subject 07 pending 07.11. Agent box 07.7 execution and
artifact verification are complete; coverage is still partial. Current mechanics
review and final plan signoff remain independent human actions.

Latest independent replay at 0224f91: 229 passed / 4 expected failures / 823 deselected in 270.13 s, exit 0. Build passed; plan/human mirrors/relative links verified. Final record/plan peer review pending.
