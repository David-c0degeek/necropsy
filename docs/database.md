# Analysis database

[Home](../README.md) · [Documentation](README.md) · [Reading results](reading-results.md)

`necropsy ingest <snapshot.zip> --db <file.duckdb>` normalizes a raw WCL
snapshot into a DuckDB database. Everything after acquisition reads this
database; it never needs the network.

## Rebuild, never migrate

The database is always rebuilt from the raw snapshot. A build writes to
`<db>.tmp-<pid>` beside the target and replaces the target only when the build
succeeds, so a failed ingest leaves the existing database untouched. A target
built from a different snapshot (archive SHA-256 or scope) is only overwritten
with `--replace`. Ingest refuses a target that has a `<db>.wal` file (the
database is open or was not closed cleanly), because replacing the file could
lose changes still in that log. The target must stay closed for the whole
ingest: its state is checked before the build and again just before the swap,
and a target that gained a `.wal` or changed in between is left as it is and
the ingest fails. A program that opens the target in the instant between that
last check and the swap is not detected on every platform. `snapshot_meta.schema_version` records the schema; any schema
change means a rebuild.

## Event identity

The v6 export stores, per selected Hunter and per pet, every event the actor
caused (`source_NNN.json`) and every event aimed at it (`target_NNN.json`).
Streams overlap: an event between two exported actors is in both actors'
streams. A single stream can also hold byte-identical events that really
happened twice (simultaneous hits).

- An event is identified within its fight by `event_uid`, the SHA-256 of its
  key-sorted JSON. `(report_code, fight_id, event_uid)` is the identity.
- Its count is its largest multiplicity in any single stream; `events` holds
  one row per occurrence (`copy_index` 0..n-1).
- Streams that disagree on an identity's multiplicity produce an
  `event_anomalies` row (`multiplicity-mismatch`).
- Pages are never deduplicated by content. When the events that open a page
  repeat events that closed the previous page at the same timestamp, all of
  them are kept and the stream records a `boundary_ambiguities` count.

For the Haplina export: 3,674,640 stream events → 863,536 events, no anomalies.

## Coverage and absence

`stream_coverage` has one row per expected stream: each selected participant's
source and target stream, each listed pet's streams, and a `pet-discovery` row
when a participant's `pets.json` is missing. `status` is `complete` only when
pages run contiguously from `001`, the last page's `nextPageTimestamp` is
`null`, and the export recorded no error for the stream.

Analyses may treat a missing event as "did not happen" only through
`necropsy.normalize.coverage.has_complete_coverage`, which also requires zero
boundary ambiguities and zero multiplicity mismatches. Otherwise the answer is
UNKNOWN.

Only the selected Hunters and their pets have streams. Raid-wide facts (threat,
boss target time, other players' actions) are not in the data.

## Tables

| Table | Contents |
|---|---|
| `snapshot_meta` | Schema version, snapshot format and SHA-256, scope (`full`/`subset`), subject, zone, partition, cohort, source errors |
| `snapshot_issues` | Members the reader did not recognise or could not place |
| `benchmark_participants` | Why each fight is present: the subject's fight or a cohort entry (boss, position, player, server) |
| `reports`, `fights` | Report metadata and the selected fights |
| `actors`, `abilities` | Report master data, including `pet_owner` |
| `player_details` | Per-report player role, specs, `faction_id` and raw combatant info |
| `report_rankings` | Per-fight ranking data embedded in each report |
| `rankings` | Leaderboard rows and the subject's own rankings |
| `combatant_info` | `combatantinfo` events: faction, talent points (e.g. `12/33/6`), gear, auras |
| `stream_coverage` | Completeness and trust of every expected stream |
| `events` | One row per event occurrence: typed hot columns plus the raw event as a JSON object (`json_extract(raw, '$.field')`) |
| `event_anomalies` | Multiplicity mismatches and page-boundary ambiguities |
