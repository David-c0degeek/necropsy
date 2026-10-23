# Reviewed production restart and alert supervision

The owner authorized a separate Codex reviewer while Claude was unavailable.
The full queue/image review and corrected handover review passed before the
20:39 UTC production restart. Existing conditional restart approval was retained.
These receipts record actual operations and preserve their failed guard checks.

The initial reviewed image is used by the unchanged status-page container.
The capture worker now uses the separately reviewed alert-retry image, built
from the same immutable public 0.6.1 wheel and queue. Its full source gate passed
2714 fast tests and 74 related runner tests with eight workers. The new image's
network-disabled preflight also exercised bounded alert sends, stopping and
actual sleeping-child delivery/cleanup without credentials or network access.

The worker-only rollout occurred during quota wait with no live capture child.
All 34 deferred entries and inflight state were unchanged. Docker's process view
needed a PID column; that guard stopped before mutation and was corrected and
reviewed. A whole-second heartbeat compared with a microsecond launch time then
caused a false timeout. The actual new container start, newer status-file mtime,
fresh heartbeat and all reviewed state/image/mount checks verified readiness.
No capture was interrupted or state reset to force a pass.

`alert-retry-rollout.json` records exact worker/image IDs, source/manifest hashes,
private backup location, retained www ID, unchanged state and guarded retirement.
Private inspect, credential and log contents stay outside Git. Only two active
Necropsy containers remain; all old data, journals and images are preserved.
The watchdog runs every 15 minutes against the new runtime. One initial automatic
start notification failed, then delivered; no manual test notification was sent.

At the recorded observation all 34 runs were quota-deferred until 21:41:39 UTC
(23:41 Amsterdam), with zero completed/usable runs. Empty or quota-partial output
is not approved actor evidence. Further capture/intake, policies, content, batch
and final product acceptance remain open. Local AI remains off.
