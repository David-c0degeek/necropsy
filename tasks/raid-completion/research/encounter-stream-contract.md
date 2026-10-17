# Encounter stream contract investigation

2026-10-17; shared-contract work remains in progress. No runtime ranking/phase
policy is certified by this investigation.

## Verified seams

Current cache StreamKey only permits player/pet positive actor IDs and source/
target directions. fetch._pages already sends nullable WCL sourceID/targetID.
Snapshot v1 LiveStream restricts the same roles/directions; its writer requires
exact player/pet streams and reader proves each certified page/request. Existing
stream coverage queries qualify actor plus direction; an actorless encounter
stream must never manufacture player/pet coverage. Normalization already merges
raw overlapping streams with maximum multiplicity and marks conflicting counts.
Twenty immutable actor streams in seven same-revision public research fights
are exact raw subsets of terminal whole-fight pages, with matching multiplicity;
see encounter-stream-overlap.json. This bounded evidence is not a general proof.

## Implementation constraints

Use the existing client, cache, pagination, revision checks, journal, budget and
finalization. Add explicit actorless encounter/critical stream keys (actor=None,
direction=all), never actor0 or a fake NPC/player. The critical stream binds the
server-documented isCritical filter in canonical request identity; it must not
be confused with unrestricted whole-fight coverage. Preserve existing actor
request bytes, cache names/identities and default acquisition until the archive
contract is complete. No second downloader or normalization path.

Next archive change requires explicit live format2, retaining v1/v0 reading and
unchanged Naxx default writing. Version2 will certify whole-fight pages with
normal digest/revision/bounds/endpoint/termination proofs and explicit stream
scope. It must reject wrong fights, altered pages and filtered streams claiming
whole-fight coverage. Complete encounter coverage is separate from actor absence
qualification. Critical data must be checked against unrestricted data before
ranking reconstruction. Missing context remains unknown, never a timer or a
zero opportunity. Optional new analysis fields must remain saved-only on render.

## Proportional pre-mortem before shared changes

PM-2: after adding whole-fight data, player totals silently change because an
actor0 surrogate or filtered stream is treated as complete actor coverage.
Guardrails: nullable actor plus explicit scope, negative identity/filter tests,
keep existing actor coverage predicates and same-raw Naxx byte checks. Raw merge
must retain event identity/multiplicity, never sum overlapping stream counts.

PM-3: a quota stop or historical journal reuse appears to certify a complete
fresh global capture. Guardrails: normal terminal cache marker and finalization,
per-page revision/bounds/digests, no successful marker on interrupted fetch,
unchanged ADR0008 historical-resume semantics. Research fresh before/after
checks remain separate from normal resumed acquisition guarantees.

Proceed with these guardrails. First increment extends shared cache/fetch only;
no default collection or validated ranking/phase change until versioned archive,
normal pipeline, independent real facts and both rendered artifacts pass.
