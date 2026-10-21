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
- [ ] **03.1** (agent) Naxx queue: 34 configurations minus usable existing archives, 1–3 reviewed public candidates each (owner's characters excluded), pinned research, `capture_queue verify` clean. Pair review.
- [ ] **03.2** (agent) Image and smoke: current release wheel (cut a release only if the runner needs a change), smoke with the exact production argv on a Naxx entry.
- [ ] **03.3** (product-owner) Approve restarting the Tower runner with the Naxx queue; watchdog re-enabled. Mirrored.
- [ ] **03.4** (agent) Tower restart per the unraid-tower skill with a change record; monitor; handle attention states.
- [ ] **03.5** (agent) Intake: copy finished archives to the PC, verify hashes, add provenance, register actor sources (`actor_problems` clean). Partial captures classified with evidence; missing configurations stay OPEN with the reason.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
