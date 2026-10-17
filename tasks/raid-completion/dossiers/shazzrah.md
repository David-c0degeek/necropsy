# Shazzrah â€” partial evidence dossier

Reviewed 2026-10-17. Initial sourced strategy and personal Curse exposure;
no complete boss/class/role/faction or domain acceptance.

## Identity and sources

Era zone2000/encounter50667, NPC12264, Humanoid; rules apply only to partitions1/2.
Primary [Classic strategy guide](https://www.wowhead.com/classic/guide/shazzrah-molten-core-strategy-wow-classic),
[Curse19713](https://www.wowhead.com/classic/spell=19713/shazzrahs-curse) and
[Deaden Magic19714](https://www.wowhead.com/classic/spell=19714/deaden-magic).
The Classic spell records distinguish a Curse increasing magic damage taken
from a hostile Magic buff reducing magic damage taken. Pages also contain
seasonal variants; those numbers and mechanics are not substituted for Era.
Deaden Magic's NPC listing identifies Shazzrah as Humanoid. No nominal duration,
Blink schedule, resistance threshold or movement interval creates an observation.
The Counterspell spell page was blocked; guide/comment disagreement about its
geometry is unresolved, so no numeric range, frontal model or measured lockout
policy is implemented. Class strategy distinguishes Mage/Druid curse removal
from Priest/Shaman hostile Magic removal. It does not imply assigned duty.

## Immutable observations

Two normal public finalized six-source captures, `mc-shazzrah-holy` and
`mc-shazzrah-hunter`, add12 independent actor cases. Registers/member manifests
under `tests/golden/raids/` retain exact identities, raw digests and source/target
termination. Original150 expectations remain unchanged; total27 archives/162
cases. All21,559,194 new extracted raw bytes pass unlimited gitleaks8.30.1.

| Actor | Exact source | Curse observation | Meaning |
|---|---|---|---|
| Almsivi, Holy | yGLZpJgXT3nW1CFK/fight17/actor10 | Apply6.500 s, fight end22.094 s |15.594 s known affected,6.500 s initial unknown; end censors an active effect. |
| Trazel, Hunter | Fzv2pKaA31GmTtcQ/fight45/actor125 | Apply9.683 s, fight end12.942 s |3.259 s known affected,9.683 s initial unknown; no removal inferred. |
| Brizzly, Holy comparison | JL3GPWMXrQNpczHF/fight28/actor9 | Apply11.339 s, remove14.805 s, duration24.774 s | Positive transition pair, no inferred removal assignment. |
| Kwyjibow, Hunter comparison | 4rz6C3VGTWkm7LAM/fight32/actor1 | Apply9.684 s, remove14.486 s, duration26.144 s | Positive transition pair. |

All six selected Holy source streams lack successful dispel effects removing
Deaden Magic19714. These actor streams do not establish a missing raid job,
available purge opportunity or boss buff uptime. No selected positive actual
Counterspell interrupt is claimed. A gap in healer casts cannot diagnose a
lockout. Curse duration alone cannot measure lost damage or a failed dispel.

## Runtime and remaining work

Per-raid YAML reuses shared state, coverage and saved static strategy. Both
pages show preparation, Blink recovery/tank pickup coordination, curse/removal
capabilities and healing range/backup plans. Optional saved facts and exposure
remain separate from personal grades. No renderer computes current policy for
old saved JSON; Naxx remains outside this Era policy.

New real golden replays, all162 independent raw cases,40 focused checks, fresh
installed replay outside checkout and both pages/packages pass. Eight structural
page/viewport checks pass; positive Holy Report and Hunter Playbook mobile
sections inspected. [Review receipt](../research/shazzrah-review.json) retains
limits. The snapshot/client schema does not change.

Open: actual Counterspell interrupts and recipient lockouts, Blink/threat/target
opportunities, positive hostile removals and assignment, pet/summon positioning,
loadout/item, all legal class/faction/tank examples, native/foreign/ranking
reconciliation and human domain/product acceptance. These two representative
roles and static strategy do not close any complete cell.

Class-filter correction: independent catalog review caught Shazzrah hostile
Magic-removal applicability using Rogue WCL ID8 instead of Shaman9. Corrected
to Priest7/Shaman9. All nine class names now independently check curse and
hostile-removal capabilities against the shared catalog;8 strategy tests pass
(0.39 s). Reviewed every current MC/AQ/BWL class-specific strategy filter; other
filters agree with their intended classes. Earlier Holy/Hunter observed windows
and raw expectations are unaffected. Lesson: numeric membership tests can mirror
a wrong policy; assert semantic class names for capability rules.
