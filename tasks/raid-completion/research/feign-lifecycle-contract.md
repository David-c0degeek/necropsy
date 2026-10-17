# Feign Death lifecycle correction guardrails

2026-10-18, before changing analysis. PM-1/PM-2/PM-3 apply. Reuse shared
metrics, actor-effect and NPC-window seams; preserve immutable raw events and
normalization/schema. Add one shared raw flag classifier, with actual callers.

It shipped and a Hunter's Feign Death erased otherwise measured aura state.
The real countercase is Vadik11, Geddon `ApbxvjzTX8mqVnY1/25`, in the retained
`mc-geddon-hunter` native archive: Ignite Mana19659 applies at14980ms, a raw
`death` with `feign:true` occurs15460ms, and19659 damage continues at17970,
20974,23982,26964,29976,32988,35980,38973 and41985ms. Fight ends43113ms,
with no recorded removal. Current observed-aura reset handling does not inspect
the flag. Expected aura state freezes independently: unknown0–14980ms,
active14980–43113ms (28133ms known affected;14980ms initially unknown).
This remains end-censored exposure, not a mana-loss, opportunity or quality grade.

The raw protocol flag is `feign`, observed in14 selected Hunter death rows
across the sampled AQ40/MC/BWL archives. The official
[DeathEvent scripting documentation](https://www.warcraftlogs.com/scripting-api-docs/warcraft/interfaces/RpgLogs.DeathEvent.html)
uses its own `isFeign` property. Distinguish the scripting interface from raw
JSON; do not introduce an unobserved raw alias or infer death from spell casts.

- A literal raw`feign:true` is not a real death and must not reset aura state
  or contribute a genuine death observation. Absent flag and literal`false`
  retain ordinary death behavior. Resurrections remain genuine state resets.
- Malformed flag values (null, strings, numbers, arrays/objects) stay unresolved;
  never coerce them to true/false or establish a known absence. Retain positive
  genuine deaths under partial/ambiguous evidence without certifying a total.
- Actor and NPC consumers must retain their existing coverage, target identity,
  instance, ambiguity and initial-state guards. Feign events remain in raw/
  normalized data and independent facts with the exact flag.
- Freeze the raw countercase and hand-reviewed windows before runtime change.
  Preserve all existing525 actor/322 recipient/41 pet and8 actor-effect contexts.
  Mutation checks must detect changing or removing the flag in a validly
  rehashed archive. Actual source and installed saved output must show the
  corrected window; old JSON rendering does not gain reanalysis.
- Check baseline Naxx outputs. Any changed semantics require exact explanation;
  do not alter a frozen expectation or hide a difference behind a snapshot update.

NPC image lifetime research remains separate:12 Skeram contexts retain72
numbered image summons but no image death rows;60 instances have positive
overkill,12 have none. No raw NPC existence/attackability or split-end policy is
enabled by this correction. No aura removal or continuous opportunity is
invented from last damage or a guide timer. Proceed with guardrails.
