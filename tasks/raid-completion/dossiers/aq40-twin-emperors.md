# Twin Emperors — partial evidence dossier

Reviewed 2026-10-17. Era zone2005/encounter50715; catalog NPCs 15275, 15276.

[Encounter source](https://www.wowhead.com/classic/guide/twin-emperors-veklor-veknilash-temple-of-ahnqiraj-strategy); [pinned primary consumer](https://raw.githubusercontent.com/DeadlyBossMods/DBM-Vanilla/efc7ed4e3f448b783296758e31f37bd3a46cabaf/DBM-Raids-Vanilla/AQ40/TwinEmps.lua).
[Classic spell review](../research/aq40-classic-spell-review.json) and
[implementation guardrails](../research/aq40-initial-contract.md) constrain versions and interpretation.

Veknilash (15275) and Veklor (15276) retain separate targets despite shared health. Twin Teleport (799/800), Unbalancing Strike (26613), Mutate Bug (802) and Explode Bug (804) are distinct.

Veklor resists physical attacks; Veknilash has magic immunities with a Holy exception. Verify the actual ability and target, not the class label alone.

Teleport recovery changes tank and healing duties. Addon timers cannot define observed safe attack windows.

Initial static strategy is separate from personal findings. Full raw actor,
phase/opportunity, ranking, both-faction/category and domain acceptance remain
open; no guide timer or addon prewarning certifies an observed boundary.
