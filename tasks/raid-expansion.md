# Independent Classic Era raids

Add AQ40, BWL and MC as independent modules alongside Naxxramas. A run selects
exactly one raid and generates its own snapshot, analysis, Report and Playbook.
Saved analyses expose their raid and can be filtered by raid.

## Pre-mortem and implementation guardrails

Failed future: a BWL run silently uses Naxx encounter rules or resumes as Naxx,
and its Playbook makes unsupported claims about ranked damage.

- **PM-1 (High)** — Raid identity is lost between resolution, acquisition and
  offline analysis. [evidence: wcl/context.py, wcl/acquire.py, snapshot/v1.py,
  report/analysis_json.py hard-coded Naxx]. Persist the selected WCL zone in the
  character URL/checkpoint and snapshot; resolve every downstream rule from that
  identity. Reject encounters outside the selected raid. Preserve legacy Naxx
  defaults and archives. Detection: focused cross-raid integration tests.
- **PM-2 (High)** — New raids inherit empirical Naxx ranking exclusions or boss
  advice. [evidence: rules/classic_era/zones/naxxramas.yaml and *_guidance.yaml].
  Use separate packaged rules per raid; label unvalidated exclusions explicitly,
  retain unknown facts, and verify that Naxx guidance never appears in new raids.
  Detection: rule and report tests; real-log validation remains outstanding.
- **PM-3 (Medium)** — Saved runs cannot be distinguished by raid, or imported runs
  resume against another zone. [evidence: tui/service.py saved titles and import
  URLs]. Preserve zone on import and expose raid metadata and filters in the
  library. Detection: library/bridge tests.

Verdict: PROCEED WITH GUARDRAILS. No schema migration or existing-output rewrite.

## Source verification

WCL Vanilla authenticated `worldData.zone(id).encounters` queried 2026-10-16:
MC 2000 / 50663–50672; BWL 2002 / 50610–50617 plus combined Ebonroc / Flamegor
50631; AQ40 2005 / 50709–50717. These are Classic Era IDs, not retail or SoD.
Public catalog: https://vanilla.warcraftlogs.com/zone/statistics/2005 .

## Implementation and risk disposition

- PM-1 — **Mitigated**: independent raid definitions and packaged rules; URL zone
  persists in checkpoints and saved sessions; snapshot readers/writers and cohort
  keys validate encounters against the selected module. Offline analysis reads
  the snapshot zone. Existing Naxx defaults and format-v1 archives remain valid.
- PM-2 — **Prevented**: new modules have their own rule/fact/guidance files.
  Unvalidated ranked totals and ranked target shares remain unknown; recorded
  WCL Hunter scores are retained as independently sourced comparisons. No Naxx
  boss guidance is reused in the new raids. Authored mechanics guidance and
  real-log exclusion reconciliation remain documented domain follow-ups.
- PM-3 — **Mitigated**: saved runs expose raid identity; desktop and terminal
  libraries filter by raid. Imported analysis URLs retain the document's zone.
  Tests cover independent saved runs, imported documents and both UI selectors.

## Verification

- Existing unit suite: 902 passed; 67 targeted unit checks passed after the score,
  context and packaging changes, including loading modules from an installed wheel.
- Full integration suite: 272 passed. Six final CLI/terminal checks also passed
  after adding explicit raid-option and invalid-selection coverage.
- Synthetic raid integration checks cover Hunter, Druid and shared class reports
  across all four raids: acquisition, validated snapshots, replay, both rendered
  pages, imports, module boundaries, resolution, saved libraries and terminal UI.
- Desktop synthetic Chromium check: four raid selectors, matching character raid,
  enabled analysis, saved-analysis filtering and mobile overflow; no JS errors.
- Python lint/type checks, desktop TypeScript/production build and diff checks pass.
- Real WCL encounter catalog checked; no full real-log acquisition/acceptance for
  the three new raids was performed. Native desktop account/UI acceptance remains
  separate from the synthetic browser check.
