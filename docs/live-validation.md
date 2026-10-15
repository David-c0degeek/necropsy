# Observed live validation

[Documentation](README.md) · [Authentication](auth.md) · [Live acceptance procedure](live-acceptance.md)

On 2026-10-14, the personal-use Classic Era Hunter/Naxxramas flow completed
against the WCL user endpoint for character 86583560, partition 1. Sign-in and
actual Windows WinVault credential storage were exercised. This does not validate
macOS/Linux credential stores, public-client PKCE, other classes or game sites.

The saved acquisition attempted all 15 bosses and obtained five usable detailed
same-faction entries plus 25 metadata entries per boss. Eleven bosses had complete
acquisition coverage. Patchwerk, Loatheb, Anub'Rekhan and Instructor Razuvious were
partial because some listed pet/guardian actors had no usable owner. The command
returned exit 4 and wrote a verified snapshot, analysis, report, playbook and package.
No owner was guessed and the partial result was not relabeled complete.

The archive SHA-256 is
`5853b9485a14bb0a39c8e95ff9f3a6c33ab6b60e69174bbebde16b797aab9c0d`.
The original acceptance receipt reports artifact checks and secret scan passed.
All 15 subject fight selections match the historical reference; cohort differences
follow the documented live same-faction selection instead of historical overall top five.
The original snapshot and receipt are retained unchanged in local verification output.

One explicitly enabled hourly reset wait took 3240.989 seconds, from an observed
3240-second countdown. Account points across different hourly periods remain
unknown; the wait is not an exact API cost measurement.

Offline replay of that archive with the reporting correction restores all 15
overall rank-one DPS headlines. Saved leaderboard values are observed scalar
context where event calculations are unavailable, separate from deep samples.
All 15 recommendation/playbook/subject/cohort/baseline records remain unchanged.
Desktop/mobile checks retained the detailed sections and added a quick opening plan.

These results establish this run's authentication, acquisition and output behavior.
They do not establish game-mechanics correctness, full pet coverage, product
acceptance or distribution readiness. On 2026-10-14 the domain reviewer accepted
the mechanics, historical Sapphiron exclusion and documented partial-live scope
for personal use, conditional on supported accuracy improvements. Final personal-use
milestone sign-off was explicitly approved later that day after the accuracy audit
and engineering close-out. Application distribution remains gated on PKCE. Pattern scans with no findings do not prove
that every possible secret is absent.

A saved-source accuracy audit found no exact summon-owner mapping for the ownerless
Battle Chicken/Arcanite Dragonling instances. These and vanquished tentacles can be
Hunter tools; that eligibility does not prove individual ownership. The partial
classification and unknown attribution remain unchanged.


## Registered public-client observations — 2026-10-15

The owner registered Necropsy's public client. Its public ID is packaged, so
`necropsy auth login` now needs no client-ID option. The default CLI completed
actual S256 browser sign-in through `http://localhost:8765/callback` on Windows.
The selected WinVault record is public mode with no client secret. The `-` shown
by WCL for the public registration is never used as a secret.

`necropsy auth status --check` queried the user API; `necropsy resolve` with
`--endpoint user` resolved the existing Hunter character and Naxxramas context.
A real public refresh succeeded and rotated the refresh token; only the public
client ID was supplied to the token endpoint, without Basic authentication.

Existing production query shapes also passed through the user endpoint:
leaderboard page, current report bundle (including rankings/player details),
a one-second bounded event page (eight returned events), and an archived report
bundle with `archiveStatus.isArchived=true`. No additional OAuth scopes were
requested. These observations establish those tested reads for this account,
not access to every private report or another account's archive entitlement.

The observed application budget was 1800 points/hour, with 61.02 points spent
after the probes. Other app activity may contribute to that reading. Existing
bounded acquisition policy remains unchanged. No full-raid acquisition with
this public client is claimed by these query probes.

The rebuilt wheel passed clean installation, default public login with synthetic
OAuth/user API responses, offline Hunter replay and package integrity, WinVault
probe and unlimited-size extracted/output secret scans. The real login above ran
from the checkout; installed authentication has synthetic evidence. No real
tokens, authorization codes or refresh values are included in these records.

These observations alone do not establish independent installation/authorization/
acquisition on another account and machine or publication approval. The later
owner attestation below records those decisions; macOS/Linux credential-store
support remains unverified.


## Independent acceptance and release approval — 2026-10-15

The product owner replied “Approved” to the completed engineering/public-client
work and publication gate, then explicitly confirmed “Independent test passed”
when asked whether another WCL account on another machine completed installation,
sign-in and report generation. This is owner-attested acceptance; the agent did
not observe the independent machine or receive its OS, raw outputs or detailed
receipt. Do not describe those missing details as independently inspected.

The supported release target remains Windows with Python >=3.14, backed by the
local install/live WinVault evidence above. Linux has synthetic CI installation
coverage; real Linux/macOS credential-store support is not certified. Version0.1.0
is distributed through the private repository's GitHub release for authorized
collaborators. No public package-index availability is implied.
