# Desktop Updates Plan

## Collaboration model

| Field | Value |
|---|---|
| Mode | solo |
| Primary owner | agent |
| Coordinator | agent |
| Resume safety | required |
| Parallel branches | no |
| Notes | Main; previous user approval to commit and push persists. No release publication or personal installation is part of implementation. |

### Parallel work tracker

Not applicable in solo mode.

### Checkpoint gate

Update subject boxes, progress, tracker and affected decisions/lessons/docs; run
relevant verification and exercise the changed flow; commit and push coherent
checkpoints. Never rewrite pushed history. Keep public code and commit messages
independent of disposable plan references. One checkpoint may cover related boxes.

## 1. Subject

Offer Update reports on known saved analyses, explicitly check for app updates,
and let a managed installation install an available release and restart. Preserve
analysis data, saved-run identity, resume ownership and existing installation
recovery. Reuse current report rendering and versioned installer assets.
Portable/source builds receive an honest manual release-download path. No WCL
acquisition, automatic background update, new updater signing infrastructure,
release publication or modification of David's installed app is required.

### Risks and rollback

| Risk | Impact | Mitigation / rollback |
|---|---|---|
| Saved output hashes become stale | Resume rejects refreshed runs | Same output lock, preflight Checkpoint validation, output/metadata rollback on error; preserve analysis bytes. Existing crash-recovery boundary remains explicit. |
| Wrong or incomplete release | Unusable update or downgrade | Stable semantic versions; fixed GitHub repository and release URLs; complete platform assets and hashes; recheck before installation. |
| Installer fails or app closes during install | Current app unavailable | Reuse fresh version directories, readiness checks and preserved prior versions; keep GUI alive while installing and wait safely on close. |

Revert feature commits to remove the UI/backend additions. App updates retain old
version directories; saved-data and vault locations are separate from app files.

## 2. Authoritative inputs

| Source | Contribution |
|---|---|
| main at 8632344 | Baseline and approved report-layout work |
| docs/decisions/0010-graphical-desktop.md | Python engine, allowlisted IPC, trusted rendering and save-before-exit |
| docs/decisions/0011-gui-default-installation.md | Private staged installs, exact version readiness, publish-before-switch |
| src/necropsy/wcl/checkpoint.py and analyze.py | Output ownership and shared run lock |
| install.ps1, install.sh, scripts/check_bootstrap.py | Versioned install and failure recovery |
| tasks/desktop-updates/pre-mortem.md | Retained predictions and guardrails |
| https://docs.github.com/en/rest/releases/releases | Stable release metadata and assets |
| https://docs.github.com/en/rest/releases/assets | Download URLs, sizes and optional asset digest |
| https://v2.tauri.app/plugin/updater/ | Native updater candidate; deferred because existing distribution uses custom bootstrap and no updater signing setup |

### Verification commands

| Purpose | Command | Notes |
|---|---|---|
| Python lint/types | uv run ruff check .; uv run ruff format --check .; uv run mypy | Required |
| Python build | uv build | Includes desktop modules/resources |
| Targeted backend | uv run pytest tests/unit/test_desktop_engine.py tests/unit/test_report_refresh.py tests/unit/test_app_updates.py -q | New failure/recovery contracts |
| Fast suite | uv run pytest -m "not golden and not live and not acceptance" -q | Browser included |
| UI | npm run build; npm run format:check | cwd desktop |
| Native | cargo fmt --check; cargo clippy --locked -- -D warnings | cwd desktop/src-tauri |
| Native runtime | uv run python scripts/check_desktop_window.py desktop/src-tauri/target/debug/necropsy-desktop.exe --screenshots workspace/desktop-updates | Requires Vite server; isolated app library/profile |
| Frozen/installer | Existing build_desktop, package_desktop and check_bootstrap flows | Extend relevant smoke checks; platform boundaries documented |

## 3. Subject file index

| # | File | Subject | Depends on |
|---|---|---|---|
| 00 | tasks/desktop-updates/00-tooling-research-and-readiness.md | Research and baseline | — |
| 01 | tasks/desktop-updates/01-saved-reports.md | Refresh known saved reports | 00 |
| 02 | tasks/desktop-updates/02-release-checks.md | Stable release discovery | 00 |
| 03 | tasks/desktop-updates/03-install-and-restart.md | Managed update and UI | 02 |
| 04 | tasks/desktop-updates/04-verification-and-docs.md | Integration, docs and delivery | 01, 03 |

## 4. Decision log

| ID | Date | Title | Decision | Rationale | Refs |
|---|---|---|---|---|---|
| D001 | 2026-10-16 | Distribution reuse | Use versioned published bootstrap assets, not Tauri plugin updater | No existing updater signing/release manifest; retain verified private-runtime staging | 02, 03; ADR to be added |
| D002 | 2026-10-16 | Existing GUI rendering | Open Playbook already renders current templates; Update reports persists HTML/package | Earlier conversational assumption was incorrect; data conversion is unnecessary | 01; desktop guide |
| D003 | 2026-10-16 | Proportional teardown | Waive whole-repo cleanup-audit; review touched surfaces for duplication/dead code | Feature-scoped work, no repository teardown requested | 04 |
| D004 | 2026-10-16 | Release boundary | Implement and verify; no public release or personal install without a separate delivery instruction | Commit/push authorization does not itself publish release binaries | manual-actions.md |

