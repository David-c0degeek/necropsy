# 00 - Tooling Research And Readiness

## Goal
Establish a trustworthy starting point: stable hardware, a green baseline on the
current main, a measured local-runner trial, an inventory of every existing Naxx
asset and evidence, and a pre-mortem whose guardrails are mapped into the plan.

## Boxes
- [ ] **00.1** (product-owner) XMP disabled in BIOS (memory at JEDEC speed), machine restarted; memtest result if run. Mirrored in `manual-actions.md`.
- [ ] **00.2** (agent) Baseline on main at the start commit: `uv sync --locked`, lint/types, ordinary suite, Naxx golden and browser controls. Record the exact Naxx-compatibility commands into §2 (legacy/live replays, saved-output byte checks, package test).
- [ ] **00.3** (agent) Hardware check: the full seed gate at `NECROPSY_GATE_WORKERS=8`, three runs, after 00.1. Clean in 3 of 3 sets the default back to 8 (§4 row); any failure keeps 4 and is recorded with logs, never overridden by a later pass.
- [ ] **00.4** (agent) Local runner trial. `localbox serve` the Qwen3.6 35B-A3B APEX-I-Quality tune; run one real work order through LocalPilot headless (proposal: rewrite one existing MC raw-discovery count as a templated script whose output is checked against a frozen MC fact). Record command lines, wall time, tokens, verifier result, and whether the model stayed inside `workspace/naxx-drafts/`. Record the GPU/RAM load next to a gate run (00.3 conflict check).
- [ ] **00.5** (agent) Naxx inventory: zone 2006 encounters and WCL encounter IDs; which configurations already have real archives (haplina_naxx, druid, classes) and whether each is full-raid, partition and faction; existing Naxx guidance (8 bosses) and facts (15); every place that treats Naxx specially (`encounter_strategy` returns None for Naxx; others found by search). Write `tasks/naxx-completion/inventory.md`.
- [ ] **00.6** (agent) Pre-mortem for the plan (scope: register/strategy seam, local work orders, capture queue). Create `pre-mortem.md` from retained PM-* risks and map each guardrail to boxes.
- [ ] **00.7** (agent) Partition decision: partition 1 only, or 1 and 2 as separate cell sets; §4 row with the WCL availability evidence.
- [ ] **00.8** (agent) Readiness summary and pair DESIGN_AGREED on the plan before 01 starts.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
