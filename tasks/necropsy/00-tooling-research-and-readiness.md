# 00 — Tooling Research And Readiness

## Goal
Research the stack, official WCL API documentation, existing tooling, and the
read-only inputs (v6 exporter, raw export, definitive playbook) before any code
lands. Convert findings into concrete plan rules, gates, and commands.

## Boxes
> No implementation subject starts until this subject is `DONE`, `ABANDONED`,
> or waived by decision. A failing baseline from 00.3 blocks implementation
> subjects unless a §4 row accepts it.

- [x] **00.1** (agent) Read `docs/origin/*`, the v6 exporter README, and the
      definitive playbook README; list constraints (truth model, same-faction
      default, offline reproducibility, secrets), the correction history
      (v1 → Alliance-normalized v2 → definitive), and the architectural
      direction so later subjects can flag drift.
- [x] **00.2** (agent) Inventory the v6 exporter (`wcl_hunter_deep_export.py`,
      `wcl_auth.py`): GraphQL queries issued, export layout (`profile.json`,
      `manifest.json`, `selection.json`, `leaderboards/`, `user_rankings/`,
      `reports/`, `events/<code>/fight_<n>/<actor>/source_NNN|target_NNN.json`,
      `pets.json`), pagination, rate-limit handling, auth flows. Produce a
      prior-art map: reused verbatim / rewritten / dropped.
- [x] **00.3** (agent) Smoke-install the exact proposed stack on Windows with
      CPython 3.14 via uv (duckdb, pydantic, typer, jinja2, httpx, keyring,
      pytest, ruff, type checker); run an empty pytest/ruff baseline; confirm
      or correct §2 commands. Fallback to 3.13 only with a new §4 row.
- [x] **00.4** (agent) Research current best practices from primary sources:
      uv project layout + lockfile, pytest markers for fast/golden/live suites,
      DuckDB Python API (bulk JSON ingest), Jinja2 self-contained HTML, type
      checker choice. Record only plan-affecting findings.
- [x] **00.5** (agent) Verify WCL v2 API facts against official docs: vanilla
      OAuth endpoints, `/api/v2/client` vs `/api/v2/user`, `rateLimitData`,
      `characterRankings` args/pagination, `Character.faction`, `gameData`,
      report `events` pagination, archive entitlement, PKCE support. Record
      links and access date.
