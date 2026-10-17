# Naxx preservation reference

Baseline source: 30e89ce. Captured before new encounter-domain implementation.
The existing content inventory is tasks/necropsy/06-8-parity-inventory.md;
its historical Hunter prose is not an oracle for new actors.

- All 15 encounter IDs/sections remain present in both full generated pages.
- The original fact register contains 211 facts: 207 verified against raw,
  four disputed with recorded resolutions; 161 mandatory. Existing acceptance
  register passes. Preserve actual resolutions rather than upgrading labels.
- Existing fixtures: original Hunter historical export/subset/oracles, nine
  Druid fixture records and eight class records. One class record is a
  budget-only Holy Priest attempt; it is not usable Holy healing evidence.
- Druid and other class inferred role labels were accepted with explicit
  product limits. Their arithmetic/role regression is not independently
  adjudicated assignment ground truth and does not waive new raid validation.
- The frozen research/naxx-reference.json binds 101 rule, fixture, provenance
  and oracle files, 153,207,138 checked-out bytes. Subsequent hash verification
  found no changes. Full raw LFS data is available locally.

## Actual replay comparison

Extracted src from git source 30e89ce into ignored workspace and ran that engine
against the exact full historical archive and verified derived database. Ran
the current engine against the same archive. Both use installed version 0.4.0
and identical dependency versions; the earlier 0.3.1 taxonomy preview was
explicitly rejected as an incomparable baseline.

Initial comparison: analysis.json and Playbook identical; Report differed only
in the foundation's generic ranking-caveat wording, affecting package bytes.
Restored the historical Naxx wording through an inline template expression,
retaining the caveat for new raids without adding template whitespace.
After render from the unchanged saved analysis, **all four artifacts are byte
identical**: analysis.json, Report, Playbook and the package. Exact hashes are
in research/naxx-foundation-replay.json. Neither raw evidence nor saved analyses
were rewritten.

## Verification

- Ordinary full baseline after fixture repairs: 1227 passed, 251 deselected,
  418.57 seconds.
- Full existing golden suite: 244 passed, four expected failures, one browser
  test defect. The failing test used a cross-page href as a CSS selector;
  identical buggy code exists at baseline. Repaired the test to visit and verify
  every actual file/fragment destination, retaining all 17 navigation links and
  all 15 sections. Targeted actual Chromium rerun: 1 passed, 80.13 seconds.
- Current template compatibility change: all four baseline artifact bytes match;
  render/raid integration: 59 passed, 26.71 seconds.
- New raid raw/source tests do not replace these Naxx checks. Final shared-engine
  changes still need the relevant historical/live/legacy/class regression suites.

No new Naxx domain waiver, fixture completion, reviewer acceptance or publication
is inferred from these results.
