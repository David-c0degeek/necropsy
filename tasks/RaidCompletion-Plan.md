# RaidCompletion-Plan.md — Complete Classic Era raid forensics and Playbooks

> **Status: IN PROGRESS — readiness complete; evidence and initial shared strategy active.** Created 2026-10-16.
> **Purpose.** Deliver complete MC, BWL and AQ40 boss/class analysis at the
> evidence and product depth established by Naxxramas, while preserving Naxx.
> Current raid selection and generic report plumbing are a baseline, not completion.
>
> **Disposable.** The plan and its `tasks/raid-completion/` folder are deleted (or
> archived out of the repo) once the subject ships to production. Deleting or
> archiving the folder is human-owned and happens only after §8 sign-off; the
> agent never deletes the plan folder. Shipped
> code, comments, tests, identifiers, and commit messages must not depend on or
> reference them — see §6.11. Commit the folder anyway while the plan is live,
> so it is resume-safe across machines and context resets (§6.14).

> **Terms.**
> - **Subject** — one file under `tasks/raid-completion/` (`NN-<slug>.md`). 5-8 per plan.
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
| Notes | Solo, no subagents. Foundation and research preserved in pushed checkpoint `9aded83` on `main`, based on `30e89ce`. Creation-time no-action statement is historical; execution began 2026-10-16. Existing WCL user-endpoint tooling only; no publication or new infrastructure. |

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
| n/a | n/a | n/a | n/a | n/a | solo | No parallel workers |

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
  plan-agnostic: no box IDs, decision IDs, plan filenames, `tasks/raid-completion/`,
  or `slice`/`slices` (see §6.11). Repo commit style still applies.

Checkpoint names should describe durable project work, not plan administration.
Example commit message shape: `Add provider retry policy tests`, not
`Complete 03.2`.

---

## 1. Subject

Fully implement **Molten Core (10 bosses), Blackwing Lair (8 bosses plus the separately verified combined Ebonroc / Flamegor encounter), and AQ40 (9 bosses)** as independent raid modules sharing one evidence engine. Cover all nine classes, their 19 current WCL category pools, all 27 declared game talent trees as build context, explicit Balance/HPS, legal factions and evidenced encounter duties. Deliver sourced encounter facts, observed phases/opportunities, target/ranking rules, class-specific measurements, loadout and execution guidance, coordination advice, independent golden facts, real captures and usable per-raid Playbooks/Reports. Preserve all 15 Naxxramas encounters, existing archives, saved analyses, acquisition/resume and report/package behavior. AQ20, ZG, Onyxia, SoD, Anniversary rulesets and other expansions are outside this request's AQ40/BWL/MC scope; do not silently add them. No automatic talent diagnosis, fabricated ranking pools, universal healing/tank quality scores, or promised DPS gains.

### What FULLY implemented means

The binding completion contract is [coverage-contract.md](raid-completion/coverage-contract.md). The seed [coverage-matrix.csv](raid-completion/coverage-matrix.csv) has **952 TODO cells**: 28 new WCL encounter entries × 34 legal category/metric/faction configurations. These include 27 canonical bosses and the BWL combined variant. Counts come from the current repo catalog and must be rechecked in 00/01. Each cell needs working analysis, applicable encounter/class advice, positive and negative behavior tests, usable real actor evidence, independent measurement checks and a rendered review. A blank file, generic advice repeated on every boss, synthetic-only fixture, or budget-only snapshot cannot close a cell. A small legitimate cohort can be complete as a small sample; its median remains unknown below the evidence threshold. Lack of logs is an OPEN evidence gap, not N/A or DONE. N/A requires actual ruleset illegality or demonstrated WCL unavailability and a recorded source/reason; availability limits cannot be hidden behind a broad full-support claim.

Naxx is the preserved reference, not a certificate that every existing class/category has real-log acceptance: its known Holy Priest and other accepted evidence limits remain explicit. Full expansion completion cannot inherit those waivers for the three new raids. Any scope reduction needs an explicit owner decision and must be described as partial delivery, not full completion.

### Risks and rollback

