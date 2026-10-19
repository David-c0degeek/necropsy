# Changelog

[Home](README.md) · [Documentation](docs/README.md) · [Roadmap](docs/roadmap.md)

Notable user-facing and developer changes. Versioned entries describe repository
versions; the published GitHub release is listed on the releases page.
Development changes appear under **Unreleased** until built and published.

## Unreleased

## 0.5.0 - 2026-10-19

- Add `NECROPSY_CREDENTIAL_FILE` for unattended POSIX servers without an OS
  credential store (ADR 0023). The file must be a regular 0600 file in a 0700
  directory owned by the running user; any failed check refuses, with no
  fallback. `necropsy auth export | ssh server '... necropsy auth import'`
  moves a sign-in from your computer without a temporary token file. Desktop
  and terminal sign-in keep using the OS store.
- Add `necropsy analyze --outcome-json FILE`, a small machine-readable result
  for unattended runners: the exit code, stop class, known quota reset time,
  snapshot path and SHA-256, and the run checkpoint's SHA-256. An unknown reset
  time is recorded as unknown, never guessed.

- Show recorded Garr Warlock Curse of Recklessness, Curse of the Elements and
  Curse of Shadow applications with the curse, target and time, and ask which curse your raid assigned before copying a reference
  choice. Curses are not uptime, assignment or benefit evidence.

- Verify Garr Firesworn Banish applications against literal event identity,
  roster and instance bindings, and name each recorded add, instance and time in
  a control review prompt. Counts from older snapshots without full encounter
  coverage are now unknown; their recorded applications stay visible.

- Split recorded Priest absorption by ability and recipient on both raid pages.
  Review shield recipients separately from other absorption; keep effect counts,
  casts, assignments and healing quality distinct, with incomplete totals unknown.

- Show raid-roster Shaman interruptions of Sulfuron's Dark Mending on both pages,
  naming the actual sources and target instances. Keep selected-player utility,
  ranking scores and unknown interrupt opportunities separate.

- Show owned summon healing and credited absorption separately on both raid
  pages. Verify individual ownership and event integrity; keep actor totals,
  WCL scores and unresolved pet listings separate.

- Show recorded Priest Dispel Magic and Paladin Cleanse removals of Ignite Mana
  on Geddon, with unambiguous exposure
  endpoints alongside self-dispels. Keep coordination advice separate from
  reaction quality, saved mana and unknown dispel opportunities.

- Show recorded Priest Dispel Magic removals of Chromaggus Blue affliction,
  separate from casts and effects performed by other players. Keep conflicting
  ownership or chronology unknown instead of reporting a count or absence.

- Withhold complete NPC aura counts and windows when other streams add events
  beyond the certified encounter read; preserve the positive transitions.

- Retain observed Skeram image summons and per-instance event bounds. Preserve
  overlapping groups and unknown endpoints without claiming damage opportunity.

- Require a supported positive same-faction pet comparison before advising a
  Hunter to bring a pet. Preserve recorded absence when that advice is withheld.

- Preserve measured aura exposure across recorded Feign Death. Keep genuine
  deaths and resurrections as state resets, and leave malformed death flags unknown.

- Keep Hunter opening guidance explicit when no comparable ranged opening is
  recorded, and hide the reference ability section when no comparison exists.

- Retain observed AQ40 boss aura state separately for Sartura, Huhuran, Twin
  Emperors and Ouro, plus personal Sand Blast exposure. Unnumbered NPC windows
  require exact fight metadata proving a single instance; missing C'Thun
  vulnerability transitions do not supply a timed weakening window.

- Add initial sourced strategy and facts for every AQ40 boss, with conditional
  control, poison/Frenzy handling, target, tank and healing coordination. Keep
  static strategy separate from observed phase windows and ranking eligibility.

- Keep practice guidance explicit when no eligible recorded comparison exists;
  do not suggest copying an unavailable leader's opener or ability mix.

- Add observed BWL player aura exposure with labelled cohort examples. Preserve
  unknown initial state, lifecycle resets and censored effects; reject coerced
  raw recipient/spell identities before certifying durations or absence.

