# Healer analysis corrections

## Pre-mortem and implementation guardrails

Proceed with guardrails. Saved snapshots remain immutable; regenerate outputs offline.

- **PM-1 (Medium): false healer duties and advice.** [evidence:
  `analysis/classes/classic_era/druid.py:_duties`, `report/druid.py:_recommendations`]
  Lowering thresholds globally would classify incidental heals as assignments;
  throughput/cast differences can reflect assignments rather than mistakes.
  Keep the one-action threshold in Loatheb encounter data only, preserve stream
  checks and mixed-duty detection, suppress cadence advice on restricted-healing
  encounters, and label new comparison findings as low-confidence reviews.
  Detection: targeted positive, negative and incomplete-stream regressions.
- **PM-2 (Medium): invented certainty from missing metadata.** [evidence:
  `report/druid.py:comparison_key`, `_event_comparison`, `experience.py:experience`]
  Removing the talent gate could imply unknown builds match; hiding all missing
  metrics could make a partial analysis appear complete. Keep builds unknown,
  preserve the category/role/faction/difficulty/partition gates, list unavailable
  role-relevant measurements and reasons, and retain unknown input values.
  WCL's optional overheal field uses sparse-zero semantics, verified against
  WoWAnalyzer `src/parser/core/Events.ts` and
  `src/parser/shared/modules/throughput/HealingDone.tsx` on branch `midnight`.
  Default only absent fields to zero; null/malformed fields and incomplete
  source coverage must stay unknown. Verify both positive and negative cases.
  Detection: missing-build cohort and rendered-warning regressions.

## Scope

1. Encounter-aware healer inference; optional build comparison context.
2. Evidence-backed healer reviews for cadence/throughput and cooldown usage.
3. Measurement-specific comparison and assessment limits in the shared reports.
4. Focused regressions, required checks, and replay of the supplied Drunkbear snapshot.

## Resolution

- PM-1: **Mitigated**. Loatheb alone uses a one-heal signal; the existing
  cast-share and complete-stream requirements remain. Regression cases cover
  no heals, one/two heals, incomplete streams and incidental off-healing.
  Cadence/throughput reviews are suppressed under Corrupted Mind. Comparative
  findings retain low confidence, assignment caveats and recorded values.
- PM-2: **Prevented**. Build metadata is optional, unknown build matches remain
  null, and known differences exclude unknowns. Existing role/faction/category
  gates remain. Primary-measurement warnings retain unknown reasons and samples.
  Sparse zero-overheal handling is tested separately from null/malformed values
  and incomplete streams.

## Verification

- Ruff lint/format, strict mypy and source/wheel builds passed.
- 51 focused healer/Druid/product tests and 36 focused/golden replay tests passed.
- Full fast suite: **1,074 passed, 251 deselected** in 335.54 seconds.
  Command: `uv run pytest -m "not golden and not live and not acceptance" -q --tb=short`.
- All eight Druid desktop/phone browser regressions passed. The interactive
  browser connection was unavailable; automated rendered-page checks passed.
- Replayed the original report's latest 90-fight snapshot, SHA-256
  `9be31bf9eb216dbd10c55d8100f3ee6b31521d331948b5f4aecaab92fa4623d1`.
- Result: 15 personal encounters, 74 eligible references, 27 low-confidence
  review findings (14 throughput, 8 cadence, 4 cooldown, 1 overhealing).
  Loatheb retains four references and has no cadence/throughput finding;
  Kel'Thuzad retains five despite unknown talents. No primary healing comparison
  is unavailable. Original event/pet coverage limitations remain intact.
- Independently counted and deduplicated raw heal events in all 15 personal
  fights: effective healing and sparse-zero overhealing match the analysis.
- Refreshed original saved HTML, analysis and ZIP after backing up the previous
  outputs and checkpoint under `workspace/drunkbear-before-healer-fix-20261016`.
  Revalidated checkpoint ownership digests after publication. No API acquisition
  or raw snapshot modification was needed.
- Release 0.3.1 authorized by the user. Build and verify all native packages
  on a temporary release branch; publish and verify assets before switching
  main installers. Existing installations are not modified by publication.


## Release 0.3.1

Published [v0.3.1](https://github.com/David-c0degeek/necropsy/releases/tag/v0.3.1)
from `bc1b310dc504468b8f26735c901678b87f5468b0` after:

- [Python CI](https://github.com/David-c0degeek/necropsy/actions/runs/38895236311)
  passed Windows, macOS and Linux.
- [Native CI](https://github.com/David-c0degeek/necropsy/actions/runs/38895236316)
  passed all four platforms, including fresh private installation,
  GUI/engine readiness, checksum refusal and failed-upgrade recovery.
- Final assembled wheel/sdist passed unlimited-size gitleaks scans, isolated
  installed public CLI flow, offline replay and exported-package integrity.
- Exact Windows CI archive passed the native-window offline example, report
  navigation, review persistence, saved library and save-before-quit checks.
- Its frozen 0.3.1 engine independently replayed the original 90-fight snapshot:
  15 personal encounters, 74 eligible sources, 27 findings. Loatheb retained four
  sources with no cadence/throughput finding; missing-talent Kel'Thuzad retained
  five and produced a review finding.
- All nine public release assets were downloaded without authentication and
  SHA-256 verified against the assembled bundle before main installers switched.

Local receipts: `workspace/release-0.3.1-distribution-final.json`,
`workspace/release-0.3.1-public-verification.json`, and per-platform bootstrap
receipts under `workspace/release-0.3.1-ci/`. Installed user app was not replaced.
