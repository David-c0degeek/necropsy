# Target instance aura observations

Accepted design2026-10-17. Observed NPC buffs use the existing encounter rule,
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
encounter coverage. Filtered critical scope and captured player directions do
not certify them. Positive transitions survive partial coverage. Saved coverage
references explicitly identify the actorless role, null actor and all direction.
Original actor coverage serialization and historical aura policies stay unchanged.

Optional target_aura_windows and cohort_target_aura_windows are saved in
playbook evidence and shown in both pages. Old saved documents do not acquire
new policy on render. These fields describe target state, not physical phases,
attackability, immunity, assignment, lost throughput or quality. They cannot
change ranked amount, denominator, cohort eligibility or comparison medians.

Rollback removes these optional policies/observations while preserving saved
JSON rendering and historical/live archive readers. No database schema changes.
