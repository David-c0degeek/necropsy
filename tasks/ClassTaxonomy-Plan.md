# ClassTaxonomy Plan

## Collaboration model

| Field | Value |
|---|---|
| Mode | solo |
| Primary owner | agent |
| Coordinator | agent |
| Resume safety | required |
| Parallel branches | no |
| Notes | Existing research changes are part of this work. Checkpoints on a feature branch; no merge or release required. |

### Parallel work tracker

Not applicable: solo.

### Checkpoint gate

Update boxes, progress, decisions and lessons; run relevant verification and exercise changed behavior; review documentation impact; commit coherent checkpoints and push without rewriting history. Shipped code and commits remain plan-agnostic.

## 1. Subject

Implement separate Classic Era game talent trees/race validity and WCL ranking category metadata, preserve encounter evidence and broad-pool comparison scope, expose independent build preference/category choices in CLI, TUI and desktop, persist preferences through snapshots/resume, and render evidence honestly. All nine classes are included. Exact WCL classifier replication, full talent allocation inference, new game families, global unranked-build leader searches and release publication are outside this implementation.

### Risks and rollback

| Risk | Impact | Mitigation / rollback |
|---|---|---|
| Archive spec semantics change | Old replays fail | Preserve category keys and legacy checkpoints; optional additive fields; rollback code without touching raw archives |
| User tree becomes API slug | Requests rejected or comparisons mislabeled | Explicit category selection independent of declared tree; exact query tests |
| Unknown becomes known | False build/race claims | Source validation, three-state matches and validity checks; no race inference |

## 2. Authoritative inputs

| Source | Contribution |
|---|---|
| main checkout | Integration base; initial production tree clean, three research documentation files pending |
| docs/class-taxonomy-research.md and evidence JSON | Live WCL name/slug/ID catalog, tree evidence and bounded rules |
| docs/decisions/0005-class-and-encounter-duties.md and 0006-shared-class-combat-evidence.md | Existing separate evidence contracts |
| CONTRIBUTING.md, docs/architecture.md, tasks/lessons.md | Shared pipeline, unknowns, immutable archives, verification |
| tasks/class-taxonomy/pre-mortem.md | Stable risks and guardrails |

### Verification commands

| Purpose | Command | Notes |
|---|---|---|
| Build | uv build | Wheel and sdist |
| Python lint / format | uv run ruff check .; uv run ruff format --check . | Existing rules |
| Typecheck | uv run mypy | src/tests/scripts |
| Fast tests | uv run pytest -m "not golden and not live and not acceptance" | Includes browser checks when available |
| Desktop build | npm run build (desktop) | TypeScript / Vite |
| Behavior | targeted catalog, desktop/TUI, CLI/resume, snapshot/offline and rendered-report tests | Actual selection -> query/persist -> report evidence |

## 3. Subject file index

| # | File | Subject | Depends on |
|---|---|---|---|
| 00 | tasks/class-taxonomy/00-tooling-research-and-readiness.md | Tooling research and readiness | â€” |
| 01 | tasks/class-taxonomy/01-catalog-and-evidence.md | Game catalog and evidence | 00 |
| 02 | tasks/class-taxonomy/02-selection-and-persistence.md | Selection and persistence | 01 |
| 03 | tasks/class-taxonomy/03-reports-and-comparisons.md | Reports and comparisons | 01, 02 |
| 04 | tasks/class-taxonomy/04-verification-and-documentation.md | Verification and documentation | 01, 02, 03 |

## 4. Decision log

| ID | Date | Title | Decision | Rationale | Refs |
|---|---|---|---|---|---|
| D001 | 2026-10-16 | Research reuse | Reuse completed same-day primary research; no new dependencies or WCL requests required | Evidence already captured/reviewed | 00.4â€“00.7; docs/class-taxonomy-research.md |
| D002 | 2026-10-16 | Separate selection | Keep --spec/--category as WCL selection; add --talent-tree as declared intent, independent of category and observed talents | Avoid silently remapping ambiguous hybrids and breaking scripts | 02.1; durable ADR to follow |
| D003 | 2026-10-16 | Scope review | Waive whole-repo cleanup-audit; inspect changed seams during close-out | A fresh whole-repo teardown is outside this feature | 04.2 |

