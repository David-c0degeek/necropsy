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
- CI on Linux and Windows (lint, strict types, fast tests) and a manual golden workflow.
