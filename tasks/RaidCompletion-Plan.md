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
| Mode | `coordinated` |
| Primary owner | Claude (implementation lead; Codex while Claude is unavailable) |
| Coordinator | Claude for implementation; Codex for UI/UX |
| Resume safety | required |
| Parallel branches | `no` — reviewers are read only |
| Notes | Since 2026-10-18 the user directs a Claude/Codex pair (D028): Claude leads implementation until its usage runs out, Codex leads UI/UX and reviews. Exactly one writer at a time; ownership moves only by explicit pair handoff (UI/UX implementation is handed to Codex), and ownership returns to Codex before Claude loses tool access. The writer serializes all DuckDB work, captures and replays. Earlier: user authorized three read-only reviewers on2026-10-18 (D021). Reviewers do not edit, run database workloads, capture WCL data or spawn further agents. Foundation/research checkpoint9aded83 derives from30e89ce; execution began2026-10-16. Existing WCL user-endpoint tooling only; no publication or new infrastructure. |

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
| Summon logic review | /root/summon_review | n/a — read only | current working tree and observed-summon guardrails | none — no edits | reviewed | Unrelated malformed chronology fixed; reviewer rechecked, six regressions included in286 passing tests. research/parallel-review-20261018.json |
| Oracle integrity review | /root/oracle_review | n/a — read only | raw registers, independent checker and checkpoint evidence | none — no edits | reviewed | Marker identity aliases and duplicate-target assertion fixed; reviewer rechecked, all122 raw tests pass. research/parallel-review-20261018.json |
| Class/duty priorities review | /root/class_review | n/a — read only | master plan, subject06, coverage and real callers | none — no edits | reviewed | Aura merged-event guard is next; Holy advice and Hunter/missing-family evidence remain open. research/parallel-review-20261018.json |
| Implementation and verification | Codex root | main | reviewer findings | root owned all changed files | handed off | Superseded by D028 pair handoff at cc83584; historical row |
| Implementation lead (pair) | Claude, current pair-handoff owner | main | Codex UI/UX review and pair verdicts | owner holds all changed files | active | One writer by pair handoff; all edits, captures and database workloads serialized under the owner; UI/UX writes via handoff to Codex |

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
| Matrix / content gate | `uv run python scripts/check_raid_coverage.py --inventory`; `uv run python scripts/check_raid_coverage.py --inventory --staged`; `uv run python scripts/check_raid_coverage.py --require-complete` | Interface to implement in 01.7; inventory never substitutes for the strict gate. Reject unresolved cells, missing facts and generic-only advice. |
| Independent facts | `uv run pytest tests/golden/test_fact_checks_full.py tests/golden/test_ranking_rules_full.py tests/golden/test_druid_replay.py tests/golden/test_class_replay.py -q` | Existing Naxx contracts; add exact per-raid checker/test paths with 01.6. Do not treat old facts as new-raid proof. |
| Raid raw and replay evidence | `uv run pytest tests/golden/test_raid_evidence.py -q`; `uv run python scripts/check_raid_facts.py tests/golden/raids/removal-facts.json`; substitute `facts.json`, `healing-facts.json`, `effect-facts.json`, `control-facts.json`, `aura-facts.json`, `summon-facts.json`, `pet-facts.json` | Select affected fixture IDs with `-k` for a checkpoint; final full gate retains all fixtures. Independent raw expectations are never regenerated from analyzer output. |
| Qualified utility behavior and real pages | `uv run pytest tests/unit/test_removal_exposure.py tests/unit/test_encounter_removals.py tests/unit/test_encounter_effects.py tests/unit/test_rules_package.py -q`; `uv run pytest tests/browser/test_removal_browser.py tests/browser/test_paladin_capture_browser.py -q` | Shared guard/policy negatives and real desktop/mobile/print evidence. Keep database workloads serialized with native capture and other replays. |
| Separate summon healing | `uv run pytest tests/unit/test_summon_healing.py tests/unit/test_healing_recipients.py -q`; `uv run pytest tests/golden/test_raid_evidence.py tests/browser/test_shaman_capture_browser.py -q -k 'mc-restoration-shaman-raid-context or real_shaman_support'` | Independent17-unit raw arithmetic, unknown ownership/type/amount/recipient, occurrence-join integrity and real shared pages. Full ordinary and Naxx/installed-output controls remain required. |
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
| D010 | 2026-10-17 | Explicit encounter event scope | Extend existing cache/fetch with actorless encounter and server-filtered critical scopes, then integrate an explicitly versioned live archive contract. Preserve v0/v1 reading, Naxx acquisition and actor absence predicates; no default collection or ranking/phase certification in the cache-only increment. | Twenty raw actor streams match seven terminal public whole-fight research payloads exactly; per-target Ignite and hostile cast/phase evidence require actors outside the selected cohort. Existing actor-only snapshots cannot prove those observations. | 01.6; 02.1-02.3/02.7; research/encounter-stream-contract.md; PM-2/PM-3 |

