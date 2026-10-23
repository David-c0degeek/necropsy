# Real-v2 actor DPS arithmetic drafts

All 89 retained participants were attempted with explicitly empty exclusions.
Forty-nine match their exact published leaderboard rows across 13 bosses;
40 remain refused: 26 disagreeing pet listings and 14 missing pet-discovery
files. Neither Loatheb nor Patchwerk has an admitted row. No exclusions, owners
or zero-pet defaults were fitted to make a row pass.

Hydrate the pinned archive through Git LFS, then run from the repository root:

```powershell
uv run python tasks/naxx-completion/research/real-v2-dps-20261023/check.py
uv run python scripts/freeze_dps_ranking.py check tasks/naxx-completion/research/real-v2-dps-20261023/51107-9fFYrZPRQvp7wL2H-32.oracle.json
```

Run the second command for each `.oracle.json`; `replay-checks.json` records
all 49 strict checks with zero differences. Specs retain portable archive paths.
`inventory.json` retains every attempt and original refusal. The initial
15-participant trial (eight matches, seven refusals) is preserved separately in
`initial-registered-*` receipts.

The separate standard-library ZIP/Counter checker imports no production or
freezer code. It independently binds ownership and re-enumerates raw damage,
maximum source/target multiplicity, every member/index witness, totals,
duration, exact published decimal tokens and Fraction residuals. Its receipt is
`independent-review.json`. This is an independent calculation by the author,
not an independent reviewer verdict.

The checker initially compared witness list order, then failed on a pet row
because it also selected a pet's damage observed in its owner's target stream.
The corrected check compares witness multisets and selects outgoing damage for
each stream's own actor. No oracle, exclusion or ownership evidence was changed
to obtain agreement. The original failed logs remain in the local workspace.

Scope completeness does not establish owned-damage eligibility: some
capture-complete contexts are refused by the stricter ownership check. These
are draft actor arithmetic oracles, not validated cell policies, accepted boss
exclusions, raid-wide ranking rules or performance grades. No cell is COMPLETE.