| Risk | Impact | Mitigation / rollback |
|---|---|---|
| Empty raid files or generic class tables pass as complete | Players receive plausible pages with no useful boss coaching | Per-cell contract and content/evidence gates; keep current support limitations until actual validation closes them. Revert module rules independently. |
| Wrong encounter windows, targets, duty or combined-dragon mode | Misleading comparisons and recommendations | Sourced rules + observed phase evidence + independent per-boss reconciliation; retain recorded WCL scores and unknown event totals until validated. |
| Golden checks reuse the analyzer as their oracle | Incorrect arithmetic passes every test | Freeze raw evidence, compute expected facts independently, review discrepancies and prove mutation sensitivity. |
| Shared encounter work regresses Naxx, saved runs or other classes | Existing users lose trustworthy outputs | Naxx historical/live/legacy replay, both HTML pages and package regression; immutable inputs; additive/versioned contracts and no in-place saved-output migration. |
| Evidence collection consumes quota or exposes private material | Incomplete captures or leaked identities/tokens | Existing quota/checkpoint/cache path, deduplicated multi-actor fixtures, access/provenance policy and scans; stop/resume, no credentials in fixtures. |
| Publication precedes domain/product acceptance | A transport-ready build is advertised as complete support | Stage a reviewable candidate; public completion/release claims follow §7/§8; preserve previous installed release and rollback receipt. |

---

## 2. Authoritative inputs

