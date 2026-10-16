# 01 - Saved reports

## Goal

Persist current templates into a known saved analysis without a new run or API calls.

## Integration analysis

Extend DesktopEngine and report publisher; use RunLibrary/SavedRun, existing output lock and Checkpoint ownership. Preserve analysis bytes, session status, source snapshot and review keys. Report opening already renders trusted templates; this action persists derived files.

## Boxes

- [ ] **01.1** (agent) Validate selected run, preserve identity/data and serialize refresh with the existing output lock.
- [ ] **01.2** (agent) Publish regenerated HTML/package with checkpoint finalization and rollback on render/write/metadata failure; exercise resumed ownership validation.
- [ ] **01.3** (agent) Add Update reports to library rows and active-report controls with offline success/error feedback and busy handling.

## Hindsight checkpoint

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log

Pending.
