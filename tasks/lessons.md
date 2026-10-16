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
- 2026-10-15: Class expansion must preserve the established product hierarchy, not just expose raw JSON in HTML. Reuse shared plans, metrics, equipment and interaction components with class-specific evidence adapters. Validate actual pages alongside the original class at desktop and mobile sizes.
- 2026-10-15: Name cross-class comparisons by the common action (ability use). Count recorded actor casts separately from damage/healing ticks and pets, preserve coverage-aware unknowns, and show counts plus duration-normalized rates without implying optimal play.

- 2026-10-15: Heading parity does not establish playbook parity. Verify execution-row content and per-action evidence alongside the established class; test first-use timing against actor ownership to avoid counting incoming casts.

- Verify ranking filters independently of game-data talent labels: Classic Era generic DPS/Healer metadata and ranking categories differ. Keep actual builds visible.
- Classify dual-purpose casts using matching actor/target effects; Holy Shock demonstrates why an ability name alone cannot establish duty.
- Budget-only snapshots prove honest empty handling, not role behavior. Record raw actor/event coverage independently of synthetic contracts or successful output generation.

- 2026-10-14: Query actual WCL class/spec taxonomy. Druid is WCL class 2; Guardian is Tank and still ranked by DPS. Category scores never substitute for tank survival or threat.

- 2026-10-14: Top Guardian category parses can have cat/bear attacks without tank hits. Exact ranking taxonomy is not encounter assignment. Conversely a real tank can have repeated Maul/Swipe and incoming melee with no recorded form aura; preserve both affirmative actions and unknown intervals.

- 2026-10-14: WCL resourceActor is a side flag, not an actor ID. Official resource filter probes with unequal source/target returned 1 for source and 2 for target; zero resource capacity is unusable, not a real empty resource pool.

- 2026-10-14: Count secondary duty share as well as affirmative casts; preserve incidental actions without forcing a hybrid aggregate. Retain direct tank evidence even when its cast share is small; domain review must adjudicate thresholds.

- 2026-10-14: Free-form class sections do not guarantee every optional nested display field exists. Render optional details as unknown/absent and test older saved class documents.

- 2026-10-15: Verify category/metric combinations independently. A Balance ranking category can contain a healing performance; category defaults must not erase explicit HPS or an encounter healing assignment.

- 2026-10-15: Compare all four saved Hunter artifacts, not just JSON. Jinja control-block trimming changed a brand newline; an inline expression restored both HTML and package bytes.

- 2026-10-15: Establish the selected view contract before validating isolated role examples. Keep every requested encounter, separate personal eligibility from learning examples, and show acquired rank accurately when #1 lacks duty evidence.

- 2026-10-15: Under a shared API budget, acquire personal raid coverage before deep comparisons; prioritize missing-personal encounters for examples and reserve finalization. Verify that order against a real complete raid capture.

- 2026-10-15: A sparse sample is a disclosure requirement, not a reason to hide individual comparisons. Spec and faction select Druid peers; talent points remain explicit context. Separate descriptive one-player differences from population summaries and causal advice.

- 2026-10-15: Verify actual API filtering, not just successful responses. Unsupported advanced filters may silently return the same unfiltered rows; use documented arguments and verify results before claiming faction-specific #1.

- Record explicit product acceptance separately from evidence adjudication. When the owner accepts limits and retires additional review, reconcile subject boxes, manual actions, current verdicts and final gates together; never claim an unperformed review or leave contradictory current trackers.


- 2026-10-15: Credential mode belongs in identity. Preserve legacy personal
  records and separate public PKCE records even for the same client ID; commit
  selection last and reject incompatible endpoints before HTTP.
- 2026-10-15: Distribution proof requires installed CLI behavior and actual
  replay outside the checkout. Use a unique synthetic service for real OS-store
  probes. Keep package metadata free of developer sample paths; local engineering
  checks cannot stand in for registered-app or independent-user acceptance.


- 2026-10-15: Record human acceptance at its actual evidence level. An owner can
  attest that an independent test passed without giving raw outputs; record the
  attestation and missing details rather than inventing OS/artifact facts or
  repeatedly requesting the same approval. Preserve the declared platform scope.
- 2026-10-15: A public OAuth client does not imply public repository hosting.
  Publish approved artifacts through the configured channel and preserve existing
  repository visibility unless the user separately requests a visibility change.


## Game identity and ranking categories

- Store WCL display names and slugs separately from game talent-tree identities.
  A WCL Protection Warrior may have Fury-heavy talent totals; declared build
  preference does not narrow a category leaderboard.
- Three tree totals are source-specific evidence, not a full talent allocation.
  Validate triples, ranges and totals; ignore spell-name decorations and reject
  leaderboard placeholders. Ties and missing values cannot establish a primary
  tree or a build match.
- Exercise optional selector values using the installed widget runtime. Textual
  empty selections use Select.NULL; build/type checks alone did not catch the
  obsolete sentinel because it resolved as an inherited boolean.
