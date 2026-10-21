# 00 - Tooling Research And Readiness

## Goal
Establish a trustworthy starting point: stable hardware, a green baseline on the
current main, a measured local-runner trial, an inventory of every existing Naxx
asset and evidence, and a pre-mortem whose guardrails are mapped into the plan.

## Boxes
- [x] **00.1** (product-owner) XMP disabled in BIOS (memory at JEDEC speed), machine restarted; memtest result if run. Mirrored in `manual-actions.md`.
- [x] **00.2** (agent) Baseline on main at the start commit: `uv sync --locked`, lint/types, ordinary suite, Naxx golden and browser controls. Record the exact Naxx-compatibility commands into §2 (legacy/live replays, saved-output byte checks, package test).
- [x] **00.3** (agent) Trusted baseline (D004), after 00.1: three full seed gates at `NECROPSY_GATE_WORKERS=8`, three serial `check_raid_coverage --inventory` runs, and the CI fast suite, each with command, exit status and full log kept. Every failure is classified (assertion vs suspected corruption/native crash) and recorded; none is overridden by a later pass. All clean: baseline trusted, default workers back to 8 (§4 row). Any suspected-corruption failure: no Naxx evidence work on this host until the owner's next hardware step; ordinary failures are fixed as defects.
- [x] **00.4** (agent) Local runner trial. `localbox serve` the Qwen3.6 35B-A3B APEX-I-Quality tune; run one real work order through LocalPilot headless (proposal: rewrite one existing MC raw-discovery count as a templated script whose output is checked against a frozen MC fact). Record command lines, wall time, tokens, verifier result, and whether the model stayed inside `workspace/naxx-drafts/`. Record the GPU/RAM load next to a gate run (00.3 conflict check).
- [x] **00.5** (agent) Naxx inventory: zone 2006 encounters and WCL encounter IDs; which configurations already have real archives (haplina_naxx, druid, classes) and whether each is full-raid, partition and faction; existing Naxx guidance (8 bosses) and facts (15); every place that treats Naxx specially (`encounter_strategy` returns None for Naxx; others found by search). Write `tasks/naxx-completion/inventory.md`.
- [x] **00.6** (agent) Pre-mortem for the plan (scope: register/strategy seam, local work orders, capture queue). Create `pre-mortem.md` from retained PM-* risks and map each guardrail to boxes.
- [x] **00.7** (agent) Partition decision: partition 1 only, or 1 and 2 as separate cell sets; §4 row with the WCL availability evidence. A separate partition 2 scope changes the denominator and needs the partition in the cell identity (current keys omit it).
- [x] **00.8** (agent) Readiness summary and pair DESIGN_AGREED on the plan before 01 starts.

## Readiness summary (00.8)

- **Host:** trusted at 2133 MT/s JEDEC (D004, D006). Seven baseline runs and two later full gates
  passed; a suspected-corruption failure reopens D004.
- **Baseline:** main at 61cdb30 is pushed and green (`pre_review.py --full`, 8 workers). Naxx
  compatibility commands are in §2; one stale browser fixture was fixed (7ad535d).
- **Scope:** partition 1, 15 bosses × 34 configurations = 510 cells (D008). Partition 2 is a
  separate extension.
- **Largest gap:** Naxx has no encounter context (`inventory.md`). Box 01.5 adds it, gated on the
  archive's v2 encounter streams and in `duty.applies` itself; v1 output stays byte-identical
  (PM-1). Captures wait for that release (PM-2). Existing v1 archives stay reusable where 01.1
  accepts them.
- **Seats:** Claude owns and writes; Codex reviews and builds independent oracles, partition and
  quota evidence and leads UI/UX (D007). The local runner failed the raw-discovery trial 0 of 3,
  so raw discovery stays with Claude; it gets one guidance-draft trial in 02.3 (D009).
- **Quota:** no bound yet. The first normal v2 capture measures a short fight and one of the
  Four Horsemen, Gothik or Kel'Thuzad before the bulk queue (03.1).
- **Risks:** PM-1 to PM-5 (`pre-mortem.md`), verdict PROCEED WITH GUARDRAILS. PM-3 has an
  oracle contract (`research/oracle-design.md`).
- **Next:** 01.1 (Naxx in raid scope, 952 → 1462 cells), 01.5 (encounter context), then 01.2 to
  01.4.

## Hindsight checkpoint
- [x] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

### Captain Hindsight, 2026-10-21 (cc637a7..56fa625)

- **Keep:** the trusted baseline with every log kept; the narrowed inventory; D007 to D009 recorded with evidence; research promoted byte-exact with hashes; the local-runner trial bounded by an independent verifier and a tree hash. Verification cited: `workspace/naxx-baseline-20261021/summary.tsv`, `pre-review-full-3.log` (PASS at 61cdb30, pushed).
- **Fix before closing:** the reviewer's verdict and DESIGN_AGREED on 5e1f3ca and 56fa625 (00.8 requires it).
- **Record:** five lessons in `lessons.md` (plan references in three commit bodies; browser suite outside the gate; no commits during a gate; per-dimension evidence claims; local-runner result). PM-4 and PM-5 calibrated and CH-MISS-1 added in `pre-mortem.md`. No human action pending: 00.1 done, LocalPilot grants removed.
- **Risk:** host stability rests on an operational baseline, not a root cause. Quota cost is a scenario until the first v2 Naxx capture measures it. No shipped behaviour changed except one test fixture; no user docs drifted.
- **Verdict:** DO NOT CLOSE until the reviewer agrees; then CLOSE with no further action.

