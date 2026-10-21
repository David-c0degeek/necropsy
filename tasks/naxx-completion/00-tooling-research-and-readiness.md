# 00 - Tooling Research And Readiness

## Goal
Establish a trustworthy starting point: stable hardware, a green baseline on the
current main, a measured local-runner trial, an inventory of every existing Naxx
asset and evidence, and a pre-mortem whose guardrails are mapped into the plan.

## Boxes
- [x] **00.1** (product-owner) XMP disabled in BIOS (memory at JEDEC speed), machine restarted; memtest result if run. Mirrored in `manual-actions.md`.
- [x] **00.2** (agent) Baseline on main at the start commit: `uv sync --locked`, lint/types, ordinary suite, Naxx golden and browser controls. Record the exact Naxx-compatibility commands into §2 (legacy/live replays, saved-output byte checks, package test).
- [x] **00.3** (agent) Trusted baseline (D004), after 00.1: three full seed gates at `NECROPSY_GATE_WORKERS=8`, three serial `check_raid_coverage --inventory` runs, and the CI fast suite, each with command, exit status and full log kept. Every failure is classified (assertion vs suspected corruption/native crash) and recorded; none is overridden by a later pass. All clean: baseline trusted, default workers back to 8 (§4 row). Any suspected-corruption failure: no Naxx evidence work on this host until the owner's next hardware step; ordinary failures are fixed as defects.
- [ ] **00.4** (agent) Local runner trial. `localbox serve` the Qwen3.6 35B-A3B APEX-I-Quality tune; run one real work order through LocalPilot headless (proposal: rewrite one existing MC raw-discovery count as a templated script whose output is checked against a frozen MC fact). Record command lines, wall time, tokens, verifier result, and whether the model stayed inside `workspace/naxx-drafts/`. Record the GPU/RAM load next to a gate run (00.3 conflict check).
- [x] **00.5** (agent) Naxx inventory: zone 2006 encounters and WCL encounter IDs; which configurations already have real archives (haplina_naxx, druid, classes) and whether each is full-raid, partition and faction; existing Naxx guidance (8 bosses) and facts (15); every place that treats Naxx specially (`encounter_strategy` returns None for Naxx; others found by search). Write `tasks/naxx-completion/inventory.md`.
- [x] **00.6** (agent) Pre-mortem for the plan (scope: register/strategy seam, local work orders, capture queue). Create `pre-mortem.md` from retained PM-* risks and map each guardrail to boxes.
- [ ] **00.7** (agent) Partition decision: partition 1 only, or 1 and 2 as separate cell sets; §4 row with the WCL availability evidence. A separate partition 2 scope changes the denominator and needs the partition in the cell identity (current keys omit it).
- [ ] **00.8** (agent) Readiness summary and pair DESIGN_AGREED on the plan before 01 starts.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-21 · 00.1 · Owner rebooted with XMP off (boot 11:54 CEST). Verified with Win32_PhysicalMemory: four F4-3600C16-16GTZNC modules at ConfiguredClockSpeed 2133. No memtest run.
2026-10-21 · 00.2 (partial) · At cc637a7: `uv sync --locked`, `ruff check .`, `ruff format --check .` (339 files), `mypy` (273 files) all exit 0. Naxx golden, browser controls and the compatibility commands for §2 remain.
2026-10-21 · 00.2 · Naxx compatibility at 34bf7ea: golden without test_raid_evidence on 8 workers 460 passed, 4 xfailed, 2 errors; browser 90 passed, 2 errors; acceptance 1 passed. Both errors were the same ordinary assertion in the `paladin_site` fixture (`tests/browser/test_paladin_capture_browser.py`): it asserted no subject `exposure_removal_correlations`, which 7930e66 deliberately added for Lucifron (golden expects Resurgance [49976, 52266, 2290, 4987]). The fixture went stale because no gate runs the browser suite when only rules change. Fixed: the fixture now requires exactly that Lucifron pair and none elsewhere; 2 passed. Commands recorded in §2.
2026-10-21 · 00.3 · Trusted baseline at cc637a7, run sequentially by `workspace/naxx-baseline-20261021/run_baseline.sh`; every command, exit, HEAD, UTC start/end and full log kept there. Seed gate (`uv run pytest -m "not live" tests/golden/test_raid_evidence.py -k seed_capture -n 8 --dist worksteal -rfE`) ×3: 52 passed each, exit 0. Serial `check_raid_coverage.py --inventory` ×3: exit 0, logs byte-identical (sha256 af74bb04dfd0), 26 COMPLETE, problems []. CI fast suite: 2559 passed, 29 skipped, exit 0. No failure to classify. Baseline trusted (D006).
2026-10-21 · 00.5 · `inventory.md`: 15 encounters, 17 v1 Naxx archives (partition 1), guidance gaps, and the missing encounter context for zone 2006. Added box 01.5.
2026-10-21 · 00.6 · `pre-mortem.md`: PM-1 to PM-5, verdict PROCEED WITH GUARDRAILS.
