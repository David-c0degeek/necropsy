# 01 — Foundation And Golden Fixture

## Goal
A runnable, empty-but-real Python project (`necropsy` package, CLI entry point,
lint/type/test, CI) plus the frozen golden fixture with hashes and provenance,
a fast deterministic subset, and a golden-fact register whose every entry has a
source and a status.

## Integration analysis
> Fill before ticking any box in this subject. Reuse and integrate before
> adding — no new code until this is recorded (§6.17). Build on the prior-art
> map from 00.2 and the architectural direction from 00.1.
>
> **Evidence, not prose.** Each bullet names concrete files/symbols (e.g.
> `necropsy/snapshot/v0.py::read_events`), not "the relevant modules". "None
> found" is a valid answer only when it records the search that proved it (the
> grep/scan run). A generic Integration analysis that names nothing is not
> done — it is how a duplicate parallel system slips past this gate.
>
> - **Existing code found** — relevant modules, services, abstractions, workflows.
> - **Behaviour to preserve** — contracts, public APIs, tests, callers that must keep working.
> - **Reuse / extend** — what is reused, extended, or refactored instead of duplicated.
> - **Do not duplicate** — what already exists and must not be reimplemented.
> - **Integration point + why** — where the change lands and why it is the correct seam.
> - **Vision fit** — supports or conflicts with the project vision/ADRs (00.1); cite drift if any.
> - **Risks** — duplication, architectural drift, or accidental complexity introduced.

- **Existing code found** — TBD
- **Behaviour to preserve** — TBD
- **Reuse / extend** — TBD
- **Do not duplicate** — TBD
- **Integration point + why** — TBD
- **Vision fit** — TBD
- **Risks** — TBD

## Boxes
> ID = `<subject-id>.<box-number>` (subject index ID · box ordinal). Stable — never
> renumber; mark retired boxes done and struck with `ABANDONED; see D###`
> (see §4), don't delete. A human-owned box recorded `DEFERRED` in
> `manual-actions.md` stays `[ ]` and follows the §5 Done rule.
> Owner MUST be one of the §5 enum:
> agent · release-engineer · product-owner · tech-lead · domain-sme.

- [ ] **01.1** (agent) uv project at repo root: `src/necropsy/` laid out per
      spec §10 adapted for Python-only Milestone A (`wcl/`, `acquisition/`,
      `snapshot/`, `normalize/`, `benchmark/`, `analysis/{generic,classes,encounters}/`,
      `reports/`, `storage/`), `rules/classic_era/`, `tests/{unit,integration,golden}/`.
      Create directories only as code lands in them. `necropsy --help` and
      `necropsy --version` work.
- [ ] **01.2** (agent) GitHub Actions CI: `uv sync --locked`, ruff, type check,
      fast tests on Windows + Linux. Golden suite as manual/scheduled job with
      LFS checkout. Green run recorded.
- [ ] **01.3** (agent) Git LFS tracks the full v6 export zip under
      `tests/golden/haplina_naxx/raw/`; `PROVENANCE.md` records origin path,
      export timestamp, auth mode from `manifest.json`
      (`clientSecretIncludedInExport=false`, `userAccessTokenIncludedInExport=false`),
      character/zone/partition, SHA-256 of the zip and an extracted-file
      manifest. Definitive playbook HTML/CSVs frozen alongside with hashes;
      v1/v2 outputs stored under `historical/`, marked superseded.
- [ ] **01.4** (agent) Golden-fact register `tests/golden/haplina_naxx/facts.yaml`:
      each fact has id, statement, expected value + tolerance, mode
      (`historical` / `live`), source (file + row/section), status
      (`verified-against-raw` / `oracle-only` / `disputed`), `mandatory`
      (bool), and `resolution` (required for `disputed` and for excluded
      `oracle-only` facts). Mandatory set is non-empty: every spec §11 fact plus
      at least one fact per boss. A loader test rejects unknown statuses and
      mandatory facts that are not `verified-against-raw` at the §7 gate. Seed from spec §11
      and the definitive playbook: Patchwerk Raptor counts (Smcadogx 11,
      Charies 9, Andrenn 8, Xert 0, Xal 6); Smcadogx Horde/Orc via Blood Fury
      20572 with 9 WF extra attacks; 63 Alliance / 12 Horde (historical mode
      only — mixed overall top 5); Snape death ~25.678 s on Grobbulus; Gothik
      foreign-trash shares; KT MC-utility timestamps; Haplina 12/33/6; pet ranks
      (Bite 8 / 17261, Dive 3 / 23148, Lightning Breath 6 / 25012); shot counts.
- [ ] **01.5** (agent) Deterministic subset fixture committed plainly (no LFS):
      Patchwerk (Haplina + recorded top 5), plus Grobbulus, Gothik, KT for
      Haplina and the rank-1 comparator, with every stream those fights need.
      Generator script reproduces it from the full zip and verifies hashes.
      Size budget recorded (target < 25 MB).
- [ ] **01.6** (agent) Bounded extraction helper for the full zip (cache dir,
      hash-verified, idempotent, refuses path traversal and oversize entries)
      used by golden tests; clean-clone replay steps in README.
- [ ] **01.7** (domain-sme) Review `facts.yaml` seed: confirm trusted oracle
      facts, mark known-wrong ones `disputed` with a note.

## Hindsight checkpoint
> Run after all boxes in this subject are complete and before marking
> the subject `DONE` in §5. Use the embedded prompt in "Appendix: Captain
> Hindsight Prompt". Record the review result here. An interim run after
> a large or risky box is allowed and recorded the same way; it does not
> replace the closing run. In this coordinated pair plan, the navigator's
> `VERDICT AGREE` on the subject's diff precedes the Hindsight run.
>
> Required output sections: Keep; Fix before closing; Record; Risk;
> Verdict (`CLOSE` or `DO NOT CLOSE`). If the verdict is `DO NOT CLOSE`,
> leave the subject open, add/reopen boxes or update decisions/lessons,
> and rerun this checkpoint after the fixes.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
