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

- **Existing code found** — none in the repo (00.2: only docs and plan files). Prior art outside the repo: `D:\repos\wcl_access_test\wcl_hunter_deep_export.py` writes the export layout (`export_actor_events`, `write_json`, `shutil.make_archive`); no reader exists anywhere.
- **Behaviour to preserve** — the raw export's exact bytes (immutability, plan §6.21); the oracle files' exact bytes (frozen with `-text`).
- **Reuse / extend** — exporter layout knowledge (member paths, `selection.json` shape) reused by `scripts/fixture_tools.py::subset_members`; uv/ruff/mypy/pytest configuration from the 00.3 smoke run.
- **Do not duplicate** — one archive reader (`necropsy.snapshot.archive.VerifiedArchive`) serves the subset generator, the fixture tests and (later) snapshot ingest; no second zip/extraction path.
- **Integration point + why** — `src/necropsy/snapshot/archive.py`: snapshots are archives, so verified archive access is the seam every later reader builds on. `tests/golden/haplina_naxx/` holds fixture + oracle + facts; `tests/fixtures/` holds the subset; `scripts/` holds developer-only tooling.
- **Vision fit** — supports spec §2 step 7 / §11 (immutable raw, golden fixture) and plan §6.21–6.22; D015/D016 adjust 01.5/01.6 without changing intent.
- **Risks** — zip bytes depend on the zlib build (mitigated: member manifest is the cross-machine contract; byte check skips with a reason on a different zlib); LFS bandwidth (mitigated: manual golden workflow only); `VerifiedArchive` and `scripts/fixture_tools.py` have test-and-tooling callers only until snapshot ingest wires the reader (disclosed in README and D016).

## Boxes
> ID = `<subject-id>.<box-number>` (subject index ID · box ordinal). Stable — never
> renumber; mark retired boxes done and struck with `ABANDONED; see D###`
> (see §4), don't delete. A human-owned box recorded `DEFERRED` in
> `manual-actions.md` stays `[ ]` and follows the §5 Done rule.
> Owner MUST be one of the §5 enum:
> agent · release-engineer · product-owner · tech-lead · domain-sme.

- [x] **01.1** (agent) uv project at repo root: `src/necropsy/` laid out per
      spec §10 adapted for Python-only Milestone A (`wcl/`, `acquisition/`,
      `snapshot/`, `normalize/`, `benchmark/`, `analysis/{generic,classes,encounters}/`,
      `reports/`, `storage/`), `rules/classic_era/`, `tests/{unit,integration,golden}/`.
      Create directories only as code lands in them. `necropsy --help` and
      `necropsy --version` work. `pyproject.toml` registers pytest markers
      `golden` and `live` with `--strict-markers`, mypy strict (with `types-PyYAML`), ruff; `CHANGELOG.md`
      created.
- [x] **01.2** (agent) GitHub Actions CI: `uv sync --locked`, ruff, type check,
      fast tests on Windows + Linux. Golden suite as manual/scheduled job with
      LFS checkout. Green run recorded.
- [x] **01.3** (agent) Git LFS tracks the full v6 export zip under
      `tests/golden/haplina_naxx/raw/`; `PROVENANCE.md` records origin path,
      export timestamp, auth mode from `manifest.json`
      (`clientSecretIncludedInExport=false`, `userAccessTokenIncludedInExport=false`),
      character/zone/partition, SHA-256 of the zip and an extracted-file
      manifest. Definitive playbook HTML/CSVs frozen alongside with hashes;
      v1/v2 outputs stored under `historical/`, marked superseded. gitleaks
      scans the extracted full fixture (no size cap) with zero findings before
      the first LFS push.
- [x] **01.4** (agent) Golden-fact register `tests/golden/haplina_naxx/facts.yaml`:
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
- [x] **01.5** (agent) Deterministic subset fixture committed plainly (no LFS):
      Patchwerk (Haplina + recorded top 5), plus Grobbulus, Gothik, KT for
      Haplina and the rank-1 comparator, with every stream those fights need.
      Generator script reproduces it from the full zip and verifies hashes.
      Size budget recorded (target < 25 MB). Amended by D015: the budget applies
      to the compressed subset zip of original member bytes (13.6 MB); a
      generated `subset.json` defines the subset scope.