| D011 | 2026-10-17 | Instance-aware NPC aura state | Extend shared observed aura transitions and scoped evidence for exact NPC actor/instance buffs, saved into existing playbook and both pages. Keep initial/lifecycle/identity uncertainty; no physical phase or personal opportunity inference. | Real Majordomo four-instance counterexample has simultaneous applications but different removals. Actor-only or filtered coverage cannot certify windows; Aegis and reflection are distinct effects. | 01.6; 02.1/02.2/02.7/02.8; 03.1/03.2/03.4–03.8; PM-2/PM-3; [ADR0017](../docs/decisions/0017-target-instance-aura-windows.md) |

| D012 | 2026-10-17 | Actor support and event provenance | Extend recipient-qualified new Era actor absorption/combined support while preserving heal-only values and unknowns. Correct existing class Report dict.copy collisions to numeric indices or explicit Unknown; retain Naxx Hunter bytes and all saved analysis values. |66 independent HPS cases require credited absorbs, not incoming mitigation. Source/installed comparison exposed identical JSON but nondeterministic class Report addresses. No oracle regeneration or universal ranking certification. | 01.6; 02.3/02.7/02.8; 03.2/03.7; 06.10; PM-2/PM-3; CH-MISS-1; ADR0014 |

| D013 | 2026-10-17 | Normal encounter context acquisition | Enable existing encounter-context acquisition in shared run_analyze only for new Era zones2000/2002/2005 partitions1/2. Preserve actor-only low-level default, Naxx/non-Era acquisition, old snapshots, quota reserves and immutable resume. | Real public v2 captures across all three raids pass independent raw checks and source/installed artifact equality. Nine actual CLI scope cases and quota-stop/resume verify selection and incomplete scopes; normal live continuation retains bounded partial evidence. No ranking/phase/assignment policy is certified. | 01.6; 02.1/02.2/02.7/02.8; 07.1; PM-2/PM-3; ADR0016; research/normal-context-pre-mortem.md |

