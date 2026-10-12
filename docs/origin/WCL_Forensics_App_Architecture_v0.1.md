# WCL Forensics — Product & Architecture Specification v0.1

## Product goal

A local-first Warcraft Logs analysis application.

User pastes a Warcraft Logs character URL. The app:

1. Resolves the exact game/site, character, faction, class, WCL spec/role, raid zone and ranking partition.
2. Builds a fair benchmark cohort by default:
   - same game/version
   - same zone/encounter
   - same partition
   - same class
   - same WCL spec/category
   - same role
   - same faction
3. Downloads the user's best/relevant fights plus benchmark fights.
4. Normalizes the WCL data into a reusable local analytical database.
5. Runs generic, class-specific and encounter-specific forensic analyzers.
6. Produces:
   - interactive offline report
   - boss-by-boss playbook
   - full benchmark tables
   - raw evidence / CSV exports
   - recommendation/confidence metadata
7. Optionally shows cross-faction absolute-ceiling comparisons, clearly separated and heavily caveated.

The Haplina Classic Era Naxxramas report is the golden reference implementation.

---

# 1. Product principles

## 1.1 Same-faction by default

Cross-faction comparisons are disabled by default.

The primary cohort must match the subject's faction.

If the user explicitly enables cross-faction comparisons, the UI must show both:

- **Realistic benchmark** — same faction
- **Cross-faction ceiling** — other faction / all factions

Cross-faction data must never silently replace the same-faction recommendation.

The report must explain detected faction-specific advantages such as:
- Windfury
- Shaman vs Paladin support
- racial cooldowns
- racial pet/melee bonuses
- faction-specific gear/content when relevant

## 1.2 Class + spec + role, not class alone

Never compare:
- Balance Druid vs Restoration
- Feral DPS vs Druid Tank
- Warrior DPS vs Warrior Tank
- Healing Paladin vs Tank Paladin
- etc.

Use WCL's own ranking taxonomy as the primary classification where available:
- class
- spec/category
- role

Then inspect talents and behavior as a second layer.

## 1.3 Exact build is a feature, not always the top-level filter

A WCL category can contain multiple talent builds.

Example:
- WCL may classify Classic Hunters under Marksmanship.
- Actual top builds can be 20/31/0, 5/31/15, etc.

The benchmark filter should first match the WCL category/role.
Then the analyzer should:
- fingerprint actual talents
- cluster builds
- report which build dominates
- compare the user to the appropriate build cluster when sample size supports it

Do not over-filter to an exact talent allocation if that would destroy sample quality.

## 1.4 Evidence levels

Every important claim in the report gets an evidence type:

- **Observed** — direct WCL/API field or direct event
- **Derived** — deterministic calculation from observed events
- **Inferred** — rule-based inference
- **Unknown** — not supported by available data

Examples:

Faction:
- Observed

Orc:
- Observed/derived only when Blood Fury or a reliable game-data race field proves it

Windfury:
- Confirmed when buff/extra-attack evidence proves it
- "Not observed" when no evidence exists
- Never automatically label "No Windfury" just because no proc occurred

Pet family:
- Observed when WCL/game data says it
- Inferred when ability compatibility uniquely or strongly implies it

## 1.5 Separate player execution from environment

Each recommendation should be classified as one of:

- **Player controllable**
- **Gear/build**
- **Pet**
- **Raid assignment**
- **Raid speed/environment**
- **Faction/racial/external**
- **RNG / low-confidence**

This prevents advice such as telling a player to "play better" when the ranking gap is actually a 20-second Sapphiron speedkill or a Horde-only Windfury interaction.

---

# 2. User flow

## Step 1 — Paste WCL character URL

Examples:
- /character/id/<id>
- /character/<region>/<realm>/<name>

The URL parser resolves:
- WCL site family (Vanilla / Classic / Fresh / SoD / Retail as later supported)
- character ID or name/server/region
- canonical character ID where possible

## Step 2 — Authorize WCL

Desktop application should use OAuth PKCE.

Reason:
- do not ship a client secret in a desktop binary
- supports `/api/v2/user`
- allows user-authorized/private/archive access where the WCL account permits it

Tokens go in the OS keychain and never into report exports.

