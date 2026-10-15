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
- [x] **05.1** (agent) Prepare an opt-in real-account acceptance procedure and receipt covering installation, sign-in/refresh, supported acquisition, output/package integrity, permissions, quota limitations and secret scanning.
- [x] **05.2** (product-owner) Run or observe the documented flow on another person/account and machine; confirm no developer secret is requested, outputs and uncertainty are understandable, and declared platform behavior is acceptable.
- [x] **05.3** (agent) Run the latest fast/golden/acceptance/browser and build checks, complete documentation/cleanup/lessons/PM calibration and solo Codex review; carry any unsupported platform or permission limit explicitly into the release notes.
- [x] **05.4** (release-engineer) Approve and publish the reviewed package only after the public-client and independent-user gates pass; record the exact version, artifact hash and supported platforms.

## Hindsight checkpoint
Before marking DONE: Codex performs solo review and records Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt (master D003; user ended Claude pairing). No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log
2026-10-15 · 1 · 05.1/05.3 · Extended existing live-acceptance procedure with another account/machine installation, consent/cancel/refresh, ranking/report/archive/quota checks, output/package integrity, offline replay, unlimited extracted scans, logout/removal and explicit product/publication receipt. No second harness or acquisition pipeline introduced. User confirms no public client exists; registration instructions supplied; no second-person acceptance or release approval inferred. Final verification and review in progress; manual gates stay open. Documentation only for 05.1; verified against actual CLI help, installed probe and existing acceptance harness. Pushed checkpoint follows.


2026-10-15 · 2 · 05.3 · Final local fast regression 974 pass plus 11 subsequently
added artifact-boundary checks; golden/acceptance 246 pass with the same four
accepted xfails; browser 41 pass; build/lint/format/types/lock checks pass.
Windows clean wheel/public mock/offline replay/package integrity and real WinVault
probe pass; wheel/sdist reproducible and extracted/output scans pass. Ubuntu CI
for 0cfdab0 passes final complete fast collection; Windows CI still running at this
record. Final solo review and PM calibration in verification.md/pre-mortem.md;
no unresolved engineering defect. Docs updated, cleanup waived by D007, lasting
lessons promoted. Implementation checkpoint 0cfdab0 pushed; documentation receipt
checkpoint follows. No publication or independent tester acceptance claimed.

## Final review
Keep: extend existing live harness and retain actual artifact/account scope.
Fix before closing: 05.2 independent account/machine and 05.4 publication approval
remain required; public registration/live permissions remain prerequisites.
Record: verification.md and package-receipt.json contain commands, hashes and scope;
PM-1/PM-2 prevented/mitigated, PM-3 mitigated with live horizon Inconclusive.
Risk: registered public-account/refresh/archive support remains unobserved.
Verdict: DO NOT CLOSE subject 05; all agent implementation/review work is complete,
required independent and release human actions remain open.

2026-10-15 · 3 · 05.3 · Registered public default and live login/refresh/query
observations recorded; subjects01/03 now CLOSE. New package/default-login
check and scans pass; prior Windows/Ubuntu CI completed green. Only independent
05.2 and publication05.4 remain; no second person/account/machine is inferred.


2026-10-15 · 4 · 05.2/05.4 · User replied “Approved”, then explicitly answered
“Independent test passed” to the question about another WCL account and machine
completing installation, sign-in and report generation. This resolves product-owner
acceptance by attestation, not agent-observed raw evidence. OS and tested artifact
hash were not supplied; do not invent them. Existing supported Windows/Python3.14
scope remains. Publication approved for reviewed CLI; use the existing private
GitHub repository (no PyPI target configured and no visibility change authorized).
Release artifact documentation updated; package rebuild/verification and publication
are in progress. Receipt: independent-acceptance.json. Checkpoint follows.


2026-10-15 · 5 · 05.4 · Published v0.1.0 through existing private GitHub repository,
target62d1e9404b5704f56ca247f45417dcd1f65430ec. Wheel/sdist/SHA256SUMS uploaded,
downloaded and compared byte-for-byte before publication; published GitHub digests
and sizes match local artifacts. Code CI cbb04f5 passes Windows and Ubuntu; release
metadata-only delta passes 67 focused auth/package checks and isolated installed
artifact/replay/store/scans. Exact version/hash/platform/URL in release-receipt.json.
User approval and independent acceptance are explicit; no PyPI or public visibility
change performed. Final record commit/push follows.

## Closing review after publication
Keep: one pipeline, public-client identity, approved OS store, explicit endpoint,
scoped platform/permission limitations, verified released artifact hashes.
Fix before closing: none. Human independent acceptance is explicitly owner-attested,
not relabelled as agent-observed OS/raw receipt. Publication is complete.
Record: independent-acceptance.json, package-receipt.json, public-auth-receipt.json,
release-receipt.json, PM calibration, durable docs and permanent lessons.
Risk: Windows release scope only; account quota/privacy/archive permissions vary;
four known golden xfails and evidence/coverage limitations remain accepted.
Verdict: CLOSE subject05; supersedes earlier interim DO NOT CLOSE reviews.