| D014 | 2026-10-17 | Class-qualified NPC control state | Extend existing target aura state with player class/debuff policies; activate separate Garr Banish ranks, exact instances and raw integer identity guards. Preserve personal SOURCE counters, observed-only uncertainty and NPC buff defaults. | Six independent raw control contexts/manual integer-ms expectations and all named caster classes distinguish Forand fight/Greasecup effect from Finia personal zero. Coerced IDs are checked before exclusion; unresolved lifecycle owners carry global refs and withhold windows. No physical opportunity, assignment or quality inference. | 01.6; 02.1/02.2/02.7/02.8; 03.4/03.6/03.7/03.8; PM-2/PM-3; ADR0017; research/npc-control-window-contract.md |
| D015 | 2026-10-17 | Incremental evidenced BWL implementation | Extend the existing shared facts/static strategy contracts to all eight individual BWL bosses alongside the already implemented combined entry, while 01/02 remain open. | Normal full BWL acquisition retains53 public selected actors,106 player directions and106 global scopes. Independent raw spell/recipient checks and pinned primary consumer/tooltips constrain class and version applicability. Missing Nefarian personal faction and one pet owner remain explicit. No phase/ranking or full acceptance reduction. | 01.5/01.6; 02.1/02.5; 04.1–04.9; PM-1/PM-2/PM-3; research/bwl-initial-contract.md |
| D016 | 2026-10-17 | Identity-qualified actor exposure and cohort examples | Extend existing observed-only actor effects to evidenced BWL mechanics and save separately labelled cohort exposures. Check raw recipient/spell projections and lifecycle ownership before exclusion; retain unknown evidence/coverage instead of coerced absence. | Seven independently frozen contexts/15 manual timelines, all nine class selectors and raw mutation/identity tests. Missing personal Nefarian stays absent despite available cohort Priest calls. No physical phase, resource quantity, stun uptime or quality inference; original401/239 measurements preserved. | 01.6; 02.1/02.2/02.7/02.8; 04.4/04.7/04.8; PM-2/PM-3; ADR0015; research/bwl-observed-effects-contract.md |
| D017 | 2026-10-17 | Incremental evidenced AQ40 implementation | Extend existing shared facts/static strategy to all nine AQ40 bosses while 01/02 remain open; preserve independent raw actor/recipient/context evidence from normal quota-limited acquisition. | First capture retains29 public actors across all nine personal bosses,58 player directions/58 global scopes; comparisons stop before Viscidus and two pet listings remain missing. A zero-point resume stops earlier and cannot replace the stronger immutable first archive. Exact Summon Images747 events resolve176525 image identity in six captured Skeram fights, without ranking eligibility. No phase, duty, faction/class or acceptance reduction. | 01.5/01.6; 02.1/02.5; 05.1–05.9; PM-1/PM-2/PM-3; research/aq40-initial-contract.md |
| D018 | 2026-10-17 | Cardinality-qualified AQ40 aura observations | Extend existing NPC aura windows to explicitly singleton boss policies using exact fight enemyNPCs actor/gameID/instanceCount1 metadata; preserve numbered-add requirements, actor exposure and independent buff/debuff raw checks. | Six frozen NPC contexts/nine manual target timelines plus actual4.994-second Sand Blast exposure precede rule activation. Full54-actor capture preserves earlier29 dimensions and supplies all nine personal/five-cohort sections. One native analysis failure recovers on byte-identical offline and actual CLI runs; its cause remains recorded, not claimed fixed. No physical phase/ranking/duty inference or acceptance reduction. | 01.6; 02.1/02.2/02.7/02.8; 05.2/05.4/05.7/05.8; PM-2/PM-3; research/aq40-observed-aura-contract.md; research/aq40-normal-analysis-incident.md |
| D019 | 2026-10-18 | Evidence-qualified pet absence advice | Require the shared three-known-value minimum and a positive same-faction trained-pet median before emitting the shared comparative pet-absent instruction. Preserve known absence and zero DPS, classification uncertainty, guardian exclusion and roster guards. | Sartura has five known comparisons with median zero; Sapphiron has only two with an unknown median. Both retain absence but lose unsupported advice on reanalysis. Original Naxx fact register still requires all four historical absences; a separate policy test requires three supported actions. No frozen expectation regeneration or opportunity/assignment claim. | 02.5–02.8; 05.5; 07.4–07.6; PM-1/PM-2/PM-3; ADR0005; research/pet-absence-evidence-contract.md |
| D020 | 2026-10-18 | Qualified per-instance summon event bounds | Save exact numbered summons and elapsed bounds to the first recorded positive-overkill hit, with shared NPC identity/cardinality and genuine-death qualification. Preserve overlapping groups and unknown endpoints; no life, attackability, opportunity, ranking denominator or grade is inferred. | Twelve independently frozen fights/72 images precede production modeling;60 event bounds and12 unknown endpoints. Raw scalar, scope, metadata/variant and contradictory-event negatives are required. Source and installed Holy/Hunter outputs agree; final verification and interim Hindsight remain prerequisites to checkpointing. Original expectations/archives remain immutable. | 01.6; 02.2/02.7/02.8; 05.3/05.7; 07.4–07.7; PM-1/PM-2/PM-3; ADR0015; research/observed-summon-window-contract.md |
| D021 | 2026-10-18 | Review collaboration | Change from solo to parallel review after the user explicitly selected “Use three reviewers.” Three read-only agents review summon logic, oracle integrity and class/duty priorities; root retains all edits on main. | Independent review can overlap implementation without write conflicts or concurrent DuckDB workloads. No reviewer branches, mutations, captures, database commands or nested delegation. Review findings and root dispositions must be recorded before checkpointing. | Collaboration model; 01/02/05/06/07; parallel work tracker |
| D022 | 2026-10-18 | Qualified Priest mechanic-removal effects | Reuse shared removal observations for Chromaggus Blue23153 with Priest Dispel Magic527/988. Validate relevant raw/normalized ownership, recipient, spell, type, timestamp and fight before exclusions; malformed required metadata or missing normalized ownership/chronology withholds counts. New policy requires actor-source trust plus exact encounter-All/event-set proof; existing policies retain their scope contract. | Six raw contexts freeze three988 effects and five other-owner counterexamples before activation; only988 has real positives. Counts do not establish assignment, reaction time, opportunity or quality. Three read-only reviewers check model, independent oracle and regression boundaries; nullable chronology findings fixed with negatives. No full class/cell/subject closes. | 01.6; 02.2/02.5/02.8; 04.3/04.7; 06.5; 07.4–07.7; PM-1/PM-2/PM-3; ADR0015; research/chromaggus-priest-removal-contract.md |
| D023 | 2026-10-18 | Explicit exposure endpoints alongside self-removal | Extend the shared Priest removal policy to Geddon19659 and save optional exact aura-endpoint/self-dispel pairs through existing personal/cohort Playbook seams. Require source/target plus exact All/event-set proof, strict raw identity/chronology and unique unambiguous endpoints. Preserve standalone counts; coordination text supplies no reaction grade, causation, saved mana/damage or opportunity claim. | Six directly frozen contexts establish one988 effect, five zeros and1608ms exposure before policy activation. Investigation also corrects24 older swapped Shazzrah/Geddon healing selectors using raw named NPC/fight roster bindings while preserving all322 expected measurements. New Paladin evidence remains unregistered until its separate acceptance; empty enemy rosters remain explicit gaps. | 01.6; 02.2/02.5/02.8; 03.6/03.7; 06.5; 07.4–07.7; PM-1/PM-2/PM-3; ADR0015; research/geddon-removal-correlation-contract.md; research/mc-recipient-selector-investigation.json |
| D024 | 2026-10-18 | Paladin-specific Geddon Cleanse evidence | Add a separate class6 policy restricted to Cleanse4987, reusing the existing qualified removal/pairing algorithms. Keep Priest527/988 applicability separate; Purify1152's Holy school does not grant Magic removal. | Six directly frozen Paladin contexts establish four successful effects/two actors, four zero actors and Anrylla's2882ms self-exposure pair. Resurgance's three effects target others and cannot end his personal exposure. Classic capability sources and adverse tests distinguish effects from casts/assignment/quality. Only the MC policy asset changes in the wheel; all prior12 removal expectations remain unchanged. | 02.5/02.7/02.8; 03.6/03.7; 06.4; 07.4–07.7; PM-1/PM-2/PM-3; ADR0015; research/paladin-geddon-cleanse-contract.md |
| D025 | 2026-10-18 | Separate owned-summon healing | Add optional individual healing/absorption/rate evidence to generic Era combat pet entries and shared saved healing context for both pages. Reuse recipient classification only after strict ownership, full-event integrity and occurrence-multiplicity checks. | Raw Shaman expectations precede modeling:17 known-owned units across59 qualified owner contexts, plus one missing listing left unknown. Damage0 does not imply healing0; approximate score fit cannot establish ownership/ranked HPS. All actor metrics, scores, Hunter/Druid and Naxx contracts remain separate. Reviewers found both-null identity/type and duplicate ability-join seams; adverse tests guard them. | 02.2/02.5/02.8; 03.7; 06.7/06.11; 07.4–07.7; PM-1/PM-2/PM-3; ADR0018; research/owned-summon-healing-contract.md |
| D026 | 2026-10-18 | Raid-roster interruption context | Add optional deduplicated report/fight observations through shared saved JSON/rendering, initially class9 Era Sulfuron. Exact friendly class/NPC-instance/raw event bindings and All/event-set proof qualify counts; partial totals preserve positives. | Four qualified effects belong to Sabshaw, Minni and Healybeams, not selected players or inferred talent builds. All six raw contexts frozen before model/checker; no opportunity or personal-utility waiver. | 02.2/02.4/02.5/02.7/02.8; 03.7; 06.7/06.11; 07.4–07.7; PM-1/2/3; ADR0019; research/raid-interrupt-review.json |
| D027 | 2026-10-18 | Priest credited absorption context | Add optional actor/report/fight-deduplicated ability and recipient splits through shared healing classification and both-page rendering. Initial review prompt requires positive10901; other ranks remain outside prompt coverage. | Strict player SOURCE binding plus All/event-set proof qualifies totals; valid observations survive uncertainty. All60 independent raw contexts were frozen first. Preserve existing actor metrics/scores and old saved rendering; do not infer cast frequency, assignment, proc causes or quality. | 02.2/02.4/02.5/02.7/02.8; 03.7; 06.5/06.11; 07.4–07.7; PM-1/2/3; ADR0020; research/absorption-review.json |
| D028 | 2026-10-18 | Pair implementation lead | Change Mode from `parallel` (D021 read-only reviewers, now complete) to `coordinated`: the user directs Claude to lead implementation until its usage runs out, with Codex leading UI/UX and reviewing; Codex reclaims implementation when Claude is unavailable. | One writer at a time through explicit pair handoff keeps edits and serialized DuckDB/capture work unambiguous across two terminals; UI/UX changes go through a handoff to Codex. Completed D021 reviewer rows stay as historical evidence. | All subjects; §Collaboration ownership; no branch change (main) |
| D029 | 2026-10-18 | Owned control integrity and certainty correction | Harden `control.applications()` in place: direct occurrence reads, literal raw/normalized validation before exclusion, unique Player-class source, typed enemy roster/instanceCount binding, and target-specific review prompts for qualified instance-bearing observations. Complete counts require strict player SOURCE plus encounter event-set proof. | A trusted SOURCE stream cannot rule out a disjoint owned identity added by another merged stream. Format1 Garr counts become unknown (certainty correction); raw facts, Rumplock's observed 18647/Firesworn100/instance8/4258ms and earlier independent registers stay unchanged. Zero supplies no criticism; no assignment or uptime inference. | 02.x control seam; 03 Garr; 06 Warlock; PM-1/2/3; ADR0021; research/garr-owned-control-contract.md |
| D030 | 2026-10-18 | Owned curse context on the control engine | Parameterize `control.py` by policy kind and add a Garr `curses` policy (all Recklessness/Elements/Shadow ranks) saved as optional `playbook.curse_applications`, with one assignment-confirmation prompt per spell/target/instance. | Reuses every D029 proof unchanged, keeps control output byte-identical, and avoids a second parser. All three Garr subjects match an independent pre-model freeze; applications are not uptime, benefit or assignment. Other encounters unconfigured until evidenced. | 06.8; 03 Garr; ADR0022; research/garr-owned-curses-independent-observation.json, research/garr-curse-primary-sources.json |
| D031 | 2026-10-19 | Unattended capture queue on Tower | Run the remaining raid configuration captures as one reviewed serial queue (93 scheduled runs; 9 reuse registered evidence) in a container on Tower, built from the published v0.5.0 wheel, with a LAN status page, Notifiarr alerts and a host watchdog. Captures are evidence only: no cell is validated, completed or registered until its outputs are imported to the PC, archive hashes verified and the normal review runs. | Quota limits made attended captures the bottleneck. The user approved the design, the release, the sign-in transfer and go-live after the real test alert arrived. The pair reviewed every slice (credential file ADR 0023, outcome receipts, runner, queue, status page, image, Tower deploy). | 01.5/01.6; tower-capture-design.md; ADR 0023; unraid-tower `changes/2026-10-19-necropsy-capture-deploy.md` |
| D032 | 2026-10-19 | Work order and working rules after the capture deploy | Order: (1) small deterministic automation first: an analyzer-independent raw fact-freeze tool, a closure-record/register generator that verifies committed Git-blob pins (never blesses working-tree output), the Edge visual harness as a committed dev tool and one pre-review gate (lint, EOL, hash pins, recurring review findings); each built against the pilot cell and one contrasting case, without a new framework. (2) Eligible IN_PROGRESS cells on the registered captures; having a capture never proves a cell. (3) Boss-scoped work across all 28 entries. (4) Class notes. (5) Read-only imports of finished Tower captures. Evidence-blocked cells stay open without blocking other bosses or classes. Rules: one shared-tree writer at any moment; parallel implementation only in separately owned worktrees with recorded ownership and review boundaries; deterministic scripts instead of models where possible; cheaper models only for bounded, checkable work (Claude: haiku/low mechanical, sonnet/medium bounded research and first drafts; Codex: luna/low, sol/medium); design, semantics, evidence decisions, review and integration stay with the top model; the owner verifies all delegated output before review and cheap-model output is never evidence; reviews batch per coherent boss or class contract, with small checkpoints kept for shared semantics, schema, auth and concurrency; measure usage on the first batch instead of assuming savings. | User asked both agents to stretch usage with cheaper models and parallel tracks while keeping cross-review. Pair DESIGN_AGREED (codex #94) on claude #104; persisted after slice 6 as agreed. | §Collaboration model; 01/02/06/07; lessons.md |
| D033 | 2026-10-20 | D032 step 1 automation delivered | Delivered and pair-reviewed: scripts/fact_freeze.py (78e48f6), scripts/closure_pins.py (67dc212), scripts/visual_check.py with capture status browser tests (c4f8e2e), scripts/pre_review.py with tasks/raid-completion/review-checklist.md (fd31c81). Unattended capture incident 1 fixed by v0.5.1 (7c2138a) and redeployed. Next: step 2, eligible IN_PROGRESS cells on registered captures, using the gate before every review. | Built against the pilot and contrasting cases as agreed; the closure verifier keeps the pilot's mixed-commit source-review pin visible as a real failure. Tools are mechanical evidence only. | D032; pre-mortem PM-D032-1..3; lessons.md |
| D034 | 2026-10-20 | Capture units replace per-cell delivery | The unit of work becomes the capture unit: one configuration (class, category, metric, faction) in one raid, 102 units, each closing its 8 to 10 cells together. Order: (T1) scripts/unit_preflight.py lists every cell's missing dimensions, actor-source usability and class-scoped boss rules before work starts; (T2) scripts/render_parity.py renders one capture from a pinned commit, from source and an isolated wheel, into one receipt with payload, output, per-boss content and anchored visual checks; (T3) scripts/close_unit.py writes, pins and registers a unit's closures from one reviewed spec (closure commit, then coverage commit); (T4) faster gates: xdist only after its unexplained failures are explained, zone-rule changes run their raid's seed replays, targeted golden runs are labelled, and the full serial golden file runs once per unit closure; (T5) boss-major content for all classes at once, with cheap-model drafts under D032 rules; (T6) three review boundaries per unit (content, frozen facts and ranking, receipt plus closures plus close-out records). First measured unit: the remaining 8 MC Paladin Holy/HPS/Alliance cells, target under 6 h end to end. Guardrails: per-cell evidence decisions stay; a green receipt or a neighbouring cell never makes a cell COMPLETE; a unit can close some cells and leave others OPEN; unknown or unsupported page content is an explicit outcome; reviewer sampling is evidence, not blanket visual sign-off; measure setup and total elapsed time, including waiting and rework, and stop adding automation if end-to-end cost rises. Quota-bound or evidence-blocked units stay OPEN. | The user judged per-cell delivery undeliverable: Lucifron took about 14 h for cell 2 of 952, roughly half of it waiting or rework. Most evidence is produced per capture already. Pair DESIGN_AGREED (codex #161) on claude PLAN D034. | D032; D033; 01/03/06/07; lessons.md |
| D035 | 2026-10-20 | Parallel gate and parallel draft work by owner decision | Supersedes D034's T4 wording (xdist only after the earlier failures are explained; the full serial golden file once per unit closure): the pre-review gate runs golden replays on NECROPSY_GATE_WORKERS workers (default 8, 0 for serial) with -rfE, and every pytest run's complete output, exit, command, HEAD and worker setting is kept in its own file under the Git directory (necropsy-gate-logs), linked from the gate detail. A parallel failure is diagnosed when it occurs; a later serial pass never turns the original FAIL into a pass, and a crash without a pytest summary stays FAIL. Bounded per-boss research, drafting and raw discovery may run as parallel subagents that write drafts only outside the repository; the single shared-tree writer verifies every draft against its source and the raw data before it enters the tree (D032). | The user, after D034's first tools: "Keep going autopilot. Use parallel. If errors arise again fix as they come." The owner accepts the risk of the three unexplained parallel failures from the first sweep. Codex STEER #165 accepted the override and set the logging and failure guardrails. | D034; scripts/pre_review.py |
| D036 | 2026-10-21 | Layer-based completion replaces per-cell closures by owner decision | A cell is COMPLETE when four layers verify, recorded for many cells in one batch manifest (tests/golden/raids/batches/<batch>.json, written by scripts/raid_batch.py and verified by scripts/check_raid_coverage.py): (1) engines, one digest per raid over every package file except the zone files plus the raid's zone rules without the cell-scoped parts, verified by the golden tests and re-attested by a new batch when they change; (2) capture, one committed render_parity receipt per capture with identical source and installed renders, a clean wheel payload, every text of each cell's boss present, clean visual checks and one sampled picture; (3) content, one digest per boss, class and metric over the strategy items, the encounter facts and the cell's ranking metric policy, reviewed once per boss and configuration; (4) register, a coverage reference to the manifest bytes and the cell, with the actor source, the independent fact cases (pinned by case digest) and the ranking oracle joined by exact boss, configuration and actor identity. Every artifact is pinned by SHA-256. Shared edits no longer cascade: an unrelated edit leaves cells complete, an engine edit makes its raid stale until re-attested, a content edit makes only that boss and configuration stale. One review per batch covers engine changes, content diffs, receipt summaries and the generated register diff. Existing closures stay valid as history; they are not a new approval of cells that were pending. Kept: raw-first oracles, no unknown becomes zero or N/A, owned-listing gaps stay OPEN, guidance only for unmeasured duties, one shared-tree writer. | Per-cell pinned closures turned every shared-file edit into re-render, re-pin and re-review cascades (one class-notes change reopened 17 cells). The owner: "yes - and lets do this now. because we will never finish this work currently." Pair DESIGN_AGREED (codex #191) on claude PLAN #195, with negative checks for missing artifacts, wrong identity, changed manifest bytes and stale layers. | D034; D035; scripts/raid_batch.py |

---

## 5. Master progress tracker

A subject is DONE only after all boxes, behavior receipts and durable checkpoints exist and its closing Hindsight verdict is CLOSE. Owners are agent, release-engineer, product-owner, tech-lead and domain-sme. Human-owned boxes are mirrored. No boxes are complete at plan creation.

| Done | # | File | Status | Owner summary | Human actions mirrored? |
|---|---|---|---|---|---|
| [x] | 00 | `tasks/raid-completion/00-tooling-research-and-readiness.md` | DONE | agent: 8; CLOSE; foundation/research checkpoint pushed | n/a |
| [ ] | 01 | `tasks/raid-completion/01-evidence-and-coverage-contract.md` | IN_PROGRESS | 52 archives/893 actor cases/634 recipients/347 pet contexts; Shaman damage/healing totems; two Paladin roster gaps and unresolved guardians remain explicit | n/a |
| [ ] | 02 | `tasks/raid-completion/02-shared-encounter-and-class-contracts.md` | IN_PROGRESS | shared strategy on all28 entries, local effects/control, qualified summon bounds and exposure/self-removal pairing; remaining contracts open | n/a |
| [ ] | 03 | `tasks/raid-completion/03-molten-core.md` | IN_PROGRESS | agent: 9; domain-sme: 1 | yes |
| [ ] | 04 | `tasks/raid-completion/04-blackwing-lair.md` | IN_PROGRESS | initial strategy/exposure and qualified Priest Blue-removal effects; full boss/class/domain obligations open | yes |
| [ ] | 05 | `tasks/raid-completion/05-aq40.md` | IN_PROGRESS | agent: 9; domain-sme: 1; initial facts/strategy, observed NPC context and partial real class coverage | yes |
| [ ] | 06 | `tasks/raid-completion/06-all-class-validation.md` | IN_PROGRESS | Priest Blue/Geddon and Paladin Geddon utility active; Shaman Restoration and expanded Elemental evidence registered; ten Elemental positive peer cells, five duty-unknown personal contexts and one duty-unknown Golemagg peer; nine Shadow/Alliance peer cells (40 of 50 peers eligible, no personal Shadow fight, Garr TODO); nine Restoration Druid/Alliance cells (9 personal fights, 44 cohort entries, Sulfuron TODO); separate summon healing, raid-roster interrupts and Priest absorption-recipient review active; full class/domain gates open | yes |
| [ ] | 07 | `tasks/raid-completion/07-product-and-release-acceptance.md` | IN_PROGRESS | agent: 8; product-owner: 1 | yes |

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
