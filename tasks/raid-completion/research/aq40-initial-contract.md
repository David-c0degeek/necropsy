# AQ40 implementation guardrails

Reviewed 2026-10-17. Continue the existing acquisition, normalization, raid
facts, static strategy, saved JSON and report/package seams. No new acquisition
or rendering engine. The existing PM-1/PM-2/PM-3 remain binding; this is their
AQ40 application, not a separate risk numbering scheme.

## Failed futures and constraints

- **PM-1: plausible advice hides incorrect capabilities.** A healer cleanses
  Huhuran's Wyvern Sting without accounting for removal damage; a Hunter tries
  to remove Berserk as though it were Frenzy; a tank uses a generic taunt swap
  on a threat-handoff encounter. Classic spell records distinguish 26180,
  26051 and 26068. Use conditional assigned recovery, separate Frenzy removal
  from Berserk and avoid unsupported taunt claims. No mandatory numeric Nature
  resistance, pet-soak suggestion or class-category-to-duty inference.
- **PM-2: static guides become measured opportunities.** Addon health warnings,
  timers and emotes become exact split, burrow, freeze or stomach windows.
  Pinned consumer code has prewarnings and scheduled callbacks, not a complete
  event boundary contract. Keep static strategy separate from observed effects;
  require exact caster/recipient/instance and actual transitions before adding
  windows. Ouro Sand Blast is 26102 and Sweep is 26103. Generic Birth 26586 is
  shared with C'Thun actors; its name alone cannot identify an Ouro emergence.
- **PM-3: a successful capture masks identity or evidence gaps.** Skeram 176525
  appears in a seasonal addon branch, yet an earlier candidate Era report lists
  that same-name NPC. Treat its identity as unresolved until raw report version,
  season, scope and event evidence establish it; do not silently exclude it or
  certify it as an image. Likewise, Twin Emperor target eligibility depends on
  the actual target and ability school, not a whole class label. Do not sum
  shared-health damage or infer WCL ranking exclusions from guide prose.

The first normal capture now resolves the Skeram identity question for six
specific fights: Classic gameVersion2, null classicSeasonID, NPC15263 casts
Summon Images747 and summons NPC176525 instances1–6 in three pairs. The
[independent raw enumeration](aq40-first-capture-context.json) preserves these
exact transitions. This supports image identity in those fights, not a global
season classifier, complete split windows or ranking eligibility.

## Evidence and regression gates

[Pinned primary consumer review](aq40-addon-source-review.json) preserves exact
source hashes; [Classic spell review](aq40-classic-spell-review.json) separates
spell identities, effect text and dispel metadata. Both are research, not frozen
actor or window oracles. Preserve original native archives and sidecars, budget
reserves and missing personal/pet evidence. Freeze independent raw actor and
recipient facts before production analysis. Verify source and installed saved
JSON, both pages and package; keep existing MC/BWL facts and Naxx output stable.

Proceed with guardrails. Initial static strategy is reversible at the AQ40 rule
files and does not certify phase, ranking, duty or full matrix acceptance.
