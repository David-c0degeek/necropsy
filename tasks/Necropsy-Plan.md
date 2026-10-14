# Necropsy-Plan.md — Milestone A: Headless Hunter/Naxx Forensics

> **Disposable.** The plan and its `tasks/necropsy/` folder are deleted (or
> archived out of the repo) once the subject ships to production. Deleting or
> archiving the folder is human-owned and happens only after §8 sign-off; the
> agent never deletes the plan folder. Shipped
> code, comments, tests, identifiers, and commit messages must not depend on or
> reference them — see §6.11. Commit the folder anyway while the plan is live,
> so it is resume-safe across machines and context resets (§6.14).

> **Terms.**
> - **Subject** — one file under `tasks/necropsy/` (`NN-<slug>.md`). 5-8 per plan.
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
> - **Golden fixture** — the frozen Haplina v6 export (raw WCL JSON) plus the
>   frozen definitive playbook and its provenance record.
> - **Historical mode** — analysis of the frozen fixture with its recorded
>   cohort (overall top 5 per boss, faction-annotated). Deterministic.
> - **Live mode** — `necropsy analyze <url>` against current WCL data with a
>   same-faction cohort. Not reproducible to the rank; rankings are mutable.

---

## Collaboration model

> One plan shape supports solo work, coordinated human/agent work, and true
> parallel work. Keep the plan low-noise by starting in `solo` unless
> multiple active workers are expected now. Upgrade by §4 Decision-log row
> when the need appears; do not fork the plan or switch templates.

| Field | Value |
|---|---|
| Mode | `coordinated` |
| Primary owner | agent pair: Claude Code (driver) + Codex (navigator) via the pair-programming mailbox; one write owner at a time |
| Coordinator | same as Primary owner |
| Resume safety | required |
| Parallel branches | `no` |
| Notes | Remote: `https://github.com/David-c0degeek/necropsy` (private, personal account). Human roles: David is `product-owner` (scope, sign-off) and `domain-sme` (Classic Era Hunter knowledge, golden-fact adjudication). Every subject closes with a pair review (`VERDICT AGREE`) before its Hindsight checkpoint. |

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

n/a — Mode is `coordinated` (D010).

| Subject | Owner | Branch | Dependencies | Conflict-risk files | Status | Handoff notes |
|---|---|---|---|---|---|---|
| | | | | | | |

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
  compile it. Here: run the changed `necropsy` CLI command against the subset
  or full fixture and record observed-vs-expected output.
- **Doc-currency:** if the box changed behaviour, architecture, commands, usage,
  configuration, setup, troubleshooting, or developer workflow, update every doc
  that depends on it in the *same* checkpoint — user- and developer-facing alike
  (see §6.16 for the full scope) — or record in the Progress log that none
  applied and why.
- Commit the coherent checkpoint and push the branch. In this pair plan the
  navigator reviews the diff (`VERDICT AGREE`) before the checkpoint closes.
  If the repo has no remote, record that once in the Collaboration model Notes and treat the
  local commit as the checkpoint.
- Never rewrite pushed checkpoint history — no force-push, rebase, or reset
  of checkpoint commits.
- Keep commit messages, branch names, and PR titles/descriptions
  plan-agnostic: no box IDs, decision IDs, plan filenames, `tasks/necropsy/`,
  or `slice`/`slices` (see §6.11). Repo commit style still applies.

Checkpoint names should describe durable project work, not plan administration.
Example commit message shape: `Add provider retry policy tests`, not
`Complete 03.2`.

---

## 1. Subject

> One paragraph. What is being built. What is explicitly out of scope.
> The "out of scope" half is as important as the "in scope" half — it
> stops the plan from sprawling.

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

> Fill at plan creation; `n/a` requires a one-line reason. What can go
> wrong once this ships, and how the change is undone or disabled —
> revert, feature flag, config switch, migration down-script. Data and
> compatibility hazards belong here too. Revisited at the §7 gate.

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
| Python 3.14 wheel gaps on Windows | Blocked setup | Retired risk: 00.3 smoke run green on CPython 3.14.6; fallback 3.13 by decision if a new dependency lacks wheels |
| Actor-scoped coverage (only selected Hunters + `petOwner` actors have streams) | Threat, boss-target time, raid composition unknowable from v0 data | Those fields are `UNKNOWN` with coverage refs, never inferred; live acquisition may add streams later by decision |

Rollback: greenfield repo, no consumers. Each subject is a set of pushed
checkpoint commits; revert by `git revert` of the subject's commits.

---

## 2. Authoritative inputs

> Table. One row per input doc / branch / spec / archived plan.
> Contribution column says exactly what each input gives.

