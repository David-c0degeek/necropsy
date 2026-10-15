# 00 — Tooling Research And Readiness

## Goal
Research the project stack, current best practices, official documentation,
assistant skills, MCPs, and local tooling before implementation starts. Convert
the findings into concrete plan rules, gates, enabled tools, and references so
later subjects can execute with the right context already in place.

## Boxes
> Subject 00 is required unless explicitly waived in the plan's §4 Decision log.
> No implementation subject starts until this subject is `DONE`, `ABANDONED`,
> or waived by decision. A failing Build/Test baseline from 00.3 blocks
> implementation subjects unless a §4 Decision-log row accepts it.

- [x] **00.1** (agent) Read repo instructions and authoritative project docs —
      including any vision, ADR, roadmap, planning, and lessons docs; list
      applicable constraints, clean-room/provenance rules, existing conventions,
      and the intended architectural direction so later subjects can flag drift.
- [x] **00.2** (agent) Inventory language, framework, runtime, package manager,
      CI, existing commands, and repo structure; identify the implementation
      surfaces this plan will touch and map where each belongs in the current
      architecture and what similar functionality already exists (prior-art
      map), so implementation subjects reuse or extend before adding new code.
- [x] **00.3** (agent) Run baseline build/test/lint commands and confirm or
      correct the plan's §2 Verification-commands table, or record exact
      blockers and the command output needed to reproduce them.
- [x] **00.4** (agent) Research current best practices for the detected
      language/framework/runtime/testing stack using official or primary
      sources; record only findings that affect this plan.
- [x] **00.5** (agent) Research APIs, libraries, providers, or standards this
      plan depends on using official or primary sources; record links,
      versions, and date-sensitive notes.
- [x] **00.6** (agent) Discover existing capabilities before building any. Run
      all five rungs, widest last: (1) skills, tools, and MCP servers already
      loaded this session; (2) installed-but-unloaded skill directories — user,
      project, and plugin-bundled; (3) the plugin/marketplace registry this
      machine already trusts; (4) the live MCP inventory (the running list, not
      the config file — a server can be configured and dead); (5) a web search,
      **on every run**, and on the *concrete name* whenever the plan touches a
      named product, format, service, or API (`all-classes MCP server`, `all-classes
      skill`, official docs) — never the generic category, which is what makes
      a real hit look absent. Classify each candidate `adopt`, `defer`, or
      `reject` with rationale, trust notes, source URL, permissions,
      install/config command, and setup cost. Record the result even when
      nothing is found; stopping at rung 1 is the default failure, not a
      finding.
- [x] **00.7** (agent) Set up only approved local tooling/config needed before
      coding — approved means confirmed by the user or already allowed by
      project config; the `adopt` classification from 00.6 is a recommendation,
      not approval. Installing anything that adds credentials, network-reachable
      services (e.g. MCP servers), or repo-config permission grants needs a
      human-owned box mirrored into `tasks/all-classes/manual-actions.md`. Record
      install/config/provenance; never commit secrets; keep security-sensitive
      permissions out of repo config unless narrowly justified.
- [x] **00.8** (agent) Bake adopted findings into the plan: update the §2
      Verification-commands table, §6 cross-cutting principles, §7 gates,
      subject boxes, §4 decisions, and
      `tasks/all-classes/lessons.md` as needed. Inventory the doc surfaces this plan
      will touch — user- and developer-facing alike (full scope in §6.16) — so
      later subjects update them in
      the same checkpoint as the change (§6.16). Research that changes no plan
      artefact is not complete; either bake in the finding or record why it was
      rejected/deferred. End with an implementation-readiness summary.

- [x] **00.9** (agent) Perform a change-specific pre-mortem before contract/auth/refactor work; persist retained original predictions, concrete box owners, gate obligations and the calibration check into this plan. If no material risk survives, record that verdict rather than creating an empty artifact.

## Hindsight checkpoint
> Run after all boxes in this subject are complete and before marking
> the subject `DONE` in §5. Use the embedded prompt in "Appendix: Captain
> Hindsight Prompt". Record the review result here. An interim run after
> a large or risky box is allowed and recorded the same way; it does not
> replace the closing run.
>
> Required output sections: Keep; Fix before closing; Record; Risk;
> Verdict (`CLOSE` or `DO NOT CLOSE`). If the verdict is `DO NOT CLOSE`,
> leave the subject open, add/reopen boxes or update decisions/lessons,
> and rerun this checkpoint after the fixes.

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/all-classes/lessons.md` line here too whenever the slice taught something.


## Readiness evidence — 2026-10-15

Python3.14/uv/DuckDB/Pydantic/Jinja/pytest/Playwright; no dependency or server added.
Existing entry paths, class registry, generic evidence/metrics, Druid event totals,
class-aware document/view/package seams and source-qualified execution component
are reused. No second acquisition or normalizer. Hunter legacy defaults remain.
README/architecture/roadmap/ADR0005/permanent lessons establish shared offline
pipeline, evidence-preserving unknowns and separated category/duty/assignment.

Baseline: uv build passed (wheel and sdist), ruff check/format and mypy passed;
88 context/cohort/execution tests passed; preceding Druid correction27focused and
16actual browser cases passed. The attempted nonexistent test_roles.py command
collected nothing; corrected baseline above passed. Prior full source CI ad833d8
passed Linux867/Windows868; current presentation source8425ce5 has separate CI.

Primary evidence: https://www.warcraftlogs.com/api/docs and
https://classic.warcraftlogs.com/v2-api-docs/warcraft/gameclass.doc.html plus
https://classic.warcraftlogs.com/v2-api-docs/warcraft/encounter.doc.html.
Authenticated vanilla gameData/classes returned all9 classes. Live Patchwerk51118,
partition1 first-page probes verified MageFire/Frost, PaladinHoly/Protection/
Retribution, PriestHoly/Shadow, RogueAssassination, ShamanElemental/Enhancement/
Restoration, WarlockDestruction and WarriorFury/Protection. Holy/RestorationHPS
queries return those labels; damage queries preserve corresponding categories.
Combat/Affliction/HunterSurvival filters returned zero rows; they are not invented
as supported ranking categories. The initial1118 encounter probe returned empty
rows; corrected to the pinned ClassicEra51118 and retained corrected receipts.
Raw metadata receipts: workspace/classic-era-{class-specs,ranking-probes,filter-probes}.json.
GameData localized DPS/Healer names are not accepted as ranking specName directly.

Capability discovery: loaded skill/tool catalog and live ALL_TOOLS inventory have
no WarcraftLogs MCP; installed user/project/plugin skills and trusted plugin
catalog contain no WCL acquisition skill. Existing repo bounded WclClient is
adopted. Name-specific web search found vinylflamingo/wcl-mcp (defer: unreviewed
external service duplicates the existing authenticated cache/client). No new tool
or permission setup needed. Official GraphQL schema and live probes are stronger
contract evidence than a new connector. No library upgrade is needed.

Pre-mortem PM-1/2/3 predictions are persisted before implementation, with concrete
owners and subject guardrails. Revert additive catalog/plugin/report changes for
rollback; raw archives are immutable. No new credentials/config/service.

## Captain Hindsight
Keep: existing pipeline/components; verified API labels and explicit talent-build
separation. Fix before closing: none for readiness. Record: corrected encounter
probe and nonexistent test-path invocation; no unsupported filters called supported.
Risk: remaining live role samples and product acceptance still require evidence.
Verdict: CLOSE for readiness; implementation and domain acceptance not implied.
