# Readiness evidence

2026-10-14. Starting tree `main`, clean, Milestone A personally approved. The
existing pair session continues with Codex owning writes; Claude agreed the design
in mail 177 and is dormant until requested reviews. No notifier or subagents.

## Constraints and prior art

Read master/subject files, README, architecture, roadmap, origin specification,
ADR index and snapshot decision, previous review packet, and lasting lessons.
Keep one CLI → acquisition/cache → v0/v1 reader → schema-2 DuckDB → analysis JSON
→ report/playbook/package pipeline. No auth/distribution changes. Raw fixtures
and historical oracles are immutable. Human acceptance and real fixtures cannot
be replaced by synthetic checks. Exact build comparison applies when known;
missing role/category/build evidence cannot qualify an entry for a median.

Prior art: registry `analysis/classes/__init__.py`; `ParticipantFight` resolution;
coverage/evidence factories; environment profile; generic cast/death/target metrics;
benchmark entry and faction split; `wcl/context`, `cohort`, `acquire`, `fetch`;
v1 reader/writer; optional fields in strict analysis envelope; shared render
assets/templates and package publisher. `benchmark.analyze_entry` currently
bypasses the registry and creates Hunter analysis unconditionally. Report metrics,
JSON entry fields, recommendation/playbook/overview and exports assume Hunter.
Class actor verification and all ranking queries also assume Hunter DPS.

## Stack and verification

Python >=3.14, uv/uv_build locked in `uv.lock`, DuckDB, Pydantic v2, Jinja2,
HTTPX, Typer, keyring, PyYAML; pytest, Ruff, mypy, Playwright. Linux/Windows CI
runs `uv sync --locked`, Ruff check/format, mypy, non-golden/live/acceptance tests.
`uv build`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`
passed at baseline. Broad baseline tests started before code changes; result is
recorded in the subject log when complete. Included Hunter subset replay produced
four bosses and twelve recommendations at `workspace/hunter-before-druid` for
byte comparison. Golden checks use local LFS data; browser requires installed
Chromium. Never claim an unavailable secret scanner passed.

## Primary-source research and actual API observations

- [WCL v2 API](https://www.warcraftlogs.com/api/docs) remains authoritative;
  [Encounter schema](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/encounter.doc.html)
  exposes metric/className/specName. Enum existence does not prove support for a
  particular game category. Validate rows and preserve query dimensions.
- [Pydantic model compatibility](https://docs.pydantic.dev/latest/concepts/models/):
  retain strict envelopes, use optional additive class fields, regenerate schema;
  no blanket `extra=allow` relaxation. Existing archived Hunter fields remain valid.
- Existing approved authenticated client resolved supplied character 110733843:
  Haplina / Dragonfang / EU / Alliance / classID 2 / partition 1 (S0).
- Authenticated `gameData.class(id:2)` returned Druid specs: 1 Balance (`Balance`),
  2 Feral (`Feral`), 3 Tank (`Guardian`), 4 Healer (`Restoration`). WCL class IDs
  are not Blizzard class IDs. Do not guess category slugs from talent trees.
- Source/target All events already request resources. Incoming healing/damage,
  form auras and resources need analysis, not another acquisition subsystem.
- User supplied their own balance/restoration character for this task. No feral,
  tank or mixed-role fixture or domain adjudication has yet been supplied.

## Capability discovery (five rungs)

1. Loaded skill/tool inventory: use pair, tooling readiness and pre-mortem;
   existing first-party web/shell tools suffice. No WCL connector is exposed.
2. Installed user/project/plugin skill directories inspected: no WCL-specific
   acquisition/analyzer skill found; existing addon repair targets a different job.
3. Existing trusted plugin cache/registry inspected (bundled, curated, c0degeek).
   No adopted WCL service. No registry/permission edits required.
4. Live callable tool inventory inspected: GitHub/document tools, no WCL MCP.
   The repo's authenticated WCL client is already available and approved.
5. Named web search `Warcraft Logs MCP server skill GitHub` found
   [vinylflamingo/wcl-mcp](https://github.com/vinylflamingo/wcl-mcp): **defer**;
   third-party credentialed process, additional setup/trust/egress, duplicates
   existing client. No installation command executed (would require new auth and
   server setup). Retail API and TrinityCore MCP candidates: **reject**, wrong
   data/version/job. Existing repo client: **adopt**, already configured, zero
   install cost, credentials remain in approved OS store, bounded fixed endpoint.

## Executable consequences

Retain all five roles and explicit unknowns. Follow `pre-mortem.md` PM-1–PM-3;
negative cross-role tests and legacy byte replay are required gates. User docs to
update with behavior: README, CHANGELOG, docs index, getting-started, warcraft-logs,
architecture, roadmap, reading-results, analysis-json/schema, Druid guide,
developer contribution notes as applicable. Existing Hunter guide remains valid.
No new dependency/service/tool installation. Real-role acceptance and human
domain review remain open until evidence exists; missing evidence is never zero.
