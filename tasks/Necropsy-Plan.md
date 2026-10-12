# Necropsy-Plan.md — Milestone A: Headless Hunter/Naxx Forensics

> **Disposable.** This plan and its `tasks/necropsy/` folder are deleted (or
> archived out of the repo) once Milestone A ships. Deleting or archiving the
> folder is human-owned and happens only after §8 sign-off; the agent never
> deletes the plan folder. Shipped code, comments, tests, identifiers, and
> commit messages must not depend on or reference it — see §6.11. The folder is
> committed while the plan is live so it is resume-safe across machines and
> context resets (§6.14).

> **Terms.**
> - **Subject** — one file under `tasks/necropsy/` (`NN-<slug>.md`). Subject
>   `00` is reserved for tooling research and readiness.
> - **Box** — one `[ ]` checklist item inside a subject file, ID
>   `<subject-id>.<box-number>`. Stable; never renumbered.
> - **Slice** — one agent work-session, one line in a subject's Progress log.
> - **Checkpoint** — plan files updated, verification recorded, commit created,
>   branch pushed.
> - **Golden fixture** — the frozen Haplina v6 export (raw WCL JSON) plus the
>   frozen definitive playbook and its provenance record.
> - **Historical mode** — analysis of the frozen fixture with its recorded
>   cohort (overall top 5 per boss, faction-annotated). Deterministic.
> - **Live mode** — `necropsy analyze <url>` against current WCL data with a
>   same-faction cohort. Not reproducible to the rank; rankings are mutable.

---

## Collaboration model

| Field | Value |
|---|---|
| Mode | `coordinated` |
| Primary owner | agent pair: Claude Code (driver) + Codex (navigator) via the pair-programming mailbox; one write owner at a time |
| Coordinator | same as Primary owner |
| Resume safety | required |
| Parallel branches | `no` |
| Notes | Remote: `https://github.com/David-c0degeek/necropsy` (private, personal account). Human roles: David is `product-owner` (scope, sign-off) and `domain-sme` (Classic Era Hunter knowledge, golden-fact adjudication). Every subject closes with a pair review (`VERDICT AGREE`) before its Hindsight checkpoint. |

Mode rules:

- `solo` — one active worker owns the plan at a time.
- `coordinated` — one primary worker owns the plan, with explicit non-agent
  boxes mirrored into `manual-actions.md`; no parallel branch table.
- `parallel` — multiple workers on separate subjects; requires a §4 row first.

If Mode changes, append a §4 Decision-log row.

### Parallel work tracker

n/a — Mode is `coordinated`.

| Subject | Owner | Branch | Dependencies | Conflict-risk files | Status | Handoff notes |
|---|---|---|---|---|---|---|
| | | | | | | |

### Checkpoint gate

Before considering a box done:

- Update the box, subject Progress log, §5 tracker, and any affected §4
  decisions / lessons / manual actions.
- Run the relevant command from the §2 Verification-commands table, or record
  the exact blocker and reproduction command.
- **Behaviour verification:** for a box that changes runtime behaviour, run the
  changed flow end-to-end (CLI command against the fixture subset or full
  fixture) and record observed-vs-expected output in the Progress log. A green
  `pytest` alone does not close it.
- **Doc-currency:** update every dependent doc in the same checkpoint, or record
  `n/a` with a reason (§6.16).
- Commit the coherent checkpoint and push `main` (or the working branch).
- Never rewrite pushed checkpoint history.
- Keep commit messages, branch names, and PR titles plan-agnostic (§6.11).

---

## 1. Subject

Build **Milestone A** of Necropsy: a headless Python CLI that turns Warcraft
Logs data for a Classic Era Hunter in Naxxramas into the definitive forensic
package (offline HTML report + boss-by-boss playbook + `analysis.json` + CSV
tables + evidence), with same-faction benchmarking by default and an explicit
evidence/confidence model. Work is **offline first**: ingest the existing
frozen v6 export, normalize into DuckDB, run generic + Hunter + Naxx analyzers,
emit versioned `analysis.json`, render HTML solely from that JSON. Only then add
live acquisition (`necropsy analyze <url>`): WCL client, character context
resolver, same-faction benchmark selector with pagination, rate-limit pacing,
cache, and a v1 raw snapshot format. The analyzer is a **fresh implementation**
validated against raw events — ChatGPT's analysis scripts did not survive; its
CSVs/report are an oracle to triage against, not ground truth.

