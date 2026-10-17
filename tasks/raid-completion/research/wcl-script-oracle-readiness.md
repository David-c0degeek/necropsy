# WCL script-oracle capability review

2026-10-18. Primary documentation review; UI execution remains unverified.
This is an independent oracle candidate, not a replacement capture path.
Normal authenticated acquisition/cache/quota/revision/finalization/writer
contracts remain in force. No new package, service, plugin or account installed.

The official [scripting introduction](https://www.warcraftlogs.com/scripting-api-docs/warcraft/)
describes creating a script pin from the report's Queries / New Script UI.
The [Fight interface](https://www.warcraftlogs.com/scripting-api-docs/warcraft/interfaces/RpgLogs.Fight.html)
documents `isEventExcludedFromDamageRankings`, enemy-death collections, phase
metadata, and downtime transitions. These could provide independent reference
observations for residual target eligibility and missing raw phase/lifecycle
boundaries. The method's descriptive text and return description use opposing
excluded/counts wording; positive and negative controls are required before
trusting its Boolean polarity. Documentation alone is not a measured answer.

The [report sandbox guide](https://www.archon.gg/classic-fresh/articles/help/report-components-the-sandbox)
describes a preview Run operation and leaving without saving. The older
introduction still calls components forthcoming; do not infer current account
or Era availability from that stale sentence or the current site's product route.
The [Actor/Event interfaces](https://de.warcraftlogs.com/scripting-api-docs/warcraft/interfaces/RpgLogs.Event.html)
also caution that event disposition can change with mind control. A static
Player/NPC roster type cannot settle control-time hostility.

Available/deferred tool discovery found no WCL connector or scripting executor.
The browser skill was read and its shipped runtime module verified. Browser
setup succeeded, URL selection returned `No browser is available`; the documented
bootstrap troubleshooting and one read-only browser-list call returned `[]`.
No UI script, dashboard, signed-in state, session storage or private API was
accessed. No browser-control workaround or alternate capture engine was used.
This optional oracle does not block ongoing offline implementation; no user
input was requested. A future connected report UI should use a local preview,
record exact report/fight/revision/filters, polarity controls and raw-row
identity bindings, and preserve its measured output before accepting a policy.

The [DeathEvent interface](https://www.warcraftlogs.com/scripting-api-docs/warcraft/interfaces/RpgLogs.DeathEvent.html)
documents the scripting `isFeign` field. Actual frozen raw API death rows use
`feign:true`; this difference was verified directly rather than guessing a raw
alias. It exposed the concrete Geddon lifecycle issue recorded in
[the correction guardrails](feign-lifecycle-contract.md).
The [DamageEvent interface](https://de.warcraftlogs.com/scripting-api-docs/warcraft/interfaces/RpgLogs.DamageEvent.html)
distinguishes damage amount, absorbed damage and nullable overkill. Its scripting
shape does not replace validation of the captured GraphQL raw event fields or
establish a universal ranking numerator.

Independent Skeram lifecycle research from12 retained contexts records72
numbered747 summons to176525, no image death rows,60 instances with positive
overkill and12 without. No positive damage has a strictly later timestamp than
the first positive-overkill row for those60 instances; same-timestamp events
remain unordered. Missing endpoints stay unknown. No split-duration,
continuous existence, attackability or damage-opportunity policy is activated.
Exact raw observations: [lifecycle register](skeram-image-lifecycle-observations.json).
