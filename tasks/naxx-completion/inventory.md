# Naxxramas inventory (box 00.5)

Taken 2026-10-21 at cc637a7. Every row was read from the tree at that commit.

## Encounters

The zone is 2006 (`src/necropsy/raids/naxxramas.py`, `zones/naxxramas.yaml`). The 15 WCL
encounter IDs follow `naxxramas.yaml` order.

| ID | Boss | Facts | Guidance `encounters` | Guidance `pet` | Ranking exclusions / native targets |
|---|---|---|---|---|---|
| 51118 | Patchwerk | yes | yes | | |
| 51111 | Grobbulus | yes | | | |
| 51108 | Gluth | yes | | yes | Zombie Chow excluded |
| 51120 | Thaddius | yes | yes | | |
| 51117 | Noth the Plaguebringer | yes | yes | | |
| 51112 | Heigan the Unclean | yes | | | Frenzied Bat, Plagued Bat excluded |
| 51115 | Loatheb | yes | yes | | Healing restriction, minimum one healing action |
| 51107 | Anub'Rekhan | yes | | | Corpse Scarab excluded |
| 51110 | Grand Widow Faerlina | yes | | | Naxxramas Worshipper excluded |
| 51116 | Maexxna | yes | yes | | |
| 51113 | Instructor Razuvious | yes | | | Death Knight Understudy excluded |
| 51109 | Gothik the Harvester | yes | yes | | Native targets: Gothik plus three wave types |
| 51121 | The Four Horsemen | yes | yes | | |
| 51119 | Sapphiron | yes | yes | yes | |
| 51114 | Kel'Thuzad | yes | | | |

- `naxxramas_facts.yaml` (rule `naxx-encounter-facts-v1`, retrieved 2026-10-13) covers all
  15 bosses. It also has a `creature_type_items` section.
- `naxxramas_guidance.yaml` (rule `naxx-execution-v1`) has `general`, `encounters` for 8 bosses
  and `pet` for 2 bosses. It has no `strategy`, `control`, `curses`, `effects` or `removals`
  section. The MC guidance has all of them.

## Existing archives

All 17 Naxx snapshot archives are `necropsy.live-snapshot` **formatVersion 1**, user endpoint,
zone 2006, partition 1. None is a v2 snapshot with whole-fight encounter streams.

| Archive | Subject faction | Bosses | Fights | Stopped |
|---|---|---|---|---|
| `classes/raw/class-mage-fire.zip` | Alliance | 51118 | 4 | |
| `classes/raw/class-paladin-holy.zip` | Alliance | 51118 | 6 | |
| `classes/raw/class-priest-holy.zip` | Alliance | 51118 | 0 | quota stop in subject rankings |
| `classes/raw/class-priest-shadow.zip` | Horde | 51118 | 6 | |
| `classes/raw/class-rogue-assassination.zip` | Alliance | 51118 | 6 | |
| `classes/raw/class-shaman-restoration.zip` | Horde | 51118 | 6 | |
| `classes/raw/class-warlock-destruction.zip` | Alliance | 51118 | 4 | |
| `classes/raw/class-warrior-protection.zip` | Alliance | 51118 | 6 | |
| `druid/raw/druid-balance.zip` | Alliance | 51118 | 6 | |
| `druid/raw/druid-feral.zip` | Alliance | 51118 | 6 | |
| `druid/raw/druid-guardian.zip` | Alliance | 51118 | 6 | |
| `druid/raw/druid-restoration.zip` | Alliance | 51118 | 6 | |
| `druid/raw/druid-tank-view.zip` | Alliance | 51118 | 5 | |
| `druid/raw/druid-mixed.zip` | Alliance | 51121 | 6 | |
| `druid/raw/druid-sapphiron-restoration.zip` | Alliance | 51119 | 6 | |
| `druid/raw/druid-balance-view.zip` | Alliance (cross-faction) | all 15 | 54 | quota stop at 51107 comparisons |
| `druid/raw/druid-balance-comparisons.zip` | Alliance (cross-faction) | all 15 | 54 | quota stop at 51107 comparisons |

