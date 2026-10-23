# Positive selected-actor facts from real v2 evidence

The 15 newly registered actor contexts were scanned for exact class-capability
catalog spell IDs, personal debuff transitions and explicit actor dispels.
Eight contexts have positive observations: 96 debuff transitions, one Remove
Curse (2782) cast and one explicit dispel. Seven have no selected positive rows;
that is not absence or zero opportunity. The full inventory retains all 15.

Hydrate the archive through Git LFS and run from the repository root:

```powershell
uv run python tasks/naxx-completion/research/real-v2-actor-facts-20261023/generate.py --out workspace/actor-facts-review
uv run python scripts/fact_freeze.py check tasks/naxx-completion/research/real-v2-actor-facts-20261023/naxxramas-51119-2-balance-dps-alliance.facts.json
```

The generator requires a fresh directory under `workspace/`. It pins the intake,
archive, exact capability source catalog and current fact-freeze implementation.
It independently enumerates SOURCE/TARGET pages with maximum multiplicity,
compares every projected positive row against fact-freeze and checks each
retained raw member/index witness. Raw discovery uses no analyzer or mechanic
rules. The resulting recipes use portable relative archive paths; strict replay
of all eight relocated fact files reports zero differences in `replay-checks.json`.
The inventory records every scanned page digest and each fact-file digest.

This is an author calculation with a separate enumeration, not an independent
reviewer verdict. Exact catalog spell IDs do not cover every spell rank or
establish build availability, cooldown readiness, assignment or opportunity.
Debuff rows are not paired into aura lifetimes and may be player-caused.
Dispels retain explicit recipients and removed abilities without reconstructing
response times or friendliness. Missing pet ownership and faction remain
unknown. No source conflict, mechanic policy, grade or coverage cell is approved.
