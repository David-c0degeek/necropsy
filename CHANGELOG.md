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
- CI on Linux and Windows (lint, strict types, fast tests) and a manual golden workflow.
