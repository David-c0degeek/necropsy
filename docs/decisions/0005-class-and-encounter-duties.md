# Class analysis and encounter duties

Status: accepted engineering contract; domain acceptance is separate.

The existing class registry dispatches analysis by the report actor's observed
class. Hunter and Druid share acquisition, cache, snapshot verification,
normalization, evidence factories, document generation, rendering assets and
package publication. Class-specific document sections and templates describe
different measurements through those same entry points.

Build, WCL category, observed action signals, inferred encounter duty and user
assignment override are distinct. Talents alone never establish duty. Categories
are verified against WCL's game data: Druid Balance/Feral/Guardian use DPS and
Restoration uses HPS. Guardian DPS is a ranking category score, never tank quality.

Druid primary baselines require exact known class, encounter, faction, build,
category, duty, ranking metric and partition. Mixed, unknown or overridden duties
do not have a whole-fight single-role baseline. Inferred duty membership cannot
produce an observed/confirmed median. Different builds remain visible without
silently filling the sample. Three known values are required.

Snapshot v1 remains readable for Hunter. Optional Druid category metadata and
explicit metric dimensions preserve its query semantics; a category-only key can
derive its metric solely from the verified category policy. The reader rejects
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