| Source | Contribution |
|---|---|
| `main` branch | Merge base / target branch |
| `docs/origin/WCL_Forensics_App_Architecture_v0.1.md` | Product + architecture spec v0.1 (principles, evidence model, cohort model, schema, plugin interface, milestones) |
| `docs/origin/Haplina Analysis.md` | Full ChatGPT investigation: derivations, corrections (faction/race/WF), expected facts, design rationale |
| `D:\repos\wcl_access_test\` (read-only) | v6 exporter (`wcl_hunter_deep_export.py`, `wcl_auth.py`), README of auth findings (vanilla.warcraftlogs.com OAuth, port 8765), raw export `exports\wcl_hunter_deep_export_20261012_145328.zip` (80 MB; 1,407 files / 1.7 GB unpacked). **Contains `.wcl_user_token.json` — never copy.** |
| `tasks/necropsy/pre-mortem.md` | Retained pre-mortem risks PM-1..PM-3 for live acquisition, their guardrails and calibration |
| `D:\Parsing\Results\Playbook\Haplina_Naxx_Definitive_Playbook.html` (+ `.zip`, `boss_playbook_definitive.csv`, `top5_definitive_with_faction_race_wf.csv`, `README.txt`) | Frozen report oracle (definitive; supersedes v1 and Alliance-normalized v2) |
| `D:\Parsing\Results\*.csv`, `Haplina_Naxx_Forensic_Pack.zip`, `Playbook\Archive\` | Historical derived outputs; oracle candidates for the golden-fact register, status per fact |
| WCL v2 API docs (vanilla.warcraftlogs.com/v2-api-docs) | GraphQL schema, `rateLimitData`, OAuth endpoints (verified in 00.5) |

### Verification commands

> Single source for "the relevant verification command" used by the
> Checkpoint gate and the §7 gates. Fill what is known at plan creation
> (`TBD` allowed); subject 00.3 confirms or corrects the rows against the
> real repo, and 00.8 bakes in any additions. Stack here: Python + uv.

| Purpose | Command | Notes |
|---|---|---|
| Install | `uv sync --locked` | Confirmed by 00.3 smoke run (uv 0.11.21, CPython 3.14.6) |
| Build | `uv build` | Confirmed by 00.3 smoke run |
| Test (fast) | `uv run pytest -m "not golden and not live and not acceptance"` | Subset fixture only; ordinary CI; markers enforced by `--strict-markers` |
| Test (golden) | `uv run pytest -m golden` | Needs `git lfs pull` of the full fixture; local + scheduled/manual CI |
| Test (acceptance) | `uv run pytest -m acceptance` | Golden-fact register gate; expected to fail until analyzers verify every mandatory fact; run at §7 |
| Test (live) | `uv run pytest -m live` | Needs keyring credentials; manual only, never CI |
| Lint/format | `uv run ruff check . && uv run ruff format --check .` | Confirmed by 00.3 smoke run |
| Type check | `uv run mypy` | mypy strict, configured in `pyproject.toml` (D012) |
| Plan-specific gate | clean-clone replay: fresh clone → `git lfs pull` → `uv sync --locked` → `uv run necropsy offline <fixture> --out <dir>` → golden suite | Defined in 01 |
| Plan-specific gate | `gitleaks git . --redact` and `gitleaks dir <generated package dir> --redact` | gitleaks 8.30.1 (00.7); zero findings required |

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
| D001 | 2026-10-12 | Project name | `necropsy`, private repo `David-c0degeek/necropsy` | User asked for a made-up name; personal account, not org | `README.md`; §2 inputs; Collaboration model Notes |
| D002 | 2026-10-12 | Offline-first order | Deviates from spec §13 order: build ingest→analyzers→JSON→HTML on the frozen export (01–06) before the live WCL client (07) | Data already exists; analyzer is the hard/valuable part; no API quota burned while contracts settle. Pair-agreed | 01.1–07.10; §3; `docs/roadmap.md`; spec §13 |
| D003 | 2026-10-12 | Analyzer is a rewrite | Analyzer is fresh code validated against raw events; ChatGPT CSVs/report are an oracle to triage, not to force-match | Sandbox scripts lost; only the exporter survives | 01.4, 03.6, 04.7, 05.6 |
| D004 | 2026-10-12 | Fixture storage | Full v6 zip in Git LFS (golden suite); small deterministic subset committed plainly (fast CI); SHA-256 hashes + provenance file | User chose in-repo private; LFS quota + CI speed | 01.3, 01.5 |
| D005 | 2026-10-12 | Auth for Milestone A | Reuse user's confidential client (secret + user token in OS keyring) for personal use only; PKCE public client is a hard gate before any distribution | User has client ID+secret; spec mandates PKCE for desktop binaries | 07.2, 07.9, 07.10; `manual-actions.md`; §7 PKCE gate |
| D006 | 2026-10-12 | Python version | Provisional CPython 3.14 (installed); 00 smoke-installs the exact locked stack on Windows; fallback 3.13 by new decision row | Spec says 3.12+; DuckDB/Polars publish cp314 wheels, unproven for full env | 00.3, 00.7 |
| D007 | 2026-10-12 | Trimmed stack for A | Typer CLI + Pydantic contracts + DuckDB + Jinja2 + httpx (07 only). No FastAPI. Polars only on measured need; analytics implemented once (SQL in DuckDB or Python, not both) | YAGNI until desktop (B) | 00.3, 01.1, 02.3, 06.1, 07.1 |
| D008 | 2026-10-12 | Two run modes | Historical mode (frozen fixture, recorded overall-top-5 cohort, faction-annotated) is the deterministic acceptance target; live mode (same-faction cohort) is accepted on contract/coverage, not exact ranks | Definitive playbook's "Alliance comparator" is best Alliance within overall top 5, not a same-faction top 5; live rankings mutate | 01.4, 05.3, 05.6, 07.4, 07.7; §7 acceptance gates |
| D009 | 2026-10-12 | Plan location | `tasks/Necropsy-Plan.md` + `tasks/necropsy/` (template convention), not `docs/plan/` | Template standard; durable docs go to `docs/` | `tasks/Necropsy-Plan.md`; `tasks/necropsy/*`; `README.md` |
| D010 | 2026-10-12 | Collaboration mode | `coordinated` instead of the template default `solo` | User asked for Claude Code + Codex pair programming, and the plan has product-owner / domain-sme / release-engineer boxes; one write owner at a time via the pair mailbox, no parallel branches | Collaboration model; `manual-actions.md`; every subject Hindsight checkpoint |
| D012 | 2026-10-13 | Type checker | mypy in strict mode, configured in `pyproject.toml`; pyright not adopted | Python-native, cp314 wheel, no Node toolchain; one gate tool | 00.4; 01.1; §2 Type check |
| D013 | 2026-10-13 | No third-party WCL client or MCP | Necropsy owns its httpx GraphQL client; the evaluated community WCL MCP servers and PyPI packages are rejected | None of the evaluated candidates (00.6) meets Necropsy's needs; the MCP servers would receive WCL credentials from unknown authors | 00.6; 07.1 |
| D014 | 2026-10-13 | Explicit DuckDB schemas | Raw-derived tables use declared column types, never JSON auto-inference | Auto-inference typed `targetID` as `HUGEINT` on a real page; types must be stable across fixtures | 00.2; 02.3 |
| D015 | 2026-10-13 | Subset fixture is a compressed archive | The fast-test subset is a deterministic zip of original member bytes plus a generated `subset.json`; the < 25 MB budget applies to the zip (13.6 MB) | Exporter JSON is pretty-printed: the same 12 fights are ~290 MB raw; original bytes must stay unmodified | 01.5; `tests/fixtures/haplina_naxx_subset.zip`; `scripts/fixture_tools.py` |
| D016 | 2026-10-13 | Read snapshots from the zip, no extraction | `VerifiedArchive` streams members from the zip with whole-file and per-member digest checks; the bounded-extraction helper is not built | Avoids a 1.8 GB cache and its invalidation; same safety guarantees. `VerifiedArchive` is library code whose non-test callers are `scripts/fixture_tools.py` now and snapshot ingest next | 01.6; 02.2; `src/necropsy/snapshot/archive.py` |
| D017 | 2026-10-13 | Defer the fact-register review | 01.7 is recorded `DEFERRED` and batched with the 05.7 Hunter-domain review | User asked to be interrupted only when needed; most facts are still oracle-only, so a review now would be repeated after analyzers verify them | 01.7, 05.7; `manual-actions.md` |
| D018 | 2026-10-13 | Page-boundary repeats are kept, schema as shipped | v0 keeps every page occurrence and flags same-timestamp repeats across page boundaries instead of removing them; table set consolidated (pets in `actors`, gear/talents/auras in `combatant_info`, buffs as event types, subject in `snapshot_meta`) | Content equality cannot distinguish a replayed page from genuine identical events (navigator CHALLENGE); fewer tables with JSON for nested combatant data is simpler and loses nothing | 02.3, 02.4, 02.5; `docs/database.md` |
| D019 | 2026-10-13 | Rules are package data | Rule files live in `src/necropsy/rules/<game>/*.yaml` and load via `importlib.resources`, not a top-level `rules/` directory | Must ship inside the wheel for the CLI and the future desktop sidecar; verified by installing the built wheel in an isolated venv | 03.2, 04.5, 05.1; spec §10 |
| D020 | 2026-10-13 | Faction fallback and fact checkers | When no faction field exists, rule `raid-class-faction-v1` INFERS faction from a Paladin-only or Shaman-only raid (validated on 80 fixture reports, mixed reports never used). Golden facts are verified only by registered checkers that compute them from the analysis database; analyzers are library code whose non-test caller arrives with `analysis.json` (05.5) | Two cohort Hunters have no faction field; the oracle's 63/12 split is reproduced with them INFERRED. Checker-backed verification keeps `verified-against-raw` honest | 03.2, 03.6, 05.5; `tests/golden/fact_checks.py`; `docs/evidence-model.md` |
| D021 | 2026-10-13 | Ranking damage rule | WCL-comparable damage = damage by the Hunter and every pet-linked actor to anything except the Hunter and its own pet-linked actors (`external-damage-v1`); encounter rules supply further exclusions | Checked on all 75 top-five rows: 64 exact without exclusions; every mismatch is on a boss whose adds WCL excludes (Faerlina, Razuvious, Anub'Rekhan, Gluth, Heigan). Pet classification does not change ranking damage | 04.5, 05.1, 05.2; `docs/hunter-analysis.md` |
| D022 | 2026-10-13 | Pet ability ranks not reported | Pets report spell IDs and names; rank numbers are not mapped | Neither Wowhead tooltips nor Petopia give an authoritative spell-ID→rank map; the golden fact is stated in spell IDs. Defer 04.8 to the batched 05.7 review | 04.5, 04.8; `hunter.yaml` |
| D023 | 2026-10-13 | Naxx ranking exclusions are empirical | Encounter rule `naxx-ranking-exclusions-v1` lists the adds WCL leaves out of ranked damage (Zombie Chow, Frenzied/Plagued Bat, Corpse Scarab, Naxxramas Worshipper, Death Knight Understudy), found by searching per boss for the exclusion set that reproduces the recorded ranked amounts | WCL does not document them; with the set, all 90 recorded fights match within 15 damage. Probe kept for re-validation | 05.1; `rules/classic_era/zones/naxxramas.yaml`; `tasks/necropsy/evidence/05-ranking-exclusions.py` |
| D024 | 2026-10-13 | Encounter data and baseline scope | Encounter rules hold only data an analysis consumes (ranking exclusions, native targets); phase, burst-window and pet-hazard data waits for an analyzer that uses it. Historical baseline B = same-faction entries of the recorded top five (≥3 known values, else UNKNOWN); outlier flags wait for the live 20–30 entry cohort | YAGNI: unconsumed rule data cannot be tested; a five-entry sample has no meaningful outliers | 05.1, 05.3, 07 |
| D025 | 2026-10-13 | Inactive pets | A pet-linked actor with no events caused or received in a fight, on trusted coverage, is `inactive` (`pet-inactive-v1`); a Hunter with no participating Hunter pet has Hunter-pet DPS 0, not UNKNOWN | Snape was listed but absent on Gluth/Heigan/Anub/Sapphiron; without this the pet-absent finding and the pet-DPS medians were unknowable. In 05.7 review | 05.4; `hunter.py::_inactive`; `benchmark.py::hunter_pet_dps` |
| D026 | 2026-10-13 | analysis.json size and references | Each evidence reference lists at most 10 event occurrences plus the full `event_count`; floats rounded to 6 digits, keys sorted. Full-export document ≈ 9.7 MB | Keeps the document renderable and diffable; the database holds every occurrence | 05.5; `docs/analysis-json.md` |
| D027 | 2026-10-13 | Inferred membership propagates | Same-faction selections are graded by `same-faction-membership-v1` (weakest faction proof among subject and members); inferred membership makes medians, projected shot-target ranges and the ceiling INFERRED and caps recommendation confidence; aggregates cite one reference per member | Two cohort factions are inferred (D020); aggregation must not upgrade them to confirmed. Navigator review finding | 05.3, 05.4; `benchmark.py::membership`; `docs/evidence-model.md` |
| D028 | 2026-10-13 | Unclassifiable targets and typed analysis.json | A damaged target without target ID, actor record or game ID makes the native/foreign split UNKNOWN (listed separately, no padding finding). analysis.json v1 types the envelope, headers, ceiling, findings and recommendations; free-form analysis sections keep their keys but every nested evidence object is validated. Ranking exclusions carry `basis: empirical`; a golden test keeps the 90/90 validation standing | Missing metadata is not proof of foreignness; the renderer (06) needs a real consumer contract; empirical rule validity must be visible in output | 05.2, 05.5; `targets.py`; `analysis_json.py`; `tests/golden/test_ranking_rules_full.py` |
| D029 | 2026-10-13 | Weave per target role | Raptor Strike adoption is judged separately on the boss and on every other hostile NPC (`weave-verdict-v2`, thresholds unchanged); unresolved targets make an entry's roles UNKNOWN. Replaces the single verdict; the oracle's Gothik "conditional" is expressed by per-role counts | User review 05.7: Gothik's top five weave only on adds, never on Gothik. Thresholds kept rather than tuned to an oracle label (navigator challenge) | 05.4, 05.7; `benchmark.py::raptor_roles`, `weave_adoption` |
| D030 | 2026-10-13 | Start trash | Encounter rules gain `start_trash` (Spirit of Naxxramas on Gothik): neither native nor foreign, reported separately, foreign share over all three | Present in the first ~50 s of all six recorded Gothik kills, the subject's included; user review 05.7 | 05.2, 05.7; `naxxramas.yaml` |
| D031 | 2026-10-13 | Tauren-only fill and deeper live cohort | When a same-faction median has fewer than 3 known values, a separate `tauren_fill` view recomputes it with other-faction entries proven Tauren and with Windfury proven absent; LOW confidence; never the ceiling, kill time or weave. Live mode pages past the top five for 3+ same-faction entries | User: Orc and Troll racials distort too much; go deeper in the list where possible | 05.3, 07.4; `benchmark.py::tauren_fill` |
| D032 | 2026-10-13 | Raid speed v2 | Flag basis is the same-faction median kill time (>=3 known, 1.5x), else the fastest same-faction kill (2.0x); both comparisons always in `analysis.json`; report UX for the secondary view is navigator-led | Grobbulus 1.57x of the fastest but 1.27x of the median; user prefers the median with the fastest shown separately and assigned UX/UI to Codex | 05.4, 06; `benchmark.py::raid_speed` |
| D033 | 2026-10-13 | Ranked damage by target | Every damaged target carries a ranking category (counted / excluded / own / unclassifiable); per boss, same-faction median share per counted target (>=3 known, membership graded) and the subject's share | User asked which mobs count toward the parse per boss | 05.5; `targets.py::RankedTarget`, `benchmark.py::ranked_target_shares` |
| D034 | 2026-10-13 | Navigator leads UI, UX and docs | Codex leads all UI/UX and documentation work — HTML report/playbook, CLI help and output wording, README, docs/, CHANGELOG and GitHub-facing material — and takes write ownership via handoff for UI/docs-only units; Claude reviews for code and evidence accuracy. Behaviour-changing code still ships its factual doc update in the same checkpoint | User: "super user friendly experience, layout and documentations ... Codex leads on those" | 06; all doc surfaces |
| D035 | 2026-10-13 | Package scope | The package holds report, playbook, exact analysis.json bytes, manifest (sha256 per member), CSV tables and per-boss evidence; it is named from numeric IDs only. Including the raw snapshot or the DuckDB file is deferred until a user needs it | Keeps the package small and avoids shipping raw logs; adding either later is a new opt-in member in `package.build_outputs` | 06.3; `docs/getting-started.md` |
| D036 | 2026-10-13 | Keyring backend allowlist | Credentials are read or written only through exactly one allowlisted OS credential backend instance selected from the keyring configuration by class identity (never through the chaining facade) (Windows Credential Locker, macOS Keychain, Secret Service, KWallet); null, fail, plaintext, file or unknown backends are refused before any access, and there is no file fallback. `keyring` is a runtime dependency under D005 | The keyring facade can silently pick an insecure backend; the exporter's file fallbacks must not be inherited (PM-1) | 07.2; `tasks/necropsy/pre-mortem.md`; [0001-personal-authentication](../docs/decisions/0001-personal-authentication.md) |
| D037 | 2026-10-13 | Bounded API pacing | The WCL client has finite retries, an overall deadline, capped jittered backoff, Retry-After support, typed errors never retried when permanent, page budgets with repeat detection, and no silent endpoint downgrade; unknown query cost stays unknown and an estimate above the hourly budget needs an explicit policy | Throttles or malformed pages must not hang the CLI or yield a silently incomplete cohort (PM-2) | 07.1, 07.4, 07.5; [0002-bounded-acquisition](../docs/decisions/0002-bounded-acquisition.md) |
| D038 | 2026-10-13 | Character context discovery | Only WCL hosts over HTTPS with exact path parsing; zone defaults to the supported zone from rule data (Naxxramas) and partitions come from the zone's own partition list; ambiguity is returned for the user to choose; faction is OBSERVED only from WCL's canonical faction name, otherwise UNKNOWN with the raw faction object kept (no ID table until a live check verifies one); UNKNOWN faction blocks same-faction selection | A wrong host/partition/faction would contaminate same-faction acquisition (PM-3) | 07.3, 07.4; [0002-bounded-acquisition](../docs/decisions/0002-bounded-acquisition.md) |
| D039 | 2026-10-13 | Definitive playbook is the visual template | The report and playbook will match the layout and look of the definitive playbook (box 06.8), replacing the earlier palette; the navigator owns the redesign and acquisition beyond 07.1–07.3 waits until it ships | User 06.6 verdict: "the latter is MUCH nicer UX/UI wise. I want to use that as template. it should look the same." | 06.6, 06.8; D034 |
| D040 | 2026-10-13 | Reference content with sourced general guidance | The definitive playbook is the content floor as well as the visual template. Snapshot observations and same-faction statistics remain separate from cited client/guide knowledge; general advice has named rules and visible conditions. Full overall cohort is always available as context without changing the primary baseline. Existing JSON additions are optional; ranking raw is reused without changing the DB schema | User: preserve EVERYTHING, add without taking away, and cite sources. Training costs/phase clocks and inferred WF matching require explicit limits | 06.8; parity inventory; analysis/playbook.py, guidance.py, gamedata.py |
| D041 | 2026-10-13 | Live cohort key and guild faction | The live cohort key records every comparison dimension as enforced, recorded or unknown: site, game (build unknown at selection), zone, partition, encounter, difficulty (hardModeLevel 0) and class Hunter and role dps are enforced; raid size is recorded (row size is attendance, not the format); spec is all Hunter specs because no spec filter is applied or verified. Ranking rows carry only the guild's faction, so `guild-faction-v1` (0 Alliance, 1 Horde; checked against the recorded fixture 36/36 and 7/7) gives INFERRED at best, an observed check overrides it, and unknown rows are never counted | Ranking rows have no character faction; a strict key must not silently broaden or pretend spec matching | 07.4; `wcl/cohort.py`; benchmarks.yaml `live_cohort`; [0002-bounded-acquisition](../docs/decisions/0002-bounded-acquisition.md) |
| D042 | 2026-10-13 | Acquisition cache generations | The acquisition cache is keyed site + report code + revision + fight and stores API data only. Every file (report bundle, event page, completion marker) is written to an owned temp, fsynced and published by a hard link that fails if the name exists, so readers see no file or the whole file and nothing published is ever replaced (identical bytes reused, different bytes CacheConflict, no hard links CacheUnsupported). Each bundle and stream is written under an OS advisory lock (msvcrt/fcntl) that the OS releases if the process dies; the next holder removes only that stream's unmarked pages and temps. The marker is published last, holds the canonical request identity (fetch-time data kept apart in `meta`) plus per-page SHA-256 and event counts, and is re-verified on every read. Each events page also carries the report revision and must equal the bundle's; a stream completes only on an explicit null cursor. Durability is what fsync plus link give on the filesystem in use; the directory entry is not fsynced everywhere | A resumed fetch must not mix revisions, replace completed data or certify truncated evidence (PM-4, PM-5, PM-2) | 07.5; `wcl/cache.py`, `wcl/fetch.py`; [0003-immutable-generations](../docs/decisions/0003-immutable-generations.md) |
| D043 | 2026-10-13 | Live subject fight and verified deep entries | The subject's fight per boss is its highest-amount Hunter ranking (ties: higher rankPercent, earlier startTime, missing after present, then code and fight; conflicting duplicate rows excluded) — rule `subject-fight-v1`, which reproduces the recorded export's choice on 15 of 15 bosses. Every deep entry (subject, cohort, optional cross-faction #1) is acquired as one generation — bundle, exact Hunter player actor by name and realm, observed faction from playerDetails combatantInfo.factionID, pets from the fight's friendlyPets, then player and pet streams — and a revision change restarts the whole entry once. An attempted check without an observed faction discards the guild inference; only observed same-faction entries count, replacements come from the same-faction metadata in order, and coverage counts completed entries (target 5 and minimum 3 kept apart) | A deep comparator must be the right person, faction and report generation, and a short cohort must say so | 07.5; `wcl/acquire.py`; benchmarks.yaml `subject_fight`; [0003-immutable-generations](../docs/decisions/0003-immutable-generations.md) |
| D044 | 2026-10-13 | Live snapshot v1 | A live snapshot keeps the v6 member layout for reports, events and rankings and replaces profile/manifest/selection with one strict `necropsy-snapshot.json` (subject from the resolved context, zone and partition, requested bosses with acquisition coverage, cohort key dimensions, verdicts and dropped rows, stream identities and page digests). Each report's bundle is one combined same-revision query over the exact selected fight set, fetched while finalizing acquisition; a revision mismatch refuses the snapshot. The reader reuses the v6 reader through two seams and never falls back to it for a malformed live descriptor. The derived DB schema moves to version 2 (mode, limitations, acquisition) and an older DB is rebuilt from the same verified archive. analysis.json mode is `historical` or `live` | Live data must reach the unchanged offline pipeline with its provenance and limits intact (PM-6, PM-7) | 07.6; `snapshot/v1.py`, `snapshot/v1_writer.py`, `wcl/acquire.py::finalize_reports`; [0004-snapshots-and-derived-outputs](../docs/decisions/0004-snapshots-and-derived-outputs.md) |
| D011 | 2026-10-12 | Tool installs approved | User approved all installs named in the plan: uv, git-lfs, secret scanner (gitleaks or equivalent), and LFS storage for the 80 MB fixture on the personal account | Explicit user approval in session | 00.7, 00.9, 01.3; `manual-actions.md` |

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
> **Human-owned boxes** are mirrored into `tasks/necropsy/manual-actions.md`
> so they don't get lost between agent-owned boxes. Keep the two in sync.
>
> **Done rule.** A subject is `DONE` when every box is `[x]` — except a
> human-owned box recorded `DEFERRED` (with rationale) in `manual-actions.md`,
> which stays `[ ]`, is annotated `DEFERRED — see manual-actions` in its
> subject file, and does not block subject closure. A deferred box is never
> ticked; it carries forward as an open item (e.g. 07.10 blocks distribution).
> Agent-owned boxes cannot be deferred this way; they need a §4 row and the
> abandoned format.

| Done | # | File | Status | Owner summary | Human actions mirrored? |
|---|---|---|---|---|---|
| [x] | 00 | `tasks/necropsy/00-tooling-research-and-readiness.md` | DONE | agent: 8; product-owner: 1 | yes |
| [x] | 01 | `tasks/necropsy/01-foundation-and-golden-fixture.md` | DONE | agent: 6; domain-sme: 1 | yes |
| [x] | 02 | `tasks/necropsy/02-snapshot-ingest-and-normalize.md` | DONE | agent: 6 | n/a |
| [x] | 03 | `tasks/necropsy/03-evidence-model-and-generic-analyzers.md` | DONE | agent: 6 | n/a |
| [x] | 04 | `tasks/necropsy/04-hunter-classic-era-plugin.md` | DONE | agent: 7; domain-sme: 1 | yes |
| [ ] | 05 | `tasks/necropsy/05-naxx-encounters-and-recommendations.md` | IN PROGRESS | agent: 6; domain-sme: 1 | yes |
| [x] | 06 | `tasks/necropsy/06-report-and-package.md` | DONE | agent: 6; product-owner: 2 | yes |
| [ ] | 07 | `tasks/necropsy/07-live-acquisition.md` | IN PROGRESS | agent: 8; product-owner: 1; release-engineer: 1 | yes |

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
2. ~~*(C#)* One class per file.~~ n/a — Python.
3. ~~*(C#)* Nullable reference types enabled.~~ n/a — Python; full type hints checked by the 00.4-selected type checker instead.
4. ~~*(.NET)* No new build warnings.~~ n/a — replaced by: ruff and the type checker report zero findings.
5. **Keep code modular and locally understandable.** Prefer small, cohesive modules with explicit boundaries. Split files before they become catch-all dumping grounds; split methods when branching, nesting, or mixed responsibilities make them hard to scan. If a file or method has to be large, record why and pin the coordinated behaviour with tests.
6. **Cyclomatic complexity stays low.** Branch-heavy methods are blockers unless the branching is inherent to the domain and covered by focused tests. Prefer guard clauses, extracted decision helpers, table-driven cases, or explicit strategy objects over deep `if`/`else`, nested `switch`, or boolean-flag flows. If the repo has a cyclomatic-complexity threshold, meet it; otherwise treat double-digit complexity in a method as design pressure to simplify.
7. **Spec at the contract level, not the SDK level.** State requirements as testable contracts on observable behaviour. Do not prescribe SDK call shapes — that's the implementer's choice. (Lesson from messaging plan: the spec said "one `SendAsync` per message" and the SB SDK couldn't honour the per-message error semantics implied. Three Decision-log amendments resulted. State *what* must be true, not *how* to call.)
8. **Coverage % is a smell-detector, not a goal.** A test exists to pin observable behaviour, not to chase a number. If you can't articulate "this test prevents future-X bug", delete it. Coverage gate failures should provoke "why is this code path untested?" — not "let's write a test that touches it". Architecture tests pin contracts; coverage gates flag gaps. Don't conflate them.
9. **Every plan box has an owner and a stable ID.** Owner from the §5 enum; ID `<subject-id>.<box-number>`. See §5.
10. **Lessons land in `tasks/necropsy/lessons.md` as they happen**, not at the gate — per-plan run-notes that die with the folder. Durable lessons migrate to the permanent `tasks/lessons.md` at §7.
11. **Code and public metadata are plan-agnostic.** Comments, test names, commit messages, branch names, PR titles, and identifiers must read as permanent project artefacts. Never reference the plan, slices, box IDs (`<subject-id>.<box-number>`), decision-log entries (`D###`), or this file — they vanish when the plan is deleted after go-live (see the Disposable note). A dangling `// see 03.2` or `// per Decision D007` becomes a broken reference in production. Put the *why* directly in the comment. (A durable design rationale belongs in an ADR, not a plan ref — see §4 ADR promotion.)
12. **Captain Hindsight review before subject close.** Before marking a subject `DONE`, run the subject's Hindsight checkpoint. Record Keep / Fix before closing / Record / Risk / Verdict in the subject file. A `DO NOT CLOSE` verdict is a blocker: add or reopen boxes, update §4 decisions, or append lessons before closing.
13. **Tooling research before implementation.** Every plan starts with subject `00 - Tooling Research And Readiness` unless explicitly waived in §4. No implementation subject starts until subject 00 records repo context, baseline verification, stack best practices, official sources, and any approved Skills/MCP/tooling setup. A waiver must explain why the research step is unnecessary or unsafe for this plan.
14. **All plans are resume-safe.** A checked box must be backed by a durable checkpoint: plan updates, verification note or blocker, commit, and push (no-remote exception per the Checkpoint gate). One checkpoint may cover several related boxes, but no box is ticked merely because work exists in an unpushed workspace.
15. **Parallelism is opt-in.** Start in `solo` unless multiple workers are known upfront. If the plan changes to `parallel`, add a §4 decision and fill the Parallel work tracker before concurrent subject work starts.
16. **Documentation ships with the change.** Every box runs a *documentation-impact review*: name which docs the change touches and update them in the *same* checkpoint, or record `n/a` with a one-line reason (in the Progress log, confirmed at the §7 gate). The trigger is broad — behaviour, architecture, commands, usage, configuration, setup, troubleshooting, or developer workflow. The scope is every doc a user *or* contributor relies on, not only user-facing ones: README, usage/setup guides and HOWTOs, CHANGELOG/release notes, API/command/config reference, architecture and design docs, developer-onboarding/contributor docs, troubleshooting/runbooks, examples, wiki pages, and prompt/skill docs. (Durable architecture *decisions* still graduate to an ADR per §4; this rule covers the prose docs around them.) Docs are a durable knowledge sink that survives the disposable plan folder (alongside ADRs and the permanent `tasks/lessons.md`); plan files are not the place for knowledge a future user or contributor needs. Update docs to match what *shipped*, never what was planned.
17. **Reuse and integrate before adding.** No implementation box starts until that subject's `## Integration analysis` records where the change belongs, what already exists, what is reused or extended, the chosen integration point and why, and whether it supports or conflicts with the project vision/ADRs. Prefer expanding, connecting, or refactoring existing code over new parallel code; new code is justified only when no existing surface fits. (Lesson: agents accrete duplicate code when they skip the prior-art check — see the 00.2 prior-art map and 00.1 vision review.) **Wire or delete:** new public surface (a function, endpoint, flag, command, or export) ships wired to a real non-test caller, or is explicitly disclosed as library-only/unwired — in the docs or a §4 decision — never as undisclosed dead surface a later cleanup-audit has to discover.
18. **Truth model is non-negotiable.** Every surfaced claim carries an evidence level (`OBSERVED` / `DERIVED` / `INFERRED` / `UNKNOWN`). Windfury is `CONFIRMED` / `NOT_OBSERVED` / `UNKNOWN`; race is named only from a structured field or racial-ability event. Absence claims require recorded coverage of the relevant stream; otherwise `UNKNOWN`.
19. **Same-faction by default; never silent substitution.** Cohort keys (game, zone, partition, encounter, size, class, WCL spec/category, role, faction) are never relaxed silently. Shortfall, inaccessible archive/private data, or partial streams yield an explicit partial-coverage result. Cross-faction data is opt-in, shown separately, never merged into same-faction medians.
20. **Controllability on every recommendation.** Each is classified player / gear-build / pet / raid assignment / raid speed-environment / faction-racial-external / RNG-low-confidence. Gaps are reported as observed gap + likely impact + confidence, never as a precise DPS gain.
21. **Raw is immutable; analysis is reproducible offline.** Raw WCL payloads are stored unchanged with hashes; everything after acquisition runs with no network. HTML is rendered only from `analysis.json`.
22. **Secrets never leave the keyring.** No client secret or user token in repo, fixtures, cache, logs, `analysis.json`, or export packages.
23. **Encounter knowledge ≠ class knowledge.** Class plugins and encounter plugins are separate modules; stable metadata (spell IDs, native targets, racials, pet abilities) lives in versioned rule files under `rules/`.
24. Pre-Mortem obligations live in tasks/necropsy/pre-mortem.md; every PM-* risk must have Plan refs and a non-Pending resolution before sign-off.

---

## 7. Gate review (run last; tick everything)

> Run only when §5 is fully ticked. §7 is the engineering gate the agent
> ticks; §8 is human acceptance that follows it.

- [ ] All §5 subjects done (or explicitly `ABANDONED` with a §4 row), applying the §5 Done rule for `DEFERRED` human boxes
- [ ] Subject 00 completed, or explicitly waived/abandoned with a §4 row
- [x] Build command from the §2 Verification-commands table passes with 0 errors and 0 new warnings (ruff + type checker clean)
- [ ] Fast and golden test commands from the §2 Verification-commands table pass; coverage gate met if the repo enforces one
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
- [ ] Shipped code/tests/comments/identifiers are plan-agnostic — grep the repo **excluding `tasks/`** for box IDs (`\b\d\d\.\d+\b`), decision IDs (`\bD\d{3}\b`), the literal `tasks/necropsy/`, the plan filename `Necropsy-Plan.md`, and `\bslices?\b`; zero hits after triaging false positives (version strings can match the box-ID pattern; "slice" may be a legit domain term). See §6.11
- [ ] Commit messages are plan-agnostic — `git log main..HEAD` mentions no box IDs, decision IDs, `tasks/necropsy/`, `Necropsy-Plan.md`, or `slice`/`slices` (apply the same false-positive triage; file grep does not cover commit messages)
- [ ] Branch names and public PR titles/descriptions are plan-agnostic if used
- [ ] `tasks/necropsy/manual-actions.md` — every human-owned box resolved or explicitly deferred
- [x] Run the `cleanup-audit` teardown review (whole-repo sweep) before sign-off, **or** waive it with a §4 Decision-log row (e.g. a sweep ran recently, or the repo is too young to have accrued cruft). Triage every finding: fix-now / fold into a *new* plan / won't-fix with a reason. Findings that warrant real work open a **new** plan — never this one, which is disposable and about to be deleted (see the Disposable note). Report-only: a non-empty report does not block sign-off, but an un-run (un-waived) or un-triaged audit does. Distinct from the per-subject Captain Hindsight checkpoints — this is the one whole-repo pass
- [x] `tasks/necropsy/lessons.md` reconciled; lasting lessons migrated to the permanent `tasks/lessons.md` (create it if missing) before the `tasks/necropsy/` folder is deleted (see Disposable note)
- [ ] **Historical-mode acceptance:** clean-clone replay of the full fixture produces a package against which the golden-fact register passes, where: (a) the set of `mandatory: true` facts is non-empty and covers at least every spec §11 fact plus one fact per boss; (b) every mandatory fact has status `verified-against-raw` and passes within tolerance; (c) every `oracle-only` fact is either promoted to `verified-against-raw` and passes, or carries a recorded exclusion reason; (d) every `disputed` fact carries a recorded `domain-sme` resolution (corrected value or exclusion). No fact passes silently by status alone
- [ ] **Live-mode acceptance:** `necropsy analyze https://vanilla.warcraftlogs.com/character/id/86583560` completes against live WCL, produces a same-faction package with recorded coverage, cohort provenance, and no silent faction/partition substitution
- [x] **Secret scan:** repo history, fixtures, and a generated package contain no client secret or token
- [ ] **PKCE distribution gate** (07.10) remains `[ ]` with status `DEFERRED` in manual-actions and is listed in §8 notes as an open blocker for any binary distribution
- [ ] If tasks/necropsy/pre-mortem.md exists, every PM-* risk has a terminal Resolution; Captain Hindsight calibration is recorded for every risk whose outcome is observable; unelapsed observation horizons are Inconclusive rather than false positives; every CH-MISS-* row has a future lesson.
- [ ] Plan handed to reviewer for §8 sign-off

Independent final-gate evidence, 2026-10-14: `uv build`, ruff check/format and
mypy passed. Fresh remote clone at `8aa4988` with full Git LFS fixture and locked
sync: `uv run pytest -m 'golden or acceptance'` passed 229 tests, with four
recorded expected failures and 791 deselected, in 353.81 seconds. This includes
registered raw-evidence facts, fact-register acceptance and full report/package
generation. Its actual four output artifacts and hashes are retained under
`workspace/clean-clone-replay-artifacts-20261014T1258Z/verification.json`.
Gitleaks redacted scans found no matches in repository history, fixture archives
(nested depth 2; about 2.13 GB expanded) or that generated package (about 43.77 MB
expanded). These are pattern-scan results, not proof against every possible secret;
the authenticated live package is checked separately by its acceptance harness.
Whole-repository cleanup findings are triaged in `cleanup-audit-2026-10-14.md`;
lasting lessons are in `tasks/lessons.md`. Live acceptance, subject close-out,
broader human mechanics review and §8 sign-off remain open.
Historical replay is verified, but the complete historical acceptance gate stays
open for explicit domain-sme resolution of `sapphiron.weave-verdict`: its current
exclusion cites the three-entry rule without human-review attribution. The other
three disputed fact resolutions already cite user review on 2026-10-13. Confirm
the remaining exclusion in the existing broader 05.7 review; passing the automated
register check does not replace the plan's human requirement.

---

## 8. Acceptance / sign-off

> Filled by the user or reviewer after §7 passes. This is intentionally
> separate from §4: sign-off is acceptance, not a spec amendment.

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
- If tasks/necropsy/pre-mortem.md exists, calibrate the PM-* risks relevant to this review target and append any unpredicted material failure as the next CH-MISS-*; do not rewrite the original prediction fields.
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
