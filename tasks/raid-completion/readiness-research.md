# Readiness research — 2026-10-16

## Starting state and constraints

Base is `30e89ce` on main with the documented uncommitted raid foundation.
`git status --short` matched the foundation inventory, including the new module,
rules, documentation and synthetic tests. No AGENTS.md or CLAUDE.md exists in
this checkout or C:/repos. CONTRIBUTING.md, the master and eight subjects,
coverage contract, boss inventory, risk register, prior raid receipt, class
taxonomy research, original Naxx encounter/content inventory, evidence model,
architecture, lessons and ADRs 0002/0005/0006/0012 establish these constraints:

- One production acquisition/cache/normalization/analysis/render/package path.
- Immutable raw captures; no golden refresh to make an analyzer agree.
- Category, metric, declared tree, observed build and duty remain independent.
- Unknown is null; whole-fight absence needs trusted coverage; medians need
  three known values; individual sparse examples remain useful.
- Old Naxx documents and historical/live archives remain readable. No in-place
  migration of saved outputs. Keep Naxx-only accepted evidence limits explicit.
- Public leaderboard/report fixtures are already authorized by project policy
  and prior owner instructions recorded in fixture provenance. Use only public
  sources for new committed captures; existing user-endpoint credentials do not
  authorize publishing private report content. Raw public names are identities,
  not anonymized data. Scan extracted members with unlimited file size.
- Preserve installed releases. Domain/product reviews are prepared on concrete
  artifacts; publication and final sign-off remain separate.

## Verified metadata, rather than inferred support

Fresh authenticated user-endpoint queries through `WclClient`, its existing
OS-store token provider and rate accounting produced the frozen sanitized
[metadata](research/metadata.json) and [schema](research/schema.json). Full probe
scripts/results are ignored under `workspace/raid-research/`.

Observed: all local encounter ID/name pairs match live metadata: MC 10, BWL 9
(including 50631), AQ40 9. All 19 local category IDs/names/slugs match the live
class catalog. The CSV contains 952 unique rows, 34 distinct legal configurations
per encounter, all TODO. Local ranking-policy validation accepts their metrics;
Paladin is Alliance-only and Shaman Horde-only. There are 27 declared trees.
This establishes catalog scope, not real-event acceptance for any row.

**Important ruleset finding:** all three zones expose partitions 1 S0, 2 S0
without world buffs, 3–6 Season of Mastery, and 7–11 Hardcore variants. Zone/site
identity alone cannot establish Era mechanic applicability. Initial new-domain
policies/captures must explicitly use Era partitions 1/2, retain buff partition
identity, and refuse unsupported partition assumptions. Existing Naxx archives
must not be reclassified or rejected by that new-domain guard.

Schema confirms characterRankings arguments className/specName/metric/partition,
plus a generic filter, with **no dedicated faction argument**. Use existing
local candidate filtering and observed report verification; do not invent one.
Report.events supports actor/direction/fight bounds, includeResources and
pagination via the existing client. Schema availability does not establish a
mechanic or a ranking exclusion.

Bounded availability probe: partition-1 Holy Priest HPS Lucifron and combined
dragons each returned 100 first-page rows; Viscidus Hunter DPS returned 100.
These are candidate sources only, not usable event captures. Therefore neither
Holy Priest scarcity nor combined-dragon unavailability can be assumed from the
old Naxx evidence gap. Three leaderboard calls plus metadata/schema cost only
a few points. Auth status was signed in using Windows WinVault public mode;
the first reading was 73/1800 points used, subsequent availability 76.15/1800.
Never record tokens. Keep normal 90% account ceiling and finalization reserve;
do not start an unbounded multi-hour capture sweep.

## Prior-art map and doc impact

| Concern | Extend existing implementation | Preserve |
|---|---|---|
| Raid identity/catalog | raids/__init__.py, model.py and module definitions; rules/classic_era/zones | URL/checkpoint/zone identities, strict selected-raid validation |
| Category/build/faction | analysis/class_catalog.py, taxonomy.py, roles.py; wcl/context.py and cohort.py | 19 actual pools, explicit Balance HPS, 27 independent declarations |
| Capture/resume | wcl/acquire.py, checkpoint.py, cache.py, client.py, snapshot/v1_writer.py | quota, endpoint, immutable generations, actor ownership and page proofs |
| Targets/windows | analysis/encounters/__init__.py, generic/targets.py, generic aura/event helpers | unknown target/coverage semantics; no Naxx exclusion inheritance |
| Static encounter knowledge | analysis/gamedata.py::encounter_facts and per-zone facts YAML | static knowledge is never observed timing |
| Advice | analysis/guidance.py and playbook.py; class plugin action sets | current Hunter advice is specialized, not an all-class contract |
| Class documents | report/combat.py, druid.py, analysis_json.py | optional compatible schema fields and production plugin callers |
| Views/package | report/render class components, package/export; desktop and tui library | both pages, source anchors, saved identity, offline behavior |
| Independent facts | tests/golden/facts.py and existing raw replay tests; scripts/fixture_tools.py | no production metric/recommendation call in expected arithmetic |
| Acceptance coverage | durable normal-source manifest + developer checker | separate implementation/synthetic/real/review states; never read tasks at runtime |

