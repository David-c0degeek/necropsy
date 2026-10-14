# Manual actions

> Mirror of every human-owned box from the subject files (see §5). One
> row per human action; keep in sync with the owning subject file.
> Status is one of `TODO`, `DONE`, `DEFERRED` (a deferral needs a rationale),
> `SUPERSEDED` (a later decision/box replaced it — cite it), or `ABANDONED`
> (cite the §4 row). Only terminal states (`DONE`/`DEFERRED`/`SUPERSEDED`/
> `ABANDONED`) may survive into an archived plan — never `TODO`.
> Owner is a non-`agent` role from the §5 enum.

| Box ID | Owner | Action | Source subject | Status | Deferral rationale |
|---|---|---|---|---|---|
| 00.9 | product-owner | Approve uv / git-lfs / secret-scanner installs; confirm LFS storage for the 80 MB fixture | 00 | DONE | Approved by user 2026-10-12 (D011) |
| 01.7 | domain-sme | Review golden-fact register seed; mark disputed facts | 01 | DEFERRED | Batched with 05.7 once analyzers verify facts against raw data (D017) |
| 04.8 | domain-sme | Review one boss's Hunter analyzer output for mechanics correctness | 04 | DEFERRED | Batched with 05.7 once per-boss output exists (D017 pattern) |
| 05.7 | domain-sme | Review weave matrix and per-boss recommendations vs definitive playbook; also covers the deferred 01.7 fact-register review and 04.8 Hunter-mechanics review | 05 | IN PROGRESS | 2026-10-13: user decided the disputed items (weave per role, Spirit of Naxxramas as start trash, Tauren-only fill, raid speed vs median with fastest shown, pet DPS 0 without a pet; Grobbulus left to driver + navigator). Remaining: the wider fact-register and Hunter-mechanics read-through, proposed once the HTML report (06) exists |
| 06.6 | product-owner | Side-by-side review of generated playbook vs definitive playbook | 06 | DONE | 2026-10-13: user compared both. Must-fix: the definitive playbook (`D:/Parsing/Results/Playbook/Haplina_Naxx_Definitive_Playbook.html`) is "MUCH nicer UX/UI wise"; use it as the template — Necropsy's report/playbook should look the same. Redesign unit led by Codex (D034) |
| 06.7 | product-owner | Approve Playwright + Chromium download for the headless HTML smoke check, or choose a manual browser check | 06 | DONE | 2026-10-13: user approved installing Playwright (dev dependency) + Chromium for the automated smoke check |
| 07.9 | product-owner | Run `necropsy auth login`; confirm redirect URI `http://localhost:8765/callback` is registered | 07 | DONE | 2026-10-14: user completed login; local auth status confirms signed-in WinVault storage and real user-endpoint queries succeed. Successful callback verifies the registered redirect. |
| 07.10 | release-engineer | Register a WCL public PKCE client before any distribution | 07 | DEFERRED | Carried to Distribution 01.3 (public registration) and 02/03 (PKCE/acquisition); Milestone A is personal-use only (D005). See tasks/Distribution-Plan.md. |

| 07.11 | product-owner | Accept/reject the proposed personal-use partial-live boundary (all 15 bosses with five usable deep samples; four partial pet-ownership cases). See review-packet.md. | 07 | TODO | D046 proposes acceptance; silence leaves this open. |
