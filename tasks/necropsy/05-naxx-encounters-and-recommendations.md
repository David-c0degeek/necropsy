# 05 — Naxx Encounters, Benchmarks And Recommendations

## Goal
Encounter rules for Naxxramas, the three-view benchmark model, structured
recommendations, and the versioned `analysis.json` contract — the only input
to report rendering.

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