- `haplina_naxx/raw/wcl_hunter_deep_export_20261012_145328.zip` is a pre-Necropsy exporter ZIP
  (no snapshot marker), with oracle playbooks. `tests/fixtures/haplina_naxx_subset.zip` is its
  subset and is also the desktop demo asset (`desktop/engine.py`, `scripts/build_desktop.py`).
- Only the two Balance view archives cover more than one boss, and both stopped on quota.
  Every other archive covers one boss. No archive was captured for full-raid cell evidence.
- Whether any of these can be a registered actor source is decided by `actor_problems` in 01.1.
  It needs live identity, a matching public report, the subject's class, category, metric and
  faction, and complete source and target actor streams.

## Places that treat Naxx specially

| Location | Behaviour | Consequence for this plan |
|---|---|---|
| `analysis/encounters/strategy.py:34` | `encounter_strategy` returns None for `naxxramas` | No strategy items for Naxx (01.2) |
| `report/analysis_json.py:819` | Skips the whole encounter-context block for `naxxramas`: raid interrupts, duty, effects, mechanic removals, exposure-removal correlations, control, curses, target aura windows, summons, cohort examples, strategy | Naxx pages lack every encounter-context section that MC cells were judged on |
| `analysis/encounters/duty.py:24` | `applies` only for zones 2000, 2002, 2005; called by class role inference (`classes/classic_era/combat.py:165,200`, `druid.py:245`) and by `control.py`, `effects.py`, `interrupts.py` | No duty context for Naxx; widening it changes role inference upstream of the pages (PM-1) |
| `snapshot/v2.py:67` | A v2 snapshot outside zones 2000, 2002, 2005 is rejected | A Naxx capture cannot carry encounter streams |
| `wcl/acquire.py:1014` | `supports_encounter_context` only for zones 2000, 2002, 2005 | Acquisition never collects Naxx encounter streams |
| `rules/classic_era/raid_scope.yaml` | Lists aq40, bwl, mc only | Naxx has no cells (01.1) |
| `analysis/generic/targets.py:161` | Native-target rule validated on Naxx (64 of 75 top-five) | Existing, keep |
| `wcl/acceptance.py:230` | The legacy acceptance gate is Naxx-only | Existing, keep |
| `raids/__init__.py:14` | `DEFAULT_RAID = NAXXRAMAS` | Existing, keep |

## Gap that 01 must add

The 01 integration analysis names the strategy seam only. The larger gap is encounter context.
Before a Naxx cell can be COMPLETE on a dimension that needs encounter context, Naxx needs:

1. Encounter-stream acquisition and the v2 snapshot for zone 2006 (`acquire.py`, `snapshot/v2.py`).
2. The encounter-context block in `analysis_json.py` for Naxx, with Naxx `control`, `curses`,
   `effects`, `removals` and `strategy` rules.
3. `duty.applies` gated on the archive's encounter-stream capability, not on the zone. It runs
   upstream of the page, in class role inference (`duty.guard_action_duty` and `duty.applies`
   in `analysis/classes/classic_era/combat.py` and `druid.py`), and in `control.py`,
   `effects.py` and `interrupts.py`.
4. Byte-identical output for every existing v1 Naxx archive and for the legacy Hunter and Druid
   pages, because those archives have no encounter streams.

## What existing archives can and cannot supply

The v1 archives cannot supply whole-fight encounter or critical streams. Any dimension that
reads them (raid interrupts, encounter effects and removals, exposure-removal pairs, control and
curse applications, target aura windows, summons, reference fight context) needs new v2 evidence.

They can still supply evidence where their scope is enough. `actor_problems` accepts a v1
archive with live identity, a public report and complete source and target actor streams.
Actor streams carry actor-target effects and boss-melee observations, and the archives carry
ranking metadata and the existing frozen facts and regression replays. D036 does not require
encounter streams for every dimension. 01.1 decides per archive and per cell which dimensions
each one covers; nothing here registers or rejects a cell.

**Acquisition strategy (proposal for 00.7/03.1):** recapture all 34 configurations in v2 so
that every cell has full encounter coverage from one capture, and keep the v1 archives as
reusable actor, fact, ranking and regression evidence where 01.1 accepts them. This is a
deliberate choice for uniform encounter coverage, not a finding that v1 evidence is unusable.
