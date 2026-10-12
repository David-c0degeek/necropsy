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
| 01.7 | domain-sme | Review golden-fact register seed; mark disputed facts | 01 | TODO | |
| 04.8 | domain-sme | Review one boss's Hunter analyzer output for mechanics correctness | 04 | TODO | |
| 05.7 | domain-sme | Review weave matrix and per-boss recommendations vs definitive playbook | 05 | TODO | |
| 06.6 | product-owner | Side-by-side review of generated playbook vs definitive playbook | 06 | TODO | |
| 06.7 | product-owner | Approve Playwright + Chromium download for the headless HTML smoke check, or choose a manual browser check | 06 | TODO | |
| 07.9 | product-owner | Run `necropsy auth login`; confirm redirect URI `http://localhost:8765/callback` is registered | 07 | TODO | |
| 07.10 | release-engineer | Register a WCL public PKCE client before any distribution | 07 | DEFERRED | Milestone B; Milestone A is personal-use only (D005) |
