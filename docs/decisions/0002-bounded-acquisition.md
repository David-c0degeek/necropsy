# Bounded acquisition with explicit context and fair cohorts

Status: Accepted · Date: 2026-10-13

[Decision index](README.md) · [Reading results](../reading-results.md)

## Context

A report can look persuasive while comparing the wrong site, partition, faction
or sample. API throttles and incomplete pages also need a bounded, visible result.
Guild faction and player faction use different fields and cannot share a mapping
without evidence.

## Decision

Parse supported HTTPS character URLs before credential access. Resolve the
supported zone's partition list and return ambiguity for a user choice. Treat
character faction as observed only for canonical names. Keep one selected API
endpoint throughout acquisition; never downgrade after a permission failure.
Bound retries, deadlines, backoff, pagination and budget policy.

Record every cohort dimension as enforced, recorded or unknown. Seek five deep
same-faction entries, with three known values needed for medians, and up to 25
metadata entries including the deep sample. Guild faction supplies inference;
only observed same-faction report actors enter the deep cohort. Record unresolved,
contradicted and inaccessible candidates rather than silently counting them.
Optional other-faction overall #1 is separate context. Select the subject's
highest ranking `amount` with deterministic ties and exclude conflicting duplicates.

## Alternatives and consequences

The historical overall top five remains replayable, but is not a separately
selected same-faction top five. Paging deeper improves the live sample without
making it a population estimate. Treating guild faction as proof or adding
metadata-only rows to event medians was rejected. Unknown and partial coverage
remain visible; an API budget stop may prevent finalization and produce no report.

Implementation: [client](../../src/necropsy/wcl/client.py),
[context](../../src/necropsy/wcl/context.py),
[cohort](../../src/necropsy/wcl/cohort.py),
[acquisition](../../src/necropsy/wcl/acquire.py).

An explicit `analyze --wait-for-reset` permits one observed hourly reset wait per
run, capped at one hour and interruptible. It keeps the acquisition in memory
and the output lock held rather than repeating fresh candidate verification.
Default runs still stop without waiting. Combined reports stay fresh and revision
checks still refuse changed evidence after the wait. The receipt/summary records
the wait, while cross-reset account-point attribution stays unknown.

