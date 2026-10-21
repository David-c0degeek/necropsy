# Offline verifier contracts

The local runner failed both raw-count and guidance trials. Codex performs these
tasks; a verifier does not authorize another model trial or production promotion.
No command here calls WCL.

## Fact-freeze specs

Reuse `scripts/fact_freeze.py`; do not build a second parser or invoke generated
scripts. A reviewed JSON spec identifies the archive path and SHA-256, exact
report/fight/actor/player contexts, and named queries. Each stream is explicitly
`all` or `actor`; absence of the selected stream fails rather than selecting the
other. The supported query kinds and strict keys are documented in that script.
An archive and spec belong to one fresh ignored work directory. Pin the actual
spec and archive bytes before running, retain stdout/stderr and the interpreter
version, and keep the generated facts as a draft.

```powershell
uv run python scripts/fact_freeze.py freeze SPEC.json --out FACTS.json
uv run python scripts/fact_freeze.py check FACTS.json
```

`check` recomputes raw values and locators and compares types as well as values.
An edited value, bad archive hash, missing or foreign stream, aliased identity or
ambiguous NPC/window must fail. The existing test suite contains these negatives:

```powershell
uv run pytest tests/unit/test_fact_freeze.py -q
uv run python scripts/fact_freeze.py check tests/golden/raids/lucifron-paladin-mechanics.json
```

Current readiness: 55 tests passed and the existing real fact file had zero
differences. This establishes the reusable verifier, not new Naxx facts. A
coordinator must still review the query's intended scope and compare raw events
independently before freezing expectations. `check` cannot prove a semantically
wrong spec chose the right question, or that every relevant raid actor was captured.

## Raw discovery counts

The scanner under `workspace/codex-naxx/oracle-tool/` remains a prototype, outside
production. Its query binds report, fight, encounter, scope and numeric filters;
its archive and entries sidecar are hashed. It uses standard-library parsing and
does not import the analyzer. Counters preserve event multiplicity; SOURCE/TARGET
overlap merges by maximum multiplicity instead of summing or collapsing to a set.

Twenty-three synthetic tests passed. A separate raw Counter loop matched five
real v1 boss cases, totaling 4329 selected occurrences. The loop reuses validated
member bytes from the same archive loader, so it does not independently validate
that loader. Detailed commands, tool digest, case counts, raw-result digests and
limits are in `offline-verifier-readiness.json`; local query/result files remain
under the ignored workspace.

Required before promotion: validate an actual certified v2 archive, prove full
eligibility/identity and encounter scope, preserve unknown rather than infer
absence, and independently enumerate the selected raw events. Synthetic v2
negatives and a real v1 replay do not substitute for that evidence. An event in
critical but absent from encounter-All is a contradiction. No prototype output
can certify a COMPLETE cell, assignment, position, phase, opportunity or ranking.

## Guidance

The ten original orders remain immutable historical artifacts. Their 2/10
original machine score and coordinator rejection are in
`guidance-trial-results.json`. Later source research changes the boss ledger's
input hash; reproduce the trial from committed revision `d53811d85986`, not by
repinning or repairing old orders. Machine validity is separate from content
review; exact quote presence cannot establish that a new claim follows from it.

The new capability catalog and boss `capability_refs` are research references.
The existing guidance linter does not resolve them into allowed support keys.
Any future capability-aware contract needs independent applicability/citation
checks before those references can support a draft.
