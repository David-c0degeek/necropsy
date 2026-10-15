# Manual actions

Mirror non-agent boxes exactly. TODO stays open; deferral needs an explicit rationale and scope decision.

| Box ID | Owner | Action | Source subject | Status | Deferral rationale |
|---|---|---|---|---|---|
| 01.3 | release-engineer | Register/configure the public Necropsy WCL client and approved callback URI after the researched requirements are known. Supply only the public client ID to package configuration; never supply a shared secret. | 01 | DONE — user supplied public ID; live S256 callback and secret-free token/refresh verified | |
| 05.2 | product-owner | Run or observe the documented flow on another person/account and machine; confirm no developer secret is requested, outputs and uncertainty are understandable, and declared platform behavior is acceptable. | 05 | PENDING — receipt/procedure prepared in docs/live-acceptance.md | |
| 05.4 | release-engineer | Approve and publish the reviewed package only after the public-client and independent-user gates pass; record the exact version, artifact hash and supported platforms. | 05 | PENDING — receipt/procedure prepared in docs/live-acceptance.md | |

Registration steps: docs/warcraft-logs.md#public-application-sign-in .
Only the public client ID is needed; never send a shared secret.
Registered public app and exact callback verified live. Public token refresh/rotation,
character lookup, leaderboards, current and archived report bundles and events pass
on the user endpoint; see public-auth-receipt.json. Independent acceptance remains open.
