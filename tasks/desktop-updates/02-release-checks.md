# 02 - Release checks

## Goal

Discover stable updates from the official repository and expose version/readiness information.

## Integration analysis

Use existing httpx runtime and Python bridge; credentials never enter this path. Compare semantic stable versions and use versioned release assets consumed by existing installers, with no new dependency.

## Boxes

- [ ] **02.1** (agent) Implement bounded, explicit latest-release discovery and semantic version comparison; reject drafts/prereleases/downgrades and malformed metadata.
- [ ] **02.2** (agent) Validate canonical release URLs and a complete platform asset set with size/digest metadata; report offline/rate-limit/no-release errors clearly.
- [ ] **02.3** (agent) Wire Check for updates and a result panel showing installed/latest versions, notes and available install/download action.

## Hindsight checkpoint

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log

Pending.
