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

- **Existing code found** — TBD
- **Behaviour to preserve** — TBD
- **Reuse / extend** — TBD
- **Do not duplicate** — TBD
- **Integration point + why** — TBD
- **Vision fit** — TBD
- **Risks** — TBD

## Boxes
> ID = `<subject-id>.<box-number>` (subject index ID · box ordinal). Stable — never
> renumber; mark retired boxes done and struck with `ABANDONED; see D###`
> (see §4), don't delete. A human-owned box recorded `DEFERRED` in
> `manual-actions.md` stays `[ ]` and follows the §5 Done rule.
> Owner MUST be one of the §5 enum:
> agent · release-engineer · product-owner · tech-lead · domain-sme.

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

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