**Out of scope** (roadmap in `docs/roadmap.md`, not this plan): desktop UI
(React/Tauri, Milestone B), FastAPI sidecar, generic class/spec/role
classification beyond what Hunter needs (Milestone C), other class plugins
(Milestone D), other raids/game variants (Milestone E), PKCE public-client auth
and any binary distribution, hosted/backend mode, DPS counterfactual
simulation, Polars unless a measured need appears (D007).

### Risks and rollback

| Risk | Impact | Mitigation / rollback |
|---|---|---|
| Golden oracle wrong (ChatGPT miscomputed a value) | Tests pin a bug as truth | Golden-fact register (01) records provenance + status per fact; mismatches are triaged by `domain-sme`, never force-matched |
| Old mixed-faction outputs treated as same-faction truth | Re-introduces the Smcadogx faction-bias bug | Historical vs live modes separated; 63A/12H is a historical-mode fact only; the definitive playbook (not v1/v2) is the frozen report oracle |
| Source+target event streams double-counted | Inflated counts/DPS | Dedupe contract in 02 with explicit tests on self-targeted and overlapping events |
| Missing stream read as "did not happen" | False recommendations (e.g. "no pet") | Coverage/completeness recorded per report+fight+actor+stream; absence claims require coverage; else `UNKNOWN` |
| 80 MB zip / 1.7 GB unpacked too heavy for CI and LFS quota | Slow/failed CI, LFS bandwidth overage | Small deterministic subset committed plainly for ordinary CI; full zip in LFS for `golden` marker suite; bounded extraction |
| Credentials leak into repo/exports/fixtures | Account compromise | Secret + user token in OS keyring only; fixture provenance check asserts no token/secret; `.wcl_user_token.json` never copied; secret-scan gate in §7 |
| Personal confidential-client auth ships in a distributed build | Secret exposure | D005: personal-only; PKCE is a hard gate before any distribution (manual action) |
| Live WCL API changes / rate limit (observed 1,800 pts/h) | Live mode fails mid-job | Resumable cache, `rateLimitData` pacing, explicit partial-coverage result; offline mode unaffected |
| Python 3.14 wheel gaps on Windows | Blocked setup | 00 smoke-installs the exact locked stack; fallback 3.13 by decision |

Rollback: greenfield repo, no consumers. Each subject is a set of pushed
checkpoint commits; revert by `git revert` of the subject's commits.

---

## 2. Authoritative inputs

