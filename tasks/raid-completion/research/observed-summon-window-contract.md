# Observed summon boundaries: implementation guardrails

2026-10-18, before new summon-boundary implementation. This extends the existing
shared encounter contract; it does not close physical phase/opportunity work.
PM-1/PM-2/PM-3 remain applicable.

The proposed change failed by turning consecutive Summon Images casts into
exclusive image-presence phases. In actual `6H9PmqR2QCnNAzVh/2`, image1 is
summoned at9684ms and has positive overkill at44230ms; later image groups are
already summoned near19383ms and33939ms. Ending the first interval at the next
cast loses more than24 seconds of this image's observed chronology. Preserve
each actor/instance independently and allow overlapping groups. Boss progression,
image presence, range and physical damage opportunity are different claims.

The second failure was pretending every image had a death endpoint. Across12
retained Skeram contexts,72 numbered747 summons link15263 to176525, but there
are no image death rows.60 instances have positive-overkill damage markers;
12 have none. No positive damage is strictly later than the first such marker
in the sampled60; same-timestamp rows are unordered. A last damage timestamp or
fight end cannot supply a missing endpoint. Raw observations were independently
frozen before model work in
[the lifecycle research register](skeram-image-lifecycle-observations.json).

Required implementation boundaries:

- Reuse raid-owned policies, existing encounter scope/revision checks, NPC
  catalog/cardinality qualification, optional evidence-tree JSON and both page
  adapters. Do not clone an aura engine or fabricate buff events for summons.
  Keep genuine/feign/ambiguous death classification shared.
- A policy-qualified summon is an observed event, not a full phase. Preserve
  raw caster, ability, target and numbered instance identity. Validate available
  raw values against normalized IDs without coercion. Missing/ambiguous identity
  remains unknown; never assign instance1 or borrow another NPC's singleton.
- A duration, when justified, is the elapsed time between qualified observed
  summon and terminal markers for that exact instance. State the marker kind.
  It does not establish continuous attackability, player range, assignment,
  required target switches, available casts or lost DPS. Missing or conflicting
  endpoints must not produce a duration. No normalization or personal grade.
- Positive event observations may survive partial data; exact counts, absences
  and complete boundary claims require certified unrestricted All coverage.
  Actor-only or critical-only scopes cannot supply it. Global scope does not
  manufacture selected-player SOURCE coverage.
- Repeated summons for one instance, missing instances, forged/wrong owners or
  targets, malformed/zero/negative/Boolean overkill, reversed boundaries,
  later contradictory positive evidence, same-time conflicts, explicit feigns,
  resurrected/reused units and fight truncation need meaningful negatives.
  Do not infer units alive before the first positive marker.
- Independently freeze raw counts/identities/boundaries and explicit unknown
  expectations before comparing runtime output. Preserve all current525 actor,
  322 recipient,41 pet and9 actor-effect contexts. Keep the12 research contexts
  independent from any production normalizer or analyzer used for acceptance.
- New optional observations must have actual non-test analysis and both-page
  callers. Old saved JSON gains no reanalysis during rendering. Preserve Naxx
  artifacts or review a necessary semantic difference explicitly. Keep all raw
  archives and prior expected measurements immutable; verify staged metadata
  bytes and LFS identities before checkpointing.

Implementation must start after the in-flight lifecycle correction's full
ordinary-suite verification and checkpoint. The official scripting enemy-death,
phase and ranking oracle remains unverified because no browser connection was
available; do not invent its result or bypass the normal capture pipeline.
