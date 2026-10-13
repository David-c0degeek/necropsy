# Changelog

[Home](README.md) · [Documentation](docs/README.md) · [Roadmap](docs/roadmap.md)

Notable user-facing and developer changes. Entries under **Unreleased** are
implemented in the development checkout; they are not a published release.

## [Unreleased]

### Added

- **Warcraft Logs sign-in and character lookup (personal use).** `necropsy auth
  login | status | logout` signs in with your own confidential WCL client: the
  client secret is entered at a hidden prompt and, with your token, stored only in
  the OS credential store (never a file). `necropsy resolve <character URL>` shows
  the character, faction, raid and partition, refusing non-Warcraft Logs and not yet
  supported sites. Live acquisition comes next; a public PKCE client is required
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
