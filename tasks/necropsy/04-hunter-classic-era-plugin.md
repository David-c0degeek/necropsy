# 04 — Hunter Classic Era Plugin

## Goal
A Hunter Classic Era analyzer implementing the plugin interface (spec §3) for
the Hunter-specific forensics behind the Haplina findings.

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
- [ ] **04.1** (agent) Class plugin interface + registry; Hunter is the only
      implementation (no stubs for other classes).
- [ ] **04.2** (agent) Auto Shot cycle reconstruction: every Auto→Auto interval
      with RF/Quick Shots overlap and Aimed/Multi/Raptor/Refocus inside;
      clipped-cycle detection. Semantics match `auto_interval_reconstruction.csv`.
- [ ] **04.3** (agent) Special-shot cadence: Aimed/Multi per minute, gaps,
      opener timeline, RF timing, Renataki equipped vs Refocus cast, Hunter's
      Mark, explosives (Dense Dynamite, Sapper).
- [ ] **04.4** (agent) Melee weave: Raptor count + DPS, white-melee count,
      WF-attributed share; Raptor-only weave distinguished from WF melee package.
- [ ] **04.5** (agent) Pet forensics: family evidence (observed vs inferred from
      ability compatibility in `rules/classic_era/pets`), ranks from spell IDs,
      DPS, start/stop relative to fight, death + killing blows, absent pet
      gated on coverage.
- [ ] **04.6** (agent) Hunter gear context: ranged weapon, trinkets, scope,
      melee setup per fight; dominance per boss from cohort.
- [ ] **04.7** (agent) Golden: Patchwerk Raptor counts; Haplina Patchwerk Aimed
      timestamps (10.91 → 75.47); Gothik Aimed gap; KT 38.97 s Aimed gap;
      Patchwerk pet DPS; 24/24 Renataki → Refocus (historical mode).
- [ ] **04.8** (domain-sme) Review one boss's Hunter output for mechanics
      correctness.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