| Source | Contribution |
|---|---|
| Working tree on `30e89ce` and `tasks/raid-expansion.md` | Uncommitted selection/acquisition/module foundation; receipt from prior turn is historical, not this plan's readiness result |
| User instruction, 2026-10-16 | Full boss/class implementation like Naxx; independent raids, Playbooks and saved-analysis views |
| `tasks/Necropsy-Plan.md`, `tasks/necropsy/05-naxx-encounters-and-recommendations.md`, `tasks/necropsy/06-8-parity-inventory.md` | Naxx evidence, golden-fact, advice-content and presentation depth to match; do not copy player-specific oracle values |
| `tests/golden/haplina_naxx/`, `tests/golden/druid/`, `tests/golden/classes/` | Existing fixture/provenance conventions and actual accepted evidence limits |
| `tasks/AllClasses-Plan.md`, `tasks/ClassTaxonomy-Plan.md`, `tasks/lessons.md` | Class/category/duty separation, real-event validation lessons and accepted Naxx-only boundaries |
| `docs/architecture.md`, `docs/evidence-model.md`, `docs/decisions/` | One offline pipeline, immutable sources, graded claims, compatible snapshots and outputs |
| `src/necropsy/raids/`, `rules/classic_era/zones/`, `analysis/`, `report/` | Actual implementation seams; new facts are empty and boss guidance absent today |
| `tasks/raid-completion/pre-mortem.md`, `coverage-contract.md`, `coverage-matrix.csv`, `boss-inventory.md` | Binding scope, risk guardrails, every-cell progress and boss-specific research questions |
| `pyproject.toml`, `uv.lock`, `desktop/package.json`, `.github/workflows/` | Locked runtime, tooling and existing build/test/release workflows |
| [WCL API documentation](https://www.warcraftlogs.com/api/docs), [Vanilla ranking guide](https://vanilla.warcraftlogs.com/help/ranks) | Primary contracts; reviewed for planning 2026-10-16; current schema, filtering and encounter-specific ranking policies still require 00/01 verification |

### Verification commands

These are repo commands, not claims of execution in this planning turn. Subject 00 confirms them and records the exact environment/base. New plan-specific scripts/tests must be added to this table when implemented; TBD rows cannot pass the final gate.

| Purpose | Command | Notes |
|---|---|---|
| Locked setup | `uv sync --locked` | Preserve current Python/toolchain from repo metadata |
| Python lint / format / types | `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy` | CI-aligned |
| Ordinary automated suite | `uv run pytest -m "not golden and not live and not acceptance"` | Synthetic contracts + ordinary integration; not real-log acceptance |
| Golden evidence | `uv run pytest -m golden` | Authorized LFS/raw fixtures required; skipped/unavailable evidence is not a pass |
| Acceptance register | `uv run pytest -m acceptance` | Extend existing markers/fact-register conventions for every new raid |
| Installed wheel | `uv build`; `uv run pytest tests/unit/test_rules_package.py` | All module/rule assets plus installed replay outside checkout |
| Desktop frontend | From `desktop/`: `npm ci`; `npm run build`; `npm run format:check` | Existing lockfile; no dependency upgrade presumed |
| HTML behavior | `uv run pytest -m browser` | Recorded Chromium/viewport setup; every raid/class plus legacy Naxx views |
| Existing native/offline probes | `uv run python scripts/check_desktop_engine.py --help`; `uv run python scripts/check_desktop_window.py --help` | Read current flags in 00; --help is discovery, not acceptance |
| Live capture / quota resume | `uv run necropsy analyze CHARACTER_URL --raid RAID --category CATEGORY --metric METRIC --partition 1 --endpoint user --cache workspace/raid-cache --out workspace/CAPTURE`; repeat with `--resume` | Substitute a verified public actor and unique output, retain receipts; never default CI live traffic. No implicit reset waiting. |
| Matrix / content gate | `uv run python scripts/check_raid_coverage.py --inventory`; `uv run python scripts/check_raid_coverage.py --require-complete` | Interface to implement in 01.7; inventory never substitutes for the strict gate. Reject unresolved cells, missing facts and generic-only advice. |
| Independent facts | `uv run pytest tests/golden/test_fact_checks_full.py tests/golden/test_ranking_rules_full.py tests/golden/test_druid_replay.py tests/golden/test_class_replay.py -q` | Existing Naxx contracts; add exact per-raid checker/test paths with 01.6. Do not treat old facts as new-raid proof. |
| Input/output integrity | `uv run python scripts/fixture_tools.py manifest ARCHIVE`; `gitleaks dir EXTRACTED_OR_OUTPUT --redact --max-target-megabytes 0`; `uv run pytest tests/unit/test_rules_package.py -q`; `uv run python scripts/check_docs.py` | Substitute concrete retained capture paths; manifests plus strict snapshot reader/member hashes. Scan all extracted bytes and generated outputs. |
| Naxx compatibility | Existing golden, live-v1/legacy, browser and package checks selected in 00 | Record expected allowed changes; no silent baseline rewrite |

---

## 3. Subject file index

| # | File | Subject | Depends on |
|---|---|---|---|
| 00 | `tasks/raid-completion/00-tooling-research-and-readiness.md` | Tooling research and readiness | — |
| 01 | `tasks/raid-completion/01-evidence-and-coverage-contract.md` | Evidence acquisition, independent facts and completion matrix | 00 |
| 02 | `tasks/raid-completion/02-shared-encounter-and-class-contracts.md` | Shared encounter, class and recommendation contracts | 00, 01 |
| 03 | `tasks/raid-completion/03-molten-core.md` | Complete Molten Core encounter implementation | 01, 02 |
| 04 | `tasks/raid-completion/04-blackwing-lair.md` | Complete Blackwing Lair encounter implementation | 01, 02 |
| 05 | `tasks/raid-completion/05-aq40.md` | Complete AQ40 encounter implementation | 01, 02 |
| 06 | `tasks/raid-completion/06-all-class-validation.md` | All-class/category/faction validation and Naxx regression | 03, 04, 05 |
| 07 | `tasks/raid-completion/07-product-and-release-acceptance.md` | Per-raid product, installed verification and acceptance | 06 |

Execution is solo in dependency order. MC, BWL and AQ40 each own their module rules/facts/guidance, fixture facts and acceptance receipts; shared mechanics live in existing generic/class/encounter seams. Completing a raid implementation subject does not advertise full support before 06/07 and §8. Supplementary contracts and the CSV are part of the plan, not shipped runtime dependencies.

---

## 4. Decision log

Append-only. Record deviations, previous/new collaboration modes, affected boxes and rationale. Retire boxes with the template's struck-and-done `ABANDONED; see D###` form, never deletion. A durable architecture decision must also be promoted to `docs/decisions/` and linked here. No scope reduction may be described as full completion.

| ID | Date | Title | Decision | Rationale | Refs (box IDs / files / ADR#) |
|---|---|---|---|---|---|
| D001 | 2026-10-16 | Scope and completion baseline | AQ40/BWL/MC full domain implementation; Naxx preserved. Current plumbing is input, not completed implementation boxes. | User explicitly requests full boss/class depth after the foundation delivery. | §1; coverage-contract.md; 01.1; 07.9 |
| D002 | 2026-10-16 | Execution mode | Solo; no subagents or parallel branches. | No delegation was requested; keep one resume-safe owner. | Collaboration model; 00.1 |
| D003 | 2026-10-16 | Era partition boundary | New encounter policies and evidence initially apply to partitions 1/2 only; preserve separate world-buff cohorts. Add explicit applicability guards before new domain rules run. Existing Naxx replay semantics remain unchanged. | Fresh worldData includes SoM and Hardcore partitions under the same zones; site/zone alone does not prove ruleset. | readiness-research.md; 02.1–02.3; PM-2 |
| D004 | 2026-10-16 | Baseline fixture repair | Extend the two hand-built score-test snapshot_meta tables with existing production zone_id; retain every previous score assertion. No production fallback or evidence upgrade. | Full ordinary baseline: 1192 passed/35 failed, all failures caused by omitted fixture column; corrected targeted run: 35 passed. Ruff/format/mypy and 31 cross-raid flows pass. | 00.3; tests/unit/test_recorded_dps.py; tests/unit/test_leaderboard_headline.py |
| D005 | 2026-10-17 | Golden navigation check repair | Verify each sidebar href against its actual local target document/fragment, including cross-page truth-model links. Preserve both pages and all 15 sections. | Existing browser test treated report.html#truth-model as a CSS selector in Playbook; identical test bug exists at 30e89ce. Raw golden run otherwise 244 passed/4 expected failures. No product behavior or oracle changed. | 00.3 follow-up; 01.2; tests/golden/test_report_full.py |
| D006 | 2026-10-17 | Evidence-led shared strategy sequencing | Begin the shared static-strategy contract on three already evidenced encounters while remaining 01 phase/duty contracts and capture backlog stay open. No subject or cell closes early. | 01 explicitly permits work on evidenced bosses; nine public six-actor captures and independent arithmetic exist. Separating general strategy from personal findings is independently implementable while quota delays another capture. No scope or acceptance reduction. | 01 goal; 02.1/02.5/02.8; PM-1/PM-2 |
| D007 | 2026-10-17 | Recipient-qualified healing semantics | New Era raid effective healing uses supported friendly recipients; preserve raw source sums under additive keys and expose boss/unclassified healing. Historical Naxx and saved JSON retain their prior arithmetic. | Real Guardian sources credit Shadow of Ebonroc healing to tank actors: raw source ownership is not friendly support or a universal HPS policy. No original raw fact expectations change. | 02.3/02.4/02.7/02.8; PM-2/PM-3; [ADR 0014](../docs/decisions/0014-recipient-qualified-healing.md) |
| D008 | 2026-10-17 | Observed actor-effect boundary | Save strict local debuff exposure separately from guide strategy and unknown global phase/opportunity. Preserve historical aura defaults; simultaneous contradictory transitions stay unresolved. | Actor streams prove local transitions but sampled WCL phase fields do not establish complete physical windows. Event hash order and guide schedules cannot fill missing state. | 02.1/02.2/02.7/02.8; PM-2; [ADR 0015](../docs/decisions/0015-encounter-observations-and-strategy.md) |
| D009 | 2026-10-17 | Incremental MC work on newly evidenced encounters | Begin partial Magmadar module work using the implemented shared observation/strategy contracts and a finalized six-actor public seed while remaining 01/02 obligations stay open. | Prior shared contracts pass real/installed regressions; Magmadar now has independent raw data for fear/frenzy research. Sequencing permits concrete evidenced implementation without declaring shared contracts or any MC box complete. No scope or acceptance reduction. | 01 goal; 02.1/02.4; 03.1/03.2/03.4–03.8; PM-1/PM-2/PM-3 |

---

## 5. Master progress tracker

A subject is DONE only after all boxes, behavior receipts and durable checkpoints exist and its closing Hindsight verdict is CLOSE. Owners are agent, release-engineer, product-owner, tech-lead and domain-sme. Human-owned boxes are mirrored. No boxes are complete at plan creation.

| Done | # | File | Status | Owner summary | Human actions mirrored? |
|---|---|---|---|---|---|
| [x] | 00 | `tasks/raid-completion/00-tooling-research-and-readiness.md` | DONE | agent: 8; CLOSE; foundation/research checkpoint pushed | n/a |
| [ ] | 01 | `tasks/raid-completion/01-evidence-and-coverage-contract.md` | IN_PROGRESS | durable scope/gates, 22 real seeds and 132 raw actor checks; full contracts/coverage open | n/a |
| [ ] | 02 | `tasks/raid-completion/02-shared-encounter-and-class-contracts.md` | IN_PROGRESS | initial shared strategy on six evidenced encounters and local effects/control; remaining contracts open | n/a |
| [ ] | 03 | `tasks/raid-completion/03-molten-core.md` | IN_PROGRESS | agent: 9; domain-sme: 1 | yes |
| [ ] | 04 | `tasks/raid-completion/04-blackwing-lair.md` | TODO | agent: 9; domain-sme: 1 | yes |
| [ ] | 05 | `tasks/raid-completion/05-aq40.md` | TODO | agent: 9; domain-sme: 1 | yes |
| [ ] | 06 | `tasks/raid-completion/06-all-class-validation.md` | TODO | agent: 11; domain-sme: 1 | yes |
| [ ] | 07 | `tasks/raid-completion/07-product-and-release-acceptance.md` | TODO | agent: 8; product-owner: 1 | yes |

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
2. ~~*(C#)* One class per file.~~ Not applicable to this Python/TypeScript project.
3. ~~*(C#)* Nullable reference types enabled.~~ Existing strict mypy/TypeScript contracts apply.
4. ~~*(.NET)* No new build warnings.~~ Python/desktop verification remains mandatory.
5. **Keep code modular and locally understandable.** Prefer small, cohesive modules with explicit boundaries. Split files before they become catch-all dumping grounds; split methods when branching, nesting, or mixed responsibilities make them hard to scan. If a file or method has to be large, record why and pin the coordinated behaviour with tests.
6. **Cyclomatic complexity stays low.** Branch-heavy methods are blockers unless the branching is inherent to the domain and covered by focused tests. Prefer guard clauses, extracted decision helpers, table-driven cases, or explicit strategy objects over deep `if`/`else`, nested `switch`, or boolean-flag flows. If the repo has a cyclomatic-complexity threshold, meet it; otherwise treat double-digit complexity in a method as design pressure to simplify.
7. **Spec at the contract level, not the SDK level.** State requirements as testable contracts on observable behaviour. Do not prescribe SDK call shapes — that's the implementer's choice. (Lesson from messaging plan: the spec said "one `SendAsync` per message" and the SB SDK couldn't honour the per-message error semantics implied. Three Decision-log amendments resulted. State *what* must be true, not *how* to call.)
8. **Coverage % is a smell-detector, not a goal.** A test exists to pin observable behaviour, not to chase a number. If you can't articulate "this test prevents future-X bug", delete it. Coverage gate failures should provoke "why is this code path untested?" — not "let's write a test that touches it". Architecture tests pin contracts; coverage gates flag gaps. Don't conflate them.
9. **Every plan box has an owner and a stable ID.** Owner from the §5 enum; ID `<subject-id>.<box-number>`. See §5.
10. **Lessons land in `tasks/raid-completion/lessons.md` as they happen**, not at the gate — per-plan run-notes that die with the folder. Durable lessons migrate to the permanent `tasks/lessons.md` at §7.
11. **Code and public metadata are plan-agnostic.** Comments, test names, commit messages, branch names, PR titles, and identifiers must read as permanent project artefacts. Never reference the plan, slices, box IDs (`<subject-id>.<box-number>`), decision-log entries (`D###`), or this file — they vanish when the plan is deleted after go-live (see Purpose). A dangling `// see 03.2` or `// per Decision D007` becomes a broken reference in production. Put the *why* directly in the comment. (A durable design rationale belongs in an ADR, not a plan ref — see §4 ADR promotion.)
12. **Captain Hindsight review before subject close.** Before marking a subject `DONE`, run the subject's Hindsight checkpoint. Record Keep / Fix before closing / Record / Risk / Verdict in the subject file. A `DO NOT CLOSE` verdict is a blocker: add or reopen boxes, update §4 decisions, or append lessons before closing.
13. **Tooling research before implementation.** Every plan starts with subject `00 - Tooling Research And Readiness` unless explicitly waived in §4. No implementation subject starts until subject 00 records repo context, baseline verification, stack best practices, official sources, and any approved Skills/MCP/tooling setup. A waiver must explain why the research step is unnecessary or unsafe for this plan.
14. **All plans are resume-safe.** A checked box must be backed by a durable checkpoint: plan updates, verification note or blocker, commit, and push (no-remote exception per the Checkpoint gate). One checkpoint may cover several related boxes, but no box is ticked merely because work exists in an unpushed workspace.
15. **Parallelism is opt-in.** Start in `solo` unless multiple workers are known upfront. If the plan changes to `parallel`, add a §4 decision and fill the Parallel work tracker before concurrent subject work starts.
16. **Documentation ships with the change.** Every box runs a *documentation-impact review*: name which docs the change touches and update them in the *same* checkpoint, or record `n/a` with a one-line reason (in the Progress log, confirmed at the §7 gate). The trigger is broad — behaviour, architecture, commands, usage, configuration, setup, troubleshooting, or developer workflow. The scope is every doc a user *or* contributor relies on, not only user-facing ones: README, usage/setup guides and HOWTOs, CHANGELOG/release notes, API/command/config reference, architecture and design docs, developer-onboarding/contributor docs, troubleshooting/runbooks, examples, wiki pages, and prompt/skill docs. (Durable architecture *decisions* still graduate to an ADR per §4; this rule covers the prose docs around them.) Docs are a durable knowledge sink that survives the disposable plan folder (alongside ADRs and the permanent `tasks/lessons.md`); plan files are not the place for knowledge a future user or contributor needs. Update docs to match what *shipped*, never what was planned.
17. **Reuse and integrate before adding.** No implementation box starts until that subject's `## Integration analysis` records where the change belongs, what already exists, what is reused or extended, the chosen integration point and why, and whether it supports or conflicts with the project vision/ADRs. Prefer expanding, connecting, or refactoring existing code over new parallel code; new code is justified only when no existing surface fits. (Lesson: agents accrete duplicate code when they skip the prior-art check — see the 00.2 prior-art map and 00.1 vision review.) **Wire or delete:** new public surface (a function, endpoint, flag, command, or export) ships wired to a real non-test caller, or is explicitly disclosed as library-only/unwired — in the docs or a §4 decision — never as undisclosed dead surface a later cleanup-audit has to discover.
18. **Independent modules, shared engine.** Raid target/fact/phase/guidance policy belongs to its module. Class/event/coverage/math and rendering are shared; no boss branches scattered through class plugins or raid-specific cloned renderers.
19. **Full scope requires evidence.** The completion contract and every applicable matrix row define completion. Empty facts, headings, generic advice and synthetic-only/budget-only snapshots cannot pass. Blocked evidence remains open work.
20. **Naxx parity means content and provenance, not copied answers.** Preserve benchmark/loadout/execution/avoidance/raid-ask depth while deriving new conclusions from actual boss/class/duty evidence. Preserve Naxx behavior and its accepted evidence boundaries.
21. **Opportunity and assignment precede judgement.** Validate targets, duration, phases, immunity, class calls and duties. No universal quality score or implicit causal claim; unknowns stay unknown and recorded WCL scores remain distinct from reconstructed totals.
22. **Independent real facts.** Every legal matrix cell needs usable real actor evidence and independent applicable measurement checks. No production analyzer as its own oracle, fitted-out contradiction, arbitrary copied tolerance or N/A for scarce data.
23. **Pre-Mortem obligations live in tasks/raid-completion/pre-mortem.md; every PM-* risk must have Plan refs and a non-Pending resolution before sign-off.**
24. **No inherited waiver or premature completion claim.** Prior Naxx/domain/platform approval does not approve missing new-raid evidence. Any approved partial release is labelled partial and cannot satisfy full completion.

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
- [ ] Shipped code/tests/comments/identifiers are plan-agnostic — grep the repo **excluding `tasks/`** for box IDs (`\b\d\d\.\d+\b`), decision IDs (`\bD\d{3}\b`), the literal `tasks/raid-completion/`, the plan filename `RaidCompletion-Plan.md`, and `\bslices?\b`; zero hits after triaging false positives (version strings can match the box-ID pattern; "slice" may be a legit domain term). See §6.11
- [ ] Commit messages are plan-agnostic — `git log 30e89ce..HEAD` (replace the base only after 00 records the actual starting checkpoint) mentions no box IDs, decision IDs, `tasks/raid-completion/`, `RaidCompletion-Plan.md`, or `slice`/`slices` (apply the same false-positive triage; file grep does not cover commit messages)
- [ ] Branch names and public PR titles/descriptions are plan-agnostic if used
- [ ] `tasks/raid-completion/manual-actions.md` — every human-owned box resolved or explicitly deferred
- [ ] Run the `cleanup-audit` teardown review (whole-repo sweep) before sign-off, **or** waive it with a §4 Decision-log row (e.g. a sweep ran recently, or the repo is too young to have accrued cruft). Triage every finding: fix-now / fold into a *new* plan / won't-fix with a reason. Findings that warrant real work open a **new** plan — never this one, which is disposable and about to be deleted (see Purpose). Report-only: a non-empty report does not block sign-off, but an un-run (un-waived) or un-triaged audit does. Distinct from the per-subject Captain Hindsight checkpoints — this is the one whole-repo pass
- [ ] `tasks/raid-completion/lessons.md` reconciled; lasting lessons migrated to the permanent `tasks/lessons.md` (create it if missing) before the `tasks/raid-completion/` folder is deleted (see Disposable note)
- [ ] All applicable matrix rows COMPLETE with usable real evidence and independent facts; every N/A has a ruleset/API source and reviewed reason. No hidden BLOCKED_EVIDENCE/BLOCKED_REVIEW.
- [ ] All 27 new canonical bosses and combined BWL variant have verified targets, applicable phases/opportunities, reconciled ranking policies and useful boss/class/role advice. All nine classes, supported categories/metrics/factions and 27 declared trees behave correctly.
- [ ] Actual Playbook/Report content matches Naxx depth: preparation/loadout/execution/avoidance/utility/coordination and evidence; no empty or generic-only module is approved.
- [ ] Real capture/quota-resume receipts, independent golden/acceptance facts, mutation-sensitive negatives and provenance/privacy checks recorded per raid.
- [ ] Naxx historical/live/legacy/all-class checks, both pages and packages pass; intended semantic changes reviewed without silently upgrading old evidence boundaries.
- [ ] Real per-raid desktop/terminal/CLI, library filtering, imports/refresh/offline/export and installed candidate/rollback behavior verified.
- [ ] If tasks/raid-completion/pre-mortem.md exists, every PM-* risk has a terminal Resolution; Captain Hindsight calibration is recorded for every risk whose outcome is observable; unelapsed observation horizons are Inconclusive rather than false positives; every CH-MISS-* row has a future lesson.
- [ ] Raid/class domain reviews and concrete product corrections resolved. Prior broad approval cannot replace them; a scope reduction cannot retain the FULLY implemented claim.
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
- If tasks/raid-completion/pre-mortem.md exists, calibrate the PM-* risks relevant to this review target and append any unpredicted material failure as the next CH-MISS-*; do not rewrite the original prediction fields.
- Matrix closure without real actors/independent facts; generic-only advice; missing phase/assignment applicability; inherited Naxx waivers; ranking/variant contradictions and premature completion claims.
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
