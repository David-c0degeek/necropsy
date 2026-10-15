# Product UX overhaul

## Pre-mortem — proceed with guardrails

The redesigned overview could look authoritative while concealing missing evidence,
or make complete forensic output unreachable behind a convenient summary.

- **PM-1 (High): false certainty in triage.** Evidence: `render/view.py` preserves
  unknown values and small samples; `class_view.py` distinguishes personal data
  from learning examples. Summarize saved recommendations only, preserve their
  severity/confidence/control, separate missing personal data from no findings,
  and label comparison counts independently from metric-specific sample sizes.
  Verify missing, inferred, incomplete and tiny-sample fixtures.
- **PM-2 (High): forensic detail disappears.** Evidence: reference templates carry
  full cohorts/gear, source links, limitations and timelines; browser tests assert
  those contracts. Retain them in native disclosures, open ancestor disclosures
  on navigation, expand for print, and test content preservation and no-JS use.
- **PM-3 (Medium): visual polish breaks portable reports.** Evidence: render assets
  are inlined; browser tests cover hostile names, file URLs, local review state
  and zero requests. Use original CSS ornament only, retain storage keys, and
  verify 320/390/768/900/1280/1440 widths, light mode, keyboard and print.

## Implementation slices

1. Shared presentation-only summary, character identity and conservative triage.
2. Semantic theme system, application shell, action-first overview and boss views.
3. Progressive disclosures, comparison primitives, navigation/review workflow.
4. Responsive, accessibility, browser and deterministic-render verification.
5. Real output screenshots, product README and intent-based documentation.

Analytical JSON, acquisition, recommendation rules and output filenames stay intact.
No new score, automatic remote asset, runtime library or analytical inference.

## Delivery and risk review

- **PM-1 mitigated:** `experience.py` only orders and groups saved recommendations.
  Unknown personal data is distinct from no findings; inferred faction, missing
  medians and acquisition shortfalls remain explicit. Unit tests assert input
  immutability, conservative fallbacks, retained confidence and stable priorities.
  No analytical rules or JSON schema changed.
- **PM-2 mitigated:** full cohorts, equipment, event timelines, source links and
  evidence paths remain in native disclosures. Browser checks retain the original
  content assertions, cover keyboard revelation of nested details, no-JavaScript
  reading and print expansion/restoration. Report and Playbook keep their filenames.
- **PM-3 mitigated:** all styling and behavior is embedded. Original CSS/SVG
  ornament adds no asset requests. Local review keys and theme persistence remain.
  Browser checks cover hostile long names, blocked storage, all class accent
  contrasts, narrow layouts, reduced motion and automatic request detection.

The initial hierarchy hid recommendations beneath global setup and extensive
tables. The replacement starts with character identity, coverage, three existing
priorities and encounter triage. Boss actions precede explanations and evidence;
Playbook then leads with preparation while Report leads with comparison.

README, the documentation homepage, first-run guide and reading-results guide
now follow that same workflow. Technical evidence vocabulary remains documented
alongside plain-language labels. Class support and planned work are separate.
The banner, original monogram and screenshots use the same visual identity.

## Verification record

- `uv run ruff check .` — passed.
- `uv run mypy` — passed, 155 source files.
- Targeted render, class-report, package and browser suite — 118 passed.
- Final `uv run pytest -m 'not live' -q --tb=short` — **1,244 passed,
  1 deselected, 4 expected failures**, in 14m 28s. The final browser-only pass
  also passed all 48 scenarios; the last keyboard-focus correction passed its
  two focused navigation checks.
- Regression rerun after a stale in-memory view/template mismatch — 84 passed.
  The original full run was started during edits; its mismatch was not an
  analytical regression. The fresh complete offline run above closes the gate.
- `uv run necropsy offline tests/fixtures/haplina_naxx_subset.zip --out workspace/ux-demo-check --no-package`
  — generated the four-boss demo used for published screenshots.
- `uv run python -m scripts.capture_product workspace/ux-demo-check/analysis.json --out docs/images`
  — actual output at 1440, 1280, 900 and 390px, plus light, boss actions, next-pull
  guidance and expanded evidence. Captures reviewed visually.
- Full 15-boss Hunter and saved Restoration Druid output also checked at all four
  widths in both views: 16 viewport/view combinations, 32 collapsed/expanded
  layout states; no page overflow, script errors or automatic remote requests.
- Print preview inspected; severity colors corrected for paper and all disclosures
  expanded. Browser checks verify restoration afterward.
- `uv run python -m scripts.check_docs` — 229 local links across 22 maintained
  Markdown files resolve, including heading anchors and screenshot paths.
- `uv build --out-dir workspace/ux-dist` — wheel and source archive build; wheel
  contents include the presentation module, shared overview, CSS and JavaScript.
- `git diff --check` — passed.

## Deliberate boundaries and remaining work

- Browser verification uses Chromium. A formal assistive-technology audit and
  Firefox/WebKit coverage remain useful follow-up work; this is not an accessibility
  certification.
- Screenshots are reproducible product assets rather than pixel-exact CI baselines,
  avoiding font/platform snapshot churn. The browser suite asserts behavior and layout.
- Raid palettes beyond Naxxramas are presentation tokens only. They do not imply
  analytical support for those raids.
- Larger class/domain validation gaps remain documented in the class guides.
  No new live WCL run, authentication change or release publication is part of this
  presentation delivery.