The app can later support a hosted backend/client-credentials mode for anonymous public analysis.

## Step 3 — Resolve context

Resolve:
- faction
- class
- supported WCL specs/categories for that game/zone
- role
- level
- available zones
- partition
- difficulty / raid size where relevant
- character rankings

User confirms:
- raid/zone to analyze
- partition if multiple meaningful choices exist

## Step 4 — Role/spec resolver

Resolution order:

1. WCL ranking role/category
2. WCL spec/category
3. CombatantInfo talents
4. Behavioral verification
5. User override if confidence is not high

### Druid edge case

Possible outputs:
- Balance DPS
- Feral DPS
- Tank
- Healer

Tank evidence can include:
- WCL role=tank where available
- Bear/Dire Bear uptime
- boss target/threat/incoming-damage profile
- Maul/Swipe usage
- tank cooldown/debuff responsibilities

### Warrior edge case

Possible outputs:
- DPS
- Tank

Tank evidence can include:
- WCL role=tank
- Defensive Stance
- threat pattern / boss target time
- incoming damage
- tank-specific abilities/cooldowns
- gear context

Behavioral rules verify classification; they should not casually override WCL's ranking category.

## Step 5 — Build comparison cohort

Default comparison key:

```
site/game-version
zone
partition
encounter
difficulty/size
class
WCL-spec/category
role
faction
```

Fetch ranking pages until enough **same-faction** candidates are available.

Recommended cohort:

- top 5 same-faction fights: deep event forensics
- top 20–30 same-faction rows: robust build/gear/statistical context
- optional cross-faction overall #1/top 5: absolute ceiling, user opt-in only

Do not assume the current overall top 5 contains five usable same-faction comparators.

## Step 6 — Acquire data efficiently

Two-pass acquisition:

### Metadata pass
For 20–30 same-faction candidates:
- rankings
- gear
- talents / CombatantInfo
- report/fight metadata
- kill duration
- basic pet/actor metadata

### Deep-event pass
Download full/deep events only for:
- user's selected fight
- top 5 same-faction benchmark fights
- optional cross-faction ceiling fight
- additional anomaly/reference fight when needed

Cache by:
```
site + reportCode + reportRevision + fightID
```

Resume interrupted jobs.

Read WCL `rateLimitData` continuously and pace dynamically.

## Step 7 — Normalize locally

Keep immutable raw data and a derived analytical database.

Recommended:

```
workspace/
  raw/
    reports/...
  db/
    analysis.duckdb
  cache/
  generated/
```

DuckDB tables:

- characters
- analysis_jobs
- zones
- encounters
- benchmark_sets
- reports
- fights
- actors
- pets
- abilities
- events
- combatant_info
- gear
- talents
- buffs
- debuffs
- derived_features
- evidence
- recommendations

Raw WCL JSON is kept so analyses can be re-run without downloading again.

---

# 3. Analyzer architecture

## Generic analyzers

Work for every class:

- fight duration / phase availability
- DPS / HPS / damage taken
- casts per minute
- cooldown timeline
- buff/debuff uptime
- crit/miss/resist
- resource flow where available
- target switching
- target-integrity / padding detection
- gear comparison
- talent/build fingerprint
- consumables/world buffs
- racial usage
- external buffs
- Windfury evidence
- pets/guardians
- deaths
- raid-speed/environment effects

## Class plugins

Interface concept:

```python
class AnalyzerPlugin:
    identity
    supported_games
    supported_classes
    supported_specs_roles

    classify_build(...)
    extract_features(...)
    analyze_rotation(...)
    analyze_resources(...)
    analyze_cooldowns(...)
    analyze_gear(...)
    analyze_external_buffs(...)
    analyze_pets(...)
    make_recommendations(...)
```

Complex logic is Python.
Stable metadata/rules should live in versioned YAML/JSON.

### Hunter / Classic Era plugin — first implementation

- Auto Shot cycle reconstruction
- Aimed/Multi opportunity analysis
- Auto clipping
- Rapid Fire
- Quick Shots
- Renataki / Refocus
- FD trinket swaps where inferable
- Raptor / melee weaving
- pet uptime / deaths / skills
- guardian/engineering usage
- ammo / scope where observable
- Hunter's Mark
- hit/crit context
- faction/racial/Windfury normalization

