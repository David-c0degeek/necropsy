# 02 - Local Work Orders

## Goal
A repeatable way to hand bounded tasks to the local runner (LocalPilot on
LocalBox, Qwen3.6 35B-A3B) and accept only results that pass a machine verifier,
so that mechanical and templated work moves off the frontier models.

## Integration analysis
Inspected LocalPilot v5.0.0-108-g824f190 native `ask` and its provider adapter.
`ask` sends one text request and streams the answer without the coding-agent
tool loop, so guidance orders can run without model filesystem/shell/network
tools. Use an isolated per-order provider configuration pinned to loopback,
with the native provider `max_tokens` cap, and a thin subprocess timeout/receipt
wrapper. Actual usage counts are unknown when `ask` does not expose them.
Reuse `guidance_lint.py` for known-pattern checks; independently enforce schema,
input digests, exact quotations, conflict exclusions and applicability. Raw
discovery remains with Codex under D009/D013; no new agent runtime is needed.

Before-trial threshold: at least 9 of 10 mechanically valid drafts, zero
fabricated/misattributed material claims after coordinator content review,
zero out-of-scope tree mutations and zero unreviewed promotions. Each order
has a 600-second wall cap and a 4096-token output cap. No failed output is
hand-repaired into a pass. A machine pass remains a draft pending review.

PM-4 guardrail: verify the contract and planted defects before the first model
request; fingerprint tracked files before/after each order. Use tool-free
`ask`, never bypass permissions. Output and logs stay in the declared ignored
draft directory. Do not send WCL credentials, raw captures or API access to it.

## Boxes
- [x] **02.1** (agent) Work-order format: a JSON or Markdown file with id, goal, input bundle (paths with SHA-256, source excerpts), allowed write paths (`workspace/naxx-drafts/<id>/` only), exact output schema, verifier command, time and token caps. A driver script starts LocalPilot on one order, enforces the caps and records the run.
- [ ] **02.2** (agent) Verifiers for the first three order kinds: (a) raw discovery count script (checked against an independent enumeration), (b) fact-freeze spec (checked by `fact_freeze check`), (c) guidance draft (schema, `guidance_lint`, every claim tied to a quoted excerpt). Each verifier has negative tests with planted defects.
- [x] **02.3** (agent) Trial batch: ten orders of kind (c), guidance drafts, on a Naxx boss (kind (a) failed 0 of 3 in 00.4 and stays with Claude, D009); record pass rate, wall time and defects caught. A pass rate below the §4 threshold (set before the trial) moves that kind back to Claude.
- [x] **02.4** (agent) Runbook in the plan folder: how to serve, run, verify and discard; what the runner may never do (write the tree, call WCL, review).

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-21 · 02.1/02.4 · `scripts/guidance_work_order.py` implements the strict guidance order/draft schema, frozen input/prompt packet, exact verifier command, Git-ignored output boundary, native provider token cap, subprocess wall cap, retained rejection evidence and repository mutation fingerprint. Native `ask` capability and max_tokens were probed against the installed CLI before live trials; its direct model trial remains intentionally unrun under the owner's hold. `work-orders-runbook.md` covers serving only after that hold is lifted, running/verifying/discarding and stopping a retrying launcher. Twenty-six targeted tests pass; whole-tree mypy passes 278 files and changed-file Ruff passes. 02.2 remains open for its other work kinds; 02.3 remains open with zero executed orders. Full checkpoint gate follows commit (`NECROPSY_GATE_WORKERS=8`, fast pytest suite limited to two workers while the owner raids); receipt `workspace/codex-naxx/guidance-work-order-full-gate.log`. No guidance or completion evidence is promoted.
2026-10-21 · Preparation · Native LocalPilot `ask` verified against a loopback mock using the actual installed v5.0.0-108-g824f190 executable: one request, max_tokens 4096 on the wire, no tool definitions, expected text output and unchanged repository fingerprint. This is a runtime plumbing probe, not a model trial or token-usage measurement; receipt `research/localpilot-runtime-probe.json`. Independent verifier has 25 passing tests with malformed schema, fabricated/empty/unknown/conflicting support, wrong class/metric/source, unsupported timer, invented removal capability, missing positioning boundary, duplicate rules/categories, timeout and untracked mutation negatives. Ten Sapphiron orders frozen under `work-orders/`, covering six healer and four DPS configurations; input quotes/pins and threshold fixed before any trial.
2026-10-21 · Local inference HOLD · Owner: "stop local llm till i finish raid". LocalBox startup was interrupted; its launcher retried after the proxy was stopped, so both server processes and the proxy were explicitly stopped and no llama-server process remained. Treat that reply-check failure as interrupted startup, not evidence of a model defect. No guidance order was executed. Keep local inference off until the owner says the raid is finished; continue non-GPU preparation. Trial 02.3 remains open, with no pass rate reported.

2026-10-21 · 02.3 · Owner lifted local inference hold ("local model approved now"). Ten frozen orders executed once each: 2/10 original machine passes, only 04 content-acceptable as a draft, zero promotions and zero repository mutations. Kind (c) is rejected under D014 and returns to Codex under D013. Audit receipts and review are preserved in `research/guidance-trial-results.json`; raw drafts stay in ignored workspace directories, no failures repaired or retried. Runtime changed from pure 256k (01) to pure with 32k context override (02–07), then saved balanced 256k (08–10) at the owner's request. This mixed batch cannot compare tunes; balanced subset was 0/3 mechanically. Token usage remains unknown. Review exposed the spacing synonym missing from the positioning lint; a regression test now enforces that boundary without changing historical receipts. Owner preference: always use saved balanced tunes when available. 02.2 and the subject close-out remain open.

Verification: 27 targeted guidance tests passed before formatting; the real order-07 draft is rejected by the strengthened verifier. Full checkpoint gate runs after commit with `NECROPSY_GATE_WORKERS=8` and fast pytest at eight workers; log `workspace/codex-naxx/guidance-trial-full-gate.log`. This checkpoint does not close 02.2 or the subject.
