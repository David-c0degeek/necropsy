# Changelog

[Home](README.md) · [Documentation](docs/README.md) · [Roadmap](docs/roadmap.md)

Notable user-facing and developer changes. Versioned entries describe repository
versions; the published GitHub release is listed on the releases page.
Development changes appear under **Unreleased** until built and published.

## Unreleased

No additional changes beyond 0.2.0 below.

## 0.2.0 - 2026-10-15

### Added

- Default guided Textual TUI: character-link entry, browser sign-in, automatic
  faction/endpoint/path choices and class-appropriate spec/partition controls.
- Saved-run library with status, offline report opening, checkpoint continuation
  and older CLI-run import/recovery. Stop safely, close and return later.
- Automatic repeated quota waits with a visible countdown. Successful requests,
  interrupted stream pages and finalized reports are reused across attempts.
  Sparse or inaccessible data does not cause endless quota retries.
- Windows/macOS/Linux bootstrap scripts install private uv and managed Python,
  verify the wheel checksum/version and create OS launchers. No Git, GitHub
  login or preinstalled Python/uv is needed. Existing data/sign-in is preserved.
- Fresh bootstrap and failed-upgrade checks; headless TUI and supervisor tests.
  CI now covers all three OS families.

### Changed

- All active onboarding now leads with one install command and guided controls.
  Advanced CLI commands and saved snapshot/cache formats remain compatible.
- Public distribution replaces the old private-repository installation barrier.
  Real account/vault validation remains distinct from synthetic platform checks.

## 0.1.1 — built locally, not published as a GitHub release

### Added

- Live terminal activity, phase/boss progress and retry/reset-wait messages.
- Durable per-run request checkpoints and `analyze --resume`, including event
  pages from interrupted streams and completed finalization responses.
- Resume validates run options, character context and output digests, retains
  earlier snapshots and preserves original leaderboard capture times.
- Small-quota acquisition keeps comparison headroom when finalization can span
  attempts. Rate-limit errors with response data stop cleanly for recovery.
- Clean-installed artifact checks verify the current design and exact embedded
  CSS/JavaScript, alongside package integrity and synthetic public sign-in.

### Changed

- Rebuilt the generated application around character identity, a severity-ordered
  shortlist of existing findings, boss triage and an action → explanation → evidence
  workflow. Playbook emphasizes preparation; Report emphasizes investigation.
- Added composable class, faction and raid styling, an original geometric brand,
  intentionally designed dark/light surfaces and compact mobile navigation.
  No remote assets, fonts, dependencies or automatic requests were added.
- Added encounter filters for findings, limited comparisons and local review state.
  View switching retains the current boss; evidence jumps reveal nested details.
  Full cohorts, gear, timelines, analytical limitations and print expansion remain.
- Reworked the product README, onboarding, documentation navigation and result-reading
  guide with screenshots captured from actual generated sample output.

Analytical rules, JSON schema, saved evidence and output filenames are unchanged.

## [0.1.0] - 2026-10-15

### Added

- Public S256 PKCE login, separate mode-tagged OS-store records, explicit user
  acquisition and an isolated wheel/sdist installation audit are implemented.
  Personal clients use `auth login --mode personal`. Registered public login,
  refresh rotation and query access are verified; independent-user acceptance
  and publication are approved by the product owner. See
  [installation](docs/installation.md).

### Changed

- **Shared playbook layout and ability comparisons.** Druid pages now use the
  Hunter playbook's boss panels, metric cards, raid sheet, setup/execution cards,
  review controls and full gear/enchants components. Both classes show
  **Ability use vs [player]**, including recorded spells, shots, melee abilities
  and cooldowns as counts and uses per minute. Passive ticks and pet actions are
  separate; incomplete streams remain unknown. Packages include ability-use CSV.

- **Faction and spec choices.** Interactive character lookup asks for faction and
  spec; `--faction` and `--spec` support scripts, including Classic Era Hunter
  Marksmanship. Main playbooks use faction leaders even without a personal
  encounter. Overall-top comparisons are separately collapsed by default with
  faction context. Existing noninteractive commands remain compatible.

- **Useful sparse Druid comparisons.** One or two same-spec/faction sources now
  show individual measurements and differences, with limited-sample labels.
  Talent-point builds remain visible instead of excluding same-spec players.
  Playbooks add direct spell-count/cast-rate comparisons and separate WCL-score
  comparisons. Multi-boss acquisition captures ranking references across the raid
  before deep sampling. Both Hunter and Druid skip known other-faction guild rows
  before fetching deep reports; unknown factions still receive checks.

- **Selected Druid spec views.** `--spec Balance`, `Restoration`, `Feral` or
  `Tank` filters personal analysis by category and evidenced duty while keeping
  every requested boss visible. Missing personal encounters can show eligible
  top-player learning examples, separately from rank-one metadata and personal
  comparisons. Multi-boss acquisition gets personal fights first, prioritizes
  examples for subject-less bosses and reserves budget for fresh finalization.

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

Druid execution plans now use the same labelled plan rows as Hunter: opener, individual core abilities and recorded cooldowns, first-use timing, counts/cadence, target context and resource review. Weapons/trinkets/relic/world buffs share the same loadout hierarchy. Each comparison retains source fights; incomplete or missing personal streams stay unknown.

All Classic Era classes now support class/category selection, evidence-qualified duties, faction leaders, sparse comparisons and the shared playbook/execution/ability layout. Other classes use additive schema1 combat data and common exports. Supported API ranking labels remain distinct from talent builds; missing personal data stays ungraded.
