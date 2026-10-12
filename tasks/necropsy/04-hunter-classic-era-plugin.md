# 04 — Hunter Classic Era Plugin

## Goal
A Hunter Classic Era analyzer implementing the plugin interface (spec §3) for
the Hunter-specific forensics behind the Haplina findings.

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
