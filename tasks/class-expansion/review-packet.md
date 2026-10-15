> Current status: COMPLETE — David approved the delivered implementation/limits and instructed final closure on 2026-10-15. Additional standalone Druid SME review was retired explicitly; unperformed adjudication is not claimed. Earlier pending passages are historical.

# Druid review packet

Selected-spec implementation is verified; domain acceptance is pending. These reports are
generated local artifacts. Portable raw snapshots, manifests, provenance and
independent arithmetic checks live in `tests/golden/druid/`.

## Open these examples

| Example | Practice page | Full evidence | Facts to review |
|---|---|---|---|
| Your full Balance view | [Playbook](../../workspace/druid-balance-view/playbook.html) | [Report](../../workspace/druid-balance-view/report.html) | All 15 bosses have ranking references; 14 matching personal Balance fights; seven personal bosses have five event sources; Sapphiron has no personal grade; faction leaders drive the main view and overall top is collapsed |
| Public Feral Patchwerk | [Playbook](../../workspace/druid-feral/playbook.html) | [Report](../../workspace/druid-feral/report.html) | Stinkface; 166,047 damage over 108.1 s; form/resources/cast cadence and targets retain evidence limits |
| Your Restoration Patchwerk | [Playbook](../../workspace/druid-restoration/playbook.html) | [Report](../../workspace/druid-restoration/report.html) | 43,558 effective healing; missing overheal stays unknown; HPS is not healing quality |
| Tank and mixed Four Horsemen | [Playbook](../../workspace/druid-mixed/playbook.html) | [Report](../../workspace/druid-mixed/report.html) | Suncat tank: 107,140 incoming damage; Mìlfurion cohort: 24 cat + 92 bear casts and direct hits, hybrid, excluded from aggregate single-role comparisons |
| Your Sapphiron assignment | [Playbook](../../workspace/druid-sapphiron-restoration/playbook.html) | [Report](../../workspace/druid-sapphiron-restoration/report.html) | `arYtVP9kgnjBJp7K/48`; 24/0/27; 66 healing casts; 84,631 effective healing in 174.912 s; zero actor damage |
| Category is not duty | [Playbook](../../workspace/druid-guardian/playbook.html) | [Report](../../workspace/druid-guardian/report.html) | Suncat's Guardian Patchwerk parse has no tank hits; Harryjam's cohort entry has tank hits despite missing usable form intervals |
| Your Tank view with no personal tank data | [Playbook](../../workspace/druid-tank-view/playbook.html) | [Report](../../workspace/druid-tank-view/report.html) | Haplina has no matching personal Guardian row; Harryjam is a tank learning example at leaderboard #4; rank #1 Guardian metadata remains separate |

For another checkout, run `git lfs pull`, then
`uv run necropsy offline tests/golden/druid/raw/NAME.zip --out workspace/EXAMPLE`.
Use `druid-balance-comparisons.zip` for the latest full selected Balance view,
`druid-tank-view.zip` for your missing-personal Tank example,
`druid-mixed.zip` for Four Horsemen and
`druid-sapphiron-restoration.zip` for your Sapphiron example.

The latest Balance view uses **`druid-balance-comparisons.zip`** (the ninth raw
capture). It supersedes the earlier full-view example: all 15 ranking references
were captured before deep sampling. One or two event sources remain useful
individual comparisons with sample count; different known builds are context.
The main practice reference is your faction's eligible leader. If your personal
performance is absent, the playbook still gives the leader's recorded opener and
ability use, with no personal grade. Overall top across factions is a separate
closed disclosure, with faction/race/buff/assignment context. Interactive lookup
asks for faction and spec; explicit flags support scripts. Classic Era Hunter's
verified category is Marksmanship, with `all` retained for legacy Hunter lookup.

## Decisions David owns

These mirror the domain/product boxes. Supplying logs and authorizing fixtures
did not approve the resulting findings.

1. **01.4 — taxonomy:** accept or correct the separation of build, WCL category,
   query metric, actions, inferred duty and assignment. Provisional inference
   needs three recognized casts and at least 20% of categorized casts for a
   non-tank duty. Tank duty additionally needs repeated bear-only actions plus
   three direct encounter-enemy hits. Minor signals stay visible. Cast share is
   not time share or a proven raid assignment.
2. **03.4 / 04.4 — findings and advice:** review the damage, healing, tank and
   mixed examples. Correct misleading roles or advice. Your stated Sapphiron
   assignment agrees with the selected healing performance; public players'
   assignments remain unknown.
3. **06.3 — limits:** accept or correct sparse exact-build baselines, missing
   overheal/resources/threat/form intervals, low-confidence practice notes, and
   no whole-fight hybrid comparison. Activity spans are first/last action
   evidence, not continuous assignment phases. No requested role is deferred.
   Full Balance personal coverage does not certify complete comparison coverage,
   all-role raid coverage or universal optimal rotations.

Balance/HPS Sapphiron acquisition found public rows but no matching personal
Balance-category row; the subject correctly stays absent. The separate
Restoration/HPS capture supplies your actual healing example.

## Engineering evidence

- Latest broad local suite: 877 passed, with two subsequently added integration
  cases also passing. Serial golden/acceptance: 236 passed, four existing expected
  failures. The subsequently added full Balance golden also passed, checking
  all 15 independent actor-damage facts and personal/learning CSVs.
