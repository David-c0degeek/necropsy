# Production intake, 2026-11-11

The Naxx stage of the ordered campaign ended on 2026-11-11 at 16:55 UTC. All 34
configurations have one archive each, and every one is partial. This intake
takes in the 27 archives that are not already in the repository. The six
configurations from 2026-10-31 are unchanged. Balance DPS Alliance stays
represented by the registered measurement archive, as decided at the
2026-10-26 intake.

| Configuration | Archive | Coverage-complete bosses |
|---|---|---|
| Druid Guardian DPS Horde | `70621233-2006-20261101T123113.zip` | 10/15 |
| Druid Restoration HPS Alliance | `60117765-2006-20261102T031646.zip` | 12/15 |
| Druid Restoration HPS Horde | `77577270-2006-20261103T040708.zip` | 14/15 |
| Hunter Marksmanship DPS Alliance | `75928820-2006-20261103T162831.zip` | 11/15 |
| Hunter Marksmanship DPS Horde | `64181902-2006-20261104T151326.zip` | 11/15 |
| Mage Fire DPS Alliance | `62428883-2006-20261104T171719.zip` | 12/15 |
| Mage Fire DPS Horde | `62508348-2006-20261104T223319.zip` | 13/15 |
| Mage Frost DPS Alliance | `96494133-2006-20261105T033802.zip` | 13/15 |
| Mage Frost DPS Horde | `83910414-2006-20261105T054215.zip` | 5/15 |
| Paladin Holy HPS Alliance | `77152471-2006-20261105T150116.zip` | 11/15 |
| Paladin Protection DPS Alliance | `67666001-2006-20261105T232014.zip` | 9/15 |
| Paladin Retribution DPS Alliance | `76716431-2006-20261106T042624.zip` | 9/15 |
| Priest Holy HPS Alliance | `77573659-2006-20261106T154918.zip` | 11/15 |
| Priest Holy HPS Horde | `77516109-2006-20261107T143644.zip` | 10/15 |
| Priest Shadow DPS Alliance | `77122652-2006-20261107T163813.zip` | 9/15 |
| Priest Shadow DPS Horde | `66195792-2006-20261108T070712.zip` | 9/15 |
| Rogue Assassination DPS Alliance | `77022735-2006-20261108T142205.zip` | 12/15 |
| Rogue Assassination DPS Horde | `62246596-2006-20261108T183110.zip` | 6/15 |
| Shaman Elemental DPS Horde | `80764809-2006-20261109T140845.zip` | 11/15 |
| Shaman Enhancement DPS Horde | `74643978-2006-20261109T142333.zip` | 10/15 |
| Shaman Restoration HPS Horde | `62259058-2006-20261109T151537.zip` | 10/15 |
| Warlock Destruction DPS Alliance | `77751784-2006-20261109T171544.zip` | 11/15 |
| Warlock Destruction DPS Horde | `64322945-2006-20261110T064311.zip` | 12/15 |
| Warrior Fury DPS Alliance | `76296293-2006-20261110T135634.zip` | 11/15 |
| Warrior Fury DPS Horde | `75322236-2006-20261110T150026.zip` | 9/15 |
| Warrior Protection DPS Alliance | `75466963-2006-20261111T134356.zip` | 8/15 |
| Warrior Protection DPS Horde | `61334639-2006-20261111T164838.zip` | 10/15 |

The archives, with their `.entries` and `.sha256` sidecars, are in Git LFS
under `tests/golden/raids/raw/naxx-production-20261111/` (1.1 GB). Each one
matches its Tower sidecar and the SHA-256 that the runner state recorded for
that entry. The sources are the live capture directory
`/mnt/user/appdata/necropsy-naxx-capture-20261023/out/`; no separate Tower
retention copy was made.

## Strict read

`check.py` is the 2026-10-31 checker with new pins. It checks against the
campaign queue `tasks/capture-campaign/capture-queue.json` (`4f1a300a…`),
whose Naxx entries are the same as in the earlier queue. `receipt.json` holds
the result; a replay without `--out` must match it.

All 27 pass. No capture stopped. Every encounter, critical, player and pet
stream is complete (1,554 encounter, 1,554 critical, 3,192 player and 774 pet
streams). The pet-discovery listing is missing in every archive (187
listings). All archives are depth 3.

The archives are partial for these reasons only:

- the subject's own fight was not acquired at some bosses: the subject played
  another spec there, or, for Rogue Assassination Horde, WCL returned the
  name with a replacement character (`Jerv` + U+FFFD + `s`), so no actor matched it
  (6 bosses);
- pet ownership unknown or unresolved for some players;
- one combatant-context read with malformed event order (Clownform).

## Register fixes

Two bugs in `scripts/comparison_followup.py` came up on this data:

- Anonymous leaderboard rows (`hidden: true`, name `Anonymous`) have no
  `server` key, and the detector crashed on them. They now never match.
- Report catalogs spell realms without spaces (`PyrewoodVillage`), while
  leaderboard rows and snapshot participants keep them (`Pyrewood Village`).
  The detector refused every player from a realm with a space as "no unique
  selected player stream", and the freezer's owner check would have refused
  them too. Both now compare realms with spaces removed
  (`freeze_dps_ranking.realm_key`). Any other realm difference is still
  refused. All 97 such refusals in the first run had this cause; 13 of the
  Balance DPS Horde cells from 2026-10-31 gain admitted comparisons from it.

## Follow-up register

`followup-comparisons.json` is regenerated over the measurement archive, the
four 2026-10-31 DPS archives and the 21 new DPS archives (input list in the
commit message). 390 cells: 208 meet the minimum of 3, 166 need more
comparisons, 16 need admission work first.

Refusals that block whole configurations:

- 145 comparisons: the owner folder has no `pets.json`, because the
  pet-discovery listing is missing in every archive. This was the 28 raw
  refusals of 2026-10-31; it now refuses players of every class.
- 57 comparisons: published DPS contradicts raw events. 47 of them are Mage
  Fire (24 Alliance, 23 Horde). Both Fire configurations have 0/15 cells at
  the minimum.
- 85 comparisons: pet listings disagree. 74 of them are Shaman (38
  Enhancement, 36 Elemental, both Horde); totems are the likely cause, not
  yet checked. Both Shaman configurations are 0/15.
- 98 comparisons stay unverified under untested production exclusions
  (D025).

HPS archives (6) stay outside admission and are not in the register.

## What this does not do

No actor is registered, no policy is added and no cell changes status. The
missing pet listing, the Fire Mage arithmetic and the Shaman pet listings are
open findings for the next unit.
