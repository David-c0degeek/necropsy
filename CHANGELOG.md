# Changelog

[Home](README.md) · [Documentation](docs/README.md) · [Roadmap](docs/roadmap.md)

Notable user-facing and developer changes. Entries under **Unreleased** are
implemented in the development checkout; they are not a published release.

## [Unreleased]

### Changed

- **Druid ranking selection.** `--category Balance --metric hps` selects
  Balance-category healing performances while preserving build and observed duty.
  Default category metrics and Hunter DPS selection remain unchanged.

- **Quick opening plan.** Added a KISS card to every boss in both pages, with a
  simple comparator-based ranged opening, recorded Rapid Fire timing and usage,
  and sourced encounter notes. Detailed timelines, execution/loadout plans,
  equipment and evidence remain. Overall-#1 DPS can use observed saved leaderboard
  metadata when an event calculation is unavailable, with source/capture context
  and no changes to same-faction benchmarks; missing values explain acquisition
  scope or its recorded failure. Race availability explains the Classic Era
  metadata limitation without guessing race from missing casts.

- **Optional hourly reset wait.** `analyze --wait-for-reset` can wait once, at
  most one hour, using an observed reset countdown while preserving its selection
  and fresh finalization. The default still stops promptly on insufficient budget.
  Live acceptance records the wait source and duration; cross-reset account usage
  remains unknown rather than an exact run charge.

- **Acquisition cache format 2.** Endpoint streams coexist, and changing report
  metadata is stored as full-digest generations rather than conflicting at one
  revision. Finalization binds a fresh combined report. Older cache directories
  are refused untouched with instructions to use a new path; saved snapshots
  remain readable. Archived candidate failures stay visible and can be replaced,
  while mixed GraphQL errors remain invalid and never trigger endpoint fallback.

- **Definitive playbook layout and content.** Both pages use the requested dark
  reference layout: searchable numbered sidebar, overview and Truth model,
  metric tiles, benchmark context, loadout and execution plans, Do not and Raid
  ask panels, the full recorded top-five table, and seventeen-slot gear cards.
  Same-faction advice stays separate from other-faction context. Saved ranking
  percentiles, item names, armor-set counts and cited encounter/cooldown/pet
  guidance enrich the analysis; unknown and inferred evidence stays qualified.
  Light/system themes, source links, local review marks and analytical drilldowns
  remain available. [Reading results](docs/reading-results.md).

### Added

- **Character-URL acquisition workflow.** `necropsy analyze URL --cache DIR
  --out DIR` acquires Classic Era Hunter/Naxxramas data, saves a verified snapshot
  v1 and writes the offline report, playbook and package. It refuses earlier
  outputs, keeps one endpoint throughout, and distinguishes partial reports from
  finalization stops. Live pages show every requested boss and keep metadata-only
  rows out of event medians. Schema 2 databases are rebuilt from the same raw
  archive; historical JSON remains renderable. Integration tests use synthetic
  responses; authenticated live validation remains pending.
  [Connection and recovery](docs/warcraft-logs.md).

- **Warcraft Logs sign-in and character lookup (personal use).** `necropsy auth
  login | status | logout` signs in with your own confidential WCL client: the
  client secret is entered at a hidden prompt and, with your token, stored only in
  the OS credential store (never a file). `necropsy resolve <character URL>` shows
  the character, faction, raid and partition, refusing non-Warcraft Logs and not yet
  supported sites. A public PKCE client is required
  before any distribution.
- **Offline report and playbook.** Every `necropsy offline` run also writes
  `report.html` (findings first, then execution, comparisons and evidence) and
  `playbook.html` (a per-boss review list with local review marks), both
  self-contained, offline, keyboard- and print-friendly, in light and dark themes,
  plus a deterministic package with CSV tables, per-boss evidence and a checksum
  manifest. `necropsy render` rebuilds them from an existing `analysis.json`, and
  `--no-package` skips the ZIP. Outputs are built before the output folder
  changes and are replaced together, with rollback and a recoverable backup if
  replacing fails. [Getting started](docs/getting-started.md).
- **Offline boss analysis.** `necropsy offline` writes deterministic, versioned
  `analysis.json` with same-faction medians, a best-ranked ceiling, optional
  cross-faction context, encounter findings, and evidence-linked recommendations.
  A retained database is reused only after archive verification.
  [Output reference](docs/analysis-json.md).
- **Hunter detail.** Shot cadence and timelines, opener, Quick Shots and Rapid
  Fire uptime, Auto Shot intervals and advisory gap signals, melee, friendly
  crowd control, pet classification/family inference, pet activity and deaths,
  and gear at the pull. Inactive pet-linked actors are identified from trusted
  streams. [Hunter rules](docs/hunter-analysis.md).
- **Fairer context.** Inferred faction membership remains inferred through
  medians, shot ranges, and the ceiling. Unavailable execution medians can use
  a separate proven-Tauren fallback with low-confidence advice. Weaving is
  judged separately on bosses and other hostile NPCs. Raid speed compares with
  the same-faction median and also shows the fastest same-faction kill.
- **Damage-target explanations.** Empirical Naxxramas ranking exclusions,
  individual ranking categories, and cohort target shares with stable NPC
  identities, aliases, and known/unknown sample sizes. Gothik start trash is
  separated from native and foreign targets. Unclassifiable targets remain
  unknown; subject zero shares retain trusted coverage.
- **Evidence and normalization.** `necropsy ingest` builds a typed DuckDB
  database from v6 exports, preserving genuine event multiplicity, stream
  coverage, anomalies, and provenance, with atomic replacement. Archive checks
  cover whole-file and member digests, member safety, encryption, duplicates,
  and size bounds. [Database](docs/database.md) · [Evidence](docs/evidence-model.md).
- **Reproducible development.** Python 3.14 project, UTF-8 CLI output, packaged
  rule data, frozen golden export in Git LFS, ordinary-Git test subset, oracle
  provenance, and a golden-fact acceptance gate. Linux/Windows CI runs lint,
  strict types, and fast tests; full golden replay has a manual workflow.
- **A clearer starting point.** Sample-first setup and troubleshooting,
  a guide to reading results, documentation navigation, contributing instructions,
  and issue/PR templates.

### Changed

- CLI help explains supported inputs, output locations, database reuse, and
  separate cross-faction context. Successful commands point to the next step;
  command names, options, version output, and error exit behavior are preserved.
- README and roadmap distinguish the implemented offline JSON workflow from
  planned live acquisition, HTML reports, and the desktop app.

### Druid analysis

- Add explicit Balance/Feral/Guardian/Restoration acquisition categories and class-aware snapshot validation.
- Add Druid action-based duty inference, damage/healing/incoming metrics, mixed activity spans, reasoned offline assignment overrides and exact applicable cohorts.
- Render Druid reports/playbooks and role/metric/timeline exports through the existing output pipeline; preserve Hunter output compatibility.
- Real-log validation and domain acceptance limits are documented in `docs/druid-validation.md`.
