# 02 - Local Work Orders

## Goal
A repeatable way to hand bounded tasks to the local runner (LocalPilot on
LocalBox, Qwen3.6 35B-A3B) and accept only results that pass a machine verifier,
so that mechanical and templated work moves off the frontier models.

## Integration analysis
To be completed before 02.1. Candidates to reuse: the pair mailbox `localpilot`
role (`pair.py`), LocalPilot headless mode, existing scratch discovery scripts
(`discover_*.py`), `fact_freeze.py` specs, `guidance_lint.py`. No new runner
infrastructure if LocalPilot's own invocation suffices.

## Boxes
- [ ] **02.1** (agent) Work-order format: a JSON or Markdown file with id, goal, input bundle (paths with SHA-256, source excerpts), allowed write paths (`workspace/naxx-drafts/<id>/` only), exact output schema, verifier command, time and token caps. A driver script starts LocalPilot on one order, enforces the caps and records the run.
- [ ] **02.2** (agent) Verifiers for the first three order kinds: (a) raw discovery count script (checked against an independent enumeration), (b) fact-freeze spec (checked by `fact_freeze check`), (c) guidance draft (schema, `guidance_lint`, every claim tied to a quoted excerpt). Each verifier has negative tests with planted defects.
- [ ] **02.3** (agent) Trial batch: ten orders of kind (a) on a Naxx boss; record pass rate, wall time and defects caught. A pass rate below the §4 threshold (set before the trial) moves that kind back to Claude.
- [ ] **02.4** (agent) Runbook in the plan folder: how to serve, run, verify and discard; what the runner may never do (write the tree, call WCL, review).

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
