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
- [ ] **07.4** (agent) Benchmark selector: strict cohort key; pages rankings,
      discards opposite faction, stops at 5 deep + 20–30 metadata same-faction,
      and keeps paging past the overall top five until at least 3 same-faction
      deep entries exist per boss (bounded page budget; D031);
      shortfall and inaccessible archive/private logs yield explicit partial
      coverage, never substitution. Tested with recorded ranking pages.
- [ ] **07.5** (agent) Two-pass acquisition (metadata, then deep events for
      subject + 5 same-faction + optional cross-faction #1) into an immutable
      cache keyed site + reportCode + revision + fightID; resumable after
      interrupt.
- [ ] **07.6** (agent) Snapshot v1 writer + reader on the 02.1 contract; offline
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
