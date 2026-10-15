# 01 — Public authentication contract

## Goal
Define a distributable authentication contract and validate the registered WCL public client.

## Integration analysis
- **Existing code found:** `wcl/auth.py::Auth, wcl/cli.py::login, docs/decisions/0001-personal-authentication.md`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [ ] **01.1** (agent) Verify current official WCL PKCE requirements, registered loopback redirect support, scopes, endpoint access, refresh behavior and public-client configuration; retain dated primary-source evidence. Do not assume existing confidential-client settings can be reused.
- [ ] **01.2** (agent) Record an ADR for public-client mode, compatibility with personal confidential-client records, callback/state/challenge handling and supported platforms; include a pre-mortem before behavior changes.
- [ ] **01.3** (release-engineer) Register/configure the public Necropsy WCL client and approved callback URI after the researched requirements are known. Supply only the public client ID to package configuration; never supply a shared secret.

## Hindsight checkpoint
Before marking DONE: Codex performs solo review and records Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt (master D003; user ended Claude pairing). No CLOSE while a required human action or observable risk remains unresolved.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation has not started. Record date, per-subject slice number, box IDs, observed behavior, verification, documentation impact, and pushed checkpoint.
