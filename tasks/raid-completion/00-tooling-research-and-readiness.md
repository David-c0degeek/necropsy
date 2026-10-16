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

- [ ] **00.1** (agent) Read repo instructions and authoritative project docs —
      including any vision, ADR, roadmap, planning, and lessons docs; list
      applicable constraints, clean-room/provenance rules, existing conventions,
      and the intended architectural direction so later subjects can flag drift.
- [ ] **00.2** (agent) Inventory language, framework, runtime, package manager,
      CI, existing commands, and repo structure; identify the implementation
      surfaces this plan will touch and map where each belongs in the current
      architecture and what similar functionality already exists (prior-art
      map), so implementation subjects reuse or extend before adding new code.
- [ ] **00.3** (agent) Run baseline build/test/lint commands and confirm or
      correct the plan's §2 Verification-commands table, or record exact
      blockers and the command output needed to reproduce them.
- [ ] **00.4** (agent) Research current best practices for the detected
      language/framework/runtime/testing stack using official or primary
      sources; record only findings that affect this plan.
- [ ] **00.5** (agent) Research APIs, libraries, providers, or standards this
      plan depends on using official or primary sources; record links,
      versions, and date-sensitive notes.
- [ ] **00.6** (agent) Discover existing capabilities before building any. Run
      all five rungs, widest last: (1) skills, tools, and MCP servers already
      loaded this session; (2) installed-but-unloaded skill directories — user,
      project, and plugin-bundled; (3) the plugin/marketplace registry this
      machine already trusts; (4) the live MCP inventory (the running list, not
      the config file — a server can be configured and dead); (5) a web search,
      **on every run**, and on the *concrete name* whenever the plan touches a
      named product, format, service, or API (`<name> MCP server`, `<name>
      skill`, official docs) — never the generic category, which is what makes
      a real hit look absent. Classify each candidate `adopt`, `defer`, or
      `reject` with rationale, trust notes, source URL, permissions,
      install/config command, and setup cost. Record the result even when
      nothing is found; stopping at rung 1 is the default failure, not a
      finding.
- [ ] **00.7** (agent) Set up only approved local tooling/config needed before
      coding — approved means confirmed by the user or already allowed by
      project config; the `adopt` classification from 00.6 is a recommendation,
      not approval. Installing anything that adds credentials, network-reachable
      services (e.g. MCP servers), or repo-config permission grants needs a
      human-owned box mirrored into `tasks/raid-completion/manual-actions.md`. Record
      install/config/provenance; never commit secrets; keep security-sensitive
      permissions out of repo config unless narrowly justified.
- [ ] **00.8** (agent) Bake adopted findings into the plan: update the §2
      Verification-commands table, §6 cross-cutting principles, §7 gates,
      subject boxes, §4 decisions, and
      `tasks/raid-completion/lessons.md` as needed. Inventory the doc surfaces this plan
      will touch — user- and developer-facing alike (full scope in §6.16) — so
      later subjects update them in
      the same checkpoint as the change (§6.16). Research that changes no plan
      artefact is not complete; either bake in the finding or record why it was
      rejected/deferred. End with an implementation-readiness summary.

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

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/raid-completion/lessons.md` line here too whenever the slice taught something.

2026-10-16 · slice 1 · 00.1–00.8 · Preserved/reconciled dirty foundation on 30e89ce; inspected implementation seams, instructions, evidence/ADRs/lessons; fresh authenticated catalog/schema and bounded availability probes; all five discovery rungs; research in readiness-research.md and research/*.json. Full ordinary baseline 1192 passed/35 failed in 439.01 s; all 35 were missing zone_id in two miniature test databases, corrected and rerun 35 passed/1.15 s. No production behavior changed by repair. Additional selected-raid acquisition/snapshot/replay/render/library tests: 31 passed/16.77 s; context/installed-wheel: 16 passed/26.49 s; render subset 28 passed/20.79 s. Ruff/format/mypy/wheel/docs/desktop build/format pass; locked npm ci also passes in isolated workspace with shared CSS restored. Existing acceptance 1 passed. Golden run interrupted for serial scheduling, not passed. Complete ordinary rerun pending. Gitleaks source and plan scans pass, unlimited size. D003/D004 record findings; no new service/grant/dependency. Checkpoint pending; no implementation subjects started. Lesson: partition catalog includes incompatible rulesets, and score fixture schemas must retain zone identity.

## Plan-specific readiness outputs

- Establish a durable checkpoint for the dirty raid-foundation baseline without dropping or silently combining unrelated work. Preserve the previous turn's verification receipt; re-run the current baseline before declaring readiness.
- Inventory current class/ranking/role contracts, Naxx fact/oracle gaps, empty new facts files and generic-only new guidance. Reconcile 952 seed cells and all 28 WCL entries, including combined dragons, against live supported rulesets/partitions.
- Reconfirm allowed WCL credentials, quota budget, private/public source policy and fixture/LFS access using existing configuration. Do not install a new MCP/service or grant access as a side effect of planning.
- Verify capability discovery for concrete Warcraft Logs, Classic Era game data, DuckDB, pytest and Playwright names. Prefer existing clients/tools; recommendations are not installation approvals.
- Source research must distinguish Classic Era from seasonal/retail variants and static documented mechanics from log-observed events. Record dates/versions, uncertainties and which later boxes each finding changes.
- Add exact reproducible commands for independent fact checking, content parity and matrix completeness before readiness closes. No implementation starts with an unaccepted failing baseline.

## Readiness summary

Research and prior-art map: [readiness-research.md](readiness-research.md).
Metadata denominator verified: 952 rows/28 encounters/34 configurations,
19 category pools, 27 declared trees. Existing signed-in public user-endpoint
client and locked tooling adopted; all proposed external MCPs deferred/rejected.
No additional user credentials or permission required. Foundation baseline
failures repaired with targeted behavior verification; full ordinary rerun in
progress. Golden/raw acceptance must run serially. Readiness stays open until
commands, closing review and pushed checkpoint are reconciled.