## 5. Master progress tracker

| Done | # | File | Status | Owner summary | Human actions mirrored? |
|---|---|---|---|---|---|
| [x] | 00 | 00-tooling-research-and-readiness.md | DONE | agent | n/a |
| [ ] | 01 | 01-catalog-and-evidence.md | TODO | agent | n/a |
| [ ] | 02 | 02-selection-and-persistence.md | TODO | agent | n/a |
| [ ] | 03 | 03-reports-and-comparisons.md | TODO | agent | n/a |
| [ ] | 04 | 04-verification-and-documentation.md | TODO | agent | n/a |

## 6. Cross-cutting principles

1. Reuse the single client, normalizer, evidence, snapshot and report pipeline.
2. Every box has a stable ID and owner; progress, decisions and lessons survive resumes.
3. Production code/tests/commits must not reference disposable plan IDs or paths.
4. Perform Captain Hindsight before subject close; keep original PM predictions and calibrate outcomes.
5. Readiness precedes implementation; no new services, credentials or dependencies.
6. Checkpoint commits and pushes preserve history; never merge/release without scope for it.
7. Update affected user/developer documentation with implementation.
8. Preserve archived spec=category, historical output, unknowns, source provenance and coverage.
9. Pre-Mortem obligations live in tasks/class-taxonomy/pre-mortem.md; every PM-* risk must have Plan refs and a non-Pending resolution before sign-off.

## 7. Gate review

- [ ] All subjects done, behavior exercised and recorded, commands pass.
- [ ] Integration analyses show reuse; all new public surfaces have production callers.
- [ ] Durable selection/evidence decisions recorded in ADR and docs updated.
- [ ] All PM risks have terminal resolution and observed outcomes calibrated; misses carry lessons.
- [ ] Captain Hindsight verdict CLOSE for every subject.
- [ ] Checkpoints pushed and feature branch clean; no plan references leaked into shipped artifacts.
- [ ] Human actions resolved/deferred; cleanup review waiver recorded; lasting lessons reconciled.

## 8. Acceptance / sign-off

| Date | Reviewer | Result | Notes |
|---|---|---|---|
| | | | |

## Captain Hindsight prompt

You are now Captain Hindsight.

Review the completed subject, phase, box, or major plan section with hindsight.
Assume the work is already done, then identify what is clearer now than it was
before the work started.

Check specifically for:
- Scope drift or missed requirements.
- Spec deviations that need a Decision-log row (and whether the decision is
  durable enough to promote to the project's ADR / decision log).
- Lessons that should be recorded before context is lost.
- Tests that pin implementation details instead of observable behavior.
- Complexity, duplication, brittle design, or awkward naming that should be fixed now.
- Behaviour closed on a green build alone: a box marked done on a passing build/test exit code without the changed flow exercised end-to-end (observed-vs-expected output).
- Reuse missed or vision drift: new parallel code where existing code should have been extended, or a change that drifts from the project vision/ADRs (cross-check the subject's Integration analysis).
- Human-owned actions that need to be mirrored or resolved.
- Docs that drifted from shipped behaviour â€” user- and developer-facing alike (README, usage/HOWTO guides, CHANGELOG, API/command/config reference, architecture/onboarding docs, troubleshooting, examples, wiki, prompt/skill docs).
- Plan references that leaked into shipped code, tests, comments, identifiers,
  commit messages, branch names, PR titles, or PR descriptions.

Before returning a verdict, confirm the claimed verification against the
artefacts: rerun the relevant verification command or cite its recorded output.

Return exactly these sections:

1. Keep: what was correct and should remain.
2. Fix before closing: concrete issues, missing tests, spec drift, plan hygiene, or design problems â€” cite the file, test, or commit for each item.
3. Record: decisions or lessons that must be added to the plan files.
4. Risk: anything still uncertain after verification.
5. Verdict: CLOSE or DO NOT CLOSE.

If the verdict is DO NOT CLOSE, list the smallest concrete actions needed before
the work can be closed.


Also calibrate relevant PM risks and record CH-MISS entries without rewriting predictions.