### Future Druid plugins

Balance:
- Starfire/Wrath cadence
- Nature's Grace interactions
- DoT usage
- mana / Innervate
- consumables
- cooldown/buff timing

Feral DPS:
- powershifting
- energy tick/cycle
- shred/rip/bite usage
- MCP and item swaps where relevant

Druid Tank:
- Maul/Swipe
- rage
- Bear uptime
- threat
- incoming damage
- mitigation
- MCP
- tank assignments

### Future Warrior plugins

DPS:
- BT/MS/WW/Execute cadence
- rage use
- Heroic Strike queue behavior where reconstructable
- stance changes
- Windfury
- execute-phase usage

Tank:
- threat
- Defensive Stance
- Shield Block/mitigation where relevant
- incoming damage
- boss target time
- rage usage
- survival vs threat gearing

---

# 4. Encounter plugins

Class logic alone is not enough.

Each encounter can define:

- native encounter target IDs
- foreign/padding targets
- phases / downtime
- expected movement windows
- burst windows
- boss-specific pet hazards
- special raid assignments
- relevant debuffs/buffs
- known parse distortions

Examples from Haplina:

Gothik:
- detect non-native Naxx trash inside the fight
- show raw leaderboard DPS and native-target-only DPS separately

Kel'Thuzad:
- detect MC-control utility:
  - Freezing Trap
  - Scatter Shot
  - Rocket Helmet/Reckless Charge
- classify the lost rotation window as raid assignment rather than simply "missed casts"

Sapphiron:
- explicitly separate player execution from speedkill/raid-environment gap

---

# 5. Benchmarking model

Every boss should expose at least three views.

## A. Same-faction realistic ceiling — DEFAULT

Same:
- class
- WCL spec/category
- role
- faction
- partition
- encounter

This drives the playbook.

## B. Robust elite baseline

Same-faction top 20–30 metadata cohort.

Used for:
- gear dominance
- build dominance
- medians
- pet medians
- cooldown timing distributions
- shot/cast rates

Flag outliers instead of letting one rank-1 gimmick control the recommendation.

## C. Cross-faction ceiling — OPT-IN

Strong warning.

Display:
- absolute rank
- faction/race evidence
- faction-specific buffs
- Windfury evidence
- why this is or is not reproducible by the subject

Never silently merge this into same-faction medians.

---

# 6. Environment and bias model

For each fight create:

```text
Faction
RaceEvidence
BuildFingerprint
Role
WorldBuffProfile
ExternalBuffProfile
WindfuryStatus
RaidKillDuration
PetProfile
GearFingerprint
TargetIntegrity
RaidAssignmentFlags
```

Windfury status:

- CONFIRMED
- NOT_OBSERVED
- UNKNOWN

Race status:

- API_CONFIRMED if a reliable structured field becomes available
- RACIAL_EVENT_CONFIRMED
- INFERRED
- UNKNOWN

The UI shows the evidence source.

---

# 7. Recommendation engine

A recommendation is a structured object, not just prose.

Example:

```json
{
  "boss": "Patchwerk",
  "category": "rotation",
  "severity": "high",
  "confidence": 0.96,
  "controllability": "player",
  "finding": "Aimed Shot usage below same-faction elite cadence",
  "evidence": [...],
  "recommendation": "...",
  "benchmark": {...}
}
```

This lets the UI:
- sort by impact
- filter by confidence
- distinguish player vs raid problems
- link every claim back to raw evidence

Avoid pretending correlation is a precise DPS estimate.
Use:
- observed gap
- likely impact
- confidence
unless a simulator can actually model the counterfactual.

---

# 8. Generated package

Every completed job exports:

```
<character>_<zone>_analysis.zip
  report.html
  playbook.html
  manifest.json
  analysis.json
  tables/
    boss_summary.csv
    gear.csv
    pets.csv
    cooldowns.csv
    casts.csv
    benchmark_context.csv
  evidence/
    ...
```

Optional:
- raw snapshot
- DuckDB database

The HTML is self-contained and works offline.

