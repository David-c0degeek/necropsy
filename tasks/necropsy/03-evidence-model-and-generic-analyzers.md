# 03 — Evidence Model And Generic Analyzers

## Goal
The class-agnostic layer: evidence/provenance objects, the per-fight
environment and bias profile, and generic analyzers usable by any class plugin.

## Integration analysis
> Fill before ticking any box in this subject. Reuse and integrate before
> adding — no new code until this is recorded (§6.17). Build on the prior-art
> map from 00.2 and the architectural direction from 00.1.
>
> **Evidence, not prose.** Each bullet names concrete files/symbols (e.g.
> `necropsy/snapshot/v0.py::read_events`), not "the relevant modules". "None
> found" is a valid answer only when it records the search that proved it (the
> grep/scan run). A generic Integration analysis that names nothing is not
> done — it is how a duplicate parallel system slips past this gate.
>
> - **Existing code found** — relevant modules, services, abstractions, workflows.
> - **Behaviour to preserve** — contracts, public APIs, tests, callers that must keep working.
> - **Reuse / extend** — what is reused, extended, or refactored instead of duplicated.
> - **Do not duplicate** — what already exists and must not be reimplemented.
> - **Integration point + why** — where the change lands and why it is the correct seam.
> - **Vision fit** — supports or conflicts with the project vision/ADRs (00.1); cite drift if any.
> - **Risks** — duplication, architectural drift, or accidental complexity introduced.

- **Existing code found** — TBD
- **Behaviour to preserve** — TBD
- **Reuse / extend** — TBD
- **Do not duplicate** — TBD
- **Integration point + why** — TBD
- **Vision fit** — TBD
- **Risks** — TBD

## Boxes
> ID = `<subject-id>.<box-number>` (subject index ID · box ordinal). Stable — never
> renumber; mark retired boxes done and struck with `ABANDONED; see D###`
> (see §4), don't delete. A human-owned box recorded `DEFERRED` in
> `manual-actions.md` stays `[ ]` and follows the §5 Done rule.
> Owner MUST be one of the §5 enum:
> agent · release-engineer · product-owner · tech-lead · domain-sme.

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
> Run after all boxes in this subject are complete and before marking
> the subject `DONE` in §5. Use the embedded prompt in "Appendix: Captain
> Hindsight Prompt". Record the review result here. An interim run after
> a large or risky box is allowed and recorded the same way; it does not
> replace the closing run. In this coordinated pair plan, the navigator's
> `VERDICT AGREE` on the subject's diff precedes the Hindsight run.
>
> Required output sections: Keep; Fix before closing; Record; Risk;
> Verdict (`CLOSE` or `DO NOT CLOSE`). If the verdict is `DO NOT CLOSE`,
> leave the subject open, add/reopen boxes or update decisions/lessons,
> and rerun this checkpoint after the fixes.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
