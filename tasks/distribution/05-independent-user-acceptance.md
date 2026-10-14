# 05 — Independent user acceptance and release gate

## Goal
Prove another person can install, authorize and produce a correctly scoped report without the developer secret.

## Integration analysis
- **Existing code found:** `tests/live/test_live_acceptance.py, wcl/acceptance.py, docs/live-acceptance.md; extend the existing harness`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [ ] **05.1** (agent) Prepare an opt-in real-account acceptance procedure and receipt covering installation, sign-in/refresh, supported acquisition, output/package integrity, permissions, quota limitations and secret scanning.
- [ ] **05.2** (product-owner) Run or observe the documented flow on another person/account and machine; confirm no developer secret is requested, outputs and uncertainty are understandable, and declared platform behavior is acceptable.
- [ ] **05.3** (agent) Run the latest fast/golden/acceptance/browser and build checks, complete documentation/cleanup/lessons/PM calibration and Claude review; carry any unsupported platform or permission limit explicitly into the release notes.
- [ ] **05.4** (release-engineer) Approve and publish the reviewed package only after the public-client and independent-user gates pass; record the exact version, artifact hash and supported platforms.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation has not started. Record date, per-subject slice number, box IDs, observed behavior, verification, documentation impact, and pushed checkpoint.
