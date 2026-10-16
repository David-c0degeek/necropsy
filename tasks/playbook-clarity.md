# Report and Playbook clarity

## Scope and approach

Single-session, solo plan using the small-task tier of plan-from-template.
Turn Playbook into a boss action sheet; Report owns measurements and evidence.
Preserve typography, palette, summary, index, offline navigation and review marks.
No analysis/schema changes, new dependencies or release packaging.

## Plan

- [x] Inspect both rendering paths, existing guidance and offline/browser checks.
- [x] Separate Playbook content from Report; provide stacked before-pull,
  during-fight and raid-coordination sections, concise supported actions and
  direct boss links to Report. Avoid duplicate instructions and unsupported advice.
- [x] Communicate order with Start here; move severity/confidence classifications
  into Report explanations. Keep action-affecting uncertainty visible in Playbook.
- [x] Update affected documentation and regression checks; verify Hunter,
  Druid and other class pages at desktop/phone widths, missing personal data,
  evidence navigation, local review marks and no-JavaScript use.
- [x] Run lint, formatting, types, build and the fast suite; review the final diff,
  commit and push main as authorized by David on 2026-10-16.

## Guardrails and rollback

The likely failure is hiding an uncertainty along with reporting detail, or
leaving a sidebar link pointing to a removed section. Preserve warnings beside
actions and verify every local anchor in both pages. Keep full existing detail
in Report and analysis.json. Changes are reversible by reverting the commit;
saved snapshots and analytical rules remain unchanged.

## Verification

`uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy`;
`uv build`; `uv run pytest -m "not golden and not live and not acceptance" -q`.

## Progress and outcome

Implemented the shared action-sheet macro for Hunter and class/category views.
Report retains all prior comparisons, including the recorded-fact tables formerly
exclusive to Playbook. Preparation and execution are stacked there as well.
Conditional alternatives, unknown reasons, inferred membership, recommendation
limitations and missing-personal-data notices remain visible where needed.

Reading guide and README updated. Product screenshots regenerated from the
existing structured Hunter analysis and visually inspected at desktop and phone
widths. The capture script now opens Report for its evidence screenshot.

Final verification:

- Ruff lint and formatting pass; strict mypy passes for 183 source files.
- Wheel and source distribution build successfully. The wheel contains the new
  action-sheet template and final navigation code.
- Broad fast run: 1,146 passed, one early skip-link failure, 251 deselected
  (golden/live/acceptance). The failure came from focusing the overview heading
  after following the skip link. Focus handling now recognizes only the intended
  overview, evidence and boss destinations, and waits for initial page load.
  The exact failing test passes on rerun: all 1,147 fast cases are verified.
- Final browser suite after the navigation fixes: **49 passed** at desktop and
  phone widths, including all class categories, missing personal data, stacked
  layouts, source navigation, print, storage limits and no-JavaScript access.
- Focused rendering/class/healer regressions: **159 passed**; subsequent focused
  uncertainty and navigation checks: **54 passed**.
- Final diff and documentation-impact review complete. Main matches the fetched
  upstream before delivery; this checkpoint commits and pushes the approved work.

Close-out: preserve the shared shell and common action-sheet macro; keep
action-affecting caveats beside instructions. Do not turn missing data into a
rotation prescription. No remaining implementation blocker or manual action.
Release publication and refreshing existing saved outputs are outside this work.
