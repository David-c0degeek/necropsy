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

- **Existing code found** — generic layer (`necropsy.analysis.generic.{environment,metrics,targets,cohort}`, `necropsy.analysis.context`), Hunter plugin (`necropsy.analysis.classes.classic_era.hunter`: shots, Rapid Fire, explosives, pets, `friendly_crowd_control`, Auto-gap signal), `targets.ranking_damage(excluded=…)` hook left by 04, rule loader `necropsy.rules.load_rules`, CLI `necropsy ingest`. No encounter, benchmark or report code existed (`rg -n "encounter|benchmark|analysis.json" src` before this subject → only docstrings and the `excluded` parameter).
- **Behaviour to preserve** — evidence/coverage contracts (03), ranking-damage rule D021, all 01–04 fact checks, ingest safety rules (target WAL refusal, atomic swap, `--replace`).
- **Reuse / extend** — encounter exclusions plug into `ranking_damage(excluded=…)`; cohort distributions from `generic.cohort`; Hunter metrics consumed as-is; `offline` reuses `ingest` for the database and its integrity checks; serializer walks the existing evidence dataclasses.
- **Do not duplicate** — no second metric, damage or faction implementation; recommendations reference values by path into the same document instead of re-computing them.
- **Integration point + why** — `necropsy.analysis.encounters` (data-driven rules in `rules/classic_era/zones/naxxramas.yaml`, findings in `encounters/findings.py`) keeps encounter knowledge out of class plugins (§6.23); `analysis.benchmark` and `analysis.recommendations` sit above class + encounter layers; `necropsy.report.{serialize,analysis_json,offline}` is the only producer of `analysis.json`, which 06 renders.
- **Vision fit** — spec §7 recommendation shape and §8 benchmark views; D008 historical mode; D021; analyzers from 03/04 gain their first non-test caller (D020).
- **Risks** — historical cohort is at most five entries per boss, so medians are small-sample (min 3 known, else UNKNOWN); ranking exclusions are empirical, not documented by WCL (D023); recommendation thresholds are heuristics awaiting 05.7 review.

## Boxes
> ID = `<subject-id>.<box-number>` (subject index ID · box ordinal). Stable — never
> renumber; mark retired boxes done and struck with `ABANDONED; see D###`
> (see §4), don't delete. A human-owned box recorded `DEFERRED` in
> `manual-actions.md` stays `[ ]` and follows the §5 Done rule.
> Owner MUST be one of the §5 enum:
> agent · release-engineer · product-owner · tech-lead · domain-sme.

- [x] **05.1** (agent) Encounter plugin interface + Naxx rule files
      (`rules/classic_era/zones/naxxramas`): native target ids, phases/downtime,
      burst windows, pet hazards, known distortions for all 15 bosses.
      *Narrowed by D024: all 15 bosses listed with ranking exclusions and native
      targets where an analysis consumes them; phase/burst/hazard data deferred.*
- [x] **05.2** (agent) Gothik native vs foreign-target DPS; KT MC-control
      utility (Freezing Trap, Scatter Shot on friendly, Reckless Charge on
      friendly) classified as raid assignment; Sapphiron/KT raid-speed
      classification from kill duration vs cohort.
- [x] **05.3** (agent) Benchmark views: (A) same-faction realistic ceiling,
      (B) robust baseline from the metadata cohort (build/gear dominance,
      medians, outlier flags), (C) cross-faction ceiling, opt-in and never
      merged. Historical mode builds A as "best same-faction inside the recorded
      overall top 5" and states that limit in output.
      *B in historical mode is the same-faction entries of the recorded top 5;
      outlier flags wait for the live 20–30 entry cohort (D024).*
- [x] **05.4** (agent) Recommendation objects (spec §7 shape + controllability
      + evidence refs + benchmark ref); shot-count targets projected to the
      subject's kill duration as ranges.
