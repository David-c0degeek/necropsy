# 02 — Selection and persistence

## Goal

Deliver selection and persistence within the shared pipeline.

## Integration analysis

Extend class_catalog/roles, environment talent evidence, existing run_analyze/checkpoint and snapshot v1 seams, service/desktop/TUI selectors, and shared report templates. Preserve archived spec keys, raw immutable fixtures and historical Hunter output. No parallel client or pipeline. Research and ADR0005/0006 establish the intent; category/intent confusion and unknown promotion are the principal risks.

## Boxes

- [x] **02.1** (agent) Expose declared talent-tree preference independently of WCL category in CLI, desktop and TUI.
- [x] **02.2** (agent) Preserve preference across saved runs, legacy checkpoints, snapshot validation and offline replay.

## Hindsight checkpoint

- [x] Captain Hindsight recorded (Keep / Fix before closing / Record / Risk / Verdict).
- [x] Verdict is CLOSE.

## Progress log

2026-10-16 · session 1 · CLI --talent-tree, independent desktop/TUI selections, optional saved-run/checkpoint/snapshot declaration and reader validation delivered. Legacy --spec/--category and absent-field checkpoint semantics retained. 60 CLI/TUI/service checks passed. Survival declaration -> Marksmanship query -> snapshot -> offline HTML preserved exactly; changed declaration refused on resume. A forged Combat declaration in Hunter archive is refused. Desktop dispatch preserves Combat plus Assassination; TUI stop/reload preserves Survival. Documentation impact reviewed: class guide, setup/desktop/CLI guides, JSON schema, ADR0012 and changelog updated with implementation. Coherent implementation checkpoint committed/pushed with this record.

## Captain Hindsight

### Keep

Independent declaration/category choices; shared pipeline and optional fields.

### Fix before closing

None after runtime sentinel fix and unknown-match regression verification.

### Record

Durable contract in ADR0012; PM guardrails retained.

### Risk

Exact WCL classifiers and global unranked-build leader searches remain outside scope; broad pools disclosed.

### Verdict

CLOSE.
