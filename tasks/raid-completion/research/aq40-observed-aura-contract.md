# AQ40 observed aura guardrails

Prepared 2026-10-17 before runtime activation. Extend the existing
`actor_effects` and `encounter_auras` contracts and independent raw register
checker; no phase engine, opportunity denominator or new acquisition path.
PM-1/PM-2/PM-3 from the retained pre-mortem apply.

- **PM-2: a boss aura becomes a physical opportunity or phase.** Preserve
  Whirlwind, Frenzy, Berserk and Twin Teleport as separately labelled observed
  aura state only. The first Twin buffs last about a quarter second, not the
  entire pickup/teleport cycle. C'Thun's26235 has no recorded transitions in the
  reviewed personal fight; do not manufacture a45-second weakening interval.
  Ouro26102 is personal exposure, not avoidability, a full casting interruption
  or proof of failed tanking. No cooldown, cleanse or quality recommendation is
  derived from these durations.
- **PM-2: unnumbered repeated NPCs collapse into one target.** Raw AQ40 boss
  aura events omit targetInstance. Existing repeated-add windows correctly
  require exact instances. For a policy allowing a singleton NPC, require exact
  fight enemyNPCs metadata binding the actor/gameID to instanceCount1. Missing,
  conflicting, boolean or repeated cardinality withholds durations. Preserve
  positive observations and unknown initial state; never assume a singleton
  merely because one aura recipient appears. Existing numbered-add behavior
  must remain unchanged.
- **PM-3: the runtime creates its own expected windows.** Freeze raw
  transitions/catalog/lifecycle and manually authored integer-ms boundaries
  first. Extend the existing raw control projector with an explicit buff/debuff
  selector while preserving old debuff-default registers. Independently test
  rehashed identity, kind, ability, timing and lifecycle mutations. Verify source,
  installed JSON/pages/package and old NPC controls/Naxx. Preserve all existing
  actor/recipient measurements and all seven BWL exposure contexts.

Verified raw basis: `aq40-holy-raid-context` has complete unrestricted/critical
scopes; initial observations are frozen in aq40-first-capture-context.json and
facts.json. Native Huhuran, Sartura, Twins and Ouro identities have one instance
per selected fight. Exact raw aura/lifecycle review precedes rule activation.
No schema migration or historical Naxx aura-state change is needed. Rule changes
can be reverted independently of immutable archives. Proceed with guardrails;
all full domain and matrix acceptance stays open.

Verification found a real missing-binding countercase after the initial six
contexts were frozen. In Vallon/ywGLJZRY8gd6aFmA/49, Berserk26615 targets113,
while enemyNPCs lists only109/Ouro with count1. The existing exact-target guard
correctly withholds113 durations. Freeze the seventh raw context and explicit
unknown expectation independently after page inspection; no new runtime rule
or phase inference is needed. The original nine positive timelines remain
unchanged. Observed Mounds/Birth events use different NPC actor IDs and do not
on their own establish all physical downtime.
