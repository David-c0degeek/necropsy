# Changelog

All notable changes to Necropsy are documented here.

## [Unreleased]

### Added
- Python 3.14 project skeleton with the `necropsy` command (`--help`, `--version`);
  output is always UTF-8 so non-ASCII player names print on any console.
- Verified read-only access to snapshot zip archives (`necropsy.snapshot.archive`):
  whole-archive digest check, unsafe/duplicate/encrypted member rejection, size
  caps, and per-member SHA-256 verification against an entries manifest.
- Frozen Haplina Naxxramas golden fixture (full raw export in Git LFS, a 13.6 MB
  subset for fast tests, oracle outputs, provenance record) and a golden-fact
  register with an acceptance gate.
- `necropsy ingest`: normalizes a v6 Hunter export (full or fixture subset) into a
  DuckDB database with explicit column types, multiplicity-preserving event
  identity, per-stream coverage and anomaly records, and atomic replacement.
  Documented in `docs/database.md`.
- Analysis foundation: evidence model (OBSERVED / DERIVED / INFERRED / UNKNOWN with
  coverage-gated absence claims), rule files shipped as package data, fight
  context, environment profile (faction, racial-proven race, talents, starting
  auras, world buffs, Darkmoon Faire, Windfury, gear), generic metrics (damage,
  casts, aura uptime, deaths, activity window), target split and cohort
  distributions. Documented in `docs/evidence-model.md`.
- Classic Era Hunter plugin: shot cadence and casts, opener, Quick Shots and
  Rapid Fire uptime, every Auto Shot interval with an advisory long-gap
  signal, melee weaving, friendly crowd control, pet classification and
  family inference, gear at the pull; WCL-style ranking damage (self-damage
  excluded, encounter exclusions pluggable). Documented in
  `docs/hunter-analysis.md`.
- `necropsy offline`: snapshot to a versioned, deterministic `analysis.json`
  (JSON Schema committed) with per-boss same-faction baseline medians, shot-target
  ranges, weave adoption, ceiling, opt-in cross-faction view, Naxxramas encounter
  rules (ranking exclusions, Gothik native targets), target-integrity and
  raid-utility findings, and evidence-linked recommendations with controllability
  and confidence tiers. Pets with no events in a fight are classified inactive.
  Inferred faction membership stays inferred through every median, range and
  ceiling; unclassifiable damage targets make the target split unknown; a reused
  `--db` never skips archive verification. Weave adoption is judged separately
  on the boss and on other NPCs; raid speed compares with the same-faction
  median kill time and always shows the fastest same-faction kill too; when the
  same faction has too few entries, proven-Tauren entries fill the missing
  medians in a separate view; every boss shows which targets count toward
  ranked damage; start-of-fight trash is no longer counted as padding.
  Documented in `docs/analysis-json.md`.
- CI on Linux and Windows (lint, strict types, fast tests) and a manual golden workflow.