Doc surfaces: README/PACKAGE/CHANGELOG, docs/raids, class-analysis,
druid-analysis/validation, hunter-analysis, warcraft-logs/live-validation,
evidence-model, analysis-json + generated schema, architecture + ADR index,
desktop, getting-started, reading-results, installation/recovery, roadmap,
CONTRIBUTING, docs index, fixture provenance and developer checker usage.
Update affected surfaces with each behavior checkpoint. Historical design and
old acceptance receipts remain historical; do not overwrite their claims.

## Toolchain and baseline

Locked setup passes. Observed Python 3.14.6, uv 0.11.21, DuckDB 1.5.6,
Pydantic 2.14.1, httpx 0.28.1, pytest 9.1.1; Node 24.13.0/npm 11.20.0;
Git LFS 3.7.1; gitleaks 8.30.1. Existing React 19/Tauri 2/Vite 7 and Python
package metadata need no upgrade. Ruff check passes; format 249 files passes;
strict mypy 198 source files passes. Wheel/sdist build passes. Existing
acceptance register: 1 passed, 1477 deselected. Docs: 282 links/25 files pass.

`npm ci` initially failed EPERM because an already running checkout Vite
process holds esbuild. Did not terminate that process. Recovery using
`npm install --ignore-scripts --package-lock=false` restored tooling without
changing package metadata/locks; production build and format:check pass.
Re-run exact npm ci in an isolated frontend directory for locked verification.

Ordinary baseline is still running; record its final result before readiness
closes. A concurrent golden run was deliberately interrupted after several
passing checks so expensive raw replays run serially, consistent with the
existing lessons. Interrupted is not passed; re-run `uv run pytest -m golden`.
No runtime implementation subject is opened on this pending baseline.

Update: full initial baseline completed: 1192 passed, 35 failed, 251 deselected
in 439.01 s. Every failure was a BinderException for missing zone_id in two
miniature unit-test tables, despite that column existing in the production
schema. Corrected those fixtures without changing assertions or production
logic: 35 passed/1.15 s; Ruff/format/mypy pass. Context/installed-wheel 16 passed,
cross-raid acquisition/replay/render/library 31 passed, render subset 28 passed.
The affected baseline is repaired and supports implementation readiness; a
complete ordinary rerun is additionally in progress. Golden verification is
still required before changing shared measurement behavior and final closure.

Existing native probes accept an engine/executable positional argument;
window probe additionally supports --screenshots. Help was exercised, not the
native acceptance flow. Installed-rule test already builds/installs outside the
checkout and replays the bundled subset; extend this rather than adding a
second installation harness.

## Five-rung capability discovery and source review

1. Loaded skills/tools: readiness and pre-mortem adopted; embedded Hindsight
   available for checkpoints. Browser/Chrome/Windows tools exist if needed;
   repo-native Python Playwright is the ordinary browser regression route.
2. Inspected user .codex/skills, .agents/skills and plugin cache directories;
   no dedicated WCL/DuckDB acquisition capability found. Project has no skill
   directory; no repo-specific MCP integration was found.
3. Inspected trusted installed plugin roots (c0degeek-ai, openai-bundled,
   openai-curated[-remote], openai-primary-runtime) and c0degeek marketplace
   descriptor. Existing testing/browser tooling suffices.
4. Live callable tool inventory exposes connectors, browser/node, LocalMind,
   developer docs and web; no WCL or DuckDB MCP tools. LocalMind resources/list
   returned method-not-found: do not mistake a configured resource interface
   for a working one or rely on it for repository truth.
5. Concrete-name web searches performed for Warcraft Logs MCP/skill,
   Classic Era API MCP, DuckDB MCP, pytest skill/MCP, Playwright MCP. Candidates
   below were discovered, not installed or trusted by discovery alone.