- [x] **01.6** (agent) Bounded extraction helper for the full zip (cache dir,
      hash-verified, idempotent, refuses path traversal and oversize entries)
      used by golden tests; clean-clone replay steps in README. Amended by D016:
      no extraction; `necropsy.snapshot.archive.VerifiedArchive` reads members
      straight from the zip with the same guarantees (digests, unsafe and
      duplicate names, encryption, size caps on declared and read bytes).
- [x] **01.7** (domain-sme) Review `facts.yaml` seed: confirm trusted oracle
      facts, mark known-wrong ones `disputed` with a note.
      `DEFERRED — see manual-actions` (D017): batched with the 05.7 review, when
      analyzers have verified most facts against raw data.

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

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

**Captain Hindsight — 2026-10-13 (after navigator `VERDICT AGREE round=3`)**

1. **Keep:** one verified archive reader for every consumer (D016); fixture digests pinned in `provenance.json` and checked in fast CI on both OSes from a fresh checkout (proves `-text` keeps oracle bytes exact); subset tied to the full export by member digests, not zip bytes; acceptance gate separated from the always-green suites; facts carry source + evidence.
2. **Fix before closing:** none open. Review found and fixed: a non-existent floating `setup-uv@v10` tag, uncaught `zlib.error` on corrupt DEFLATE data, and a mistyped pinned checkout SHA that only the hosted run exposed (run 38316490928 failed; 38316637450 passed).
3. **Record:** lessons appended (no `git stash` mid-review; pin Actions by SHA and assert 40-hex length). D015/D016 amend 01.5/01.6; D017 defers 01.7. The raw probe found a second Snape death (39.0 s) the oracle never mentioned — recorded as a fact for Hunter-domain review.
4. **Risk:** `VerifiedArchive` and `scripts/fixture_tools.py` have only test/tooling callers until snapshot ingest (disclosed in D016 and README). `ubuntu-latest` moves to Ubuntu 26 on 2026-10-19 (runner annotation); CI may need a follow-up then. Acceptance gate is red by design until the analyzers land.
5. **Verdict:** CLOSE

## Progress log
> One line per slice. Date · slice number (per-subject, starting at 1) · box IDs touched · what
> shipped · how verified · checkpoint commit/push status. Append a
> `tasks/necropsy/lessons.md` line here too whenever the slice taught something.
2026-10-13 · slice 1 · 01.1, 01.3–01.6 · skeleton (uv, typer CLI with UTF-8 output, ruff, mypy strict, pytest strict markers + `acceptance` marker), `VerifiedArchive` + 20 unit tests, full fixture in LFS (sha256 f249c944…), 1,407-member entries manifest, 36 oracle files + provenance.json/PROVENANCE.md, 13.6 MB deterministic subset (two builds identical), facts.yaml (78 facts, 61 mandatory, 11 verified against raw), CI + manual golden workflow, README/CHANGELOG · observed: fast suite 48 passed; golden 2 passed (every full-export member digest verified; subset regenerates identically); acceptance fails as designed; ruff/mypy clean; gitleaks over the extracted full fixture: no leaks; `necropsy --version` → `necropsy 0.1.0` · 01.2 waits for the first CI run after push · commit pending pair review
2026-10-13 · slice 2 · 01.2, 01.7 (deferred), Hindsight · commits 0bd010a + workflow SHA fix; CI run 38316637450 success (ubuntu + windows: ruff, mypy, 49 passed); golden workflow run 38316710288 success from a clean clone with LFS (1 passed, 1 skipped: zip-byte comparison skipped on a different zlib, member manifest identical) · pushed

2026-10-14 · user acceptance · 01.7 · David: "Accepted all 3, unless we can ACTUALLY refine and improve their accuracy". This covers the three concrete review-packet items, including batched fact/Hunter mechanics review. Interpretation: current evidence-bounded results accepted; pursue only affirmative accuracy improvements, preserve unsupported unknowns. Owner audit found no exact summon link for 13 ownerless engineering guardian actor/fight cases; no runtime correction supported. Domain clarification: "Correct, vanquished tentacle, battle chicken, dragonlings, all can be part of the hunters toolkit". Attribution is still individual-source evidence, not toolkit eligibility. Closing peer/Hindsight checkpoint follows; final §8 signoff not implied.
