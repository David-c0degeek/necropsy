# Production intake, 2026-10-31

Six Naxx configurations finished on Tower after the 2026-10-26 intake. Each
final archive is new evidence: no earlier archive covers these configurations.

| Configuration | Archive | Worker | Depth |
|---|---|---|---|
| Druid Balance DPS Horde | `64347501-2006-20261027T093033.zip` | 0.7.0 | 5 |
| Druid Balance HPS Alliance | `65603754-2006-20261027T195031.zip` | 0.7.1 | 3 |
| Druid Balance HPS Horde | `76376122-2006-20261028T163059.zip` | 0.7.1 | 3 |
| Druid Feral DPS Alliance | `75650895-2006-20261029T065847.zip` | 0.7.1 | 3 |
| Druid Feral DPS Horde | `77548335-2006-20261030T095117.zip` | 0.7.1 | 3 |
| Druid Guardian DPS Alliance | `83306366-2006-20261031T073441.zip` | 0.7.1 | 3 |

The archives, with their `.entries` and `.sha256` sidecars, are in Git LFS
under `tests/golden/raids/raw/naxx-production-20261031/`. Each archive matches
its Tower sidecar and a Tower-side `sha256sum` of the source. A read-only
retention copy with verified `SHA256SUMS` and `SOURCES.txt` is on Tower at
`/mnt/user/appdata/necropsy-naxx-evidence-20261031/` (maintenance commit
`unraid-tower` f506efd). That is an on-NAS copy, not an off-server backup.

## Strict read

`check.py` opens every archive against its pinned SHA-256 and entries
manifest, reads every member back through that manifest, requires the strict
reader to report no unplaced content, checks the marker subject against its
entry in the pinned production queue (`888b8d8d…`), and reads every expected
stream. `receipt.json` holds the result; a replay without `--out` must match it.

All six pass. No capture stopped (`stopped` is null). Every encounter,
critical, player and pet stream is complete. The pet-discovery listing is
missing in every archive (2–9 listings each). Every boss has `top_n` usable
deep comparisons: 5 for Balance DPS Horde, 3 for the rest.

The archives are partial for these reasons only:

- pet ownership unknown or unresolved for some subjects or comparisons;
- the subject's own fight was not acquired at five Balance HPS Horde bosses,
  two Feral DPS Alliance bosses, one Balance DPS Horde boss and Guardian DPS
  Alliance at Sapphiron (Restoration spec there, so outside the category).

Coverage-complete bosses per archive: 9 to 13 of 15.

## Follow-up register

`followup-comparisons.json` is regenerated over the registered measurement
archive and the four new DPS archives:

    uv run python scripts/comparison_followup.py \
      tests/golden/raids/raw/naxx-balance-v2-measurement/77619978-2006-20261023T152230.zip \
      tests/golden/raids/raw/naxx-production-20261031/64347501-2006-20261027T093033.zip \
      tests/golden/raids/raw/naxx-production-20261031/75650895-2006-20261029T065847.zip \
      tests/golden/raids/raw/naxx-production-20261031/77548335-2006-20261030T095117.zip \
      tests/golden/raids/raw/naxx-production-20261031/83306366-2006-20261031T073441.zip \
      --out tasks/naxx-completion/followup-comparisons.json

75 cells; 54 meet the minimum of 3 admitted comparisons and 21 need follow-up.
The 15 Balance DPS Alliance cells are byte-identical to the previous register.

| Configuration | Meet minimum | Need follow-up |
|---|---|---|
| Balance DPS Alliance | 13/15 | Loatheb, Patchwerk |
| Balance DPS Horde | 12/15 | Loatheb, Noth, Patchwerk |
| Feral DPS Alliance | 9/15 | Anub'Rekhan, Faerlina, Razuvious, Loatheb, Maexxna, Patchwerk |
| Feral DPS Horde | 10/15 | Kel'Thuzad, Loatheb, Patchwerk, Thaddius, Four Horsemen |
| Guardian DPS Alliance | 10/15 | Anub'Rekhan, Faerlina, Razuvious, Loatheb, Patchwerk |

Refusals: 28 where the comparison's owner folder has no `pets.json` (the
missing pet-discovery listing; 20 of them at Loatheb and Patchwerk, the
ownerless-guardian bosses of D026), 16 with no unique selected player stream,
4 where published DPS contradicts raw events and 1 where pet listings disagree
(Balance DPS Horde, Anub'Rekhan, report DyHKZM9Jdvxwh7RN fight 71). Nine comparisons stay
unverified because they exercise untested production exclusions (D025). The
missing-listing refusals surface as a raw "no item named …/pets.json" message
rather than a classified reason; the Balance DPS Alliance register already
contained ten of them.

The two Balance HPS archives are outside admission: there is no HPS admission
for these archives, so all their cells stay unverified and are not in the
register.

## What this does not do

Strict-read validity, actor registration, comparison admission and cell
completion stay separate. No actor source is registered, no policy is added and
no cell changes status. Subject 03.5 stays open: 27 configurations are not yet
captured, and actor registration for these six is not done.
