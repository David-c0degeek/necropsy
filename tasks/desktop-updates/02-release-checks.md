# 02 - Release checks

## Goal

Discover stable updates from the official repository and expose version/readiness information.

## Integration analysis

Use existing httpx runtime and Python bridge; credentials never enter this path. Compare semantic stable versions and use versioned release assets consumed by existing installers, with no new dependency.

## Boxes

- [x] **02.1** (agent) Implement bounded, explicit latest-release discovery and semantic version comparison; reject drafts/prereleases/downgrades and malformed metadata.
- [x] **02.2** (agent) Validate canonical release URLs and a complete platform asset set with size/digest metadata; report offline/rate-limit/no-release errors clearly.
- [x] **02.3** (agent) Wire Check for updates and a result panel showing installed/latest versions, notes and available install/download action.

## Hindsight checkpoint

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log

2026-10-16 · 02.1-02.3 implemented. Public metadata checks use bounded HTTP,
stable numeric versions and canonical repository/asset URLs. Negative tests cover
malformed metadata, draft/prerelease/downgrade, missing assets, unsafe redirects,
rate limits and offline guidance without WCL credentials. Native-window fixture
responses exercised current, offline, portable and available-install states;
script-looking release notes remained escaped text. A real public v0.3.1 API
response was inspected during readiness; no release was published.

## Captain Hindsight

Keep: existing httpx client dependency, explicit checks and narrow allowlisted IPC.
Fix before closing: none; test_app_updates.py and native update-dialog checks
exercise policy and controls separately with stated fixture boundaries.
Record: D001 and ADR 0013 retain GitHub release trust and defer updater signing.
Risk: GitHub availability/rate limits and future asset schema changes can require
retry or manual installation. Checksums are not independent release signatures.
Verdict: CLOSE.
