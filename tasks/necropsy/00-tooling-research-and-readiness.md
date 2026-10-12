# 00 — Tooling Research And Readiness

## Goal
Research the stack, official WCL API documentation, existing tooling, and the
read-only inputs (v6 exporter, raw export, definitive playbook) before any code
lands. Convert findings into concrete plan rules, gates, and commands.

## Boxes
> No implementation subject starts until this subject is `DONE`, `ABANDONED`,
> or waived by decision. A failing baseline from 00.3 blocks implementation
> subjects unless a §4 row accepts it.

- [ ] **00.1** (agent) Read `docs/origin/*`, the v6 exporter README, and the
      definitive playbook README; list constraints (truth model, same-faction
      default, offline reproducibility, secrets), the correction history
      (v1 → Alliance-normalized v2 → definitive), and the architectural
      direction so later subjects can flag drift.
- [ ] **00.2** (agent) Inventory the v6 exporter (`wcl_hunter_deep_export.py`,
      `wcl_auth.py`): GraphQL queries issued, export layout (`profile.json`,
      `manifest.json`, `selection.json`, `leaderboards/`, `user_rankings/`,
      `reports/`, `events/<code>/fight_<n>/<actor>/source_NNN|target_NNN.json`,
      `pets.json`), pagination, rate-limit handling, auth flows. Produce a
      prior-art map: reused verbatim / rewritten / dropped.
- [ ] **00.3** (agent) Smoke-install the exact proposed stack on Windows with
      CPython 3.14 via uv (duckdb, pydantic, typer, jinja2, httpx, keyring,
      pytest, ruff, type checker); run an empty pytest/ruff baseline; confirm
      or correct §2 commands. Fallback to 3.13 only with a new §4 row.
- [ ] **00.4** (agent) Research current best practices from primary sources:
      uv project layout + lockfile, pytest markers for fast/golden/live suites,
      DuckDB Python API (bulk JSON ingest), Jinja2 self-contained HTML, type
      checker choice. Record only plan-affecting findings.
- [ ] **00.5** (agent) Verify WCL v2 API facts against official docs: vanilla
      OAuth endpoints, `/api/v2/client` vs `/api/v2/user`, `rateLimitData`,
      `characterRankings` args/pagination, `Character.faction`, `gameData`,
      report `events` pagination, archive entitlement, PKCE support. Record
      links and access date.
- [ ] **00.6** (agent) Capability discovery, all five rungs, including web
      search on concrete names ("Warcraft Logs API python client", "warcraftlogs
      MCP server", "WoWAnalyzer", "WCL GraphQL schema"). Pick a secret scanner
      (e.g. gitleaks) and confirm `git lfs version`. Classify adopt/defer/reject
      with trust notes, URL, permissions, setup cost.
- [ ] **00.7** (agent) Set up only approved tooling (see 00.9). Anything adding
      credentials or network services goes through manual-actions. Record
      provenance; commit no secrets.
- [ ] **00.8** (agent) Bake findings into the plan (§2, §6, §7, boxes, §4,
      lessons); inventory doc surfaces (README, `docs/`, `docs/adr/`, CLI help,
      CHANGELOG). End with an implementation-readiness summary.
- [ ] **00.9** (product-owner) Approve installs that 00.6 classified `adopt`
      (uv, git-lfs, secret scanner) and confirm LFS storage on the personal
      GitHub account is acceptable for an 80 MB fixture.

## Hindsight checkpoint
> Run after all boxes are complete and before marking the subject `DONE`.
> Use the plan appendix prompt. Pair `VERDICT AGREE` precedes it.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
> One line per slice: date · slice # · box IDs · what shipped · how verified ·
> checkpoint commit/push status.
