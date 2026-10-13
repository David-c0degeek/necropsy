# Live snapshots through the shared offline pipeline

Status: Accepted · Date: 2026-10-13

[Decision index](README.md) · [Database](../database.md) · [Analysis JSON](../analysis-json.md)

## Context

Several selected fights can share a report. Picking one per-fight bundle or
merging mismatched revisions would lose evidence. New acquisition provenance
must reach existing offline analysis without breaking historical replays or
pretending that live same-faction samples are the historical overall top five.

## Decision

Keep the historical member layout for reports, rankings and streams. Live v1
uses a strict top-level marker carrying resolved context, requested coverage,
cohort provenance, report sets and stream identities/page digests. Finalization
fetches one combined same-revision report per code for the exact selected fight
set; the offline writer makes no network calls. Validate actors, known pet lists,
request identities and pagination, and read the finished archive back before
publishing its ZIP, entries and checksum companions under a set lock. Never
replace a raw snapshot; failure rollback checks ownership and content.

Use the shared reader/normalizer/analysis pipeline for both formats. Rebuild
derived schema 2 databases from the same verified archive instead of migrating
in place. Carry origin mode, limitations and requested coverage into analysis
JSON and mode-aware presentation. Preserve rendering of existing historical JSON.

`analyze` requires output paths without previous analysis artifacts and holds a
run lock. Its report failure retains a saved snapshot with an offline recovery
command. `offline` and `render` intentionally replace derived files using staged
publication, backups and best-effort rollback. The shareable package excludes the
raw snapshot and database.

## Alternatives and consequences

A separate live analyzer and in-place database migration were rejected in favor
of one reproducible offline pipeline. A malformed live marker is an error, never
a signal to guess the historical format. Publication is a guarded file set, not
an atomic directory swap: a killed process can leave partial artifacts. Ordinary
failures are rolled back where possible; retained backups or raw snapshots support
recovery. Acquisition origin does not make saved pages refresh live data.

Implementation: [live reader](../../src/necropsy/snapshot/v1.py),
[writer](../../src/necropsy/snapshot/v1_writer.py),
[ingest](../../src/necropsy/normalize/ingest.py),
[CLI workflow](../../src/necropsy/wcl/analyze.py),
[derived publisher](../../src/necropsy/report/publish.py).
