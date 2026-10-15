# Lasting engineering lessons

## Evidence and analysis

- Preserve the distinction between reported scalar metadata and acquired event
  evidence. A leaderboard score can remain known while event damage/pet totals
  are unknown. Reconcile identity across sources; never add metadata-only rows to
  event baselines/advice or invent a capture time for an older saved response.
- Summaries should label sampled opening patterns and retain timing/non-use/unknown
  distinctions and sourced phase conditions. A median among recorded casts is not
  a universal or optimal pull script; keep the detailed evidence available.

- Keep frozen raw exports and historical oracles unchanged. Resolve disagreements
  against raw data and record the result; an oracle is not automatically right.
- Fact probes need the same actor/target filters as production analysis. A pet
  death stream can include a mob death, so scanning all death rows is insufficient.
- Check ranking-damage rules across every cohort row. WCL can count damage to
  mind-controlled players; excluding all player targets gave the wrong KT result.
- Normalize realm identity consistently across rankings and report actors.
  Preserve original names for presentation.
- Treat guild faction and combatant faction as separate enumerations. Guild
  faction proves an inferred affiliation, not the character's observed faction.
- Preserve uncertainty through aggregates and HTML. Empty arrays do not prove
  absence; cohort counts inherit membership grades; unknown values remain null.
- Give recommendations resolvable evidence paths and check them against emitted
  JSON. Serializer changes can silently invalidate a citation.
- Keep guide and logged ability names distinct, with named aliases in rule data.

## Acquisition and storage

- Diagnose hourly-budget failures using actual stage and observed account deltas.
  An unknown-cost reserve is not a measured query charge. Repeated fresh selection
  can dominate a run even while event caches grow; a bounded opt-in reset wait can
  preserve acquisition state without weakening fresh finalization or budget limits.

- A report revision does not freeze all metadata. Preserve endpoint-specific
  full-digest observations, bind each run to its exact generation and finalize
  combined report sets fresh rather than choosing an arbitrary cached generation.
- Ranking APIs can return legitimate anonymized identifiers outside supported
  storage identities. Reject them before HTTP/cache writes as inaccessible
  candidates; retain the reason and use the existing replacement path.
- Resuming events still costs fresh ranking, metadata and finalization requests.
  Respect the observed account-wide reset, retain completed cache streams and
  retry into a fresh output directory without relaxing the budget guard.
- Atomic replacement also needs ownership checks. Revalidate target identity
  immediately before replacement; never delete another process's WAL or a
  replacement that merely reused a deleted file's inode.
- Bulk-load JSON objects into DuckDB through NDJSON rather than pre-serialized
  JSON strings or slow row-by-row executemany inserts.
- State fixture budgets in compressed bytes; pretty-printed exports can compress
  by an order of magnitude. Verify every member as well as the archive digest.

## Presentation, tooling and collaboration

- Inventory reference sections, elements and factual sentence types before
  matching a design. Preserve content breadth while correcting overclaims.
- Combine narrow-screen overflow checks with screenshot inspection. Squeezed
  tables can pass overflow checks while breaking labels mid-word.
- Setup docs should lead with a checked command on the included fixture and label
  implemented behavior separately from planned features.
- Windows tooling that prints player names needs UTF-8 output.
- Pin GitHub Actions to immutable SHAs and confirm the published tag shape.
- Do not stash while staged pair-review work is in flight. An intended handoff
  does not grant writes; verify completed ownership and a successful write guard.
- Keep the reusable plan's guidance intact. It provides the operating contract
  for a cold resume, not disposable boilerplate.

- After a long/manual verification run, reconcile its actual receipt with both planning records and user-facing docs. A valid partial artifact proves execution, not complete coverage or product acceptance; mirror acceptance decisions explicitly and retain original evidence.

- After the final typed output-model change, regenerate the committed schema and run its exact currency check. Earlier broad test results cannot cover a later contract edit; CI caught this omission before final verification.

- Engineering/trinket guardians (including Battle Chickens, dragonlings and vanquished tentacles) may belong to Hunters. Toolkit eligibility, NPC name or temporal proximity never proves which player owns an actor; use exact same-report/fight ownership evidence and preserve unknowns when it is missing.

- Verify ranking category, query metric and observed encounter duty independently.
  A Balance-category character can have healing rankings; a Guardian-category
  parse can lack tank duty. Carry explicit metric selection through replay and
  reject incompatible comparison dimensions.
- When a shared template promises byte compatibility, compare both rendered
  pages and the package with the saved baseline. Conditional template blocks can
  change whitespace even when analysis JSON is identical.

- Establish what the selected view means before validating isolated role examples.
  A spec filter applies to personal encounter duty; a category label alone does
  not establish it. Keep missing personal data separate from labelled learning
  examples, and do not convert an exemplar into a personal median or grade.
- Under an acquisition budget, gather the user's coverage before comparison
  depth. Keep budget for fresh finalization and restore temporary policy changes
  on every exception path. Record fetch priority independently of report order.

- 2026-10-15: Large JSON files can exceed a secret scanner's default per-file cap. Explicitly scan all extracted raw members and generated outputs with an unlimited target size, recording byte counts separately.
- 2026-10-15: If native ingestion fails during overlapping large replays, serialize verification and retain the observed failure and successful rerun. Do not claim a root cause or change the normalizer without reproduction.

- 2026-10-15: Keep individual top-player comparisons useful with one or two sources and disclose n. Do not let exact talent-point equality hide same-spec/faction players. Separate recorded differences from population baselines and causal advice.
- 2026-10-15: A supported website filter may not be a dedicated API filter. Inspect the live schema and compare actual opposite-filter responses; a successful response can silently ignore an unsupported filter.