- [x] **05.5** (agent) `analysis.json` schema v1 (Pydantic; JSON Schema exported
      to `docs/`), deterministic ordering, cohort provenance, coverage summary,
      mode, tool version. `necropsy offline <snapshot> --out <dir>` writes it.
- [x] **05.6** (agent) Golden: Haplina historical-mode recommendations match the
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

- [x] Captain Hindsight review recorded (2026-10-13, agent boxes 05.1–05.6)
- [ ] Verdict is `CLOSE` — agent work CLOSE; subject stays open until 05.7 is adjudicated

**Captain Hindsight — 05 agent boxes (2026-10-13)**

- **Keep:** evidence paths resolved by test against the emitted document (caught a
  real path bug); per-member references on every aggregate; empirical rules
  labelled in output and guarded by a standing golden test (90/90); typed
  document model validated before every write; atomic output with verified reuse.
- **Fix before closing:** none in code. 05.7 (domain-sme) must adjudicate the
  disputed facts and heuristics before the subject is DONE.
- **Record:** D023–D028; lesson on cross-reference resolution tests. Navigator
  round 1 found three blocking issues the driver's own tests missed (reuse
  bypassing verification, missing metadata read as foreign, inferred membership
  upgraded by aggregation) — all were "absence/uncertainty silently becomes a
  confident value", the same class 03/04 reviews caught. Future subjects should
  add a negative test per aggregate for "unknown/inferred input in, what grade out".
- **Risk:** historical cohort is at most five entries; recommendation thresholds
  are heuristics; the exported JSON Schema does not carry the nested evidence
  check (documented); Grobbulus raid-speed flag and Gothik weave verdict await
  review.
- **Verdict:** `CLOSE` for 05.1–05.6 (commit 3c98b0e, CI run 38363722668 success).
  Subject 05 remains IN PROGRESS pending 05.7.

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
2026-10-13 · slice 1 · 05.1–05.6 · huddle (Codex DESIGN_AGREED), Naxx encounter rules (ranking exclusions reproduce 90/90 recorded fights, Gothik native targets), target-integrity and raid-utility findings, three benchmark views, recommendations-v1, analysis.json v1 + JSON Schema, `necropsy offline`; pet-inactive-v1 rule; facts promoted (176 verified, 4 disputed with resolutions) · ruff, mypy strict, fast + golden suites (399 passed, 4 xfail), acceptance passed, analysis.json byte-identical over repeated runs · not yet committed (awaiting review)
2026-10-13 · slice 2 · 05.2–05.5 · review round 1 fixes: `--db` reuse verifies archive digest and entries manifest; unclassifiable damage targets make the target split UNKNOWN (D028); inferred faction membership propagates to medians, ranges, ceiling and confidence with per-member refs (D027); raid-speed wording no longer asserts a cause; typed analysis.json schema with nested evidence validation and negative tests; ranking exclusions labelled empirical with a standing golden test · ruff, mypy strict, fast + golden + acceptance suites · not yet committed (awaiting round 2)
2026-10-13 · slice 3 · 05.2, 05.4, 05.5 · round-2 follow-up: padding confidence carries membership and links cohort target evidence; docs state the JSON Schema/pydantic validation difference · navigator AGREE round 2 · commit 3c98b0e pushed; CI run 38363722668 success; Hindsight CLOSE for agent boxes
2026-10-13 · slice 4 · 05.2–05.5, 05.7 · user review decisions: weave per target role (D029), start trash (D030), Tauren-only fill (D031), raid speed v2 with both comparisons (D032), ranked damage by target (D033); probe evidence/05-gothik-and-parse-targets.{py,txt}; navigator DESIGN_AGREED after one challenge · ruff, mypy strict, fast + golden suites · awaiting review
2026-10-13 · slice 5 · 05.2–05.5 · review round 1 fixes (game-ID-only exclusions, NPC-only Raptor roles, stable NPC identity with aliases and player/pet category rows, COMPLETE zero shares with n_unknown, phase claim removed) · navigator AGREE round 2 · commit 636eb52 pushed; CI run 38371784179 success
