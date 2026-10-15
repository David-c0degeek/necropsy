# AllClasses-Plan.md — All remaining Classic Era classes, shared playbooks, solo execution

> **Purpose.** Authorized follow-up plan created from the bundled c0degeek planning template on 2026-10-15. Implementation is shipped; engineering verification is complete and human acceptance is tracked below.
>
> **Disposable.** The plan and its `tasks/all-classes/` folder are deleted (or
> archived out of the repo) once the subject ships to production. Deleting or
> archiving the folder is human-owned and happens only after §8 sign-off; the
> agent never deletes the plan folder. Shipped
> code, comments, tests, identifiers, and commit messages must not depend on or
> reference them — see §6.11. Commit the folder anyway while the plan is live,
> so it is resume-safe across machines and context resets (§6.14).

> **Terms.**
> - **Subject** — one file under `tasks/all-classes/` (`NN-<slug>.md`). 5-8 per plan.
>   Subject `00` is reserved for tooling research and readiness.
> - **Box** — one `[ ]` checklist item inside a subject file, ID
>   `<subject-id>.<box-number>`, where `<subject-id>` is the §3 `#` / `NN`
>   filename prefix (e.g. `01`) and `<box-number>` is the box ordinal in
>   that file. Stable; never renumbered.
> - **Slice** — one agent work-session, recorded as one line in a
>   subject's Progress log. A box may span several slices; a slice may
>   tick several boxes. Slice numbers count per subject, starting at 1.
> - **Checkpoint** — a durable handoff point after one or more boxes are
>   completed: plan files updated, verification recorded, commit created,
>   and branch pushed.
> - **Collaboration mode** — `solo`, `coordinated`, or `parallel`.
>   All modes are resume-safe; only `parallel` activates branch/owner
>   coordination tables.

---

## Collaboration model

> One plan shape supports solo work, coordinated human/agent work, and true
> parallel work. Keep the plan low-noise by starting in `solo` unless
> multiple active workers are expected now. Upgrade by §4 Decision-log row
> when the need appears; do not fork the plan or switch templates.

| Field | Value |
|---|---|
| Mode | `solo` |
| Primary owner | Codex |
| Coordinator | Codex |
| Resume safety | required |
| Parallel branches | `no` |
| Notes | User ended pairing explicitly after Claude quota exhaustion; Codex implements and reviews solo. No subagents. |

Mode rules:

- `solo` — one active worker owns the plan at a time. Checkpoint
  commits/pushes are still required so another worker can resume after a
  session, account, machine, or context-window limit.
- `coordinated` — one primary worker owns the plan, with explicit
  non-agent boxes for release, product, security, infra, review, or domain
  sign-off. Use `manual-actions.md`; no parallel branch table is required.
- `parallel` — multiple workers may work concurrently on separate subjects.
  Each active subject must have an owner, branch, dependencies, conflict-risk
  files, status, and handoff notes recorded before work starts.

If Mode changes, append a §4 Decision-log row with the previous mode, new mode,
rationale, affected subjects, and branch/ownership impact.

### Parallel work tracker

> Fill only when Mode is `parallel`. In `solo` / `coordinated` plans, leave
> the starter row empty or mark it `n/a`; keep the section so a later upgrade
> has a known place to land.

| Subject | Owner | Branch | Dependencies | Conflict-risk files | Status | Handoff notes |
|---|---|---|---|---|---|---|
n/a — coordinated mode; no concurrent implementation subjects.

### Checkpoint gate

> A box is not truly done until the work can be resumed by someone else.
> A single checkpoint may cover several related boxes.

Before considering a box done:

- Update the box, subject Progress log, §5 tracker, and any affected §4
  decisions / lessons / manual actions.
- Run the relevant verification command from the §2 Verification-commands
  table, or record the exact blocker and reproduction command.
