# analysis.json

`necropsy offline` writes one `analysis.json` per run. It is the only input the
report and playbook renderers use, so everything they show must be in it.

```sh
uv run necropsy offline <snapshot.zip> --out out/            # temporary database
uv run necropsy offline <snapshot.zip> --out out/ --db work/full.duckdb   # keep and reuse it
uv run necropsy offline <snapshot.zip> --out out/ --cross-faction        # add the cross-faction view
```

The archive is always verified first: whole-file digest (against `--sha256` when
given), member safety, and, with `--entries`, every member against the manifest.
With `--db`, an existing database is then reused only when it was built by the
current database schema from that verified archive (same SHA-256); otherwise it is rebuilt under
the usual `ingest` safety rules (`--replace` is needed to overwrite a database built
from another snapshot). Without `--db`, a temporary database is created and removed
afterwards. The file is written atomically: a failed run leaves no partial file.

## Guarantees

- **Deterministic.** The same snapshot and options give byte-identical output: no
  wall-clock time, keys sorted, floats rounded to 6 digits, every list in a defined
  order (chronological lists stay chronological).
- **Every value carries its evidence.** Values are evidence objects as described in
  [`evidence-model.md`](evidence-model.md): `value`, `level`
  (`observed`/`derived`/`inferred`/`unknown`), `claim` (`value`/`complete`), and
  optional `rule`, `params`, `note`, `refs`, `coverage`. An `unknown` value has
  `value: null` and a `note` saying why.
- **Event references are capped.** Each reference lists at most 10 event
  occurrences (`uid`, `copy`) and always gives the full `event_count`. The database
  holds the rest.
- **Validated shape.** The document is the pydantic model
  `necropsy.report.analysis_json.AnalysisDocument`, validated before it is
  written; its JSON Schema is committed as
  [`analysis-json.schema.json`](analysis-json.schema.json), and a test fails if the
  two drift. Typed: the envelope (literal `schema_id`, `schema_version`, `mode`),
  options, snapshot, subject, zone, cohort, coverage, boss rules, entry headers,
  ceiling, exclusion counts, encounter findings and recommendations (enumerated
  controllability, severity and confidence; at least one evidence path). The
  analysis sections inside an entry (`environment`, `ranking`, `hunter`), the
  baseline and the findings keep free-form keys, but every evidence object nested
  anywhere in them is validated against the `Evidence` model (known level and
  claim, null value exactly when unknown, typed references). That nested check is
  done by the pydantic model (`EvidenceTree`) when Necropsy writes or a consumer
  validates with it; the exported JSON Schema cannot express it and shows those
  sections as plain objects. A consumer relying only on the JSON Schema gets the
  typed parts, not the nested evidence check.

## Top level (`schema_version` 1)

| Key | Content |
|---|---|
| `schema_id`, `schema_version`, `necropsy_version` | document identity |
| `mode` | `historical` for a snapshot replay |
| `options` | `cross_faction` |
| `snapshot` | archive SHA-256, export format, scope (`full`/`subset`), fight counts, database schema version |
| `subject` | the analyzed character (name, server, region, class) |
| `zone` | zone id, name, partition |
| `cohort` | how the comparison cohort was formed, and its `limitations` |
| `coverage` | stream, anomaly and snapshot-issue counts |
| `bosses` | one section per boss, in zone order |

## Boss section

| Key | Content |
|---|---|
| `encounter_id`, `boss` | the encounter |
| `rules` | encounter rules applied: ranking exclusions with the rule's `basis` (`empirical` — found from recorded rankings, not documented by WCL) and validation, and native targets |
| `subject` | the subject's selected kill: ranking damage, environment profile, Hunter analysis |
| `cohort` | the same structure for each comparison entry (same faction only, unless `--cross-faction`) |
| `benchmarks.baseline` | same-faction medians (Auto/Aimed/Multi per minute, Hunter-pet DPS, kill time, first Rapid Fire), shot-target ranges, weave adoption, talent / Darkmoon / item / trinket distributions, explosive and Rapid Fire use |
| `benchmarks.ceiling` | best same-faction entry inside the recorded top five, with its `membership` evidence |
| `benchmarks.cross_faction` | `null` unless `--cross-faction`; never merged into the baseline |
| `benchmarks.excluded` | entries left out of the baseline, by reason |
| `encounter` | target integrity (foreign-target share; unknown while any damaged target is unclassifiable, listed in `unclassified_targets`) and raid utility findings |
| `recommendations` | see below |

A median needs at least 3 known values; with fewer it is `unknown`, and nothing
built on it (shot targets, weave verdict, recommendations) is emitted as a
number. `benchmarks.baseline.membership` grades the same-faction selection: when
any faction in it is inferred, every median, shot-target range and the ceiling
are `inferred` too (see [`evidence-model.md`](evidence-model.md)).

## Recommendations

Each recommendation has `rule`, `category`, `controllability` (`player`,
`gear-build`, `pet`, `raid-assignment`, `raid-speed-environment`,
`faction-racial-external`, `rng-low-confidence`), `severity` and `confidence`
(`high`/`medium`/`low` — a heuristic evidence-quality tier, not a probability),
`finding`, `recommendation`, `observed`, `benchmark` (which view and how many known
values; empty for findings about the subject alone), `limitations`, and `evidence`: dotted paths into the same boss section,
for example `subject.hunter.shots.aimed_shot`. A recommendation never estimates a
DPS gain, and a rule whose inputs are unknown emits nothing.

## Historical mode limitations

A snapshot replay can only use what was recorded: the cohort is the overall top
five per boss, the same-faction ceiling is the best entry of the subject's faction
inside it, and medians come from at most five entries. `cohort.limitations` states
this in every document.