| Candidate | Disposition, permissions, setup/cost and rationale |
|---|---|
| Existing WclClient/WinVault/cache/writer | Adopt; already configured; WCL user API using existing account; zero new setup. Production caller preserves quota/provenance. No tokens printed. |
| Existing DuckDB Python + pytest + Playwright | Adopt; uv sync --locked; local fixture/files and isolated Chromium; no new server or permissions. Tests use project markers and actual report pages. |
| [vinylflamingo/wcl-mcp](https://github.com/vinylflamingo/wcl-mcp) | Defer; third-party GraphQL bridge requiring WCL API application credentials and process setup. Duplicates validated auth/cache/quota path. No install command adopted. |
| [Nighthawk42/wow_api_mcp](https://github.com/Nighthawk42/wow_api_mcp) | Defer; npx -y @nighthawk42/wow-api-mcp; third-party addon API/docs and ~200 MB source checkout, not WCL encounter/ranking evidence. No installation or credentials granted. |
| [David-J-Shibley/wow-vanilla-mcp](https://github.com/David-J-Shibley/wow-vanilla-mcp) | Defer; third-party vanilla addon API documentation server; cannot verify modern WCL ranking semantics or observed encounters. External process setup has no justified benefit. |
| [DuckDB community MCP](https://duckdb.org/community_extensions/extensions/duckdb_mcp) | Reject for this task; external DB execution/server surface duplicates local SQL and broadens access. No extension install/LOAD performed. |
| [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | Defer; npx @playwright/mcp; browser process/site access, new server setup unnecessary beside installed Python browser tests. No new grants. |
| Search hits for generic pytest skills | Reject; no authoritative project-specific replacement found; pytest is already locked/configured. No install. |

Official/primary sources checked, with plan effects:

- [WCL API](https://www.warcraftlogs.com/v2-api-docs/warcraft/) and
  [Vanilla rankings](https://vanilla.warcraftlogs.com/help/ranks/): web fetches
  returned internal errors. Do not claim those pages were read. Authenticated
  live introspection supplies current API evidence; retain ranking-policy
  questions for independent raw reconciliation in 01/02 and each raid.
- Subsequently the [Encounter schema page](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/encounter.doc.html)
  loaded successfully. It documents mutable rankings and explicit partition
  selection (omission chooses latest), metric and class/spec slugs; generic
  filter syntax matches the website. It lists old covenant/soulbind arguments
  absent from current live introspection. Use live arguments; preserve dated
  responses and never equate HTTP success to filter enforcement.
- [BWL catalog](https://vanilla.warcraftlogs.com/zone/rankings/2002?metric=progress)
  separately lists individual and combined dragon encounters. Live partition-1
  combined Holy rankings are nonempty; do not combine individual fights or
  assume a matching duration/target policy.
- [pytest markers](https://docs.pytest.org/en/stable/how-to/mark.html): existing
  strict markers separate synthetic, golden, live and acceptance. A green
  register alone is not raw replay proof; retain separate commands in §2.
- [Playwright Python](https://playwright.dev/python/docs/test-runners): isolated
  browser contexts support offline deterministic behavior; use existing Python
  integration tests, not a new runner dependency. Record viewport/print/network
  checks and do not count skipped browser tests as acceptance.
- DuckDB official concurrency URL redirected without substantive content in
  the web tool. Existing project lessons independently require serialized large
  replays after an observed native failure; do not claim a new diagnosed cause.
- Blizzard's Classic primer is already cited by the verified taxonomy research;
  use its game catalog independently of freshly observed WCL category slugs.

## Executable follow-through

Implement normal-source `scripts/check_raid_coverage.py` in 01 with `--inventory`
and `--require-complete`; the inventory path reports gaps, while the strict path
must fail until all evidence/reviews exist. Its input must be a durable manifest,
not this disposable CSV. Add `tests/unit/test_raid_coverage.py` for missing,
duplicate, fake-complete and illegal cells; use the existing golden replay/fact
framework for raw arithmetic and mutation checks. Populate exact final commands
as their real interfaces are implemented, never silently replace a strict gate
with inventory exit 0. Existing fixture-tools manifests, snapshot readers and
gitleaks unlimited scans provide integrity/provenance checks.

Pre-mortem PM-1/2/3 remain credible after code inspection: empty fact/guidance
files confirm the content gap, current resolution accepts all returned partition
IDs, and old Holy fixture is budget-only. Preserve prediction fields; mitigation
is pending until guards/content/real independent evidence actually run.
