# 01 — Foundation And Golden Fixture

## Goal
A runnable, empty-but-real Python project (`necropsy` package, CLI entry point,
lint/type/test, CI) plus the frozen golden fixture with hashes and provenance,
a fast deterministic subset, and a golden-fact register whose every entry has a
source and a status.

## Integration analysis
> Fill before ticking any box (§6.17). Name concrete files/symbols; "none found"
> must cite the search that proved it.

- **Existing code found** — TBD
- **Behaviour to preserve** — TBD
- **Reuse / extend** — TBD
- **Do not duplicate** — TBD
- **Integration point + why** — TBD
- **Vision fit** — TBD
- **Risks** — TBD

## Boxes
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
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
