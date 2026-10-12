# Necropsy roadmap

Source: `docs/origin/WCL_Forensics_App_Architecture_v0.1.md` §12.

| Milestone | Scope | Entry condition |
|---|---|---|
| A — Headless Hunter/Naxx | `necropsy offline <snapshot>` and `necropsy analyze <url>` produce the definitive package for a Classic Era Hunter in Naxxramas; same-faction default; evidence model; golden Haplina fixture | — (in progress) |
| B — Desktop UI | React + TypeScript + Vite in a Tauri shell; Python analyzer as a local sidecar; paste link, authenticate, select zone/partition, acquisition progress, boss results, export, open cached analyses offline. **PKCE public-client auth replaces the personal confidential client before any distribution.** | A's `analysis.json` contract stable |
| C — Generic classification | WCL class/spec/role taxonomy, build fingerprint clustering, Druid (Balance/Feral/Tank/Healer) and Warrior (DPS/Tank) resolution, confidence + override UI | A shipped |
| D — More class plugins | Druid, Warrior, Rogue, Mage, Warlock, then healers | C shipped |
| E — More raids / game variants | Other Classic Era raids, then Fresh/SoD/other sites | Analyzer contracts stable |

Order rationale: build the analyzer against data we already hold and can
verify, then the live client, then the UI — so the UI never couples to one
Hunter report, and Druid/Warrior prove the abstraction.
