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

Schema 3 reads historical v6 exports and Necropsy live snapshots v1/v2. A schema
1 or 2 database for the same verified archive is rebuilt atomically; it is not reused
with missing columns. Existing historical `analysis.json` files remain renderable
without rebuilding their database. Live provenance records requested boss
coverage separately from the acquired fights available for detailed analysis.

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

New live snapshots can include `confirmed_pets.json` while retaining the missing
discovery row. These actors have proven ownership and individually evidenced
streams; the full pet roster remains incomplete. A separate Hunter-pet roster
can be complete when every unresolved actor is positively classified as a
non-Hunter pet by its game ID. This never completes combined all-pet damage.

Original single-fight report generations and optional `combatant_context.json`
are retained with their acquisition digests. Context contains an earlier raw
combatant snapshot and fully paginated recipient buff changes up to the ranked
window. It is stored separately from `events`, so pre-window casts and damage
cannot enter ranked totals or per-minute rates. Older snapshots without this
evidence retain their limitations. Updated readers accept the added members;
old readers may refuse new partial-ownership snapshots safely.

Analyses may treat a missing event as "did not happen" only through
`necropsy.normalize.coverage.has_complete_coverage`, which also requires zero
boundary ambiguities and zero multiplicity mismatches. Otherwise the answer is
UNKNOWN.

Historical/v1 archives contain selected actors and their pets. Live v2/v3
archives additionally certify unfiltered whole-fight events and server-filtered
critical damage. These use actor null, direction `all`, and separate `encounter`/
`critical` roles. The reader proves their bounds, revision, endpoint, pagination
and page digests, and requires actor/critical events to be raw subsets of the
unfiltered data. Existing maximum-multiplicity merging retains each occurrence
once across these overlapping views. No table or column changes.

Live v3 Naxx target pages are byte copies of the certified encounter-All pages.
Their archive proof has no actor request identity and binds the actual All
parent instead. Ingestion retains the same selected actor `target` coverage;
unselected actors gain no certificate. Earlier formats keep their original
proof requirements. See [derived targets](decisions/0024-derived-target-streams.md).

Encounter coverage is separate from player/pet source/target coverage. An
unselected actor's events can be observed without a complete actor-direction
certificate. Filtered critical coverage cannot establish unrestricted cast or
phase absence. These data do not by themselves establish threat, positioning,
assignment, targetability or a validated ranking/opportunity policy.

## Tables

| Table | Contents |
|---|---|
| `snapshot_meta` | Schema version, snapshot format and SHA-256, scope (`full`/`subset`), subject, zone, partition, cohort, source errors; schema 2 adds `mode` (`historical`/`live`), `limitations` and the live `acquisition` provenance |
| `snapshot_issues` | Members the reader did not recognise or could not place |
| `benchmark_participants` | Why each fight is present: the subject's fight or a cohort entry (boss, position, player, server) |
| `reports`, `fights` | Report metadata and the selected fights |
| `actors`, `abilities` | Report master data, including `pet_owner` |
| `player_details` | Per-report player role, specs, `faction_id` and raw combatant info |
| `fight_player_details` | Exact single-fight combatant metadata, source member and report-content digest; no multi-fight aggregate fallback |
| `combatant_context` | Validated raw earlier snapshot and pre-window buff pages, with actor, fight, revision and source binding |
| `report_rankings` | Per-fight ranking data embedded in each report |
| `rankings` | Leaderboard rows and the subject's own rankings |
| `combatant_info` | `combatantinfo` events: faction, talent points (e.g. `12/33/6`), gear, auras |
| `stream_coverage` | Completeness and trust of every expected stream |
| `events` | One row per event occurrence: typed hot columns plus the raw event as a JSON object (`json_extract(raw, '$.field')`) |
| `event_anomalies` | Multiplicity mismatches and page-boundary ambiguities |
