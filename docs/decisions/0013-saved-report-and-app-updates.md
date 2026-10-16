# 0013 — Saved report refresh and explicit desktop updates

Status: accepted

## Context

Known analyses need current report presentation without reacquiring logs or
recomputing findings. The GUI already renders validated analysis JSON with its
installed templates, but persisted HTML and ZIP packages need an explicit refresh.
Desktop users also need a discoverable path to newer published app releases.

## Decision

Expose **Update reports** on known saved runs and the report toolbar. Use the
existing output lock, validate checkpoint ownership, and publish derived files
with checkpoint hash finalization inside ordinary-failure rollback. Preserve
analysis bytes, timestamps, run identity, resume options and review keys. Keep
the existing documented crash-recovery boundary; this is not a multi-file
crash-proof transaction. Identify renderer and analysis versions separately.

Expose an explicit **Check for updates** command. Discover stable releases only
from the official GitHub repository, compare numeric versions, require matching
platform assets, and pin/recheck asset identity before installation. Bound
downloads, restrict redirects to GitHub asset hosts, and verify SHA256SUMS plus
GitHub asset digests when supplied. Release notes are plain text.

Managed copies reuse the released per-user bootstrap scripts and versioned
staging described in ADR 0011. Preserve active launchers on failure, verify the
new GUI/engine version, and restart only after the old window exits. Installation
shares the engine's single-worker boundary; closing waits for installation to
finish. Source and portable copies receive a manual release-page path.

## Consequences

No updater service, background network polling, dependency or second package
format is introduced. The Tauri updater plugin is deferred because current
distribution has neither its signed manifests nor its updater artifact pipeline.
Checksums validate download integrity under the existing GitHub release trust
model; they do not introduce independent release signing. Existing releases need
a manual upgrade to acquire these controls. Publication of a new desktop release
remains separate from implementation and source delivery.