## Progress log
2026-10-21 · 00.1 · Owner rebooted with XMP off (boot 11:54 CEST). Verified with Win32_PhysicalMemory: four F4-3600C16-16GTZNC modules at ConfiguredClockSpeed 2133. No memtest run.
2026-10-21 · 00.2 (partial) · At cc637a7: `uv sync --locked`, `ruff check .`, `ruff format --check .` (339 files), `mypy` (273 files) all exit 0. Naxx golden, browser controls and the compatibility commands for §2 remain.
2026-10-21 · 00.2 · Naxx compatibility at 34bf7ea: golden without test_raid_evidence on 8 workers 460 passed, 4 xfailed, 2 errors; browser 90 passed, 2 errors; acceptance 1 passed. Both errors were the same ordinary assertion in the `paladin_site` fixture (`tests/browser/test_paladin_capture_browser.py`): it asserted no subject `exposure_removal_correlations`, which 7930e66 deliberately added for Lucifron (golden expects Resurgance [49976, 52266, 2290, 4987]). The fixture went stale because no gate runs the browser suite when only rules change. Fixed: the fixture now requires exactly that Lucifron pair and none elsewhere; 2 passed. Commands recorded in §2.
2026-10-21 · 00.3 · Trusted baseline at cc637a7, run sequentially by `workspace/naxx-baseline-20261021/run_baseline.sh`; every command, exit, HEAD, UTC start/end and full log kept there. Seed gate (`uv run pytest -m "not live" tests/golden/test_raid_evidence.py -k seed_capture -n 8 --dist worksteal -rfE`) ×3: 52 passed each, exit 0. Serial `check_raid_coverage.py --inventory` ×3: exit 0, logs byte-identical (sha256 af74bb04dfd0), 26 COMPLETE, problems []. CI fast suite: 2559 passed, 29 skipped, exit 0. No failure to classify. Baseline trusted (D006).
2026-10-21 · 00.4 · Local-runner trial, work order `workspace/naxx-drafts/00.4-trial/WORK_ORDER.md` (Lucifron Impending Doom and Curse applydebuff counts with locators for six contexts of the mc-holy-paladin-raid-context archive, expected values withheld), verifier `workspace/naxx-drafts/verify_00_4.py` against `tests/golden/raids/lucifron-presence-facts.json`; a reference implementation passes it. Model Qwen3.6-35B-A3B APEX-I-Quality (`localbox serve q3635ba3bapex`, 21.3 GB download), `localpilot localbox adopt` in the trial folder, then `localpilot print --model Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Quality.gguf --permission relaxed --allow-writes`. Attempt 1: run_shell denied, 69 tool calls, 325 s, script guessed the layout and errors. Attempt 2, with two exact `allow_commands` grants in the user config (since removed; backup restored): 109 tool calls, stopped at LocalPilot's 600 s cap, 72 of 72 values missing. Attempt 3, with verified layout excerpts added to the order: 76 tool calls, 601 s cap, invented event fields, empty output. Verifier: 0 of 3 PASS. The model stayed inside the folder; HEAD, porcelain status and diff hash identical before and after. `print` does not report tokens. Load next to the full gate: GPU 23.6 of 24.5 GB VRAM, 99 %; RAM 46 of 64 GB free; CPU 47 %; the gate passed. Decision D009.
2026-10-21 · 00.5 · `inventory.md`: 15 encounters, 17 v1 Naxx archives (partition 1), guidance gaps, and the missing encounter context for zone 2006. Added box 01.5.
2026-10-21 · 00.5 · Codex #199 REVISE: the first conclusion (no reusable cell evidence) overstated the code. Narrowed: v1 archives cannot supply encounter or critical streams; actor streams, rankings, facts and replays stay reusable where 01.1 accepts them; full v2 recapture is an explicit acquisition proposal. 01.5 gates `duty.applies` itself; 03.2 smoke asserts v2 streams.
2026-10-21 · 00.5 · Codex #201 AGREE on 34bf7ea..9938253; 00.5 closed.
2026-10-21 · 00.7 · Codex probe (D007 research seat), verified and promoted unchanged to `research/` (319 pinned JSON hashes match: 317 API request records plus 2 derived summaries; gitleaks clean, negative partition-2 fight IDs and the `fight > 0` gate confirmed). Decision D008: partition 1 only, 510 cells. Quota scenario (`research/quota-estimate.md`, MC-shaped, not a bound): about 2208–2531 points per 15-boss configuration; the first v2 Naxx capture must measure before bulk planning. PM-3 oracle contract: `research/oracle-design.md`.
2026-10-21 · 00.7 · Codex #9 AGREE on 05002a1; 00.7 and the research promotion closed.
2026-10-21 · 00.6 · `pre-mortem.md`: PM-1 to PM-5, verdict PROCEED WITH GUARDRAILS.
