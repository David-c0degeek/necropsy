# How published Naxx DPS credits Ignite, 2026-11-13

Research only. No freezer, register or policy change follows from this note.

## Question

Fire Mage rows contradict published DPS (73 register rows; 2 Frost Mage rows at
Faerlina too). The freezer credits each Ignite tick (ability 12654) to its
logged source, the mage who owns the debuff. Published DPS does not.

## Data

`collect.py` replays the comparison follow-up register for every Mage archive
with the arithmetic check forced to pass. For each row it keeps the freezer's
ranked total without Ignite (`nonign`), the logged Ignite (`ign`), the
published amount and the fight duration. The output is in `rows.json`: 165 Mage
rows, of which 85 have Ignite or are Fire. The implied Ignite credit of a row is
`published × duration / 1000 − nonign`.

`simulate.py` rebuilds each fight from its certified encounter `all_` pages
(the `critical_` pages in the same folder are a different stream and must not be
added) and tests credit models. A row matches when `nonign + credit` meets the
published amount within one unit of its last decimal place.

    uv run python tasks/naxx-completion/research/ignite-attribution-20261113/simulate.py pi-inst

## Result

| Model | Rows matched of 85 |
|---|---|
| Logged Ignite source (freezer today) | 10 |
| Each tick split equally among the fight's Fire-spec mages (report `playerDetails`) | 58 |
| … among Fire-spec mages with any fire-school crit in the fight | 68 |
| … among Fire-spec mages with a fire-school crit on the tick's target | 74 |
| … on the tick's target instance, owner not added | **78** |
| Same, owner always added | 76 |
| Same, exact fractions instead of floor | 17 |

The best model (`pi-inst`) splits each Ignite tick:

- Pool: Fire-spec mages in the fight (`friendlyPlayers`) with a fire-school
  (`masterData.abilities` type 4) critical hit, other than Ignite, on the tick's
  `(targetID, targetInstance)` at any time in the fight. An empty pool means
  the logged source.
- Each pool member gets `floor(amount / k)`. The remainder goes to the logged
  source if it is in the pool, otherwise to the lowest actor ID.
- A Frost-spec owner of an Ignite gets nothing unless it is in the pool. This
  explains the Faerlina Frost rows.

## Not explained (7)

- Gothik, 4 rows: the living and undead sides; pools are probably per side or per time.
- Four Horsemen, 1 row (Bigherm, +427).
- Thaddius, 1 row (Macherie, −2.7 against a bound of ±1.17): remainder or rounding.
- Faerlina, 1 Frost row (三月灬初七丶): the model gives 0, but published needs its own logged Ignite (1,686).

## Limits

- The model was fitted on the same 85 rows it is scored on; there is no holdout.
- The spec comes from report-level `playerDetails`; a mage who changed spec
  between fights would be misclassified.
- WCL documents none of this. It is an inferred reconstruction.
