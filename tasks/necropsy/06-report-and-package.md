# 06 — Report And Package

## Goal
Render the self-contained offline report and playbook solely from
`analysis.json`, matching the definitive playbook's structure (sidebar nav,
boss pages, collapsible cohort tables, reviewed checkboxes), and emit the
export package.

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

- [ ] **06.1** (agent) Jinja2 templates with inline CSS/JS, zero network
      fetches, works from `file://`, dark/light, print-friendly.
- [ ] **06.2** (agent) `report.html` (findings with evidence levels and
      show-evidence drill-down) and `playbook.html` (per boss: gear, pet, weave,
      opener, RF/Refocus, DO NOT, raid-level asks, cohort tables).
- [ ] **06.3** (agent) Package `<character>_<zone>_analysis.zip`: `report.html`,
      `playbook.html`, `manifest.json`, `analysis.json`, `tables/*.csv`,
      `evidence/`; optional raw snapshot / DuckDB. Secret scan runs on the
      package in tests.
- [ ] **06.4** (agent) Rendering twice from the same `analysis.json` is
      byte-identical and needs no WCL access.
- [ ] **06.5** (agent) Golden end-to-end: `necropsy offline` on the full fixture
      produces the package; facts register passes; HTML smoke-checked in a
      headless browser (nav works, 15 boss pages).
- [ ] **06.6** (product-owner) Side-by-side review of generated playbook vs
      `Haplina_Naxx_Definitive_Playbook.html`; list must-fix gaps.

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
