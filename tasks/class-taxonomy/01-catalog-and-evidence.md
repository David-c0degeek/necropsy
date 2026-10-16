# 01 — Game catalog and evidence

## Goal

Deliver game catalog and evidence within the shared pipeline.

## Integration analysis

Extend class_catalog/roles, environment talent evidence, existing run_analyze/checkpoint and snapshot v1 seams, service/desktop/TUI selectors, and shared report templates. Preserve archived spec keys, raw immutable fixtures and historical Hunter output. No parallel client or pipeline. Research and ADR0005/0006 establish the intent; category/intent confusion and unknown promotion are the principal risks.

## Boxes

- [x] **01.1** (agent) Deliver game tree/race catalogs and WCL ID/name/slug mapping with production callers.
- [x] **01.2** (agent) Validate source-specific talent triples; derive primary tree with unknown/tie semantics; fix build matching.

## Hindsight checkpoint

- [x] Captain Hindsight recorded (Keep / Fix before closing / Record / Risk / Verdict).
- [x] Verdict is CLOSE.

## Progress log

2026-10-16 · session 1 · Catalog and evidence delivered: 27 game trees, 19 verified WCL categories with names/slugs/IDs and eight-race validity. Source-specific talent triples reject placeholders/bools/range/total errors; primary trees derived from unique maxima; shared unknown build matches fixed. 53 taxonomy/generic/schema checks passed; 77 report/desktop/Druid checks passed. Combat-heavy Rogue, Fury-heavy tank, Arcane-heavy Frost-category Mage and tied Warlock examples exercised through snapshot -> offline JSON -> HTML/package. Documentation impact reviewed: class guide, setup/desktop/CLI guides, JSON schema, ADR0012 and changelog updated with implementation. Coherent implementation checkpoint committed/pushed with this record.

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
