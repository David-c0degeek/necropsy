> Current status: COMPLETE — David approved the delivered implementation/limits and instructed final closure on 2026-10-15. Additional standalone Druid SME review was retired explicitly; unperformed adjudication is not claimed. Earlier pending passages are historical.

# Shared class playbook review

Engineering is implemented for all nine Classic Era classes. Human product/domain review is pending (05.4), as are the original Druid domain gates. Claude pairing was ended by the user.

## Open the generated examples

| View | Practice page | What to inspect |
|---|---|---|
| Your Balance raid | [Playbook](../../workspace/druid-balance-view/playbook.html) |15bosses; Sapphiron has no personal DPS grade; faction leaders and separate collapsed overall comparison |
| Your missing-personal Tank | [Playbook](../../workspace/druid-tank-view/playbook.html) | Leader practice remains useful without claiming personal tank experience |
| Hunter | [Playbook](../../workspace/hunter-ability-use/playbook.html) | Shared ability-use comparison and established plan hierarchy |
| Mage Fire | [Playbook](../../workspace/class-mage-fire/playbook.html) | Core cast timing and cadence |
| Paladin Holy | [Playbook](../../workspace/class-paladin-holy/playbook.html) | Healing spells, opener and cooldowns; HPS is not quality |
| Priest Shadow | [Playbook](../../workspace/class-priest-shadow/playbook.html) | Damage duty, spells and resource context |
| Rogue Assassination | [Playbook](../../workspace/class-rogue-assassination/playbook.html) | Ranking category is not a talent-tree diagnosis |
| Shaman Restoration | [Playbook](../../workspace/class-shaman-restoration/playbook.html) | Effective healing, spells and assigned-target caveats |
| Warlock Destruction | [Playbook](../../workspace/class-warlock-destruction/playbook.html) | Actor casts and separate pet/summon evidence |
| Warrior Protection | [Playbook](../../workspace/class-warrior-protection/playbook.html) | Incoming-hit tank evidence; DPS-duty sources excluded from tank comparison |
| Priest Holy budget stop | [Playbook](../../workspace/class-priest-holy/playbook.html) | Honest unavailable personal/reference data; this is not a real healer fixture |

These generated files are ignored local artifacts. Portable fixture archives, hashes, member manifests and coverage provenance live in tests/golden/classes/; reproduce with `git lfs pull` then `uv run necropsy offline tests/golden/classes/raw/class-mage-fire.zip --out workspace/class-mage-fire` (substitute the fixture name).

## Evidence boundary

All fourteen added ranking-category contracts have synthetic production-path offline/package and desktop/mobile checks. Seven added classes have real public event captures, six actor entries each and independent raw amount checks. Budget-only Priest Holy verifies empty/unknown behavior; it provides no real healing evidence. Duties are inferred conservatively; assignments, optimal rotations and quality grades are not established. User review must accept or correct these limits; no agent test substitutes for that decision.

## Engineering receipts

Current receipts: 246 golden/acceptance tests passed with four existing xfails; 19 class integration checks; 56 synthetic and 48 real page/viewports. Ruff, mypy, build and isolated-wheel real Mage replay passed. Four legacy Hunter artifacts remain byte-identical. Unlimited scans covered 286,126,988 extracted raw bytes and 420,932,059 class output bytes, no findings. Source CI: [c016c4b](https://github.com/David-c0degeek/necropsy/actions/runs/38748441029), passed on Linux (907 tests) and Windows (908 tests), with platform/browser skips explicit in the job logs. Workspace receipts retain individual page/viewports and scans; source tests, provenance and arithmetic facts are committed for replay.


## Product approval

2026-10-15: David explicitly approved the delivered implementation and disclosed limits; further refinement will use another plan. Earlier pending-review statements above describe the verification handoff before this approval.