- Add initial sourced strategy for every individual Blackwing Lair boss:
  controller protection, resource and threat recovery, affliction removal and
  nine class-call responses. Keep static advice separate from measured phases,
  personal assignments and validated rankings; preserve missing personal data.

- Keep the reference player's build and duty out of personal Report context
  when personal data is missing. Preserve recorded excluded personal context
  separately from the reference and keep unknown personal duty explicit.

- Track observed Garr Banish state separately for each add instance and rank.
  Keep other Warlocks’ encounter-wide effects distinct from personal counters;
  retain unknown initial state, scope, class and malformed identity limits.

- Preserve frozen evidence hashes across Git staging/checkouts. Add staged
  receipt verification for metadata bytes and LFS object identities/sizes.

- Collect whole-fight and critical-damage context in normal MC/BWL/AQ40 Era
  analyses through the existing quota/cache/resume path. Preserve Naxx capture
  behavior, old archives and explicit incomplete encounter coverage.

- Add initial Ragnaros knockback recovery, conditional Sons control and
  class-specific party support strategy. Retain a full ten-boss Molten Core
  capture with independent actor/support checks and explicit unknown pet ownership.

- Keep partial-acquisition retry advice independent of quota resets and preserve
  the declared talent tree in the printed resume command.

- Correct class Report event identities to show numeric copy indices; avoid
  dictionary method addresses and restore deterministic report/package bytes.

- Measure credited friendly absorption separately from incoming mitigation and
  boss effects. Show combined friendly healing and shielding beside heal-only
  values; preserve unknown source/recipient/amount/coverage and saved scores.
- Add observed Golemagg Magma Splash exposure with real melee examples, retaining
  unknown initial state and censored effects without inventing stack thresholds
  or tank assignments.

- Add initial Golemagg tank/healing coordination and Majordomo add/control and
  shield strategy. Preserve observed Majordomo buff state separately for each
  add instance, with unknown initial state and scoped encounter coverage;
  show saved observations in both pages without inventing personal opportunities.

- Add initial Sulfuron add-target, interrupt-backup and divided healing strategy.
  Separate general assignments from observations; nominal cast times and absent
  personal interrupts do not establish missed opportunities.

- Add initial Shazzrah positioning, Blink recovery and class-specific removal
  strategy, sourced facts and personal Curse exposure. Keep friendly curses
  separate from hostile Magic buffs and retain unknown initial state.

- Add initial Baron Geddon bomb separation, Inferno recovery and class-specific
  support strategy. Preserve Ignite Mana observations active at fight end;
  distinguish aura exposure from mana loss, dispel quality and bomb handling.

- Add initial Gehennas curse-removal, patient-healing and positioning strategy,
  sourced facts and personal Curse exposure. Keep healing received by cursed
  targets separate from the healer's own exposure and outgoing HPS.

- Add initial Garr add-control and raid-coordination strategy. Record Warlock
  Banish applications separately from casts, retain individual Firesworn
  instances and unknown coverage, and show the evidence in both pages without
  treating zero applications as a failed assignment or control-uptime score.

- Add initial Magmadar preparation, fear recovery and Hunter/healer strategy,
  sourced facts, local Panic observations and exact Frenzy-removal evidence.
  Match the boss NPC and removing spell; keep missing identity unknown and
  successful effects separate from casts and available opportunities.

- Add observed actor-debuff windows for Lucifron and combined Ebonroc/Flamegor.
  Keep initial, contradictory and incomplete states unknown, show known exposure
  beside unknown time in both pages, and avoid inventing phases or DPS penalties.
- Record successful Lucifron mechanic-removal effects separately from casts for
  personal and acquired examples. Preserve unknown counts under incomplete
  coverage or unusable metadata; do not infer assignments or utility grades.

- Qualify new Era raid healing by recipient. Separate friendly support from
  healing credited to bosses and unresolved targets, preserve raw source totals,
  and disclose real mechanic-healing examples in both pages.