The interactive desktop UI should be able to regenerate the static package at any time without WCL access.

---

# 9. Proposed implementation stack

## Phase 1 / fastest path

Backend/analyzer:
- Python 3.12+
- FastAPI
- Pydantic
- httpx
- Polars
- DuckDB
- Jinja2
- keyring
- pytest

Frontend:
- React
- TypeScript
- Vite
- CSS/Tailwind or a small custom design system
- ECharts/Recharts only where charts add real value

Desktop wrapper:
- Tauri

Packaging model:
- React/Tauri desktop shell
- Python analyzer bundled as a local sidecar service
- local-only loopback IPC/API
- static HTML report generator uses the same analysis JSON as the desktop UI

## Why not rewrite everything in TypeScript/Rust immediately?

The working exporter and forensic analysis are already Python.
The first goal is correctness and reproducibility.
Once the data contracts stabilize, performance-critical components can be moved if required.

---

# 10. Repository layout

```text
wcl-forensics/
  apps/
    desktop/              # Tauri + React
  backend/
    api/                  # FastAPI
    wcl/                  # OAuth, GraphQL, pagination, rate limits
    acquisition/
    normalize/
    benchmark/
    analysis/
      generic/
      classes/
        classic_era/
          hunter/
          druid/
          warrior/
      encounters/
        classic_era/
          naxxramas/
    reports/
    storage/
  rules/
    classic_era/
      abilities/
      items/
      racials/
      externals/
      pets/
      zones/
  tests/
    golden/
      haplina_naxx/
    unit/
    integration/
  docs/
```

---

# 11. Golden test fixture

The existing Haplina dataset becomes a permanent regression fixture.

Examples of expected facts:

- current downloaded top-five set contains 63 Alliance / 12 Horde rows
- Patchwerk Smcadogx:
  - Horde
  - Orc via Blood Fury
  - detected Windfury extra attacks
- Patchwerk Alliance examples:
  - Charies 9 Raptors
  - Andrenn 8
  - Xert 0
  - Xal 6
- Grobbulus pet death
- Gothik foreign-trash/padding anomaly
- KT MC-control utility window
- same-faction vs cross-faction recommendations

If a future code change breaks those known outputs, CI fails.

---

# 12. Milestones

## Milestone A — Headless Hunter/Naxx MVP

Command:

```text
wcl-forensics analyze <WCL-character-url>
```

Produces the same definitive package as Haplina automatically.

Requirements:
- PKCE OAuth
- link resolver
- faction-aware benchmark selector
- same-faction top-five collection
- caching
- Hunter/Naxx analyzers
- static definitive report/playbook generator

No GUI yet.

## Milestone B — Desktop UI

- paste link
- authenticate
- select zone/partition
- see acquisition progress
- inspect boss results
- export package
- open old cached analyses offline

## Milestone C — Generic classification framework

- WCL class/spec/role taxonomy
- build fingerprinting
- Druid tank/Feral/Balance/Healer
- Warrior tank/DPS
- confidence + override UI

## Milestone D — More class plugins

Start with:
1. Druid
2. Warrior
3. Rogue
4. Mage
5. Warlock
6. healer classes

## Milestone E — More raids / game variants

Only after the analyzer contracts are stable.

---

# 13. Immediate next development steps

1. Freeze the current definitive Haplina report as the golden expected output.
2. Create the repository and package layout.
3. Refactor WCL v6 code into a reusable `wcl` client library.
4. Replace client-secret desktop auth with PKCE.
5. Implement `CharacterContextResolver`.
6. Implement `BenchmarkSelector` with strict same-faction default.
7. Add paginated collection until five real same-faction benchmark fights exist.
8. Build local cache + immutable raw snapshot format.
9. Convert the current Hunter forensic scripts into a deterministic `HunterClassicEraAnalyzer`.
10. Convert Naxx-specific observations into encounter rules.
11. Make the analyzer output one versioned `analysis.json`.
12. Rebuild the definitive HTML entirely from `analysis.json`.
13. Add CLI end-to-end test using Haplina.
14. Only then build the React/Tauri UI.

This order prevents the UI from becoming tightly coupled to one Hunter report and gives us an analyzer that can later support every class.