## 5. Master progress tracker

| Done | # | File | Status | Owner summary | Human actions mirrored? |
|---|---|---|---|---|---|
| [x] | 00 | 00-tooling-research-and-readiness.md | DONE | agent: 8 | n/a |
| [ ] | 01 | 01-saved-reports.md | TODO | agent: 3 | n/a |
| [ ] | 02 | 02-release-checks.md | TODO | agent: 3 | n/a |
| [ ] | 03 | 03-install-and-restart.md | TODO | agent: 3 | n/a |
| [ ] | 04 | 04-verification-and-docs.md | TODO | agent: 3 | n/a |

## 6. Cross-cutting principles

1. KISS, YAGNI, CLEAN, SOLID, DRY; extend existing surfaces.
2. ~~C# one class per file~~ Not a C# project.
3. ~~C# nullable reference types~~ Not a C# project.
4. ~~.NET build warnings~~ Use strict Python/TypeScript/Rust checks.
5. Keep cohesive modules and explicit boundaries; no catch-all updater logic in App or engine dispatch.
6. Keep branching understandable and pin inherent failure behavior with tests.
7. Specify observable behavior, not guessed SDK shapes.
8. Tests protect data, failed install and user flows; no coverage-percentage target.
9. Every plan box has an owner and stable ID.
10. Lessons land in the plan folder as learned; promote durable lessons.
11. Public artifacts, tests, branch/commit metadata remain plan-agnostic.
12. Captain Hindsight before subject close; record Keep / Fix / Record / Risk / Verdict.
13. Complete subject 00 before implementation.
14. Checkpoints remain resume-safe: verified work, updated plan, commit and push.
15. Solo work; no delegation unless explicitly authorized.
16. Update user and developer docs with changed behavior.
17. Record Integration analysis before implementation; wire every public surface.
18. Pre-Mortem obligations live in tasks/desktop-updates/pre-mortem.md; every PM-* has Plan refs and a non-Pending resolution before sign-off.
19. No analytical recomputation or WCL/vault access for report refresh or app updates.
20. App updates are explicit; wait for active work, validate assets and retain the working app.

## 7. Gate review

- [ ] All subjects done or explicitly abandoned by decision.
- [ ] Verification commands pass, with platform limitations explicitly recorded.
- [ ] Changed flows exercised end-to-end; observed vs expected recorded.
- [ ] Risks and rollback reviewed; every PM-* terminal and calibrated honestly.
- [ ] Integration analyses recorded; existing service, publisher and installers reused.
- [ ] No unwired public surface or unjustified duplicate implementation.
- [ ] Every closed subject has Captain Hindsight CLOSE.
- [ ] Checked boxes have progress evidence and pushed checkpoint coverage.
- [ ] Main pushed and clean; no rewritten checkpoint history.
- [ ] No disposable plan references leaked into shipped code/tests/metadata.
- [ ] User/developer docs current; durable decision promoted to ADR.
- [ ] Human actions resolved or explicitly deferred.
- [ ] Teardown waiver D003 applied; touched-code cleanup findings triaged.
- [ ] Lessons reconciled before any future plan archival (no archival performed here).
- [ ] Report refresh preserves analysis bytes, identity, review keys and resume validation.
- [ ] Release check/install reject incomplete assets, wrong hashes, unsafe URLs and downgrades.
- [ ] Failed update leaves a working installation and readable retry guidance.

## 8. Acceptance / sign-off

| Date | Reviewer | Result | Notes |
|---|---|---|---|
| | | | |

## Appendix: Captain Hindsight Prompt

> This appendix is embedded so copied plans are self-standing and do not depend
> on machine-local prompt files.

```text
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
- Docs that drifted from shipped behaviour — user- and developer-facing alike (README, usage/HOWTO guides, CHANGELOG, API/command/config reference, architecture/onboarding docs, troubleshooting, examples, wiki, prompt/skill docs).
- Plan references that leaked into shipped code, tests, comments, identifiers,
  commit messages, branch names, PR titles, or PR descriptions.

Before returning a verdict, confirm the claimed verification against the
artefacts: rerun the relevant verification command or cite its recorded output.

Return exactly these sections:

1. Keep: what was correct and should remain.
2. Fix before closing: concrete issues, missing tests, spec drift, plan hygiene, or design problems — cite the file, test, or commit for each item.
3. Record: decisions or lessons that must be added to the plan files.
4. Risk: anything still uncertain after verification.
5. Verdict: CLOSE or DO NOT CLOSE.

If the verdict is DO NOT CLOSE, list the smallest concrete actions needed before
the work can be closed.
```
