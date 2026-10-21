# 03 - Naxx Captures

## Goal
Real, public, full-raid Naxx actor evidence for every configuration, captured on
Tower from one reviewed queue, copied to the PC with verified hashes, and
registered as actor sources.

## Integration analysis
To be completed before 03.1. Reuse `scripts/capture_queue.py` (plan/resolve/emit),
`capture_runner.py`, the Tower image and status page, `stage_capture_image.py`.
Check that the queue universe and runner accept zone 2006 and the Naxx raid key.
Existing Naxx archives from 00.5 reduce the queue.

## Boxes
- [ ] **03.1** (agent) Before the bulk queue, one normal v2 capture measures quota with timestamped readings, page and event counts, including a short fight and at least one of the Four Horsemen, Gothik or Kel'Thuzad (`research/quota-estimate.md`). Then the Naxx queue: 34 configurations minus usable existing archives, 1–3 reviewed public candidates each (owner's characters excluded), pinned research, `capture_queue verify` clean. Pair review.
- [ ] **03.2** (agent) Image and smoke: current release wheel (cut a release only if the runner needs a change), smoke with the exact production argv on a Naxx entry. The smoke asserts the produced archive is a v2 snapshot with encounter and critical streams for the entry's fight, not only argv and exit (PM-2).
- [x] **03.3** (product-owner) Approve restarting the Tower runner with the Naxx queue; approval mirrored. Execution and watchdog re-enablement remain in 03.4 after all approval conditions are met.
- [ ] **03.4** (agent) Tower restart per the unraid-tower skill with a change record; monitor; handle attention states.
- [ ] **03.5** (agent) Intake: copy finished archives to the PC, verify hashes, add provenance, register actor sources (`actor_problems` clean). Partial captures classified with evidence; missing configurations stay OPEN with the reason.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-21 · Preparation · Owner directs Codex to continue while Claude has no usage (D013). Existing pair session parked with pending Claude reviews retained. Fresh read-only SSH at 17:48:59 UTC confirms runner exited on 0.5.2, status server running, parked backup directory present and 305 GiB visible free space. Image staging now accepts an explicit queue/pin pair and retains the old defaults. PM-6 records wrong-queue staging and its guardrails. No image deployed, production restart or watchdog enablement; 03.1/03.2/03.4 remain open.
2026-10-21 · Preparation validation · Eleven staging tests pass, including custom-queue binding, wrong-pin refusal without output, and requiring both custom inputs. Ruff lint/format and targeted mypy pass; `check_docs` checks 297 links. Initial normal user-endpoint quota query failed with HTTP 503 at 17:49:33 UTC (start 17:48:59); no subject/report/event requests or capture followed, and available quota remains unknown. Full checkpoint gate uses eight pytest workers via `PYTEST_ADDOPTS=-n 8 --dist worksteal` and `NECROPSY_GATE_WORKERS=8`; its result is retained in the ignored workspace log, with no completion tick inferred while it runs.
2026-10-21 · 03.3 · Owner approval "Approved" relayed verbatim by Claude in mailbox claude:16, session 20261021T120145Z-a4a14bde. Conditional on all of: released 0.6.0 and Tower image built from its wheel; real 03.2 smoke proving v2 encounter and critical streams; one measured normal v2 capture with a short and complex fight and timestamped quota evidence; Naxx queue passing `capture_queue verify` and pair review. Approval is DONE and mirrored in manual-actions.md. No restart, image deployment or watchdog change has occurred; 03.4 remains open. These records are separate from the frozen release candidate 65b1154.
