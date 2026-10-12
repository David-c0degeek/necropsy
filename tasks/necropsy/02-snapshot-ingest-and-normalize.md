# 02 — Snapshot Ingest And Normalize

## Goal
Import the v6 export ("snapshot v0") into an immutable raw store and a DuckDB
analytical database, with event deduplication and per-stream coverage, fully
offline. Snapshot v0 ingestion stays independent of the future v1 live format.

## Integration analysis
> Fill before ticking any box in this subject. Reuse and integrate before
> adding — no new code until this is recorded (§6.17). Build on the prior-art
> map from 00.2 and the architectural direction from 00.1.
>
> **Evidence, not prose.** Each bullet names concrete files/symbols (e.g.
> `necropsy/snapshot/v0.py::read_events`), not "the relevant modules". "None
> found" is a valid answer only when it records the search that proved it (the
> grep/scan run). A generic Integration analysis that names nothing is not
> done — it is how a duplicate parallel system slips past this gate.
>
> - **Existing code found** — relevant modules, services, abstractions, workflows.
> - **Behaviour to preserve** — contracts, public APIs, tests, callers that must keep working.
> - **Reuse / extend** — what is reused, extended, or refactored instead of duplicated.
> - **Do not duplicate** — what already exists and must not be reimplemented.
> - **Integration point + why** — where the change lands and why it is the correct seam.
> - **Vision fit** — supports or conflicts with the project vision/ADRs (00.1); cite drift if any.
> - **Risks** — duplication, architectural drift, or accidental complexity introduced.

- **Existing code found** — `src/necropsy/snapshot/archive.py::VerifiedArchive` (verified zip access, D016); `scripts/fixture_tools.py::subset_members` (knowledge of the export layout); exporter `wcl_hunter_deep_export.py::export_actor_events` defines the page files (`source_NNN`/`target_NNN`, `nextPageTimestamp`). No reader, schema or ingest existed (search: `rg -n "duckdb|read_json|SnapshotReader" src tests` before this subject → none).
- **Behaviour to preserve** — raw bytes untouched (reads only); fixture tests from 01; `subset.json` authoritative for scope.
- **Reuse / extend** — `VerifiedArchive` is the only archive access path (now wired into the product through `necropsy ingest`); exporter layout knowledge reused in `necropsy.snapshot.v0`.
- **Do not duplicate** — one identity rule (`necropsy.snapshot.canonical`) shared by the reader's boundary check and the merge; tests count events with a deliberately separate implementation (`tests/independent_count.py`).
- **Integration point + why** — `necropsy.snapshot.reader.SnapshotReader` (format seam, v1 plugs in later), `necropsy.snapshot.v0.V0Snapshot`, `necropsy.normalize.{schema,ingest,coverage}`, CLI `necropsy ingest`. Analyzers (03+) read only the database.
- **Vision fit** — spec §2 step 7 (raw immutable + DuckDB), plan §6.18 (absence needs coverage), §6.21 (offline), D014 (explicit types), D016 (zip streaming).
- **Risks** — DB size (~370 MB for the full export, raw JSON per event kept for re-derivation); ingest time ~60 s; a different exporter version needs a new reader rather than branches in v0.

## Boxes
> ID = `<subject-id>.<box-number>` (subject index ID · box ordinal). Stable — never
> renumber; mark retired boxes done and struck with `ABANDONED; see D###`
> (see §4), don't delete. A human-owned box recorded `DEFERRED` in
> `manual-actions.md` stays `[ ]` and follows the §5 Done rule.
> Owner MUST be one of the §5 enum:
> agent · release-engineer · product-owner · tech-lead · domain-sme.

- [x] **02.1** (agent) Snapshot contract: Pydantic models for the snapshot
      manifest (format version, source, hashes, subject, cohort definition,
      mode) and one reader interface that v0 and v1 both implement.
- [x] **02.2** (agent) v0 reader for every file kind in the v6 layout; unknown
      files are reported, not silently skipped.
- [x] **02.3** (agent) DuckDB schema (spec §7 tables trimmed to what Milestone A
      uses: characters, reports, fights, actors, pets, abilities, events,
      combatant_info, gear, talents, buffs, rankings, benchmark_sets,
      stream_coverage) with a schema version; migration = rebuild from raw.
      Every column type is declared explicitly; no JSON auto-inference.
      As shipped (D018): `snapshot_meta` (subject = characters), `snapshot_issues`,
      `benchmark_participants` (= benchmark_sets), `reports`, `fights`, `actors`
      (pets are actors with `pet_owner`), `abilities`, `player_details`,
      `report_rankings`, `rankings`, `combatant_info` (talent points, gear and
      auras as JSON — no separate gear/talents tables), `stream_coverage`,
      `events` (buffs/debuffs are event types, no separate buffs table),
      `event_anomalies`.