- Real-artifact checks: 32 page/viewport cases across eight outputs,
  zero automatic remote requests, no overflow or script errors; all eight outputs
  passed the existing acceptance artifact checker and output secret scans.
- Ruff lint/format, strict mypy and wheel/sdist build passed. Hunter JSON, both
  pages and shareable ZIP match the saved baseline byte for byte. All 26 recorded
  Hunter request bodies/endpoints also match the baseline.
- Gitleaks found no leaks in 169,740,861 initial extracted bytes or 62,401,552
  added extracted bytes, plus 32,499,807 Tank-view and 266,125,045 full Balance
  extracted bytes. The Balance output's 35,283,900 bytes were separately scanned
  without a per-file size cap. Raw ZIPs stay immutable.
- Claude mail 185 approved the corrected selected-spec runtime paths with zero
  blocking/important findings and 18 independent focused passes. Review exclusions
  (including docs, raw fixtures, most tests and broad/live/browser receipts)
  remain explicit in subject records; those are lead-verified. Optional nits
  were addressed at e8fed3e. Linux/Windows [source CI passed](https://github.com/David-c0degeek/necropsy/actions/runs/38704628831).
- Overlapping large replays produced a native loader failure; the full serial
  run passed without recurrence. Root cause remains unconfirmed.

## Selected-spec correction

David explicitly confirmed one spec/role per view, with all bosses visible.
Personal grading now requires matching category and evidenced duty. Missing data
gets an explanation plus an eligible learning example, without a fabricated
personal grade, median or gap. `--spec Balance`, `Restoration`, `Feral` and `Tank`
canonicalize to WCL categories; conflicting legacy category flags fail early.

The production CLI collected personal fights first, then learning comparisons,
prioritizing missing-personal bosses. The replacement run waited once for
1,712.99 seconds at the observed hourly reset. All 14 personal Balance fights were
retained; Sapphiron has Alyrian's acquired #1 example. Later comparison acquisition
stopped under the finalization reserve and stays explicitly partial. The snapshot,
replay, package, raw arithmetic and desktop/mobile pages were checked.

Source snapshot SHA-256:
`934d7a43f50ad27af2966a3f4efb852a3c791e56926ae87548734e4960783078`.

Agent checks never substitute for your domain decision.

## Latest comparison capture

Raw SHA-256:
`1c670a28e56ddf98b7df7b3e003817519ec9514a52ef7374eaa07836953d6a57`.
All 15 overall ranking identities and amounts are independently recorded from raw
first-page rows in the golden register. These scores are compared only with
saved WCL scores. Individual event comparisons retain their own metrics and
source count; metadata never enlarges those samples. Later deep-event coverage
remains partial after the reserved budget allowance. No reset wait was used.
Unlimited-size raw scan covered 268,170,221 extracted bytes without findings.
The updated full view passed artifact/package checks and four browser cases
(1400/390, both pages), including closed overall disclosures, zero remote loads,
no JS errors or page overflow, and working theme/search. Other receipts above
describe earlier checkpoints; the latest subject records carry final test/CI
and scoped review results for this correction.

Final engineering receipt: full serial golden/acceptance 238 passed / four
existing expected failures; 37 independent CLI passes, following 114 independent
focused passes; scoped review AGREE round2 with exclusions retained in subject
records. Eight latest real Balance/Guardian page cases pass, including the
closed overall disclosure and no-personal Guardian guidance. Four saved Hunter
artifacts remain byte-identical. Latest source CI passed: https://github.com/David-c0degeek/necropsy/actions/runs/38717484080.

Presentation update: Balance, Restoration and missing-personal Tank now use the
same metric cards, raid overview, plan panels, review marks and named gear layout
as Hunter. All supported classes share Ability use vs player, with counts and
uses/minute from recorded actor casts. [Hunter example](../../workspace/hunter-ability-use/playbook.html).
Missing personal/coverage values remain unknown. Latest engineering verification
is recorded after the scoped review and CI complete.


Latest shared presentation receipt:

Source ad833d8 is pushed. CI passed on Linux (867 passed, 27 skipped) and
Windows (868 passed, 26 skipped): https://github.com/David-c0degeek/necropsy/actions/runs/38727937515. Both deselected 243 tests.
Full serial golden/acceptance: 238 passed, four existing xfails, 895 deselected
in 386.84 s; the subsequent source-link-only correction passed all 27 report/
package integration checks. Latest raw replay and refreshed outputs for Balance,
Restoration, missing-personal Tank and Hunter passed all 16 desktop/mobile page
cases, artifact/package checks, theme/search/review persistence, no overflow,
remote requests or JS errors. All four saved legacy Hunter artifacts are byte
identical. New Hunter replays intentionally add ability evidence, table and CSV.
All existing shot counters match the generic counts across subset encounters.
Unlimited output-directory secret scans passed: Balance 50,093,915 bytes, Tank
53,215,139, Restoration 59,476,356, Hunter 3,398,300 (includes retained snapshots,
not only derived output). New commit-range scan also passed. Raw fixtures unchanged.
Claude190 agreed the design and191 supplied incorporated guardrails. Latest scoped
review request is still unread; no final independent verdict is claimed.
Human taxonomy/findings/product boxes remain open.
