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
acceptance or distribution readiness. Domain review and final milestone sign-off
remain separate human decisions. Pattern scans with no findings do not prove
that every possible secret is absent.