| Source | Contribution |
|---|---|
| `main` branch | Merge base / target branch |
| `docs/origin/WCL_Forensics_App_Architecture_v0.1.md` | Product + architecture spec v0.1 (principles, evidence model, cohort model, schema, plugin interface, milestones) |
| `docs/origin/Haplina Analysis.md` | Full ChatGPT investigation: derivations, corrections (faction/race/WF), expected facts, design rationale |
| `D:\repos\wcl_access_test\` (read-only) | v6 exporter (`wcl_hunter_deep_export.py`, `wcl_auth.py`), README of auth findings (vanilla.warcraftlogs.com OAuth, port 8765), raw export `exports\wcl_hunter_deep_export_20261012_145328.zip` (80 MB; 1,407 files / 1.7 GB unpacked). **Contains `.wcl_user_token.json` — never copy.** |
| `D:\Parsing\Results\Playbook\Haplina_Naxx_Definitive_Playbook.html` (+ `.zip`, `boss_playbook_definitive.csv`, `top5_definitive_with_faction_race_wf.csv`, `README.txt`) | Frozen report oracle (definitive; supersedes v1 and Alliance-normalized v2) |
| `D:\Parsing\Results\*.csv`, `Haplina_Naxx_Forensic_Pack.zip`, `Playbook\Archive\` | Historical derived outputs; oracle candidates for the golden-fact register, status per fact |
| WCL v2 API docs (vanilla.warcraftlogs.com/v2-api-docs) | GraphQL schema, `rateLimitData`, OAuth endpoints (verified in 00.5) |

### Verification commands

| Purpose | Command | Notes |
|---|---|---|
| Install | `uv sync --locked` | TBD — confirmed in 00.3/00.7 |
| Build | `uv build` | TBD |
| Test (fast) | `uv run pytest -m "not golden and not live"` | Subset fixture only; ordinary CI |
| Test (golden) | `uv run pytest -m golden` | Needs LFS checkout of full fixture; local + scheduled/manual CI |
| Test (live) | `uv run pytest -m live` | Needs keyring credentials; manual only, never CI |
| Lint/format | `uv run ruff check . && uv run ruff format --check .` | TBD |
| Type check | `uv run mypy src` or pyright | TBD in 00.4 |
| Plan-specific gate | clean-clone replay: fresh clone → `git lfs pull` → `uv sync --locked` → `uv run necropsy offline <fixture> --out <dir>` → golden suite | Defined in 01 |
| Plan-specific gate | secret scan of repo + generated packages | Tool TBD in 00.6 |

---

## 3. Subject file index

| # | File | Subject | Depends on |
|---|---|---|---|
| 00 | `tasks/necropsy/00-tooling-research-and-readiness.md` | Tooling research and readiness | — |
| 01 | `tasks/necropsy/01-foundation-and-golden-fixture.md` | Repo foundation, CI, golden fixture + fact register | 00 |
| 02 | `tasks/necropsy/02-snapshot-ingest-and-normalize.md` | Snapshot v0 import, raw store, DuckDB normalization, coverage | 01 |
| 03 | `tasks/necropsy/03-evidence-model-and-generic-analyzers.md` | Evidence model, environment/bias model, generic analyzers | 02 |
| 04 | `tasks/necropsy/04-hunter-classic-era-plugin.md` | Hunter Classic Era analyzer plugin | 03 |
| 05 | `tasks/necropsy/05-naxx-encounters-and-recommendations.md` | Naxx encounter rules, cohort benchmarks, recommendations, `analysis.json` | 04 |
| 06 | `tasks/necropsy/06-report-and-package.md` | Static report/playbook HTML from JSON + export package | 05 |
| 07 | `tasks/necropsy/07-live-acquisition.md` | WCL client, resolver, same-faction selector, cache, `analyze <url>` | 02, 05, 06 |

---

## 4. Decision log

| ID | Date | Title | Decision | Rationale | Refs |
|---|---|---|---|---|---|
| D001 | 2026-10-12 | Project name | `necropsy`, private repo `David-c0degeek/necropsy` | User asked for a made-up name; personal account, not org | README |
| D002 | 2026-10-12 | Offline-first order | Deviates from spec §13 order: build ingest→analyzers→JSON→HTML on the frozen export (01–06) before the live WCL client (07) | Data already exists; analyzer is the hard/valuable part; no API quota burned while contracts settle. Pair-agreed | 01–07; spec §13 |
| D003 | 2026-10-12 | Analyzer is a rewrite | Analyzer is fresh code validated against raw events; ChatGPT CSVs/report are an oracle to triage, not to force-match | Sandbox scripts lost; only the exporter survives | 01.4, 03–05 |
| D004 | 2026-10-12 | Fixture storage | Full v6 zip in Git LFS (golden suite); small deterministic subset committed plainly (fast CI); SHA-256 hashes + provenance file | User chose in-repo private; LFS quota + CI speed | 01.3, 01.5 |
| D005 | 2026-10-12 | Auth for Milestone A | Reuse user's confidential client (secret + user token in OS keyring) for personal use only; PKCE public client is a hard gate before any distribution | User has client ID+secret; spec mandates PKCE for desktop binaries | 07.2; manual-actions |
| D006 | 2026-10-12 | Python version | Provisional CPython 3.14 (installed); 00 smoke-installs the exact locked stack on Windows; fallback 3.13 by new decision row | Spec says 3.12+; DuckDB/Polars publish cp314 wheels, unproven for full env | 00.3, 00.7 |
| D007 | 2026-10-12 | Trimmed stack for A | Typer CLI + Pydantic contracts + DuckDB + Jinja2 + httpx (07 only). No FastAPI. Polars only on measured need; analytics implemented once (SQL in DuckDB or Python, not both) | YAGNI until desktop (B) | 01.1, 02, 06 |
| D008 | 2026-10-12 | Two run modes | Historical mode (frozen fixture, recorded overall-top-5 cohort, faction-annotated) is the deterministic acceptance target; live mode (same-faction cohort) is accepted on contract/coverage, not exact ranks | Definitive playbook's "Alliance comparator" is best Alliance within overall top 5, not a same-faction top 5; live rankings mutate | 05, 07, §7 |
| D009 | 2026-10-12 | Plan location | `tasks/Necropsy-Plan.md` + `tasks/necropsy/` (template convention), not `docs/plan/` | Template standard; durable docs go to `docs/` | — |

---

## 5. Master progress tracker

> **Done rule.** A subject is `DONE` when every box is `[x]` — except a
> human-owned box recorded `DEFERRED` (with rationale) in `manual-actions.md`,
> which stays `[ ]`, is annotated `DEFERRED — see manual-actions` in its
> subject file, and does not block subject closure. A deferred box is never
> ticked; it carries forward as an open item (e.g. 07.10 blocks distribution).
> Agent-owned boxes cannot be deferred this way; they need a §4 row and the
> abandoned format.

| Done | # | File | Status | Owner summary | Human actions mirrored? |
|---|---|---|---|---|---|
| [ ] | 00 | `tasks/necropsy/00-tooling-research-and-readiness.md` | TODO | agent: 8; product-owner: 1 | yes |
| [ ] | 01 | `tasks/necropsy/01-foundation-and-golden-fixture.md` | TODO | agent: 6; domain-sme: 1 | yes |
| [ ] | 02 | `tasks/necropsy/02-snapshot-ingest-and-normalize.md` | TODO | agent: 6 | n/a |
| [ ] | 03 | `tasks/necropsy/03-evidence-model-and-generic-analyzers.md` | TODO | agent: 6 | n/a |
| [ ] | 04 | `tasks/necropsy/04-hunter-classic-era-plugin.md` | TODO | agent: 7; domain-sme: 1 | yes |
| [ ] | 05 | `tasks/necropsy/05-naxx-encounters-and-recommendations.md` | TODO | agent: 6; domain-sme: 1 | yes |
| [ ] | 06 | `tasks/necropsy/06-report-and-package.md` | TODO | agent: 5; product-owner: 1 | yes |
| [ ] | 07 | `tasks/necropsy/07-live-acquisition.md` | TODO | agent: 8; product-owner: 1; release-engineer: 1 | yes |

---

## 6. Cross-cutting principles

1. KISS · YAGNI · CLEAN · SOLID · DRY (in that order when conflicting).
2. ~~*(C#)* One class per file.~~ n/a — Python.
3. ~~*(C#)* Nullable reference types enabled.~~ n/a — Python; type hints + checker per 00.4 instead.
4. ~~*(.NET)* No new build warnings.~~ n/a — replaced by ruff + type-check clean.
5. **Keep code modular and locally understandable.** Small cohesive modules with explicit boundaries.
6. **Cyclomatic complexity stays low.** Prefer table-driven rules (YAML/JSON) over branch-heavy analyzers.
7. **Spec at the contract level, not the SDK level.**
8. **Coverage % is a smell-detector, not a goal.**
9. **Every plan box has an owner and a stable ID.**
10. **Lessons land in `tasks/necropsy/lessons.md` as they happen.**
11. **Code and public metadata are plan-agnostic.** No box/decision IDs, plan filenames, or "slice" in code, tests, commits, branches, PRs.
12. **Captain Hindsight review before subject close.**
13. **Tooling research before implementation.**
14. **All plans are resume-safe.**
15. **Parallelism is opt-in.**
16. **Documentation ships with the change.**
17. **Reuse and integrate before adding.** Wire or delete.
18. **Truth model is non-negotiable.** Every surfaced claim carries an evidence level (`OBSERVED` / `DERIVED` / `INFERRED` / `UNKNOWN`). Windfury is `CONFIRMED` / `NOT_OBSERVED` / `UNKNOWN`; race is named only from a structured field or racial-ability event. Absence claims require recorded coverage of the relevant stream; otherwise `UNKNOWN`.
19. **Same-faction by default; never silent substitution.** Cohort keys (game, zone, partition, encounter, size, class, WCL spec/category, role, faction) are never relaxed silently. Shortfall, inaccessible archive/private data, or partial streams yield an explicit partial-coverage result. Cross-faction data is opt-in, shown separately, never merged into same-faction medians.
20. **Controllability on every recommendation.** Each is classified player / gear-build / pet / raid assignment / raid speed-environment / faction-racial-external / RNG-low-confidence. Gaps are reported as observed gap + likely impact + confidence, never as a precise DPS gain.
21. **Raw is immutable; analysis is reproducible offline.** Raw WCL payloads are stored unchanged with hashes; everything after acquisition runs with no network. HTML is rendered only from `analysis.json`.
22. **Secrets never leave the keyring.** No client secret or user token in repo, fixtures, cache, logs, `analysis.json`, or export packages.
23. **Encounter knowledge ≠ class knowledge.** Class plugins and encounter plugins are separate modules; stable metadata (spell IDs, native targets, racials, pet abilities) lives in versioned rule files under `rules/`.

---

## 7. Gate review (run last; tick everything)

- [ ] All §5 subjects done (or explicitly `ABANDONED` with a §4 row), applying the §5 Done rule for `DEFERRED` human boxes
- [ ] Subject 00 completed, or explicitly waived/abandoned with a §4 row
- [ ] Build command from §2 passes with 0 errors
- [ ] Fast and golden test commands from §2 pass
- [ ] Behaviour verification done for every box that changed runtime behaviour
- [ ] Remaining §2 rows (lint/format, type check, plan-specific gates) pass or are recorded `n/a`
- [ ] §1 Risks-and-rollback table reviewed
- [ ] Cross-cutting principles from §6 reviewed
- [ ] Every implementation subject recorded an `## Integration analysis`; no unjustified duplication
- [ ] New public surface wired to a non-test caller or disclosed as library-only
- [ ] Every non-abandoned subject has a Captain Hindsight checkpoint with verdict `CLOSE`
- [ ] Every ticked box has a Progress-log entry and a pushed checkpoint commit
- [ ] Durable architecture decisions promoted to `docs/adr/`
- [ ] Documentation-impact review done for every shipped box
- [ ] `main` pushed; `git status --short` clean except ignored artefacts
- [ ] If Mode is `parallel`, Parallel work tracker clean
- [ ] Shipped code/tests/comments/identifiers are plan-agnostic — grep excluding `tasks/` for `\b\d\d\.\d+\b`, `\bD\d{3}\b`, `tasks/necropsy/`, `Necropsy-Plan.md`, `\bslices?\b`; zero hits after triage
- [ ] Commit messages plan-agnostic (`git log` same patterns)
- [ ] Branch names and PR titles/descriptions plan-agnostic if used
- [ ] `tasks/necropsy/manual-actions.md` — every human-owned box resolved or explicitly deferred
- [ ] `cleanup-audit` run or waived by §4 row; findings triaged
- [ ] `tasks/necropsy/lessons.md` reconciled into permanent `tasks/lessons.md`
- [ ] **Historical-mode acceptance:** clean-clone replay of the full fixture produces a package against which the golden-fact register passes, where: (a) the set of `mandatory: true` facts is non-empty and covers at least every spec §11 fact plus one fact per boss; (b) every mandatory fact has status `verified-against-raw` and passes within tolerance; (c) every `oracle-only` fact is either promoted to `verified-against-raw` and passes, or carries a recorded exclusion reason; (d) every `disputed` fact carries a recorded `domain-sme` resolution (corrected value or exclusion). No fact passes silently by status alone
- [ ] **Live-mode acceptance:** `necropsy analyze https://vanilla.warcraftlogs.com/character/id/86583560` completes against live WCL, produces a same-faction package with recorded coverage, cohort provenance, and no silent faction/partition substitution
- [ ] **Secret scan:** repo history, fixtures, and a generated package contain no client secret or token
- [ ] **PKCE distribution gate** (07.10) remains `[ ]` with status `DEFERRED` in manual-actions and is listed in §8 notes as an open blocker for any binary distribution
- [ ] Plan handed to reviewer for §8 sign-off

---

## 8. Acceptance / sign-off

| Date | Reviewer | Result | Notes |
|---|---|---|---|
| | | | |

---

## Appendix: Captain Hindsight Prompt

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
- Truth-model violations: a claim without an evidence level, an absence claim
  without stream coverage, a race named without proof, cross-faction data
  leaking into a same-faction benchmark.
- Golden facts force-matched to oracle values instead of triaged.

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