- [x] **00.6** (agent) Capability discovery, all five rungs, including web
      search on concrete names ("Warcraft Logs API python client", "warcraftlogs
      MCP server", "WoWAnalyzer", "WCL GraphQL schema"). Pick a secret scanner
      (e.g. gitleaks) and confirm `git lfs version`. Classify adopt/defer/reject
      with trust notes, URL, permissions, setup cost.
- [x] **00.7** (agent) Set up only approved tooling (see 00.9). Anything adding
      credentials or network services goes through manual-actions. Record
      provenance; commit no secrets.
- [x] **00.8** (agent) Bake findings into the plan (§2, §6, §7, boxes, §4,
      lessons); inventory doc surfaces (README, `docs/`, `docs/adr/`, CLI help,
      CHANGELOG). End with an implementation-readiness summary.
- [x] **00.9** (product-owner) Approve installs that 00.6 classified `adopt`
      (uv, git-lfs, secret scanner) and confirm LFS storage on the personal
      GitHub account is acceptable for an 80 MB fixture. Approved upfront by
      the user on 2026-10-12 for uv, git-lfs, a secret scanner (gitleaks or
      equivalent), and LFS storage (D011). Any other tool 00.6 classifies
      `adopt` needs a new approval row in `manual-actions.md`.

## Findings

### 00.1 Constraints and direction
- Truth model: every claim carries OBSERVED / DERIVED / INFERRED / UNKNOWN; Windfury is tri-state; race only from a racial-ability event or a structured field (spec §1.4, §6; plan §6.18).
- Same-faction cohort by default; cross-faction opt-in, shown separately (spec §1.1, §5; plan §6.19).
- Class + WCL spec + role, never class alone; talent build is a second layer (spec §1.2–1.3).
- Recommendations are structured objects with controllability; never a precise DPS gain (spec §1.5, §7; plan §6.20).
- Raw WCL JSON kept immutable; analysis runs offline; HTML only from `analysis.json` (spec §2 step 7, §8; plan §6.21).
- No client secret in a distributed binary; PKCE for desktop (spec §2 step 2; D005).
- Correction history to respect: playbook v1 (overall top 5, Smcadogx as weave model) → Alliance-normalized v2 (lost layout) → **definitive** (v2 corrections + v1 layout). Only the definitive playbook is the report oracle. Its "Alliance comparator" is the best Alliance entry inside the downloaded overall top 5 (`D:\Parsing\Results\Playbook\README.txt`).
- Direction: Python analyzer core first, desktop shell later (spec §9); class plugins and encounter plugins separate (spec §3–4).
- No repo instructions (`CLAUDE.md` / `AGENTS.md`), ADRs, or lessons exist yet in the repo; `docs/adr/` is created when the first durable decision is promoted.

### 00.2 Inventory and prior-art map
Repo: `README.md`, `.gitignore`, `docs/origin/`, `docs/roadmap.md`, `tasks/` only — no code, no CI.

v6 exporter (`D:\repos\wcl_access_test\`, stdlib-only Python):

| Exporter piece | Fate in Necropsy | Lands in |
|---|---|---|
| GraphQL documents `PROFILE_QUERY`, `LEADERBOARD_QUERY` (`characterRankings`, `className: "Hunter"`, `includeCombatantInfo`), `USER_RANK_QUERY` (`encounterRankings`), `REPORT_QUERY` (fights, masterData actors/abilities, `playerDetails` with combatant info, `rankings`), `EVENTS_QUERY` (`dataType: All`, `limit: 10000`, `includeResources`), `RATE_LIMIT_QUERY`, `ARCHIVE_PROBE_QUERY` | Reuse the field selections; rewrite as parameterised documents (class/spec/role not hard-coded) | 07.1 |
| `export_actor_events` pagination: `nextPageTimestamp` → `startTime`, seen-guard, 300-page cap | Reuse logic | 07.5 |
| `WCL.gql` retry: 401 refresh, 429 `Retry-After`/backoff, 5xx/URLError exponential backoff, fixed 0.4 s pacing | Reuse retry semantics; replace fixed pacing with `rateLimitData`-driven pacing | 07.1 |
| Archive probe before the deep pass; archived-but-not-entitled recorded as an error, not silent | Reuse; becomes a coverage state | 02.5, 07.5 |
| `find_report_refs` (shape-tolerant ranking parser), `match_player_actor` (name + server) | Reuse as tested helpers | 02.2, 07.4 |
| `wcl_auth.py`: vanilla OAuth host, callback `http://localhost:8765/callback`, state validation, refresh, keyring service `warcraftlogs` / account `client:<id>` | Reuse; drop the `.wcl_secret` and `.wcl_user_token.json` file fallbacks | 07.2 |
| Selection model: overall top N by leaderboard position + the user's best rank per boss | Replaced by the same-faction selector; kept only as the historical-mode cohort definition | 05.3, 07.4 |
| Hard-coded character/zone/partition/class defaults, "upload to ChatGPT" prints | Drop | — |

Raw export facts (read-only scan, 2026-10-13): 89 selected fights in 85 reports; 90 participants (75 `top` + 15 `you`; one fight carries two); `effectiveAuthMode=user`; `errors=[]`; `rateLimitAtStart.limitPerHour=1800`. Event page files: player source 90, player target 153, pet source 291, pet target 490 (262 non-first pages); events total 1.74 GB.

Implications baked into the plan:
- **Coverage is actor-scoped.** Only the selected Hunter and actors with `petOwner = hunter` have streams. No raid-wide or boss streams, so threat, boss-target time, and raid composition are `UNKNOWN` in v0 (02.5, 03.3, §1 risk row).
- **"Pets" by `petOwner` include non-Hunter-pet actors** (Frost Trap, Battle Chicken, Skilled Bonesmith, Sheep, Vanquished Tentacle …). Pet forensics must classify hunter pet vs guardian/engineering summon vs trap object vs other (04.5).
- **Overlap sources for dedup:** self-targeted events appear in an actor's source and target streams; player→pet events (e.g. Mend Pet) appear in the player source and pet target streams (02.4).
- **Event schema must be explicit.** DuckDB `read_json_auto` inferred `targetID` as `HUGEINT` on a sample page; ingestion declares column types (02.3, D014).
- Events carry `targetIsFriendly`, which supports KT friendly-CC detection (05.2).

### 00.3 Baseline
- Repo has no code: build/test/lint baselines are `n/a` until 01.1 creates the project.
- **Stack smoke test** (not app code; scratch project only), 2026-10-13, Windows 11 Pro 10.0.26200, Git Bash:
  - Script: `tasks/necropsy/evidence/00-stack-smoke.sh`; full transcript: `tasks/necropsy/evidence/00-stack-smoke-transcript.txt`. Reproduce: `bash tasks/necropsy/evidence/00-stack-smoke.sh` from an empty scratch directory (the event-page test skips when `D:\repos\wcl_access_test` is absent).
  - Scratch location used for this review: `C:\Users\David\AppData\Local\Temp\claude\D--Parsing\ff309e1b-0157-43df-9693-d813f984547b\scratchpad\smoke` (ephemeral; the committed script is the durable record).
  - Pinned set: `duckdb==1.5.6 pydantic==2.14.1 typer==0.27.3 jinja2==3.1.6 httpx==0.28.1 keyring==25.7.0 pyyaml==6.0.3`; dev `pytest==9.1.1 ruff==0.17.0 mypy==2.4.0 respx==0.23.1 types-PyYAML`. Config: `[tool.mypy] strict = true`; pytest `addopts = "--strict-markers"` with markers `golden`, `live`.
  - Outcomes (all `exit=0`): `uv 0.11.21`; `uv init --package --python 3.14`; both `uv add`; `uv run pytest -q -s` → **3 passed** (versions probe: Python 3.14.6, keyring backend `WinVaultKeyring`; DuckDB `read_json` with declared columns read 245 events from a real page; `@pytest.mark.golden` accepted under strict markers); `ruff check .`; `ruff format --check .`; **`mypy src tests` under `strict = true` → no issues in 3 files**; `uv build`.
  - `uv.lock` sha256 `a61d3684b2bb6bb045c38629d9e08d001a9b1d59d9fec5631d0dd7328f7e7cfc` (resolution date-sensitive; recorded for this run only).
  - Finding: strict mypy failed on the first run with `Library stubs not installed for "yaml" [import-untyped]`; adding `types-PyYAML` fixed it. 01.1 adds it as a dev dependency.
- **D006 confirmed:** CPython 3.14 stays; no fallback needed.
- §2 Verification-commands table updated with the confirmed commands.

### 00.4 Best practices (plan-affecting only)
Sources accessed 2026-10-13.

| Practice | Plan effect | Primary source |
|---|---|---|
| uv packaged application: `uv init --package` (src layout + build backend), committed `uv.lock`, CI runs `uv sync --locked` | 01.1, 01.2, §2 Install | https://docs.astral.sh/uv/concepts/projects/init/ ; https://docs.astral.sh/uv/concepts/projects/sync/ ; verified by smoke run |
| Register markers and enforce `--strict-markers` so an unknown marker errors instead of silently selecting nothing | 01.1 (`golden`, `live` markers) | https://docs.pytest.org/en/stable/how-to/mark.html ; verified by smoke run |
| mypy `strict = true` in `pyproject.toml`; third-party packages without inline types need stub packages (`types-PyYAML`) | D012, 01.1 | https://mypy.readthedocs.io/en/stable/command_line.html ; https://mypy.readthedocs.io/en/stable/running_mypy.html ; smoke-run failure and fix |
| ruff for lint + format (one tool) | §2 Lint/format | https://docs.astral.sh/ruff/ |
| DuckDB `read_json` accepts an explicit `columns={...}` mapping instead of auto-detection | D014, 02.3 | https://duckdb.org/docs/stable/data/json/loading_json ; smoke run used declared columns |
| respx mocks httpx transports for client tests | 07.1 | https://lundberg.github.io/respx/ |

### 00.5 WCL API facts (official schema pages)
Source: `https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/{ratelimitdata,encounter,character,report,reporteventpaginator}.doc.html`, fetched 2026-10-13 with curl and a browser user agent (the WebFetch tool gets HTTP 403 from WCL's bot check).
- `RateLimitData { limitPerHour: Int!, pointsSpentThisHour: Float!, pointsResetIn: Int!, currentRequest: JSON! }`.
- `Encounter.characterRankings(bracket, difficulty, filter, page, partition, serverRegion, serverSlug, size, leaderboard, hardModeLevel, metric, includeCombatantInfo, includeOtherPlayers, className, specName, externalBuffs, …): JSON`. **No faction argument.** A `filter` string in site syntax exists; a faction filter through it is unverified, so the selector pages and discards (07.4). Rankings are documented as "not considered frozen … can change without notice", which supports D008.
- `Character.faction: GameFaction!` (non-null): subject faction is OBSERVED before cohort selection. `Character.gameData(specID, forceUpdate): JSON` returns only a cached Armory copy. `encounterRankings(…, includePrivateLogs, role: RoleType, specName, timeframe, compare, …)`.
- `Report.events(abilityID, dataType, death, difficulty, encounterID, endTime, fightIDs, filterExpression, hostilityType, includeResources, killType, limit 100–10000 (default 300), sourceID, sourceInstanceID, startTime, targetID, targetInstanceID, translate, useAbilityIDs, useActorIDs, viewOptions, wipeCutoff)`; `ReportEventPaginator { data: JSON, nextPageTimestamp: Float }`.
- `Report.revision: Int!` increases on re-export, so it is part of the cache key (07.5). `archiveStatus`: archived events need a subscription that includes archive access.
- OAuth/PKCE: the official `/api/docs` page sits behind human verification and could not be fetched. Third-party mirrors state a PKCE code flow exists for public clients. The v6 README proves vanilla-host OAuth (`/oauth/authorize`, `/oauth/token`, `/api/v2/user`) works with a confidential client. PKCE parameters stay **unverified** and are re-checked when 07.10 is executed (Milestone B).

### 00.6 Capability discovery
Accessed 2026-10-13. "Verdict" is a recommendation; installs need approval (00.7, D011). Search scope was limited to the queries and registries listed; a reject means the evaluated candidate does not meet Necropsy's needs, not that no alternative exists anywhere.

| Rung | Candidate | Source | Verdict | Setup cost / permissions / trust |
|---|---|---|---|---|
| 1 loaded | `c0degeek:pair-programming`, `plan-from-template`, `captain-hindsight`, `pre-mortem`, `cleanup-audit` | c0degeek plugin 2.10.0 (local) | adopt (in use) | Already loaded; no new permissions |
| 1 loaded | `frontend-design`, `dataviz` skills | claude-plugins-official (local) | adopt for 06 | Guidance only; no permissions |
| 1 loaded | MCP: Claude Docs, Exa, tui-mcp, Figma/Gmail/Drive and similar | session tool list | reject | Not WCL- or Python-analysis-specific |
| 2 installed skills | `~/.claude/skills` (c0degeek-ai, caveman, watermarks-remover, unraid), `~/.agents/skills/pair-programming`; c0degeek `wow-addon-repair` / `weakaura-repair` | local directories | reject | WoW addon Lua tooling, not log analysis |
| 3 trusted registry | `pyright-lsp` | `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/pyright-lsp` | defer | Needs a Node-based language server; editor convenience only; mypy owns the gate (D012) |
| 3 trusted registry | `playwright` (external plugin) / Playwright for Python | https://playwright.dev/python/docs/intro | defer to 06.5 | pip package + browser binary download (~100+ MB); local only; needs approval (06.7) |
| 3 trusted registry | `context7` (external plugin) | https://github.com/upstash/context7 | reject | Network-backed docs MCP; not needed |
| 4 live MCP | same as rung 1 | session tool list | reject | — |
| 5 web | `iRockyZhou/warcraftlogs-mcp` | https://github.com/iRockyZhou/warcraftlogs-mcp (0 stars, updated 2026-09-11) | reject | Unknown author; would receive WCL credentials; online-only use case |
| 5 web | `brunocardon/jack-warcraftlogs-mcp` | https://github.com/brunocardon/jack-warcraftlogs-mcp (0 stars, updated 2026-05-21) | reject | Same as above |
| 5 web | `go-wcl` | https://pkg.go.dev/github.com/math280h/go-wcl | reject | Go library; Necropsy is Python |
| 5 web | PyPI `warcraftlogs`, `warcraft-logs` | https://pypi.org/pypi/warcraftlogs/json , https://pypi.org/pypi/warcraft-logs/json → HTTP 404 | reject | Not published |
| 5 web | PyPI `wcl` | https://pypi.org/project/wcl/ (version 0.0.0, empty summary) | reject | Placeholder package |
| 5 web | WoWAnalyzer | https://github.com/WoWAnalyzer/WoWAnalyzer | reject | Retail-focused TypeScript analyzer; different game rules |
| tool | uv 0.11.21 | https://docs.astral.sh/uv/ | adopt | Already installed (`C:\Python314\Scripts\uv.exe`); no new permissions |
| tool | git-lfs 3.7.1 | https://git-lfs.com/ | adopt | Bundled with Git for Windows; LFS storage on personal GitHub approved (D011) |
| tool | gitleaks 8.30.1 | https://github.com/gitleaks/gitleaks (MIT, ~29.9k stars) | adopt | `winget install --id Gitleaks.Gitleaks -e`; publisher Gitleaks LLC; local CLI, no network service; heuristic scanner, not proof of absence |
| lib | respx 0.23.1 | https://pypi.org/project/respx/ ; https://github.com/lundberg/respx (BSD-3-Clause) | adopt (dev dependency, 07) | pip dev dependency only |
| lib | types-PyYAML | https://pypi.org/project/types-PyYAML/ | adopt (dev dependency) | Typeshed stubs; needed for mypy strict |

### 00.7 Setup performed
- gitleaks 8.30.1 installed via winget (user-approved, D011); `gitleaks` alias on PATH via WinGet Links.
- uv and git-lfs were already present; no MCP servers or repo-config permission grants added.
- Baseline scans: `gitleaks git C:\repos\necropsy --redact` → no leaks (3 commits). `gitleaks dir D:\repos\wcl_access_test --redact --max-target-megabytes 5` → 2 findings, both in `.wcl_user_token.json` (expected; that file is never copied). Export JSON files up to 5 MB had no findings; larger files and the zip are scanned after extraction in 01.3.

### 00.8 Plan updates and doc-surface inventory
Baked in: §2 commands (confirmed), §1 risk row for actor-scoped coverage, D012–D014, boxes 01.1 (strict markers, mypy strict + stubs, CHANGELOG), 01.3 (full-fixture secret scan), 02.3 (explicit schema), 04.5 (pet classification), 06.7 (Playwright approval), lessons (WCL docs fetch).
Doc surfaces later subjects must keep current: `README.md` (quickstart, clean-clone replay), `CHANGELOG.md` (created in 01.1), `docs/architecture.md`, `docs/adr/` (first ADRs from D002/D005/D008), `docs/analysis-json.schema.json` (05.5), `docs/auth.md` (07.8), CLI `--help` text, `tests/golden/haplina_naxx/PROVENANCE.md`, `docs/roadmap.md`.

### Implementation-readiness summary
- **Baseline:** no code yet; full stack smoke-tested green on CPython 3.14.6 / Windows 11.
- **Adopted:** uv, git-lfs, gitleaks, mypy (strict) + `types-PyYAML`, ruff, pytest with strict markers, respx (07).
- **Deferred:** Playwright (06.5; needs approval), pyright-lsp. **Rejected:** community WCL MCP servers, go-wcl, PyPI placeholders, WoWAnalyzer, context7.
- **Commands:** §2 Verification commands.
- **Risks:** actor-scoped coverage limits some analyses to `UNKNOWN`; PKCE details unverified (Milestone B); WCL docs need curl with a browser user agent.
- **Ready:** subject 01 can start once this subject closes.

## Hindsight checkpoint
> Run after all boxes in this subject are complete and before marking
> the subject `DONE` in §5. Use the embedded prompt in "Appendix: Captain
> Hindsight Prompt". Record the review result here. An interim run after
> a large or risky box is allowed and recorded the same way; it does not
> replace the closing run. In this coordinated pair plan, the navigator's
> `VERDICT AGREE` precedes the Hindsight run.
>
> Required output sections: Keep; Fix before closing; Record; Risk;
> Verdict (`CLOSE` or `DO NOT CLOSE`). If the verdict is `DO NOT CLOSE`,
> leave the subject open, add/reopen boxes or update decisions/lessons,
> and rerun this checkpoint after the fixes.

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

**Captain Hindsight — 2026-10-13 (after navigator `VERDICT AGREE round=2`)**

1. **Keep:** reproducible smoke evidence (`evidence/00-stack-smoke.sh` + transcript, exit codes, lock digest) independently re-run by the navigator; prior-art map tied to destination boxes; raw-export facts (actor-scoped coverage, `petOwner` noise, overlap sources, `HUGEINT` inference) converted into boxes 02.3, 02.4, 04.5 and a §1 risk row; capability table with sources and trust notes; PKCE gap disclosed rather than guessed.
2. **Fix before closing:** none blocking. Round 1 found missing reproducibility and sources; both fixed in slice 3.
3. **Record:**
   - Lesson: the subset fixture cannot be "< 25 MB" as plain JSON. Exporter JSON is pretty-printed: the planned subset (Patchwerk ×6, Grobbulus/Gothik/KT Haplina + rank 1) is ~290 MB raw but ~12.8 MB of compressed event entries in the original zip. 01.5 must store the subset as a compressed archive of the original bytes (budget measured compressed) — carried into the subject 01 huddle.
   - Lesson: the Windows console (cp1252) raised `UnicodeEncodeError` printing player names with non-ASCII characters during a read-only scan. The CLI must write UTF-8 regardless of console code page — carried into 01.1.
   - Verified by smoke run, not only by docs: strict mypy needs `types-PyYAML`.
4. **Risk:** PKCE parameters unverified (deferred, distribution-only); gitleaks is heuristic, so the full-fixture scan in 01.3 is a gate, not proof; WCL rankings mutate (D008).
5. **Verdict:** CLOSE

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
2026-10-12 · slice 1 · 00.9 · user approved uv, git-lfs, secret scanner and LFS storage (D011) · recorded in manual-actions · committed with the plan template-conformance fix
2026-10-13 · slice 2 · 00.1–00.8 · research, stack smoke test, gitleaks install, prior-art map, API facts, capability discovery, plan updates · smoke run and gitleaks scans recorded in Findings · commit pending pair review
2026-10-13 · slice 3 · 00.3, 00.4, 00.6 · review round 1 fixes: reproducible smoke script + transcript in `evidence/`, strict mypy proven (stub finding), primary-source links, setup/trust columns · smoke rerun all exit=0 · commit pending pair review
2026-10-13 · slice 4 · Hindsight · navigator AGREE round 2; Hindsight CLOSE recorded; §5 row 00 DONE · lessons appended · committed and pushed
