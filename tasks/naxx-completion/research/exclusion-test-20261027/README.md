# Production ranking exclusions under the D022 freezer, 2026-10-27

Question: do the five Naxx bosses with production `ranking_exclusions` need
those lists to admit their comparisons in the Balance DPS Alliance capture? The
bosses are Anub'Rekhan, Gluth, Grand Widow Faerlina, Heigan and Razuvious.

`probe.py` (`20f6718c46c7`) ran on the PC after the agreed replacement-memory
baseline, at commit `3306e53` with the D022 freezer plus the typed arithmetic-mismatch exception. It used the Git LFS
measurement archive `caa199389d11` and its entries `72943a8af9c3`, and the
zone rule `src/necropsy/rules/classic_era/zones/naxxramas.yaml` (`49812f244499`). For
every attempt at these bosses (subject and comparisons, 30 in all, none
skipped), it runs the DPS freezer twice on the exact published row: with the
packaged exclusion list as explicit input, and with none. `receipt.json`
(`9a187ec95ae4`) records both outcomes and the damage to excluded targets.

Result: 28 attempts admit both ways, each with excluded damage 0 and identical
totals and residuals. The 2 refusals (Razuvious: the subject and Hotsndots) stop
on missing pet listings, which are ownerless guardians, before excluded damage
is measured. Nothing is claimed about their excluded damage.

So in this cell the excluded adds take no ranked damage from any admitted
attempt. The lists are not exercised: these rows neither confirm nor refute
them. Zero excluded amount also does not prove the excluded NPCs had no
activity.

## Decision D025 and its effect

The follow-up register admits a comparison at these bosses only when the
freezer admits it with the exact packaged list and its excluded damage is
exactly 0. Such a row is recorded as exclusion-neutral with the applied list.
Positive excluded damage, or an arithmetic mismatch under the list (a typed
freezer exception), stays unverified. Evidence and ownership failures stay
refused. Subject rows never count.

The regenerated `followup-comparisons.json` (`a6c097f16840`) clears all five
admission-missing cells: Anub'Rekhan, Gluth, Faerlina and Heigan with 5 admitted
each, Razuvious with 4 admitted and 1 refused. Two of 15 cells still need
follow-up, Loatheb and Patchwerk, both because of ownerless guardians, and that
follow-up is deferred (D024). This neither validates the exclusion lists nor
certifies a cell. Cell policies for these bosses need evidence that exercises
the exclusions and are separate work.
