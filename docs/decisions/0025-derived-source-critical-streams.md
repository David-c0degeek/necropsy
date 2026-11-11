# Derived source and critical streams

Status: implemented in the development tree; unreleased.

## Context

Naxxramas already fetches each selected fight's unrestricted encounter-All data
and derives byte-identical actor targets. Requested actor-source and critical
streams repeat events present in that parent. Recorded captures demonstrate that
source projection needs transitive report-catalog ownership as well as the fight
pet listing. A fight listing alone can omit owned guardians. Critical damage
also needs a guarded rule rather than an assumption about future hit types.

## Decision

Snapshot format 4 explicitly supports `source-owned-encounter-all-v1` and
`critical-hit-type-encounter-all-v1`, alongside the existing target rule.

Source projection retains events with a sourceID or targetID in the actor's
transitive owned closure. Ownership comes from the original acquisition's
hash-bound report catalog and fight listing. Ambiguous, malformed, conflicting
or incomplete ownership retains requested source streams. Critical projection
retains damage with hitType 2, 5 or 17, and requires every damage hit type to be
an integer from the rule's explicit known domain. Unsupported inputs retain
requested critical streams. Existing verified requested cache scopes take
precedence; corruption is never hidden by deriving a replacement.

Derived records carry no API identity or costs. They identify exactly one
requested encounter-All parent by its entire immutable identity and complete
page-hash chain. Source records additionally name the canonical owned actor IDs.
The writer materializes generated pages, retaining parent page boundaries,
cursors, order, duplicates and empty pages. The reader independently reconstructs
each projection and compares exact bytes after checking parent scope, revision,
endpoint, bounds, pagination, digests and original ownership evidence. Updating
a changed child's digest does not make it valid. A separate raw verifier serves
the freezer/oracle tools without importing the runtime projector or reader.

## Consequences

The normal Era Naxxramas/MC/BWL/AQ40 paths enable these views on partitions1/2.
Unsupported partitions retain their prior acquisition behavior. V3 keeps its
Naxx-only contract; other raids use v4 even for target-only reuse when requested
source/critical scopes already exist. Older archive formats retain
their contracts; Naxx cache-first resumes can still produce v3. Released 0.7.1 readers
refuse v4, so updated consumers must accompany rollout of a v4 producer.

The normalized schema, coverage model and analysis JSON shape do not change.
Class, category, metric, faction and subject eligibility remain separate from
physical fight reuse. Synthetic request savings and recorded event equivalence
do not establish live billed-point savings or a capture completion estimate.
