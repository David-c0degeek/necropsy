# Target instance aura observations

Accepted design2026-10-17. Observed NPC auras use the existing encounter rule,
evidence, normalized event and saved playbook/render pipeline.

A WCL NPC actor can represent multiple simultaneous units. Majordomo
Magic Reflection20619 and Damage Shield21075 therefore retain exact actor plus
targetInstance, with separate caster and recipient NPC policies. A boss cast
does not apply a buff to every add or establish a universal duration. Aegis20620
is a different caster-self effect, not an add reflection buff. Classic spell
records for [Reflection](https://www.wowhead.com/classic/spell=20619/magic-reflection)
and [Damage Shield](https://www.wowhead.com/classic/spell=21075/damage-shield)
establish the mechanic identities; nominal timers do not supply observed state.

Reuse the generic observed three-state aura function for each exact entity.
Initial state is unknown until a definitive apply/remove. Simultaneous
contradictions remain unknown; lifecycle events reset state. Active effects at
fight end are censored, never assigned a synthetic removal. A repeated add
without an instance retains its observed transition but cannot be joined to a
numbered unit. An ambiguous transition or lifecycle instance withholds affected
actor windows rather than attributing it arbitrarily.

Whole-fight application counts and state durations require trusted unrestricted
encounter coverage and event-set consistency. Ingestion retains a maximum-
multiplicity union; its full-fight occurrence count must equal the trusted
All read's count, proving that no other stream added an identity or copy.
Missing or inconsistent occurrence metadata leaves complete counts/windows
unknown. Filtered critical scope and captured player directions do
not certify them. Positive transitions survive partial coverage. Saved coverage
references explicitly identify the actorless role, null actor and all direction.
Original actor coverage serialization and historical aura policies stay unchanged.

Optional target_aura_windows and cohort_target_aura_windows are saved in
playbook evidence and shown in both pages. Old saved documents do not acquire
new policy on render. These fields describe target state, not physical phases,
attackability, immunity, assignment, lost throughput or quality. They cannot
change ranked amount, denominator, cohort eligibility or comparison medians.

Garr Banish adds class-qualified player casters and debuff transitions through
the same primitive. Caster type and class must be unambiguous; a pet, NPC or
unknown class cannot impersonate a Warlock. Available raw source/target/spell
identities must match normalized integer identities without boolean/fractional
coercion, before wrong-class/recipient exclusion. An unresolved lifecycle
recipient withholds windows and carries its own event reference instead of
hiding as a different actor. Rank1/Rank2 and target instances remain separate; no cross-rank union
or sum establishes control quality. Missing/ambiguous lifecycle identity also
withholds windows. Other-player effects belong to the encounter, never the
selected player's personal uptime. Cohort text explicitly identifies the fight.
Existing SOURCE-owned personal counters retain their separate coverage contract.
Independent raw control transitions and manual integer-ms window expectations
are separate from actor arithmetic. No nominal spell duration supplies a removal.

Rollback removes these optional policies/observations while preserving saved
JSON rendering and historical/live archive readers. No database schema changes.
