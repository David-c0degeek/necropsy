# 03 — Evidence Model And Generic Analyzers

## Goal
The class-agnostic layer: evidence/provenance objects, the per-fight
environment and bias profile, and generic analyzers usable by any class plugin.

## Integration analysis
> Fill before ticking any box (§6.17).

- **Existing code found** — TBD
- **Behaviour to preserve** — TBD
- **Reuse / extend** — TBD
- **Do not duplicate** — TBD
- **Integration point + why** — TBD
- **Vision fit** — TBD
- **Risks** — TBD

## Boxes
- [ ] **03.1** (agent) Evidence model: level (OBSERVED / DERIVED / INFERRED /
      UNKNOWN), source refs (report, fight, actor, event ids), rule id, and
      coverage ref attached to every derived value; Windfury and race status
      enums per spec §6.
- [ ] **03.2** (agent) Environment/bias profile per fight: faction, race
      evidence (racial-ability rules in `rules/classic_era/racials`), talent
      fingerprint, role, world/external buffs (incl. Sayge DMF variants), WF
      status + extra-attack count + attributed damage, raid kill duration, gear
      fingerprint.
- [ ] **03.3** (agent) Generic fight metrics: duration, DPS by ability,
      casts/min, cooldown timeline, buff/debuff uptime, deaths with killing
      blows, pets/guardians (incl. engineering summons) with first/last activity
      relative to fight start/end.
- [ ] **03.4** (agent) Target integrity: per-target damage split with a
      native-target hook supplied by encounter plugins.
- [ ] **03.5** (agent) Cohort comparison: per-slot gear and enchant dominance
      (e.g. Sniper Scope 664 vs Biznicks 2523), talent build distribution,
      consumable/world-buff prevalence.
- [ ] **03.6** (agent) Golden checks: Smcadogx `RACIAL_EVENT_CONFIRMED` Orc +
      WF `CONFIRMED` 9; Alliance comparators WF `NOT_OBSERVED`; faction split
      (historical mode); Snape Grobbulus death time; Haplina 12/33/6.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
