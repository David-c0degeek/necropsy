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

- **Existing code found** — generic layer from 03 (`necropsy.analysis.generic.{environment,metrics,targets}`, `necropsy.analysis.context`), rule loader `necropsy.rules.load_rules`; no class-specific code existed (search `rg -n "Hunter|hunter" src` before this subject → only docstrings).
- **Behaviour to preserve** — evidence and coverage contracts from 03; all 03 fact checks.
- **Reuse / extend** — cast and damage aggregation, deaths, activity windows and aura handling come from `metrics` (aura uptime refactored into `aura_intervals` so Auto intervals can test haste overlap); pet discovery from `context.owned_pets`; Windfury from the environment profile.
- **Do not duplicate** — no second cast/aura/death implementation; ranking damage lives once in `targets.ranking_damage` and is used by the fact checkers.
- **Integration point + why** — `necropsy.analysis.classes` registry (`plugin_for(game, class_id)`) with `classic_era/hunter.py`; rules `hunter.yaml`, `items.yaml`. Encounter rules (05) plug into `ranking_damage(excluded=…)` and consume `friendly_crowd_control` and the Auto-gap signal.
- **Vision fit** — spec §3 class plugin list (Auto cycle, Aimed/Multi, RF, Quick Shots, Renataki/Refocus, Raptor weaving, pets, gear, Hunter's Mark); plan §6.23 (class vs encounter knowledge separate); D021 ranking-damage rule; D022 pet ranks not reported.
- **Risks** — the long-gap signal has no encounter context yet (movement, phases); `items.yaml` names are display data from an oracle join; FD trinket swaps not inferred; the plugin has only test callers until `analysis.json` (05.5).

## Boxes
> ID = `<subject-id>.<box-number>` (subject index ID · box ordinal). Stable — never
> renumber; mark retired boxes done and struck with `ABANDONED; see D###`
> (see §4), don't delete. A human-owned box recorded `DEFERRED` in
> `manual-actions.md` stays `[ ]` and follows the §5 Done rule.
> Owner MUST be one of the §5 enum:
> agent · release-engineer · product-owner · tech-lead · domain-sme.

- [x] **04.1** (agent) Class plugin interface + registry; Hunter is the only
      implementation (no stubs for other classes).
- [x] **04.2** (agent) Auto Shot cycle reconstruction: every Auto→Auto interval
      with RF/Quick Shots overlap and Aimed/Multi/Raptor/Refocus inside;
      clipped-cycle detection. Semantics match `auto_interval_reconstruction.csv`.
- [x] **04.3** (agent) Special-shot cadence: Aimed/Multi per minute, gaps,
      opener timeline, RF timing, Renataki equipped vs Refocus cast, Hunter's
      Mark, explosives (Dense Dynamite, Sapper).
- [x] **04.4** (agent) Melee weave: Raptor count + DPS, white-melee count,
      WF-attributed share; Raptor-only weave distinguished from WF melee package.
- [x] **04.5** (agent) Pet forensics: family evidence (observed vs inferred from
      ability compatibility in `rules/classic_era/pets`), ranks from spell IDs,
      DPS, start/stop relative to fight, death + killing blows, absent pet
      gated on coverage. Actors linked by `petOwner` are classified first:
      hunter pet vs guardian/engineering summon (e.g. Battle Chicken) vs trap
      object (e.g. Frost Trap) vs other (e.g. Skilled Bonesmith, Sheep); only
      hunter pets feed pet benchmarks.
- [x] **04.6** (agent) Hunter gear context: ranged weapon, trinkets, scope,
      melee setup per fight; dominance per boss from cohort.
- [x] **04.7** (agent) Golden: Patchwerk Raptor counts; Haplina Patchwerk Aimed
      timestamps (10.91 → 75.47); Gothik Aimed gap; KT 38.97 s Aimed gap;
      Patchwerk pet DPS; 24/24 Renataki → Refocus (historical mode).
- [ ] **04.8** (domain-sme) Review one boss's Hunter output for mechanics
      correctness.
      `DEFERRED — see manual-actions`: batched with the 05.7 review (D017 pattern),
      when per-boss output exists to review.

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

**Captain Hindsight — 2026-10-13 (after navigator `VERDICT AGREE round=3`)**

1. **Keep:** plugin registry with one real plugin; every Hunter value goes through the shared metrics and evidence factories; rule data with sources (fixture IDs, Petopia family table, Wowhead-corroborated item IDs); ranking damage validated against all 75 cohort rows rather than one boss; target side recorded with provenance; golden facts now 80/84, every one checker-backed.
2. **Fix before closing:** none open. Reviews fixed: name-keyed spell maps losing IDs, type-based friendliness (twice: Player/Pet, then NPC), partial gear producing a false negative, target-less damage (positive and zero amounts), Environment placeholder vs missing target.
3. **Record:** D021, D022; lessons on rule validation across the whole cohort and WCL ability-name aliases. Carry to 05: encounter exclusions (Faerlina Worshipper, Razuvious Understudy, Anub, Gluth, Heigan) to reach 75/75 ranking DPS; Gothik native targets; KT raid-utility window; long-gap signal needs phase/downtime context; Hunter consumable list.
4. **Risk:** plugin has only test callers until `analysis.json` (05.5); `auto-gap-v1` parameters (1.25 × median, 5 clean intervals) are not validated against labelled clips; fight friendly/enemy lists are WCL's and could omit actors.
5. **Verdict:** CLOSE

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
2026-10-13 · slice 1 · 04.1–04.7 · design huddle (Codex DESIGN_AGREED with guardrails), plugin registry, Hunter plugin, rules `hunter.yaml` (spell IDs from fixture, Petopia family table fetched 2026-10-13, non-Hunter pet game IDs from fixture) and `items.yaml` (oracle-join + Wowhead tooltip corroboration), `aura_intervals`, `ranking_damage` · findings: WCL ranking damage = Hunter + pet-linked actors minus self/own-pet damage (64/75 top rows exact; 11 are encounter exclusions for 05); Haplina Faerlina/Razuvious DPS gaps = Worshipper/Understudy damage; `Demoralizing Screech` alias needed · observed: Patchwerk Aimed timestamps 10.91…75.47, Gothik 282.5 s gap, KT 38.97 s gap with friendly Reckless Charge 102.51 / Scatter 115.32 and Freezing Trap 97.36, top-5 Patchwerk pet DPS 216/149/222/160/174, Cats by Claw+Dash, all 15 Haplina shot counts, Renataki→Refocus 24/24 · facts verified 80/84 · fast 176 passed · commit pending pair review
2026-10-13 · slice 2 · 04.3, 04.5, 04.6 · review round 1 fixes: spell IDs grouped by name (both Reckless Charge IDs), target-friendliness-v1 (event flag, fight friendly lists, NPC/NPC-owned pet hostile, else undecided → partial), Renataki/trinkets UNKNOWN unless both trinket slots recorded, ranking damage UNKNOWN for target-less damage and blocks exclusions on unlisted targets · regressions added; fast 182 passed, golden 84 + 2 xfail; KT friendly CC still Reckless 102.51 / Scatter 115.32 as a COMPLETE claim · commit pending pair review
2026-10-13 · slice 3 · 04.3, 04.5 · review round 2 fixes: target-less damage detected by row count (zero-amount crash fixed), target-side-v1 (event flag / fight friendly lists / fight enemy list, also via pet owner; actor type never decides; side provenance recorded), WCL Environment placeholder (-1) = no unit target · regressions added; fast suite green; golden 84 + 2 xfail; KT friendly CC complete (Reckless 102.51, Scatter 115.32) · commit pending pair review
2026-10-13 · slice 4 · 04.5 · in-round fix: missing target ID stays undecided; Environment placeholder is no-unit-target only for ground-placed abilities (Freezing Trap) · navigator AGREE round 3
2026-10-13 · slice 5 · Hindsight · commit pushed; CI run 38327193624 success; Hindsight CLOSE
