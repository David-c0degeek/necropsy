# Partial production intake

Production wrote `77619978-2006-20261024T121203.zip` for Balance DPS Alliance.
Its SHA-256 is `837485a99ae96dfd644d410933f64947a0b4b236f47cd3dbff6cda5e6f293f5b`.
The copied archive is 55,832,205 bytes. The original output is retained on Tower
under `/mnt/user/appdata/necropsy-naxx-capture-20261023/out/naxxramas-druid-balance-dps-alliance/candidate-0/.necropsy-run/snapshots/c87ae615b3d94b73a59fe76287f60f8c/`.
The verified local copy and sidecars remain in
`workspace/codex-naxx/production-intake-20261024/`.

The receipt checks both complete member manifests, every member digest and all
strict streams. The same 917 paths contain 724 byte-identical members and 193
changed JSON wrappers. No event member changed. Selected fights, participants,
strict stream statuses, counts and boundary ambiguities match the registered
measurement archive. Report player details match when the DPS/healer/tank
arrays are keyed by unique actor ID; gear and other nested arrays retain their
original order. Refreshed report rankings and user-ranking percentiles are
recorded. Leaderboards also have changed rows, including reports and characters;
these are metadata drift, not new acquired actor evidence. Marker differences
are restricted to generation hashes and leaderboard timestamps.

The existing 15 registered actor sources and dependent raw facts stay pinned to
the measurement archive. Four cohorts still lack complete pet ownership, and
the primary Kel'Thuzad actor still lacks faction evidence. No cell changes
status, no ranking is regenerated and no configuration completes from this
partial capture. Subject 03.5 remains open for the remaining configurations.

The duplicate event payload is retained privately rather than adding a second
56 MB Git LFS object without new registered evidence. Claude copied ZIP,
`.entries` and `.sha256` outside every container mount at 09:43 UTC on
2026-10-26, to the mode-0444 on-NAS evidence directory:

`/mnt/user/appdata/necropsy-naxx-evidence-20261026/production-partial-balance-dps-alliance-20261024T121203/`

`SHA256SUMS` verifies source and copy. The entries digest is
`bf956bb6cf3bb9053f2f7afe2efe01228ddcb1a374a1f9f5fc7000b4f063d8cd`;
the `.sha256` sidecar digest is
`45256e4fc20fb56a144d7db6adab32ed3ef06c8a001259d5b7ce6da2bdd80b45`.
This is an on-NAS retention copy, not an off-server backup. The maintenance
record is `unraid-tower` commit `74cbbb4`,
`changes/2026-10-26-necropsy-quota-recovered-evidence-copy.md`, with a backup
index entry; mailbox `claude:25` supplies the verified receipt.
A clean checkout needs the pinned ZIP and `.entries` restored from that evidence
directory to the workspace path above before replay; this receipt alone cannot
reconstruct those input bytes.

```powershell
uv run python tasks/naxx-completion/research/production-intake-20261026/check.py
```

The checker performs no WCL calls and no writes in replay mode. `--out FRESH`
writes a new receipt exclusively and refuses to overwrite an existing one.
The initial timestamp-only leaderboard check failed on real row drift; the
final receipt records those changes explicitly. An initial generic ID-array
normalization refused duplicate item IDs; normalization is now limited to the
three player-role arrays and rejects duplicate actor IDs.

Verification: exhaustive two-archive replay passes (917 members each,193
classified changes, equal strict scopes). The scoped Naxx inventory reports
26 IN_PROGRESS,484 TODO and no problems; Ruff and maintained-link checks pass.
Claude independently reproduced the receipt and approved the five original file
fingerprints, with two follow-ups: optimized Python guards and durable private
retention. All ten `assert` statements are now explicit guards, including scope
and receipt equality. Duplicate actor IDs and stale-receipt conditions are
refused under `python -O`; the optimized full replay has a separate retained log.
The original broad gate was deliberately interrupted for this revision, and is
not a pass (`full-gate-20261026.log`). The final gate sets both
`NECROPSY_GATE_WORKERS=8` and `PYTEST_ADDOPTS=-n 8 --dist worksteal`, with output
in `workspace/codex-naxx/production-intake-20261024/final-full-gate-20261026.log`.
A passing final gate and the revised review are required before push; neither is
implied by the inventory or the replay receipt.
