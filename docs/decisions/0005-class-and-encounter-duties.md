# Class analysis and encounter duties

Status: accepted engineering contract; domain acceptance is separate.

The shared lookup/display rule is character → faction and spec → that faction's
leaders. Interactive acquisition asks for those choices; flags support scripts.
The chosen faction is verified against the character before deep acquisition.
Missing personal encounters retain a leader-based practice playbook without
personal grading. Race and talent-point builds remain context. Unfiltered overall
leaders appear in a separate, collapsed disclosure with faction-difference
caveats. Apply this rule to every supported class plugin; current analyzers are
Hunter and Druid. Classic Era's game-data response exposes Hunter's Marksmanship
ranking category; explicit Hunter spec selection uses it rather than inventing
additional categories. Existing unselected Hunter archives retain their format.

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

Druid primary baselines require exact known class, encounter, faction,
category, duty, ranking metric, difficulty and partition. Mixed, unknown or overridden duties
do not have a whole-fight single-role baseline. Inferred duty membership cannot
produce an observed/confirmed median. Following the user's comparison correction,
known talent-point builds are recorded per source rather than filtered inside
the selected spec/faction group; differing-build counts remain explicit. One or
two sources provide individual comparisons with limited-sample labels. Three
known values are still required for a cohort median and its recommendation rule.
Saved ranking scores compare only against saved ranking scores, independently
of event metrics. Missing personal data never produces a personal gap.

A Druid view selects one spec/category and ranking metric for every requested
boss. Personal grading requires matching inferred duty as well as category.
Absent/incompatible personal data stays absent; every requested boss still
renders, including empty and unattempted bosses. Compatible top-player examples
are a separate learning surface, never substitutes for the subject or baseline.
Rank-one saved metadata does not establish an eligible event example.

Multi-boss Druid acquisition gathers personal fights, then first-page ranking
references across requested bosses before deep comparisons, prioritizing
subject-less bosses in stable encounter order. Prefetched pages are reused only
under an identical category/metric/faction/encounter/partition/endpoint identity;
completed prefetch order is validated and retained in new snapshots. Explicit
selected-spec Hunter views use the same orchestration. A conservative reserve
based on observed report-fetch account points protects fresh finalization;
comparison collection cannot wait on that reduced allowance. The original policy
is restored even on exceptions. Hunter serialization remains unchanged. Live
selection for both classes prefilters known other-faction guild rows before deep
report verification; guildless candidates still need verification. The API's
authenticated Encounter schema has no dedicated faction argument. Tested
`filter: "faction=1"`/`"faction=2"` and dot forms returned identical mixed rows;
these strings are not represented as an enforced server faction filter. Class
and Druid spec use their supported query arguments. Local faction selection is
explicit, retaining the guild inference and separate observed report checks.

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

Presentation reuses the established playbook hierarchy and components across
supported classes. Class adapters supply evidence and labels, keeping absent
personal encounters ungraded. Common optional ability-use evidence counts actor
cast events with trusted source coverage, separate from passive ticks and pets.
Counts and uses per minute are descriptive comparisons, never rotation grades.
New Hunter replays include the shared table and CSV; old saved documents retain
their compatible rendering. No additional class analyzer is implied.
