# Explicit encounter event scope and versioned live archives

Accepted design2026-10-17. Optional collection/archive support is implemented;
representative real finalized/installed acceptance is verified. Default collection
remains unchanged; complete encounter-policy acceptance remains open.

Selected actor source/target streams cannot establish other actors' fire critical
eligibility, all hostile heal attempts, or global encounter transitions. Raw
presence and complete scoped absence are separate evidence contracts.

Extend the existing acquisition client/cache/generation/finalization path with
two actorless event scopes. `encounter` requests unrestricted whole-fight All;
`critical` binds `type = "damage" AND isCritical = true` in request identity.
Both use actor null and direction all. No surrogate actor0, second downloader,
cache, report bundle or ingestion path. Existing actor request identities and
cache paths remain unchanged. Critical responses must contain damage events.
Page/revision/budget errors never publish a completion marker.

Explicit `acquire(..., encounter_context=True)` applies only to MC/BWL/AQ40 Era
partitions1/2. Entry completion includes both scopes and preserves the existing
whole-generation revision retry. Cache reuse deduplicates a report/fight shared
by several participants. Snapshot format2 adds separately certified
`encounter_streams` and acquired pages under `events/<report>/fight_<id>/encounter/`.
Existing/default acquisitions retain format1. Historical/v1 readers remain in
the shared dispatcher; unsupported/malformed versions never fall back.

Version2 reuses actor/report proofs, event-page decoding and normalizer. It proves
one unfiltered and one critical stream per selected fight, exact request identity,
combined report revision/bounds/endpoint, page/member digests and terminal
pagination. Extra or missing pages are refused. Actor/pet and critical views must
be exact raw subsets, including multiplicity, of the unrestricted view. The
normalizer's existing maximum-multiplicity merge prevents double counting.
For each captured actor direction, unrestricted events owned by that actor must
also occur in its certified direction stream; global collection cannot silently
change a captured actor's arithmetic.
Existing nullable coverage columns carry these scopes; no schema migration.

Actor absence qualification is unchanged. Unselected actors do not gain a
source/target completeness certificate from global presence. Critical data never
stand in for all casts or all phase events. No ranking reconstruction, phase,
assignment or opportunity grade is enabled by transport alone. Future policies
must bind their exact coverage footprint and independent facts. Old saved JSON
still renders its saved evidence and advice without current policy injection.

Rollback disables optional context collection while retaining historical/v1
reading and immutable captures. Older binaries refuse format2 safely; original
format1 archives remain available. Real before/after research checks do not
change historical journal-resume semantics or claim one global capture time.

Filter semantics are documented by [WCL pins](https://vanilla.warcraftlogs.com/help/pins).
Current transport verification separately tests request identity, terminal
pagination and raw subset/multiplicity; a documented filter alone does not
certify an encounter ranking policy.
