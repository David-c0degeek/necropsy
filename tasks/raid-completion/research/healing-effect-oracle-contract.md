# Healing and actor-effect identity guardrails

2026-10-18, before implementation. Applies PM-3 to the independent raw checker;
no production analyzer or frozen expectation changes are proposed.

Failed future: a validly rehashed archive changes an integer timestamp or roster
identity into an equal-valued float, or attaches an aura to another fight, yet
Python equality keeps the expected facts green. Static review reproduced these
paths in `raw_actor_effect_facts` and `raw_healing_facts`.

Preserve every existing measurement and register byte. Require exact selected
fight identity and integer ordered bounds, unique typed catalog actor IDs,
strict healing recipient roster/NPC identities, and bounded integer timestamps
plus agreeing available fight IDs for relevant effects. Sparse optional event
fight IDs remain supported. Unclassified recipients remain unknown rather than
being assigned a friendly/boss identity; contradictory explicit friendly/boss
membership must fail the raw check. Preserve the observed Environment sentinel
(`id:-1`, NPC, integer`gameID:0`); require positive identities for actual units.
Validate selected aura/lifecycle rows
before sorting them; unrelated events do not establish aura chronology.

Use valid-rehash mutation tests for aliases, bounds, duplicate identities and
contradictory fight IDs, plus unchanged registered raw replay. Tests are raw-only;
all database workloads remain suspended while the native Paladin capture runs.
Rollback is the checker change alone; inputs and expected facts stay immutable.
Verdict: PROCEED WITH GUARDRAILS under existing PM-3. This does not close a cell,
subject or domain/product gate.
