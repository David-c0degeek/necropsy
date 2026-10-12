# 06 — Report And Package

## Goal
Render the self-contained offline report and playbook solely from
`analysis.json`, matching the definitive playbook's structure (sidebar nav,
boss pages, collapsible cohort tables, reviewed checkboxes), and emit the
export package.

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
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