- Keep new Era raid duty uncertain when repeated boss melee pressure conflicts
  with a narrow action-based classification. Show personal boss pressure even
  when excluded from comparisons; preserve historical Naxx duty behavior.

- Add initial sourced preparation, execution and coordination strategy for
  Lucifron, combined Ebonroc / Flamegor and Viscidus, including class/metric
  utility context. General strategy stays separate from personal findings and
  observed phases; remaining raid-domain coverage is still incomplete.
- Add immutable public raid seed fixtures, independent raw measurement and
  mutation checks, and an explicit evidence-completeness gate. Preserve all four
  historical Naxx artifacts byte for byte against the pre-expansion engine.

- Add independent AQ40, Blackwing Lair and Molten Core raid modules. Select a raid
  before analysis; generate its own snapshot, Report and Playbook, and filter
  saved analyses by raid in the desktop and terminal apps. The CLI accepts
  `--raid aq40`, `--raid bwl` and `--raid mc`.
- Preserve raid identity through stop/resume, imported analyses and offline replay.
  New raids keep unvalidated ranking exclusions and missing encounter facts
  explicit; WCL-recorded Hunter scores remain usable without invented totals.

## 0.4.0 - 2026-10-16

- Separate optional game talent-tree declarations from WCL comparison categories
  in the desktop, terminal and CLI (`--talent-tree`). Save declarations through
  resumes and offline snapshot replay; retain legacy category flags.
- Show recorded talent totals and derived primary trees separately from WCL
  classifications, inferred duties, race evidence and catalog consistency.
  Category comparisons remain broad across builds. Reject malformed talent
  triples and keep unknown build matches unknown.
- Recorded WCL Hunter DPS remains available when event reconstruction is blocked
  by unresolved pet ownership, with an explicit source and limitation.
- Acquire confirmed pets independently of ownerless raid guardians. Hunter-pet
  comparisons can remain complete when only known engineering guardians have
  unresolved owners; complete combined damage still requires all ownership.
- Preserve original fight-scoped combatant metadata. Recover missing talent
  splits and, for encounters such as Kel'Thuzad, reconstruct starting auras from
  earlier combatant snapshots and the intervening recipient buff events.
- Reuse qualified family evidence from the same pet and owner in another
  acquired fight. Ambiguous families show their candidates.
- Restore optional overall-leader metadata for selected Marksmanship analyses.
  Show known pet absence, no Windfury procs and insufficient clean shot samples
  explicitly; omit repeated empty race columns without guessing race.
- Database schema 3 rebuilds older databases from their verified snapshots.
  Existing snapshots and analysis documents remain readable.

## 0.3.1 - 2026-10-16

- Loatheb recognizes sparse healing activity under Corrupted Mind and explains
  why whole-fight healing cadence advice does not apply.
- Druid event comparisons and recommendations remain available without talents;
  unknown builds stay labelled unknown.
- WCL sparse zero-overheal fields no longer invalidate whole-fight healing totals.
- Restoration review prompts now cover cast rates, throughput and cooldown use
  with sample counts and assignment caveats. Comparison warnings identify missing
  primary measurements instead of flagging unrelated tank fields for healers.

## 0.3.0 - 2026-10-16

- One-line installers, OS shortcuts and bare `necropsy` open the graphical app
  by default. Explicit `necropsy tui` and advanced commands remain available.
- Setup checksums the CLI and native GUI packages, verifies GUI/engine readiness
  before switching launchers, and preserves existing reports, cache and sign-in.
- Native portable packages for Windows x64, both Mac architectures and Linux x64;
  Linux installation uses an extracted AppImage runtime without requiring FUSE.
- Graphical desktop app using Tauri/React and the existing Python service:
  guided character/spec setup, browser sign-in, saved analyses, stop/resume,
  quota countdown and cooperative save-before-quit.
- Embedded Playbook/Report using the existing templates and themes, class
  accents, persistent local review marks, offline example/snapshot import and
  package export through native dialogs.
- Frozen Python engine and Windows/macOS/Linux desktop packaging workflow.
  Windows offline window/engine checks are separate from real-account and
  macOS/Linux acceptance; see the desktop guide.

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
