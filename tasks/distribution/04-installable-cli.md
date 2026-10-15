# 04 — Installable CLI and distribution boundary

## Goal
Ship a reproducible local CLI package that can be installed without this repository or developer credentials.

## Integration analysis
- **Existing code found:** `pyproject.toml`, `uv.lock`, `report/package.py`, `rules/__init__.py::load_rules`, CI and `CONTRIBUTING.md`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [ ] **04.1** (agent) Build the existing Python wheel with its rule/template/assets data; verify clean-environment installation and entry points from outside the repository. Document Python/OS requirements and one simple install/run path.
- [ ] **04.2** (agent) Declare the supported platform matrix based on actual clean-install and approved credential-store evidence. Windows is the first personal acceptance target; CI or simulated keychains alone do not prove real-store behavior on other systems.
- [ ] **04.3** (agent) Verify wheel/sdist and generated samples contain no secrets, tokens, private caches, developer-local paths or personal identifiers in public documentation/samples; include integrity/version information and a reproducible package check.
- [ ] **04.4** (agent) Publish installation, sign-in, upgrades, uninstall/logout and permission/budget recovery documentation; keep desktop UI, bundled executables, auto-update and hosted services outside this plan.

## Hindsight checkpoint
Before marking DONE: Codex performs solo review and records Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt (master D003; user ended Claude pairing). No CLOSE while a required human action or observable risk remains unresolved.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation has not started. Record date, per-subject slice number, box IDs, observed behavior, verification, documentation impact, and pushed checkpoint.
