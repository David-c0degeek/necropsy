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
- [x] **00.9** (product-owner) Approve installs that 00.6 classified `adopt`
      (uv, git-lfs, secret scanner) and confirm LFS storage on the personal
      GitHub account is acceptable for an 80 MB fixture. Approved upfront by
      the user on 2026-10-12 for uv, git-lfs, a secret scanner (gitleaks or
      equivalent), and LFS storage (D011). Any other tool 00.6 classifies
      `adopt` needs a new approval row in `manual-actions.md`.

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

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
2026-10-12 · slice 1 · 00.9 · user approved uv, git-lfs, secret scanner and LFS storage (D011) · recorded in manual-actions · committed with the plan template-conformance fix