- [x] **02.4** (agent) Event dedup contract: source and target streams of the
      same actor, and overlapping actors (player target stream vs pet source
      stream), never double count. Define event identity (report, fight,
      timestamp, type, source, target, ability, disambiguator). Identity
      reconciles **multiplicity**, never set-uniques payloads: the count of an
      event identity is taken from one authoritative stream, and copies seen in
      overlapping streams or repeated pages are matched against that count, not
      collapsed to one. Tests cover self-targeted buffs, pet events,
      player/pet overlap, and a regression case with two distinct byte-identical
      events in one authoritative stream (e.g. simultaneous hits) plus copies of
      both in an overlapping stream and a repeated page boundary — result is
      exactly two.
      Amended by D018: identity is `(report, fight, sha256(canonical JSON))`;
      overlapping-stream copies reconcile to exactly the authoritative count
      (`test_identical_hits_survive_overlapping_streams`), but page-boundary
      repeats are **kept** and flagged (`boundary_ambiguities`), never removed,
      because v0 has no page provenance to prove a replay.
- [x] **02.5** (agent) Stream coverage: per report+fight+actor+stream records
      requested, fetched pages, completeness, and fetch errors. Absence queries
      join coverage; missing coverage yields `UNKNOWN`.
- [x] **02.6** (agent) `necropsy ingest <snapshot> --db <path>` CLI; fast test
      on subset; golden test on full fixture (row counts, zero duplicate
      events, coverage complete for all 89 selected fights, timing recorded).

## Hindsight checkpoint
> Run after all boxes in this subject are complete and before marking
> the subject `DONE` in §5. Use the embedded prompt in "Appendix: Captain
> Hindsight Prompt". Record the review result here. An interim run after
> a large or risky box is allowed and recorded the same way; it does not
> replace the closing run. In this coordinated pair plan, the navigator's
> `VERDICT AGREE` on the subject's diff precedes the Hindsight run.
>
> Required output sections: Keep; Fix before closing; Record; Risk;
> Verdict (`CLOSE` or `DO NOT CLOSE`). If the verdict is `DO NOT CLOSE`,
> leave the subject open, add/reopen boxes or update decisions/lessons,
> and rerun this checkpoint after the fixes.

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

**Captain Hindsight — 2026-10-13 (after navigator `VERDICT AGREE round=3`)**

1. **Keep:** reader protocol separates layout from ingest; multiplicity-preserving identity verified against an implementation that shares no code (863,536 both ways); coverage trust combines fetch completeness with ambiguity/mismatch counts; raw event kept as a queryable JSON object; atomic rebuild with pre-build and pre-swap target checks; NDJSON bulk load (executemany was unusable).
2. **Fix before closing:** none open. Review caught and fixed: the agreed design still described content-based page dedup (CHALLENGE, now D018), `raw` stored as a JSON string, deleting the target's WAL before the swap, single-event-only boundary detection, and a WAL appearing during the build.
3. **Record:** D018 (kept page repeats, shipped table set). Lesson: atomic file replacement must re-validate the target immediately before the swap and never touch sidecar files it does not own. Lesson: a JSON column fed from NDJSON must receive objects, not pre-serialized strings.
4. **Risk:** residual race between the final target check and the swap (documented); database size ~370 MB for the full export; ingest ~60 s; v0 reader is specific to the v6 layout by design.
5. **Verdict:** CLOSE

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
2026-10-13 · slice 1 · 02.1–02.6 · design huddle (Codex CHALLENGE on page-boundary dedup accepted: keep all occurrences, record ambiguity), snapshot model + `SnapshotReader` protocol + `V0Snapshot`, DuckDB schema v1 (14 tables, explicit types), multiplicity-preserving merge, coverage + `has_complete_coverage`, atomic rebuild with `--replace` policy, `necropsy ingest`, NDJSON bulk load (executemany measured 325 s / 50k rows), docs/database.md, README, CHANGELOG, profiling evidence in `evidence/02-*` · observed: subset ingest 12 fights / 114 streams complete / 123,109 events / 0 anomalies / 10 issues (unselected Dwarfazz data) in ~9 s; full ingest 89 fights / 762 streams complete / 3,674,640 stream events → 863,536 events (= independent count) / 0 anomalies / 0 issues in 58 s; Haplina combatant talents 12/33/6; fast suite 80 passed, golden 4 passed; ruff + mypy strict clean · commit pending pair review
2026-10-13 · slice 2 · 02.3, 02.4, 02.5 · review round 1 fixes: `events.raw` stored as JSON object (was a JSON string), target WAL never deleted (ingest refuses a target with a `.wal`), boundary ambiguity detects any repeated same-timestamp group, box text amended (D018) · regression tests added (raw JSON queries, repeated group withholds coverage, WAL refusal, failed replace, busy DB on Windows) · fast 88 passed · commit pending pair review
2026-10-13 · slice 3 · 02.5 · review round 2 fix: target re-checked (WAL + identity + size/mtime) immediately before the swap; late-WAL and changed-target regressions in both modes; residual race documented in docs/database.md and `ingest` docstring · fast 92 passed · commit pending pair review
2026-10-13 · slice 4 · Hindsight · commit with CI run 38319784456 success (ubuntu + windows); Hindsight CLOSE · pushed
