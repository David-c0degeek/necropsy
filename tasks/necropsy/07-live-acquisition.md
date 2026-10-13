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
- [ ] **07.7** (agent) Manual live end-to-end (`-m live`) on Haplina's URL:
      package produced, coverage and cohort provenance recorded, API points used
      reported; divergences from historical mode recorded and explained.
- [ ] **07.8** (agent) Docs: README quickstart, `docs/auth.md` (personal-only
      warning), `docs/architecture.md`, ADRs promoted from §4.
- [ ] **07.9** (product-owner) Run `necropsy auth login` once to move the user
      token into the keyring; confirm redirect URI 8765 is registered.
- [ ] **07.10** (release-engineer) Before ANY distribution: register a WCL
      public PKCE client and replace confidential-client auth.
      `DEFERRED — see manual-actions`: never ticked in Milestone A; does not
      block closing this subject (§5 Done rule); remains an open blocker for
      any distribution.

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