- **Behaviour verification:** for a box that changes runtime behaviour, exercise
  the changed flow end-to-end and record observed-vs-expected output in the
  Progress log — a green build/test exit code alone does not close it. A
  command-level gate can pass while the behaviour is wrong (a service that
  listens but isn't ready, a grader that never ran); drive the flow, don't just
  compile it.
- **Doc-currency:** if the box changed behaviour, architecture, commands, usage,
  configuration, setup, troubleshooting, or developer workflow, update every doc
  that depends on it in the *same* checkpoint — user- and developer-facing alike
  (see §6.16 for the full scope) — or record in the Progress log that none
  applied and why.
- Commit the coherent checkpoint and push the branch. If the repo has no
  remote, record that once in the Collaboration model Notes and treat the
  local commit as the checkpoint.
- Never rewrite pushed checkpoint history — no force-push, rebase, or reset
  of checkpoint commits.
- Keep commit messages, branch names, and PR titles/descriptions
  plan-agnostic: no box IDs, decision IDs, plan filenames, `tasks/all-classes/`,
  or `slice`/`slices` (see §6.11). Repo commit style still applies.

Checkpoint names should describe durable project work, not plan administration.
Example commit message shape: `Add provider retry policy tests`, not
`Complete 03.2`.

---

## 1. Subject

> One paragraph. What is being built. What is explicitly out of scope.
> The "out of scope" half is as important as the "in scope" half — it
> stops the plan from sprawling.

Extend Classic Era Naxxramas support from Hunter/Druid to Mage, Paladin, Priest, Rogue, Shaman, Warlock and Warrior. Preserve the Hunter product hierarchy and useful class-specific execution rows; selected faction/spec controls personal duty and main leaders, with all bosses visible, sparse comparisons labelled and overall comparison collapsed. Keep historical Hunter/Druid documents renderable. Raid/game variants and auth/distribution changes are out of scope.

### Risks and rollback

> Fill at plan creation; `n/a` requires a one-line reason. What can go
> wrong once this ships, and how the change is undone or disabled —
> revert, feature flag, config switch, migration down-script. Data and
> compatibility hazards belong here too. Revisited at the §7 gate.

| Risk | Impact | Mitigation / rollback |
|---|---|---|
| Ranking labels differ from talent trees | Wrong spec or no comparisons | Verify live class metadata and filtered ranking rows; publish category mapping. Revert catalog/query changes. |
| Duty inferred from ranking alone | Healer/tank comparisons falsely grade players | Repeated action and incoming-hit evidence; partial/mixed unknowns; retain immutable raw. |
| Class-specific report copied wholesale | Druid or Hunter advice leaks across classes | One shared view and class data adapters; old-byte guards and actual execution content tests. Revert additive optional contracts. |

---

## 2. Authoritative inputs

> Table. One row per input doc / branch / spec / archived plan.
> Contribution column says exactly what each input gives.

| Source | Contribution |
|---|---|
| `main` at `8425ce5` | Known shipped baseline; subject 00 reconfirms the actual starting commit after Milestone A close-out |
| `docs/roadmap.md`, `docs/origin/WCL_Forensics_App_Architecture_v0.1.md` | Product direction; origin is design history, not implementation proof |
| `docs/architecture.md`, `docs/decisions/`, `tasks/lessons.md` | Current architecture, durable boundaries and prior failure lessons |
| `tasks/Necropsy-Plan.md`, `tasks/necropsy/review-packet.md` | Previous milestone completion and unresolved human gates; do not inherit approval |
| `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml` | Package, locked stack and actual verification commands |
| `tasks/all-classes/pre-mortem.md` | Original predictions and guardrails |
| WCL official API docs: https://www.warcraftlogs.com/api/docs | Current OAuth/GraphQL contracts to verify in subject 00, not assumed from past runs |

### Verification commands

> Single source for "the relevant verification command" used by the
> Checkpoint gate and the §7 gates. Fill what is known at plan creation
> (`TBD` allowed); subject 00.3 confirms or corrects the rows against the
> real repo, and 00.8 bakes in any additions. Fill per stack — e.g. .NET:
> `dotnet build <Solution>.sln` / `dotnet test <Solution>.sln`; Rust:
> `cargo check --workspace` / `cargo test --workspace`.

| Purpose | Command | Notes |
|---|---|---|
| Build | `uv build` | Verify installed artifact separately |
| Fast tests | `uv run pytest -m "not golden and not live and not acceptance"` | Subject 00 confirms current exclusions |
| Golden/acceptance | `uv run pytest -m "golden or acceptance"` | Full Git LFS fixture required; retain known xfails explicitly |
| Browser | `uv run pytest -m browser` | Existing approved Playwright/Chromium |
| Lint/format/types | `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy` | Existing project configuration |
| Live/manual acceptance | Existing bounded user-endpoint API probes and public example acquisition | Explicit opt-in; real-account evidence is not replaced by synthetic tests |
| Package/secret checks | Existing acceptance.check_run; gitleaks dir --max-target-megabytes 0 --redact | Current acceptance harness and approved scanner; unavailable scan is not clean |

---

## 3. Subject file index

> One row per subject file. **Aim for 5-8 subjects, not 15.** If you
> need more, the work is probably two plans.
>
> **Depends-on orders subjects in every mode.** Solo runs pick the next
> subject by this column; `parallel` runs copy it into the Parallel work
> tracker before concurrent work starts. `—` means no dependency beyond
> subject 00. Keep the graph acyclic.

| # | File | Subject | Depends on |
|---|---|---|---|
| 00 | `tasks/all-classes/00-tooling-research-and-readiness.md` | Tooling research and readiness | — |
| 01 | `tasks/all-classes/01-class-spec-catalog.md` | Classic Era class and category catalog | 00 |
| 02 | `tasks/all-classes/02-shared-class-analysis.md` | Shared class evidence and plugins | 01 |
| 03 | `tasks/all-classes/03-role-comparisons.md` | Role-aware personal selection and leader references | 02 |
| 04 | `tasks/all-classes/04-shared-playbooks.md` | Shared class playbooks and exports | 03 |
| 05 | `tasks/all-classes/05-class-validation.md` | Class validation and final verification | 04 |

---

## 4. Decision log

> Append-only. Every time the agent (or reviewer) deviates from a
> spec literal — even slightly — a row goes here. **A spec amendment
> never disappears into a slice; it is recorded as a decision with
> rationale.** This is what makes the plan survive a context-window
> reset.
>
> **Cite the box.** The Refs column names the box ID(s) (`<subject-id>.<box-number>`) and/or
> file(s) the decision touches. A decision that can't name what it
> amends is too vague — sharpen it.
>
> **ADR promotion.** A decision-log row dies when the plan folder is
> deleted. If a decision is a *durable architecture* call — anything a
> future contributor would need to understand the design — promote it to
> the project's decision log / ADR file (create one if the project lacks
> it) and cite the ADR number in the Refs column. Transient
> build-sequencing choices stay here; durable architecture choices
> graduate.
>
> **Retiring a subject or box.** If a subject or box proves wrong
> mid-run, do **not** delete it. Mark it done and struck
> (`- [x] ~~<box-id> <box text>~~ ABANDONED; see D###`), mark the subject
> `ABANDONED` in §5, and add a Decision-log row with the rationale.
> History must survive a reset; a silently deleted box looks like
> unfinished work after compaction.
>
> **Collaboration changes.** Mode changes (`solo` -> `coordinated` /
> `parallel`, or back) are decisions. Record the previous mode, new mode,
> rationale, affected subjects, and branch/ownership impact before multiple
> workers begin.

