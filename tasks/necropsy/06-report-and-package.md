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
- **Reference expansion** — `analysis_json.build_document` extends the existing JSON with `analysis.playbook`, `analysis.overview`, `analysis.guidance` and `analysis.gamedata`; `generic.catalog` reuses stored ranking raw and the existing item catalog. `render.playbook_view` supplies the shared reference presentation through `view.document_view`; the existing finding/evidence view remains the drill-down rather than being reimplemented. Both pages, CLI paths and ZIP still use the same renderer/publisher. Optional additions preserve older JSON; no database schema change or oracle-derived runtime constants.

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
- [x] **06.6** (product-owner) Side-by-side review of generated playbook vs
      `Haplina_Naxx_Definitive_Playbook.html`; list must-fix gaps.
      *User completed the comparison on 2026-10-13 and identified the must-fix:
      preserve the definitive playbook's content and appearance. Implementation
      of that verdict is tracked in 06.8; this does not claim acceptance of the redesign.*
- [x] **06.7** (product-owner) Approve installing Playwright (Python package
      plus a Chromium download) for the 06.5 headless HTML smoke check, or
      choose a manual browser check instead.

- [x] **06.8** (agent) Visual match to the definitive playbook
      (`D:/Parsing/Results/Playbook/Haplina_Naxx_Definitive_Playbook.html`, read-only
      template): report and playbook adopt its layout, palette, type scale and density
      (fixed sidebar with search and numbered bosses, gradient hero, per-boss panels
      with eyebrow, metric tiles and reviewed control, sticky-header tables), content
      still only from analysis.json with unknown/inferred labels, evidence, offline,
      escaping, print, keyboard and narrow-screen guarantees kept. Reopened by the
      user's 06.6 verdict; navigator-led (D034, D039).
      *User, 2026-10-13: "I actually simply love everything about the
      [definitive playbook], i don't want to miss anything currently there."
      Scope is content parity as well as look: every element of the template
      (overview, truth model, per-boss metric tiles, faction mix, current and
      target shot counts, pet DPS vs median, benchmark context, loadout plan,
      execution plan, Do not, Raid ask, full gear, top-five table with race
      evidence / WF procs / spec / trinkets / weapons / Raptor / white / pet / pet
      DPS) gets a data source in analysis.json or an explicit gap entry, before
      building. Prose is generated from the data, never copied from the oracle.
      User: "Benchmark context, loadout plan, execution plan, do not, raid ask,
      EVERYTHING." and "you can add to it, but do not take away from it" — the
      template is the floor; Necropsy's extra views are additions.*

- [x] **06.9** (agent) User follow-up, 2026-10-14: add a KISS opening/notes card
      without removing any detailed content; explain unknown race/DPS, verify
      Rapid Fire timings, and preserve saved overall-rank-one metadata as separate
      observed context. Implemented and reviewed (AGREE round 2). Race investigation:
      Classic Era Character.gameData returns unsupported; all 785 saved JSON
      members lack race fields. No absence-based race guessing added.

## Hindsight checkpoint

The previous CLOSE covers the earlier scope; 06.9 requires a follow-up review and closing checkpoint.

The [definitive-playbook parity inventory](06-8-parity-inventory.md) maps every
reference section, column and advice type to existing analysis data or an
owned gap. It is the implementation and content acceptance checklist for 06.8.

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

- [x] Captain Hindsight review recorded (2026-10-13, agent boxes 06.1–06.5, 06.7)
- [x] Verdict is `CLOSE` — closing run after the reference-content implementation, peer AGREE round 2 and pushed checkpoint cd64345

**Captain Hindsight — 06 agent boxes (2026-10-13)**

- **Keep:** analysis.json as the only renderer input; a pure view model where every
  wording/grade decision lives; staged publication with preflight; browser tests that
  measure real behaviour (overflow at 320/390/768 with hostile names, keyboard, print,
  storage blocked) — they caught the mobile overflow before review; screenshots shared
  early so the navigator could steer UX while mechanics were finished.
- **Fix before closing:** none in code. 06.6 (side-by-side vs the definitive playbook)
  needs the user.
- **Record:** D035; lessons below. Navigator round 1 again found uncertainty becoming
  confident text in the presentation layer (empty pet arrays read as "none", cohort
  counts shown as calculated under inferred membership) — the same class as subject 05.
- **Risk:** package holds real players' derived data (documented, not anonymised);
  publication is not crash-proof (documented recovery); one unexplained native-stack
  abort during a full local run, not reproduced.
- **Verdict:** `CLOSE` for 06.1–06.5 and 06.7 (commit e1d4f11, CI run 38381853527
  success). Subject 06 remains IN PROGRESS pending 06.6.

**Captain Hindsight — complete report and reference presentation (2026-10-13)**

