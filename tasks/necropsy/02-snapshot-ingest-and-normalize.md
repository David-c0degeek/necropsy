# 02 — Snapshot Ingest And Normalize

## Goal
Import the v6 export ("snapshot v0") into an immutable raw store and a DuckDB
analytical database, with event deduplication and per-stream coverage, fully
offline. Snapshot v0 ingestion stays independent of the future v1 live format.

## Integration analysis
> Fill before ticking any box (§6.17).

- **Existing code found** — TBD
- **Behaviour to preserve** — TBD
- **Reuse / extend** — TBD
- **Do not duplicate** — TBD
- **Integration point + why** — TBD
- **Vision fit** — TBD
- **Risks** — TBD

## Boxes
- [ ] **02.1** (agent) Snapshot contract: Pydantic models for the snapshot
      manifest (format version, source, hashes, subject, cohort definition,
      mode) and one reader interface that v0 and v1 both implement.
- [ ] **02.2** (agent) v0 reader for every file kind in the v6 layout; unknown
      files are reported, not silently skipped.
- [ ] **02.3** (agent) DuckDB schema (spec §7 tables trimmed to what Milestone A
      uses: characters, reports, fights, actors, pets, abilities, events,
      combatant_info, gear, talents, buffs, rankings, benchmark_sets,
      stream_coverage) with a schema version; migration = rebuild from raw.
- [ ] **02.4** (agent) Event dedup contract: source and target streams of the
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
- [ ] **02.5** (agent) Stream coverage: per report+fight+actor+stream records
      requested, fetched pages, completeness, and fetch errors. Absence queries
      join coverage; missing coverage yields `UNKNOWN`.
- [ ] **02.6** (agent) `necropsy ingest <snapshot> --db <path>` CLI; fast test
      on subset; golden test on full fixture (row counts, zero duplicate
      events, coverage complete for all 89 selected fights, timing recorded).

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