| ID | Date | Title | Decision | Rationale | Refs (box IDs / files / ADR#) |
|---|---|---|---|---|---|
| D001 | 2026-10-15 | Execution boundary | Begin after Druid execution parity checkpoint 8425ce5; keep prior human gates separate. | User authorized follow-up plans; planning does not imply old or new sign-off. | 00.1–00.9; previous plan §8 |
| D002 | 2026-10-15 | Scope and collaboration | All remaining Classic Era classes, shared playbooks, solo execution. Solo mode as explicitly requested; no parallel workers. | User direction in this session. | §1; subjects 01–05 |
| D003 | 2026-10-15 | Cleanup review | Waive a repeated whole-repo cleanup sweep; reuse the recent Druid sweep and perform scoped reuse/duplication review here. | No dependency/auth/cache/publisher additions; shared helpers replace duplicated Druid event analysis. Prior sweep remains in original plan; scoped review found no fix-now duplication. | 05.3; §7 |
| D004 | 2026-10-15 | Ranking categories | Support verified WCL ranking categories and class-aware aliases rather than treating every talent tree as a ranking filter. | Live filtered probes and metadata differ; documented in ADR0006 and class guide. | 01; 04 |
| D005 | 2026-10-15 | Real fixture boundary | Keep seven real class event captures plus a budget-only Holy Priest snapshot; disclose real Holy healing validation as unavailable. | Budget guard stopped further collection. No runtime category is deferred; fourteen categories have synthetic production-path validation. Human acceptance remains open. | 05.2; 05.4 |

---

## 5. Master progress tracker

> One row per subject file. A subject is `DONE` when **every** box in
> its file is `[x]` and its Hindsight checkpoint verdict is `CLOSE`.
> Abandoned boxes must use the exact struck-and-done
> format from §4. Mark a retired subject `ABANDONED` (see §4); an
> abandoned subject still gets its Done cell `[x]` (abandoned counts as
> resolved).
> §5 is "fully ticked" when every Done cell is `[x]` and every Status is
> `DONE` or `ABANDONED`.
>
> **Owner labels and summary.** Every box in every subject file MUST have
> an owner. Owners are one of: `agent`, `release-engineer`,
> `product-owner`, `tech-lead`, `domain-sme`. (Lesson from messaging
> plan: not having owner labels meant the master tracker stalled at
> "almost done" with a residue of human-owned items confused for
> agent-owned. Split them upfront.) The Owner-summary column names the
> specific roles present (e.g. `agent: 4; tech-lead: 1`), never a generic
> `human`. In a solo repo most boxes are `agent`; reserve human roles for
> sign-off boxes. If the plan needs a role the enum lacks (e.g. security
> or infra sign-off), extend the enum with a §4 Decision-log row.
>
> **Human-owned boxes** are mirrored into `tasks/all-classes/manual-actions.md`
> so they don't get lost between agent-owned boxes. Keep the two in sync.

| Done | # | File | Status | Owner summary | Human actions mirrored? |
|---|---|---|---|---|---|
| [x] | 00 | `tasks/all-classes/00-tooling-research-and-readiness.md` | DONE | agent: 9 | n/a |
| [x] | 01 | `tasks/all-classes/01-class-spec-catalog.md` | DONE | agent: 2 | n/a |
| [x] | 02 | `tasks/all-classes/02-shared-class-analysis.md` | DONE | agent: 2 | n/a |
| [x] | 03 | `tasks/all-classes/03-role-comparisons.md` | DONE | agent: 2 | n/a |
| [x] | 04 | `tasks/all-classes/04-shared-playbooks.md` | DONE | agent: 2 | n/a |
| [ ] | 05 | `tasks/all-classes/05-class-validation.md` | IN PROGRESS | agent: 3; product-owner: 1 | yes |

---

## 6. Cross-cutting principles

> These apply to every subject file. Violations are blockers, not nits.
> 1-11 are **trimmable defaults distilled from prior runs** — keep, cut, or
> trim each to what actually bites this plan. 12-17 are **structural** — the
> Checkpoint gate and §7 depend on them; keep them. Lift any others from
> `AGENTS.md` / `CLAUDE.md`. Principles 2-4 are **C#/.NET-specific** —
> drop them for a non-.NET plan. When cutting a principle, strike it
> (`~~...~~`) instead of deleting it so the numbering — and every `§6.x`
> reference in this file — stays stable. Never renumber.

1. KISS · YAGNI · CLEAN · SOLID · DRY (in that order when conflicting).
2. ~~*(C#)* One class per file.~~ Not applicable to this Python project.
3. ~~*(C#)* Nullable reference types enabled.~~ Not applicable to this Python project.
4. ~~*(.NET)* No new build warnings.~~ Not applicable to this Python project.
5. **Keep code modular and locally understandable.** Prefer small, cohesive modules with explicit boundaries. Split files before they become catch-all dumping grounds; split methods when branching, nesting, or mixed responsibilities make them hard to scan. If a file or method has to be large, record why and pin the coordinated behaviour with tests.
6. **Cyclomatic complexity stays low.** Branch-heavy methods are blockers unless the branching is inherent to the domain and covered by focused tests. Prefer guard clauses, extracted decision helpers, table-driven cases, or explicit strategy objects over deep `if`/`else`, nested `switch`, or boolean-flag flows. If the repo has a cyclomatic-complexity threshold, meet it; otherwise treat double-digit complexity in a method as design pressure to simplify.
7. **Spec at the contract level, not the SDK level.** State requirements as testable contracts on observable behaviour. Do not prescribe SDK call shapes — that's the implementer's choice. (Lesson from messaging plan: the spec said "one `SendAsync` per message" and the SB SDK couldn't honour the per-message error semantics implied. Three Decision-log amendments resulted. State *what* must be true, not *how* to call.)
8. **Coverage % is a smell-detector, not a goal.** A test exists to pin observable behaviour, not to chase a number. If you can't articulate "this test prevents future-X bug", delete it. Coverage gate failures should provoke "why is this code path untested?" — not "let's write a test that touches it". Architecture tests pin contracts; coverage gates flag gaps. Don't conflate them.
9. **Every plan box has an owner and a stable ID.** Owner from the §5 enum; ID `<subject-id>.<box-number>`. See §5.
10. **Lessons land in `tasks/all-classes/lessons.md` as they happen**, not at the gate — per-plan run-notes that die with the folder. Durable lessons migrate to the permanent `tasks/lessons.md` at §7.
11. **Code and public metadata are plan-agnostic.** Comments, test names, commit messages, branch names, PR titles, and identifiers must read as permanent project artefacts. Never reference the plan, slices, box IDs (`<subject-id>.<box-number>`), decision-log entries (`D###`), or this file — they vanish when the plan is deleted after go-live (see Purpose). A dangling `// see 03.2` or `// per Decision D007` becomes a broken reference in production. Put the *why* directly in the comment. (A durable design rationale belongs in an ADR, not a plan ref — see §4 ADR promotion.)
12. **Captain Hindsight review before subject close.** Before marking a subject `DONE`, run the subject's Hindsight checkpoint. Record Keep / Fix before closing / Record / Risk / Verdict in the subject file. A `DO NOT CLOSE` verdict is a blocker: add or reopen boxes, update §4 decisions, or append lessons before closing.
13. **Tooling research before implementation.** Every plan starts with subject `00 - Tooling Research And Readiness` unless explicitly waived in §4. No implementation subject starts until subject 00 records repo context, baseline verification, stack best practices, official sources, and any approved Skills/MCP/tooling setup. A waiver must explain why the research step is unnecessary or unsafe for this plan.
14. **All plans are resume-safe.** A checked box must be backed by a durable checkpoint: plan updates, verification note or blocker, commit, and push (no-remote exception per the Checkpoint gate). One checkpoint may cover several related boxes, but no box is ticked merely because work exists in an unpushed workspace.
15. **Parallelism is opt-in.** Start in `solo` unless multiple workers are known upfront. If the plan changes to `parallel`, add a §4 decision and fill the Parallel work tracker before concurrent subject work starts.
16. **Documentation ships with the change.** Every box runs a *documentation-impact review*: name which docs the change touches and update them in the *same* checkpoint, or record `n/a` with a one-line reason (in the Progress log, confirmed at the §7 gate). The trigger is broad — behaviour, architecture, commands, usage, configuration, setup, troubleshooting, or developer workflow. The scope is every doc a user *or* contributor relies on, not only user-facing ones: README, usage/setup guides and HOWTOs, CHANGELOG/release notes, API/command/config reference, architecture and design docs, developer-onboarding/contributor docs, troubleshooting/runbooks, examples, wiki pages, and prompt/skill docs. (Durable architecture *decisions* still graduate to an ADR per §4; this rule covers the prose docs around them.) Docs are a durable knowledge sink that survives the disposable plan folder (alongside ADRs and the permanent `tasks/lessons.md`); plan files are not the place for knowledge a future user or contributor needs. Update docs to match what *shipped*, never what was planned.
17. **Reuse and integrate before adding.** No implementation box starts until that subject's `## Integration analysis` records where the change belongs, what already exists, what is reused or extended, the chosen integration point and why, and whether it supports or conflicts with the project vision/ADRs. Prefer expanding, connecting, or refactoring existing code over new parallel code; new code is justified only when no existing surface fits. (Lesson: agents accrete duplicate code when they skip the prior-art check — see the 00.2 prior-art map and 00.1 vision review.) **Wire or delete:** new public surface (a function, endpoint, flag, command, or export) ships wired to a real non-test caller, or is explicitly disclosed as library-only/unwired — in the docs or a §4 decision — never as undisclosed dead surface a later cleanup-audit has to discover.
18. Pre-Mortem obligations live in tasks/all-classes/pre-mortem.md; every PM risk has an owner and terminal resolution before sign-off.
19. Class labels, talents, observed duties and assignments remain separate.
20. No new per-class pipeline, cache, OAuth store, publisher or invented rotation advice.
21. Shared playbook parity includes actual execution row content and source attribution, not heading-only tests.

---

## 7. Gate review (run last; tick everything)

> Run only when §5 is fully ticked. §7 is the engineering gate the agent
> ticks; §8 is human acceptance that follows it.

- [ ] All §5 subjects done (or explicitly `ABANDONED` with a §4 row)
- [ ] Subject 00 completed, or explicitly waived/abandoned with a §4 row
- [ ] Build command from the §2 Verification-commands table passes with 0 errors and 0 new warnings
- [ ] Test command from the §2 Verification-commands table passes; coverage gate met if the repo enforces one
- [ ] Behaviour verification done for every box that changed runtime behaviour — the changed flow was exercised end-to-end with observed-vs-expected output recorded, not closed on a green build/test exit code alone (see the Checkpoint gate)
- [ ] Remaining §2 Verification-commands rows (lint/format, plan-specific gates) pass or are recorded `n/a`
- [ ] §1 Risks-and-rollback table reviewed; rollback steps still accurate for what actually shipped
- [ ] Cross-cutting principles from §6 reviewed; any plan-specific architecture tests/rules hold
- [ ] Every implementation subject recorded an `## Integration analysis`; no unjustified duplication or new parallel code where an existing surface fit (see §6.17)
- [ ] New public surface added by this plan is wired to a non-test caller, or is explicitly disclosed as library-only/unwired (in the docs or a §4 decision) — no undisclosed dead surface shipped (see §6.17 "Wire or delete")
- [ ] Every non-abandoned subject has a recorded Captain Hindsight checkpoint with verdict `CLOSE`
- [ ] Every ticked box has a Progress-log entry and is covered by a pushed checkpoint commit
- [ ] Durable architecture decisions promoted to the project's decision log / ADR file (see §4 ADR promotion)
- [ ] Documentation-impact review done for every shipped box — user- and developer-facing docs updated to match shipped behaviour (see §6.16 for scope), or recorded `n/a` with a one-line reason
- [ ] Current plan/integration branch is pushed (or the no-remote note from the Checkpoint gate applies); `git status --short` has no uncommitted plan/code changes except explicitly deferred or ignored artefacts
- [ ] If Collaboration mode is `parallel`, the Parallel work tracker has no stale active owners, unmerged subject branches, or unresolved handoff notes
- [ ] Shipped code/tests/comments/identifiers are plan-agnostic — grep the repo **excluding `tasks/`** for box IDs (`\b\d\d\.\d+\b`), decision IDs (`\bD\d{3}\b`), the literal `tasks/all-classes/`, the plan filename `AllClasses-Plan.md`, and `\bslices?\b`; zero hits after triaging false positives (version strings can match the box-ID pattern; "slice" may be a legit domain term). See §6.11
- [ ] Commit messages are plan-agnostic — `git log main..HEAD` mentions no box IDs, decision IDs, `tasks/all-classes/`, `AllClasses-Plan.md`, or `slice`/`slices` (apply the same false-positive triage; file grep does not cover commit messages)
- [ ] Branch names and public PR titles/descriptions are plan-agnostic if used
- [ ] `tasks/all-classes/manual-actions.md` — every human-owned box resolved or explicitly deferred
- [ ] Run the `cleanup-audit` teardown review (whole-repo sweep) before sign-off, **or** waive it with a §4 Decision-log row (e.g. a sweep ran recently, or the repo is too young to have accrued cruft). Triage every finding: fix-now / fold into a *new* plan / won't-fix with a reason. Findings that warrant real work open a **new** plan — never this one, which is disposable and about to be deleted (see Purpose). Report-only: a non-empty report does not block sign-off, but an un-run (un-waived) or un-triaged audit does. Distinct from the per-subject Captain Hindsight checkpoints — this is the one whole-repo pass
- [ ] `tasks/all-classes/lessons.md` reconciled; lasting lessons migrated to the permanent `tasks/lessons.md` (create it if missing) before the `tasks/all-classes/` folder is deleted (see Disposable note)
- [ ] All nine Classic Era classes have class-aware supported category selection, evidence and offline outputs.
- [ ] If pre-mortem.md exists, every risk has a terminal resolution and observable Hindsight calibration; unelapsed horizons remain Inconclusive.
- [ ] Real versus synthetic class/role coverage is explicit and product acceptance remains human-owned.
- [ ] If subject 00 retains material PM risks, persist original predictions with owners before implementation; require terminal resolutions and observable Hindsight calibration before sign-off.
- [ ] Plan handed to reviewer for §8 sign-off

---

## 8. Acceptance / sign-off

> Filled by the user or reviewer after §7 passes. This is intentionally
> separate from §4: sign-off is acceptance, not a spec amendment.

| Date | Reviewer | Result | Notes |
|---|---|---|---|
| | | | |

---

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


## Implementation checkpoint

All nine classes are wired through the existing pipeline; shared class combat evidence uses ADR0006. Fourteen added category contracts pass offline/package and56browser page cases. Seven added classes have frozen real event captures; source CI and full serial golden verification pass. Human product review remains open; no pair review is required after the explicit user instruction.


## Final solo engineering handoff

All agent boxes00–05 are complete and pushed;01–04 are CLOSE. Validation subject05 remains DO NOT CLOSE solely for human05.4, mirrored in manual-actions.md. The §7 entry condition is not met while §5 includes that required human box; §7/8 are deliberately unclaimed. No request for renewed Claude pairing or repeat authorization is outstanding.

Source c016c4b passed [Linux/Windows CI](https://github.com/David-c0degeek/necropsy/actions/runs/38748441029). Local full golden/acceptance246passed with four retained xfails;19integration checks;56synthetic and48real browser page/viewports; lint/format, strict types, build and isolated installed-wheel real Mage replay pass. Four saved Hunter artifacts remain byte-identical. Seven real classes have42actor entries with independent raw amount checks; budget-only Holy Priest is explicitly not live healing validation. [Review packet](all-classes/review-packet.md) links generated outputs and portable reproduction instructions. No unresolved engineering defect is known; assignment/domain acceptance and long-term observation remain separate.


## Explicit product approval — 2026-10-15

David: "Approved. ill have another plan to make this proper." Product acceptance of the delivered implementation and disclosed evidence limits is recorded in the subject/manual-action files. Further refinement is separately scoped by the user. No new raw-finding adjudication or rerun of the formal §7 close-out is claimed by this approval record.