- **Keep:** analysis.json remains the renderer's only data contract. The shared reference frame adds all inventoried content while keeping findings and evidence drill-downs. Known non-use, unavailable casts and insufficient timing samples remain distinguishable. Source-based guidance uses named conditions, separately from logged observations. Full overall rows remain context; same-faction statistics still require three known inputs and retain inference. Both pages and the package use the existing publication path.
- **Fix before closing:** no implementation fixes remain after peer AGREE round 2 (#89). The optional host-qualified citation labels are a readability improvement, not a correctness blocker. Final record review and CI confirmation precede the work-unit boundary.
- **Record:** D040 is implemented and its durable reasoning appears in the output contract and result-reading guide. Integration analysis extended above; lessons record tri-state cast timing and dependency-based citations. The retained PM-1–PM-3 register concerns subject07 only; its live observation horizon has not elapsed and no prediction fields or calibration are changed by this report close-out. The disclosed handoff failure and recovery remain recorded in the inventory; successful acceptance and write guards were checked for both later transfers. No plan references were found in shipped source/docs/tests after excluding raw oracle CSV false positives.
- **Risk:** guide-based training costs remain unverified against server costs; ammo and actual pet training are absent from the logs. Static encounter clocks do not prove observed phase timings or optimal cooldown placement. Package privacy and publication recovery limits remain documented. Broader human mechanics review (05.7) and real auth/live acquisition (07.9) remain open in manual-actions; this closure does not complete either.
- **Verdict:** `CLOSE` for subject06 on the reviewed, pushed implementation cd64345. Evidence: peer full suite728 passed/4 known xfailed after data fixes, final focused62 checks after presentation fixes, clean ruff/format/mypy, regenerated full15boss/75row pages and screenshots at1400/390px; `necropsy render workspace/parity-full/analysis.json --out workspace/parity-rerender` emitted JSON, both pages and ZIP byte-identical to the preview. Peer round2 independently rehashed51 files and checked rendered timing/citation corrections;40 view/integration tests passed in its review. Linux and Windows CI run38417517143 succeeded. Final record review precedes moving to the next work unit.

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.

2026-10-13 · slice 1 (preparation; no 06 boxes completed) · documentation/CLI UX pass under D034: sample-first README and guides, reference navigation, current/planned roadmap, contributing and GitHub templates, accessible SVG banner, CLI help and next-step wording; analysis behavior unchanged · documented subset run: 4 bosses/12 recommendations; local links, YAML/SVG, lint/types and fast suite; awaiting peer review · not committed
2026-10-13 · slice 2 (documentation checkpoint; no 06 boxes completed) · peer AGREE round 1 on documentation/CLI UX; 271 fast tests plus documented subset/ingest/reuse/error flows passed; links, issue-form YAML, SVG XML, ruff/format/mypy clean · commit a76c35d pushed; Linux/Windows CI run 38373980724 success; approved repository description/topics applied, private visibility retained · report design next
2026-10-13 · slice 3 · 06.1–06.5, 06.7 · navigator-led design (DESIGN_AGREED after staged-publication challenge; two visual STEER rounds): view model + Jinja templates + inline CSS/JS, report.html and playbook.html, deterministic package with tables/evidence/manifest, staged publish with rollback, `necropsy render`, `--no-package`; Playwright 1.63 + Chromium (user approved 06.7) · unit, integration, browser (14) and golden end-to-end (full export: 15 bosses, byte-identical rerender) checks; screenshots light/dark desktop/mobile · awaiting review
2026-10-13 · slice 4 · 06.2–06.5 · review round 1 fixes: publish preflight refuses directories/links with artifact names; `pets_listed` added to analysis.json entries and the no-pet fact proven only with the listing; every cohort aggregate (explosives, weave adoption, foreign-share median) keeps the inferred grade; Tauren fill reported as considered vs used; RenderError for analysis.json missing nested data or evidence paths (clean CLI exit); failure/recovery docs scoped · 518 passed 4 xfailed, acceptance · awaiting round 2
2026-10-13 · slice 5 · 06.2 · round-2 wording refinements (fill applied / none qualified / too few; pet listing missing vs unrecorded vs none) · navigator AGREE round 2 · commit e1d4f11 pushed; CI run 38381853527 success; Hindsight CLOSE for agent boxes

2026-10-13 · slice 6 · 06.8 (in progress) · complete reference parity inventory agreed; data percentile/name/overall-cohort and structured playbook checkpoints reviewed, timing/evidence corrections requested; shared reference frame, boss search and Truth model, auth guide and docs links · focused analysis checks59 and browser/view/render checks47; ruff/format/mypy93 files clean; desktop/mobile draft screenshots · uncommitted, remaining global/static data and full content presentation open

2026-10-13 · slice 7 · 06.8 (review pending) · complete reference structure and dense shared presentation, all15boss content/13column overall cohort/17slot gear, percentile/name catalog/global setup and sourced conditional guidance, pet training and armor-slot correction, auth guide; evidence drilldowns retained · focused browser/view/render50 and data/guidance69 pass; full-fixture package regenerated with 75 recorded cohort rows, screenshots desktop/mobile top/Patchwerk/Gothik; full suite and peer review pending · uncommitted

2026-10-13 · slice 8 · 06.8 (final review requested) · source-based guidance integrated with conditional/unknown states, unchanged valid280TP profile, separate armor/ring counts, default-dark reference theme with persisted light/system choice, safe source links and long-name overflow checks across added sections; KT encounter clock explicitly separated from logged fight start · full suite727 passed/4 known xfailed; final focused presentation51 passed, source/test secret scans clean, docs links and full15boss desktop/mobile expanded overflow checked · uncommitted; peer review pending

2026-10-13 · slice 9 · 06.8 complete · peer round1 corrections preserve rank-one known non-use, explain known non-users in insufficient timing samples, and attach specific citations once per profile section and only to declared advice dependencies; peer AGREE round2 (0 blocking/0 important), Captain Hindsight CLOSE with integration/decision/lesson/manual-action review · peer full728 passed/4 known xfailed; Codex62 focused checks, ruff/format/mypy clean; full15boss/75row preview plus actual CLI rerender verified byte-identical JSON/HTML/ZIP; desktop/mobile timing/citation/overflow checks passed · implementation cd64345 committed and pushed; Linux/Windows CI run38417517143 success; record-only close-out follows in the same checkpoint sequence

2026-10-14 · slice 10 · 06.9 · KISS card added to both pages, preserving detailed
timelines/loadout/execution/gear/evidence. Simplified ranged comparator pattern,
observed Rapid Fire cast timing/counts and sourced encounter guidance remain
distinct; actual medians include Loatheb 40.096 s and Thaddius 81.8685 s, not a
universal pull cast. Saved overall-rank-one scores were already in verified raw
leaderboards but ignored when event calculations were absent. New scalar fallback
is observed metadata, with exact first-row/context guards and source/capture
provenance; it never alters same-faction medians or advice. Existing captured
actor identity remains when matching; legacy capture time is explicitly unknown.
Future acquisitions record UTC page capture time. Live-reader partition/page
binding, acceptance deep-sample flag and docs reconciled. Race profile API and all
saved JSON checked; no direct race metadata found, racial casts remain observed
evidence. Real verified offline rebuild fills all 15 headline DPS values; all 15
recommendation/playbook/subject/cohort/baseline records unchanged. Targeted 180
passed before final identity retention, followed by 18 guard/replay checks;
actual live/historical browser pages inspected at desktop and narrow widths.
Review, close-out and checkpoint publication pending.

### Captain Hindsight — additive opening and metadata follow-up (2026-10-14)

**Keep:** The KISS card supplements every existing detailed section. It presents
an observed comparator pattern for practice, cast timing rather than a universal
Rapid Fire pull prescription, and cited encounter guidance. Saved rank-one scalar
metadata is reused through existing normalization/analysis; no extra network
acquisition or parallel reporting path is needed. Known event calculations and
all same-faction samples, medians, advice and actor identity stay intact.

**Fix before closing:** None required after the round-1 identity-conflict correction
and typed malformed-JSON guard. Browser assertions now separately verify the seven
existing plan labels and three added labels. Multi-Shot spelling and practice-pattern
wording were tightened after the optional review notes.

**Record:** PM-10/PM-11 calibrated and lessons promoted. User-requested
"Recommended opener" label retained, with explicit comparator practice basis;
this does not claim an optimal rotation. Classic Era race availability is documented
from the actual API response and all 785 saved JSON members. Reported score source,
legacy capture-time absence, future capture timestamps and metadata/deep-sample
distinction are documented in the JSON/usage contracts and changelog.

**Risk:** Racial casts remain the available affirmative race evidence in this
acquisition. Unassigned pet owners still legitimately limit event-derived damage
and pet calculations. Legacy leaderboards have no capture timestamp; that time is
explicitly unknown. Domain mechanics review and the broader live-subject close-out
are separate and remain open.

**Verdict:** CLOSE 06.9. Evidence: verified live archive replay fills all 15 headline
scores, while all 15 recommendation/playbook/subject/cohort/baseline records are
unchanged. Live and historical pages retain their sections/gear/evidence and passed
desktop/mobile checks; actual screenshots inspected. Broad suite: 1,044 passed,
one deliberately skipped live test, four expected failures, two obsolete label-count
assertions subsequently fixed and both reruns passed. Follow-up 103 checks plus 22
latest identity/JSON/replay guards and two quick-card checks passed; ruff/format/mypy,
build and source secret scan clean. Final record/writing review follows; publication
will be recorded with the checkpoint commit.
