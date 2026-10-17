# Observed BWL actor effects — implementation guardrails

Reviewed2026-10-17 before activation. Reuse existing actor-effect state, target
coverage, saved JSON and both renderers. Applicable only to new Era raids;
Naxx and legacy whole-fight aura inference retain their contracts.

The raw candidate enumeration already frozen at194a448 establishes selected
recipient transitions for Burning Adrenaline18173, Essence of the Red23513,
Flame Buffet23341, Chromaggus afflictions and Nefarian fear/Priest calls.
No new expected values may call production aura-state or analyzer helpers.

## Pre-mortem

- Normalized BIGINT identity may conceal raw boolean/fractional/null or mismatched
  recipient/spell IDs. Inspect available raw scalar identities before excluding
  another recipient. Relevant unresolved aura or lifecycle ownership must withhold
  durations with its own unattributed event evidence; no fake actor0 or personal
  attribution. Preserve compatibility when old synthetic/raw rows omit scalar keys.
- Initial state remains unknown. Refresh/stack rows do not settle it; simultaneous
  contradiction and death/resurrection reset it. Fight end censors active state.
  No nominal debuff duration or addon timer supplies a missing removal.
- Essence of the Red is logged as a debuff despite beneficial resource context;
  exposure duration is not resource quantity, healing, damage or quality.
- Bronze exposure does not measure stun uptime. Burning Adrenaline presence is not
  a death-causality or execution grade. Personal affliction state is not patient
  state or assigned removal duty. Priest call state cannot be attributed to a
  missing Nefarian personal fight; cohort observations stay labelled examples.
- Freeze raw actor-target transitions/lifecycles separately from actor arithmetic,
  with manually reviewed integer-ms windows. The independent checker projects raw
  facts only; golden tests compare the implementation with frozen expectations.
- Validate malformed IDs, wrong actor/spell/kind, partial target coverage, lifecycle,
  truncated fights and absent personal data. Verify source/installed JSON/pages/
  package, actual mobile/desktop rendering and preserved Naxx outputs.

Full phase, physical opportunity, ranking, utility opportunities, assignments and
all-class acceptance remain open. Module policies are independently reversible;
raw snapshots and prior expected measurements remain immutable.
