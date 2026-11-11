# Capture campaign

Owner order: **Naxxramas → AQ40 → BWL → MC**.

The pinned v2 queue preserves the existing 34-entry Naxx queue exactly, then
appends the 93 scheduled entries from the parked raid queue:32 AQ40,33 BWL,28 MC.
Nine existing reuse dispositions remain outside the scheduled entries. The
136-configuration universe includes1,462 boss/configuration cells; neither
reuse disposition nor capture completion establishes accepted content cells.

Only the first unfinished raid may run. A quota wait or transient retry never
allows a later raid to consume the allowance. If a raid's pass ends with partial
or refused entries, the controller pauses for review. Clearing attention alone
does not bypass that barrier. Existing partial Naxx evidence stays partial.

Extending a live queue requires `capture_runner.py extend-queue` with the old
queue, new queue and stopped runner's state directory. It refuses an inflight
attempt, changed old definitions, wrong state identity or another state owner.
It saves a byte-identical state backup, atomically changes the queue binding,
preserves all old entry records/quota/alerts, and adds only pending new entries.
Rerunning the same successful migration is idempotent. Older runners refuse
queue v2 instead of silently ignoring the raid barrier.

Whole-fight v4 projections support all four Era raids on partitions1/2, with
ownership/hit-type fallback and verified requested cache reuse. V3 retains its
original Naxx-only contract. New target-only reuse for a legacy MC/BWL/AQ40
cache uses v4; existing archives and their raw evidence are not rewritten.

Production rollout and verification are recorded alongside the capture scaling
research and in the private Tower maintenance repository. A checked-in queue
does not itself prove it was deployed or that any raid is finished.

The verified campaign was deployed on Tower on2026-11-04 at22:06UTC, preserving
all34 prior Naxx entry records and appending93 pending entries. Evidence:
[deployment receipt](../naxx-completion/research/capture-scaling-20261104/campaign-deployment.json).
