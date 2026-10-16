# 00 - Tooling Research And Readiness

## Goal

Verify repository contracts, existing capabilities, official sources and baseline
before implementation. No AGENTS.md or project template override was found.

## Boxes

- [x] **00.1** (agent) Read repository instructions, vision and applicable ADRs/lessons.
- [x] **00.2** (agent) Inventory stack, verification and existing integration surfaces.
- [x] **00.3** (agent) Run baseline checks and confirm the verification commands.
- [x] **00.4** (agent) Research current stack guidance affecting this implementation.
- [x] **00.5** (agent) Verify GitHub release API and updater distribution contracts.
- [x] **00.6** (agent) Complete all five capability-discovery rungs and classify candidates.
- [x] **00.7** (agent) Use only already-approved tooling; record any setup.
- [x] **00.8** (agent) Bake findings, docs inventory and readiness into this plan.

## Findings and readiness

- Python 3.14/uv/Jinja/httpx; React 19/TypeScript/Vite/Tauri 2. Existing native
  shell remains unchanged in architecture; all new semantic work stays in Python.
- ADRs 0010/0011 require trusted rendering, allowlisted IPC, shared service and
  run locks, staged private-runtime installation and publish-before-switch.
- Existing GUI `report` operation already re-renders from validated analysis JSON.
  The new action persists outputs; it must not create or acquire another analysis.
- Checkpoint validates each owned output hash. Publisher already stages and rolls
  back files but is explicitly not crash-proof. Extend finalization rollback;
  do not silently weaken ownership validation or claim crash-proof transactions.
- Latest published release observed with `gh api repos/David-c0degeek/necropsy/releases/latest`:
  v0.3.1, stable, both installers, wheel/sdist, four GUI platforms and SHA256SUMS.
- Official sources: https://docs.github.com/en/rest/releases/releases and
  https://docs.github.com/en/rest/releases/assets establish public latest-release,
  uploaded asset names/sizes/digests and download URLs. https://v2.tauri.app/plugin/updater/
  requires updater signatures/artifacts not currently part of this distribution.
- Discovery: inspected loaded skills/tools, user/project/plugin skill directories,
  trusted local plugin registry directories, live ALL_TOOLS inventory and named
  web searches for Tauri updater/GitHub releases MCP/skills. Adopt existing CLI,
  httpx, Playwright and native smoke tooling: already configured, no new grants,
  credentials or install command. Defer Tauri updater plugin/signing migration
  and third-party updater skill (not installed; duplicates a different packaging
  workflow). Defer Tauri MCP server (new daemon/permissions unnecessary; native
  Playwright/CDP smoke tooling already exists). No new tooling setup is needed.
- Baseline: 27 desktop/launcher/bootstrap tests pass; npm build and format check
  pass; cargo fmt/clippy pass (21.82 s). Previous report work has documented fast
  suite verification. Required commands are in the master plan.
- Docs inventory: README, desktop guide, installation guide, architecture/ADR
  index and graphical-desktop decision. Existing reading-results/report content
  does not change analytical meaning.

## Hindsight checkpoint

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

Keep: reuse current engine, locks, publisher and installer distribution.
Fix before closing: none; baseline build/test commands passed.
Record: GUI rendering correction and updater-plugin deferral are master decisions.
Risk: installer and checkpoint failure boundaries need the planned negative tests.
Verdict: CLOSE; ready to implement with recorded guardrails.

## Progress log

2026-10-16 · 1 · 00.1-00.8 researched and baseline verified; checkpoint: this commit.
