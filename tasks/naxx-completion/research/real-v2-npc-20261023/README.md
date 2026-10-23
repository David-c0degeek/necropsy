# Positive real-v2 NPC observations

This packet freezes positive observations from one complete encounter-All
context per Naxx boss: 14 primary actor contexts and the separately verified
Kel'Thuzad comparison actor. It records 8,947 NPC-source occurrences, including
1,766 casts, with numeric enemy/catalog bindings, raw cast rows, timestamps,
multiplicity and member/index witnesses. No canonical rows overlap page boundaries
in this sample. Missing pet ownership and Teris's missing faction remain unknown.

Hydrate the pinned archive through Git LFS, then run from the repository root:

```powershell
uv run python tasks/naxx-completion/research/real-v2-npc-20261023/check.py
uv run python tasks/naxx-completion/research/real-v2-npc-20261023/generate.py --out workspace/npc-observations-review.json
```

The generator uses the standard library and no analyzer or rules. It requires a
fresh output file under `workspace/`, verifies the archive against the intake
pin, and binds its recipe and intake digests. The checker independently reads
the All pages with the existing fact-freeze parser and compares all counts,
casts, first/last timestamps and raw cast witnesses. It verifies recipe/intake
currency and reports its own source hash. `validation.json` records the actual run.

These are positive observations from recorded fight bounds. Numeric identities
and source membership do not establish universal mechanics, fixed cadence,
positions, phase origins, ownership, opportunity, aura lifetimes or a grade.
The sample does not settle source conflicts or complete any policy or cell.
