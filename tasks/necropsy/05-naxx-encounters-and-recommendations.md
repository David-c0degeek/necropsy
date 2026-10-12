# 05 — Naxx Encounters, Benchmarks And Recommendations

## Goal
Encounter rules for Naxxramas, the three-view benchmark model, structured
recommendations, and the versioned `analysis.json` contract — the only input
to report rendering.

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
- [ ] **05.1** (agent) Encounter plugin interface + Naxx rule files
      (`rules/classic_era/zones/naxxramas`): native target ids, phases/downtime,
      burst windows, pet hazards, known distortions for all 15 bosses.
- [ ] **05.2** (agent) Gothik native vs foreign-target DPS; KT MC-control
      utility (Freezing Trap, Scatter Shot on friendly, Reckless Charge on
      friendly) classified as raid assignment; Sapphiron/KT raid-speed
      classification from kill duration vs cohort.
- [ ] **05.3** (agent) Benchmark views: (A) same-faction realistic ceiling,
      (B) robust baseline from the metadata cohort (build/gear dominance,
      medians, outlier flags), (C) cross-faction ceiling, opt-in and never
      merged. Historical mode builds A as "best same-faction inside the recorded
      overall top 5" and states that limit in output.
- [ ] **05.4** (agent) Recommendation objects (spec §7 shape + controllability
      + evidence refs + benchmark ref); shot-count targets projected to the
      subject's kill duration as ranges.
- [ ] **05.5** (agent) `analysis.json` schema v1 (Pydantic; JSON Schema exported
      to `docs/`), deterministic ordering, cohort provenance, coverage summary,
      mode, tool version. `necropsy offline <snapshot> --out <dir>` writes it.
- [ ] **05.6** (agent) Golden: Haplina historical-mode recommendations match the
      definitive playbook's per-boss conclusions (spec, DMF, pet, weave matrix,
      RF timing, KT assignment, Gothik padding) as structured facts, not prose.
- [ ] **05.7** (domain-sme) Review weave matrix and per-boss recommendations vs
      the definitive playbook; adjudicate differences.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
