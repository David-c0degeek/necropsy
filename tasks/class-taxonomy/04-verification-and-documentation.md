# 04 — Verification and documentation

## Goal

Deliver verification and documentation within the shared pipeline.

## Integration analysis

Extend class_catalog/roles, environment talent evidence, existing run_analyze/checkpoint and snapshot v1 seams, service/desktop/TUI selectors, and shared report templates. Preserve archived spec keys, raw immutable fixtures and historical Hunter output. No parallel client or pipeline. Research and ADR0005/0006 establish the intent; category/intent confusion and unknown promotion are the principal risks.

## Boxes

- [x] **04.1** (agent) Verify user flows, snapshot/resume compatibility, regressions, lint/typecheck/build and desktop output.
- [x] **04.2** (agent) Update permanent docs/ADR/changelog, triage changed seams, calibrate risks and close subjects.

## Hindsight checkpoint

- [x] Captain Hindsight recorded (Keep / Fix before closing / Record / Risk / Verdict).
- [x] Verdict is CLOSE.

## Progress log

2026-10-16 · session 1 · Completed implementation and close-out review. Full existing fast/browser suite: `uv run pytest -m "not golden and not live and not acceptance" -q` -> 1144 passed, 251 deselected in 430.36s. Real-log replay: `uv run pytest tests/golden/test_class_replay.py tests/golden/test_druid_replay.py -m golden -q` -> 17 passed in 301.11s. Latest targeted checks after hardening: 53 taxonomy/generic/schema, 77 report/desktop/Druid, 60 CLI/TUI/service, focused archive declaration rejection and four expanded responsive Rogue report/playbook views passed. Ruff check/format, mypy (183 files), uv build, desktop Prettier check and TypeScript/Vite build passed. Built-wheel smoke imports both taxonomy modules and exposes --talent-tree. Historical Hunter JSON/HTML/ZIP comparison against the pre-change source is byte-identical for all four artifacts. No raw fixtures modified, no network acquisition needed.

Documentation impact: README, desktop/install/getting-started, class/WCL guide, architecture, JSON schema/contract, changelog and ADR0012 updated; local links resolve. Inspect changed seams rather than whole-repo cleanup under D003. Added APIs have production callers through selectors, normalization, snapshot reader/writer and report builder/render. No new dependencies. New snapshots require updated readers; old snapshots/checkpoints/documents remain readable. Release publication and native sign-in acceptance are outside this feature checkpoint.

Development verification caught and corrected: invalid Textual sentinel in actual optional selection flow; a new test constructing observed evidence without a source reference; an obsolete Druid wording assertion after category relabeling; formatting violations; and an edit-script encoding issue before commit. No unresolved test failures remain. Runtime behavior was exercised, not inferred from buildability.

## Captain Hindsight

### Keep

Separate intent and WCL category choices; direct primary-source name/slug metadata; observed build and inferred duty evidence; no automatic ambiguous mappings; archive compatibility. Retain collapsed identity details and keyboard-focusable scrolling tables.

### Fix before closing

None. Source validation, unknown matches, source-specific talent arrays, wrong-class declarations, resume-option immutability, old checkpoints and real replay boundaries are verified. Generated schema and all affected user guidance are current.

### Record

ADR0012 captures durable decisions. PM-1/PM-3 prevented, PM-2 mitigated and calibrated against replay evidence. CH-MISS-1 records the installed widget sentinel and the actual-flow guardrail. Lessons reconciled into tasks/lessons.md. Original PM prediction fields retained.

### Risk

Exact current WCL classifier algorithms and full individual talent allocations remain unverified; reports disclose those boundaries. No global build-specific leader search or native installer release is claimed. Optional fields are backward readable by new code, not forward readable by old strict readers.

### Verdict

CLOSE. Engineering implementation complete; coherent feature branch checkpoints pushed. No user action required to finish the requested implementation.
