# 07 — Live Acquisition

## Goal
`necropsy analyze <WCL character URL>`: resolve context, build a same-faction
cohort with pagination, acquire metadata + deep events under rate limits into a
resumable cache and snapshot v1, then reuse the offline pipeline unchanged.

## Integration analysis
> Fill before ticking any box (§6.17).

- **Existing code found** — TBD
- **Behaviour to preserve** — TBD
- **Reuse / extend** — TBD
- **Do not duplicate** — TBD
- **Integration point + why** — TBD
- **Vision fit** — TBD
- **Risks** — TBD

## Boxes
- [ ] **07.1** (agent) WCL GraphQL client rewritten from v6 learnings: site
      profiles (vanilla first), `/client` vs `/user`, pagination,
      `rateLimitData` read on every call with dynamic pacing, cost estimate
      before the deep pass, retry/backoff; tests use recorded responses.
- [ ] **07.2** (agent) Auth per the personal-only confidential-client decision:
      secret and user token in the OS keyring (no token file), auth-code flow on
      `http://localhost:8765/callback` with state check, refresh;
      `necropsy auth login|status|logout`. PKCE stays a distribution gate.
- [ ] **07.3** (agent) URL parser (`/character/id/<id>`,
      `/character/<region>/<realm>/<name>`, site family) and character context
      resolver (faction, class, WCL spec/role, zones, partitions, rankings) with
      confidence; user confirms zone/partition when ambiguous.
- [ ] **07.4** (agent) Benchmark selector: strict cohort key; pages rankings,
      discards opposite faction, stops at 5 deep + 20–30 metadata same-faction;
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
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
