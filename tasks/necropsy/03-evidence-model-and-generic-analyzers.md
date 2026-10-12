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

- **Existing code found** — database from 02 (`necropsy.normalize.schema`, `necropsy.normalize.coverage.has_complete_coverage`); no analysis code existed (search `rg -n "analysis|evidence" src` before this subject → only module docstrings).
- **Behaviour to preserve** — ingest output and coverage semantics; fixture tests.
- **Reuse / extend** — all coverage decisions go through `has_complete_coverage` (wrapped by `necropsy.analysis.context.trusted`); participants come from `benchmark_participants` and actors from `stream_coverage` (no name matching against masterData).
- **Do not duplicate** — one evidence constructor path (`necropsy.analysis.evidence` factories); one rule loader (`necropsy.rules.load_rules`); fact checks reuse analyzers rather than re-implementing them (only the event *count* has a deliberately independent implementation, from 02).
- **Integration point + why** — `necropsy.analysis.{evidence,context}`, `necropsy.analysis.generic.{environment,metrics,targets,cohort}`, `necropsy.rules` package data. Class plugins (04) and encounter rules (05) consume these.
- **Vision fit** — spec §1.4 (evidence levels), §6 (environment and bias model, WF tri-state, race status), plan §6.18–6.20; D019 moves rules into package data; D020 adds the raid-class faction rule.
- **Risks** — analyzers have only test callers until 05 builds `analysis.json` (disclosed in D020); DPS includes every actor exported as a pet, which over-counts where `petOwner` links non-pet units (Faerlina, Razuvious) until 04.5 classifies pets.

## Boxes
> ID = `<subject-id>.<box-number>` (subject index ID · box ordinal). Stable — never
> renumber; mark retired boxes done and struck with `ABANDONED; see D###`
> (see §4), don't delete. A human-owned box recorded `DEFERRED` in
> `manual-actions.md` stays `[ ]` and follows the §5 Done rule.
> Owner MUST be one of the §5 enum:
> agent · release-engineer · product-owner · tech-lead · domain-sme.

- [x] **03.1** (agent) Evidence model: level (OBSERVED / DERIVED / INFERRED /
      UNKNOWN), source refs (report, fight, actor, event ids), rule id, and
      coverage ref attached to every derived value; Windfury and race status
      enums per spec §6.
- [x] **03.2** (agent) Environment/bias profile per fight: faction, race
      evidence (racial-ability rules in `rules/classic_era/racials`), talent
      fingerprint, role, world/external buffs (incl. Sayge DMF variants), WF
      status + extra-attack count + attributed damage, raid kill duration, gear
      fingerprint.
- [x] **03.3** (agent) Generic fight metrics: duration, DPS by ability,
      casts/min, cooldown timeline, buff/debuff uptime, deaths with killing
      blows, pets/guardians (incl. engineering summons) with first/last activity
      relative to fight start/end.
- [x] **03.4** (agent) Target integrity: per-target damage split with a
      native-target hook supplied by encounter plugins.
- [x] **03.5** (agent) Cohort comparison: per-slot gear and enchant dominance
      (e.g. Sniper Scope 664 vs Biznicks 2523), talent build distribution,
      consumable/world-buff prevalence.
      As shipped: `gear_slot_distribution` / `enchant_distribution` per slot
      (missing gear or slot counted as unknown), `item_prevalence` (any slot),
      `starting_aura_prevalence` for consumables and world buffs given an ID→name
      map; the Hunter consumable list itself is Hunter knowledge and lands in 04.
- [x] **03.6** (agent) Golden checks: Smcadogx `RACIAL_EVENT_CONFIRMED` Orc +
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

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

**Captain Hindsight — 2026-10-13 (after navigator `VERDICT AGREE round=2`)**

1. **Keep:** evidence rules enforced at construction (VALUE vs COMPLETE, persisted coverage refs, NOT_OBSERVED only as COMPLETE); Windfury split into confirmed status, counts and a clearly labelled inferred estimate; every verified golden fact backed by a registered checker running the analyzers (57/79); faction rule data-validated before use; rules as package data proven from an installed wheel.
2. **Fix before closing:** none open. Review rounds fixed: Windfury "lower bound" wording and zero-match handling (two design CHALLENGEs), single-flag aura uptime, last-row-wins faction, unenforced absence contract, per-slot cohort scope, kill duration level.
3. **Record:** D019, D020. Lessons: probes must filter exactly like analyzers; realm-name normalization; guild faction enum differs. Carry to 04: pet classification (Faerlina/Razuvious DPS over-count, two facts xfail), Hunter consumable list, Hunter spell IDs in rules.
4. **Risk:** analyzers have only test callers until `analysis.json` (05.5); two cohort factions are inferences; `wf-unique-swing-v1` window (400 ms) is a parameter, not validated against a ground truth.
5. **Verdict:** CLOSE

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
2026-10-13 · slice 1 · 03.1–03.6 · design huddle (two Codex CHALLENGEs on Windfury attribution accepted: INFERRED, unique-match only, no lower-bound claim, zero matches → UNKNOWN), evidence model + factories, rules package data (racials, externals incl. WF ids, DMF, world buffs, faction codes, raid-class faction rule), context (participant → actor via coverage rows, realm-name normalization), environment profile, metrics, target split (native/foreign UNKNOWN without encounter rule), cohort distributions, fact-checker registry (subset + full) · observed: subset profiles match the oracle (kill durations, Haplina DMF Agility vs top Damage, Smcadogx Orc + WF 9/4 procs, Alliance comparators NOT_OBSERVED, Snape single death 25.678 s); probe error found and corrected (the 39.0 s death was a Fallout Slime in Snape's stream); faction split 63/12 needs two INFERRED factions; Haplina DPS matches 13/15 bosses, Faerlina/Razuvious over-count pending 04.5; facts verified against raw: 57/79 (checker-backed); fast suite 144 passed; ruff + mypy strict clean · commit pending pair review
2026-10-13 · slice 2 · 03.1, 03.2, 03.3, 03.5 · review round 1 fixes: VALUE/COMPLETE claims with persisted coverage refs (NOT_OBSERVED only as COMPLETE; direct-constructor bypass rejected), per-aura uptime with interval union and settled-state rule, faction aggregates every reading (conflict or unreadable code → UNKNOWN, no inference), per-slot gear/enchant distributions and starting-aura prevalence, faction-inference caveat documented · fast 154 passed, golden 61 passed + 2 xfail · commit pending pair review
2026-10-13 · slice 3 · 03.2 · navigator AGREE round 2 with one important note absorbed: kill duration is DERIVED (end − start), level pinned in test · fast suite green
2026-10-13 · slice 4 · Hindsight · commit pushed; CI run 38322905509 success; Hindsight CLOSE
