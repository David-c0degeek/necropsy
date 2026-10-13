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

- **Existing code found** — `necropsy.report.analysis_json` (`AnalysisDocument` model, `dumps`), `necropsy.report.offline.run_offline` (archive verification, DB reuse, atomic analysis.json write), `necropsy.report.serialize`, CLI `offline`; no HTML, template or packaging code (`rg -n "jinja|html|zipfile" src` before this subject → only snapshot ZIP reading in `snapshot/archive.py`).
- **Behaviour to preserve** — archive verification and ingest safety (`--replace`, WAL refusal), deterministic analysis.json bytes, existing CLI names/options/error prefixes, evidence semantics (unknown never a number, inferred stays inferred).
- **Reuse / extend** — pages validate input with `AnalysisDocument`; evidence paths resolve exactly as the existing evidence-path test does; `run_offline` keeps its verification and now hands the analysis bytes to `package.write_outputs`; one renderer serves `offline` and the new `render` command.
- **Do not duplicate** — no metric is recomputed in the view layer; every number comes from analysis.json; the package embeds the exact analysis.json bytes.
- **Integration point + why** — new `necropsy.report.render` (view model + Jinja templates + inline assets as package data), `necropsy.report.package` (outputs, tables, evidence, deterministic ZIP), `necropsy.report.publish` (staged publication): analysis.json is the single contract between analysis and presentation (spec §7/§10).
- **Vision fit** — offline, self-contained report/playbook from analysis.json (D002, D007 Jinja2); UX led by the navigator (D034); Playwright approved by the user (06.7).
- **Risks** — package contents are real players' derived data (stated in docs and manifest; secret/path regex is a guard, not anonymisation); view wording can drift from the data contract (mitigated by view tests and evidence labels); publication is not crash-proof (documented, backup kept).

## Boxes
> ID = `<subject-id>.<box-number>` (subject index ID · box ordinal). Stable — never
> renumber; mark retired boxes done and struck with `ABANDONED; see D###`
> (see §4), don't delete. A human-owned box recorded `DEFERRED` in
> `manual-actions.md` stays `[ ]` and follows the §5 Done rule.
> Owner MUST be one of the §5 enum:
> agent · release-engineer · product-owner · tech-lead · domain-sme.

- [x] **06.1** (agent) Jinja2 templates with inline CSS/JS, zero network
      fetches, works from `file://`, dark/light, print-friendly.
- [x] **06.2** (agent) `report.html` (findings with evidence levels and
      show-evidence drill-down) and `playbook.html` (per boss: gear, pet, weave,
      opener, RF/Refocus, DO NOT, raid-level asks, cohort tables).
- [x] **06.3** (agent) Package `<character>_<zone>_analysis.zip`: `report.html`,
      `playbook.html`, `manifest.json`, `analysis.json`, `tables/*.csv`,
      `evidence/`; optional raw snapshot / DuckDB. Secret scan runs on the
      package in tests.
      *Package name uses numeric IDs (`necropsy-<character id>-<zone id>.zip`);
      optional raw snapshot / DuckDB members deferred (D035).*
- [x] **06.4** (agent) Rendering twice from the same `analysis.json` is
      byte-identical and needs no WCL access.
- [x] **06.5** (agent) Golden end-to-end: `necropsy offline` on the full fixture
      produces the package; facts register passes; HTML smoke-checked in a
      headless browser (nav works, 15 boss pages).
- [ ] **06.6** (product-owner) Side-by-side review of generated playbook vs
      `Haplina_Naxx_Definitive_Playbook.html`; list must-fix gaps.
- [x] **06.7** (product-owner) Approve installing Playwright (Python package
      plus a Chromium download) for the 06.5 headless HTML smoke check, or
      choose a manual browser check instead.

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

2026-10-13 · slice 1 (preparation; no 06 boxes completed) · documentation/CLI UX pass under D034: sample-first README and guides, reference navigation, current/planned roadmap, contributing and GitHub templates, accessible SVG banner, CLI help and next-step wording; analysis behavior unchanged · documented subset run: 4 bosses/12 recommendations; local links, YAML/SVG, lint/types and fast suite; awaiting peer review · not committed
2026-10-13 · slice 2 (documentation checkpoint; no 06 boxes completed) · peer AGREE round 1 on documentation/CLI UX; 271 fast tests plus documented subset/ingest/reuse/error flows passed; links, issue-form YAML, SVG XML, ruff/format/mypy clean · commit a76c35d pushed; Linux/Windows CI run 38373980724 success; approved repository description/topics applied, private visibility retained · report design next
2026-10-13 · slice 3 · 06.1–06.5, 06.7 · navigator-led design (DESIGN_AGREED after staged-publication challenge; two visual STEER rounds): view model + Jinja templates + inline CSS/JS, report.html and playbook.html, deterministic package with tables/evidence/manifest, staged publish with rollback, `necropsy render`, `--no-package`; Playwright 1.63 + Chromium (user approved 06.7) · unit, integration, browser (14) and golden end-to-end (full export: 15 bosses, byte-identical rerender) checks; screenshots light/dark desktop/mobile · awaiting review
2026-10-13 · slice 4 · 06.2–06.5 · review round 1 fixes: publish preflight refuses directories/links with artifact names; `pets_listed` added to analysis.json entries and the no-pet fact proven only with the listing; every cohort aggregate (explosives, weave adoption, foreign-share median) keeps the inferred grade; Tauren fill reported as considered vs used; RenderError for analysis.json missing nested data or evidence paths (clean CLI exit); failure/recovery docs scoped · 518 passed 4 xfailed, acceptance · awaiting round 2
