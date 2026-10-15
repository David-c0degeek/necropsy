# Class analysis and encounter duties

Status: accepted engineering contract; domain acceptance is separate.

The existing class registry dispatches analysis by the report actor's observed
class. Hunter and Druid share acquisition, cache, snapshot verification,
normalization, evidence factories, document generation, rendering assets and
package publication. Class-specific document sections and templates describe
different measurements through those same entry points.

Build, WCL category, observed action signals, inferred encounter duty and user
assignment override are distinct. Talents alone never establish duty. Categories
are verified against WCL's game data: Druid Balance/Feral/Guardian default to DPS
and Restoration uses HPS. Balance also supports explicitly selected HPS, as
observed in character rankings. A Balance build can have a healing assignment.
Guardian DPS is a ranking category score, never tank quality.

Druid primary baselines require exact known class, encounter, faction, build,
category, duty, ranking metric and partition. Mixed, unknown or overridden duties
do not have a whole-fight single-role baseline. Inferred duty membership cannot
produce an observed/confirmed median. Different builds remain visible without
silently filling the sample. Three known values are required.

A Druid view selects one spec/category and ranking metric for every requested
boss. Personal grading requires matching inferred duty as well as category.
Absent/incompatible personal data stays absent; every requested boss still
renders, including empty and unattempted bosses. Compatible top-player examples
are a separate learning surface, never substitutes for the subject or baseline.
Rank-one saved metadata does not establish an eligible event example.

Multi-boss Druid acquisition gathers personal fights before comparisons, then
prioritizes subject-less bosses in stable encounter order. A conservative reserve
based on observed report-fetch account points protects fresh finalization;
comparison collection cannot wait on that reduced allowance. The original policy
is restored even on exceptions. Hunter's request order and serialization remain.

Snapshot v1 remains readable for Hunter. Optional Druid category metadata and
explicit metric dimensions preserve its query semantics; a category-only key can
derive its default metric from the verified category policy. Explicit metric
selection is retained in new Druid snapshot subjects and comparison keys. The reader rejects
conflicting participant/category/metric data. Raw member bytes, report-generation
digests, page proofs and provenance remain verified. No database table changes
are needed: existing normalized events and retained raw payloads contain the data.

Analysis schema 1 gains an optional `druid` entry section. The legacy `hunter`
section is optional for other classes and retained exactly for Hunter outputs.
Existing Hunter documents still render; the included replay remains byte-identical.
This additive change does not require rewriting archived raw logs or analyses.

Role overrides are explicit, reasoned subject-fight assignments. They survive in
the analysis document, preserve conflicting evidence and disable aggregate role
comparison. Missing resource/mitigation/threat/form/assignment data stays unknown;
synthetic tests do not substitute for real logs or domain review.
