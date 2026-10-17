# Blackwing Lair implementation guardrails — 2026-10-17

Initial expansion uses the existing raid facts/strategy/effect/window contracts,
shared normalizer and saved JSON renderers. Evidence collection is already
active under01. Incremental04 work can proceed beside unfinished02, like D006;
no full subject or matrix closure follows from initial static strategy.

## Pre-mortem and verified assumptions

- **Version bleed:** DBM supports later clients and seasonal replacements in the
  same files. Pin source revision efc7ed4e3f448b783296758e31f37bd3a46cabaf;
  exclude367987 Vael,367369 Broodlord,366305 Firemaw and Chromaggus468199/
  467884/467883/468594. A database may show seasonal effect overrides too.
- **Guide prose becomes measured phases:** all38 captured fight bundles have
  null phaseTransitions. Six Razorgore scopes contain no19873/23040 markers;
  durations16.571–38.203 seconds cannot certify the egg-control stage.
  Remaining add activity is not proof that egg control lies within WCL bounds.
  Nefarian class calls use addon monster-yell state; no nominal30-second timer
  may become an observed window. Drakonid count or20% health is not a captured
  boundary. Keep physical opportunities, phase totals and ranked totals unknown.
- **Misclassified removal:** Shadow of Ebonroc23340 has no dispel type in the
  Classic spell record, despite a guide calling it a curse. Implement tank
  handoff strategy, not a decurse claim. Veil of Shadow22687 is separately verified as a Curse in the Classic tooltip;
  the guide links different same-name23224, so do not borrow its duration. Flamegor23342 and Chromaggus23128 require Hunter enrage
  removal; no blanket Priest/Shaman purge capability.
- **Wrong vulnerability school:** primary addon maps22277 Fire,22280 Nature,
  22278 Frost,22279 Shadow,22281 Arcane. Actual Era All streams contain all five
  applied/removed aura IDs in one Chromaggus fight. No Holy/physical window,
  nominal duration, guaranteed damage gain or rotational score follows.
- **Missing personal evidence:** Fireflyy's Nefarian playerDetails lacks factionID.
  Public complete cohort actors remain useful; character faction and another
  fight cannot certify this personal fight. Do not synthesize personal zeroes.
- **Combined mode contamination:** WCL50631 is distinct from50614/50615.
  DBM mode flags do not define WCL encounter availability. Existing Era captures
  contain both original dragons; never sum individual scores/durations or add
  seasonal combined abilities. Rule scope remains Era1/2 only.
- **Regression:** restrict new policies to BWL encounter IDs. Verify named-class
  applicability, actor-only/partial unknowns, saved JSON rendering, both pages,
  installed wheel/package and unchanged Naxx outputs. Roll back module rules
  independently; immutable archives and frozen measurements remain intact.

## Evidence and sources

[Native acquisition receipt](bwl-full-cli-first-attempt.json),
[independent All enumeration](bwl-first-capture-context.json), and
[pinned primary addon identities](bwl-addon-source-review.json) retain exact
capture/source hashes. These research receipts are not accepted matrix sources.

[Classic Shadow of Ebonroc](https://www.wowhead.com/classic/spell=23340/shadow-of-ebonroc)
confirms no dispel type. [Hourglass Sand19183](https://www.wowhead.com/classic/item=19183/hourglass-sand)
cures the user's Bronze affliction. The first and resumed raw scans passed. The full resume has53 public selected
actors,106 player and106 global complete scopes, with one pet owner missing.
Independent actor acceptance and phase/ranking reconciliation remain separate gates.
