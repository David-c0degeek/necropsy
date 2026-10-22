# Manual actions

| Box ID | Owner | Action | Source subject | Status | Deferral rationale |
|---|---|---|---|---|---|
| 00.1 | product-owner | Disable XMP in BIOS, restart; optional memtest | 00 | DONE 2026-10-21 (2133 MT/s verified; no memtest) | |
| 03.3 | product-owner | Approve Tower runner restart with the Naxx queue | 03 | DONE 2026-10-21: owner approval relayed verbatim in claude:16, pair session 20261021T120145Z-a4a14bde | Conditional: release 0.6.0 and its image, real v2 encounter/critical smoke, measured normal capture, and verified/pair-reviewed Naxx queue must all precede restart. Approval only; restart not executed. |
| 07.4 | product-owner | Product acceptance of Naxx completion | 07 | TODO | |
| 02.3 | product-owner | Local inference disposition | 02 | No action needed: off and removed from active Naxx work, D016 | Tested work kinds failed acceptance; no further experiments scheduled. Codex work and isolated WCL capture continue without inference. A future owner-requested model use must verify the saved balanced tune and launch arguments. |

2026-10-22 current hold: owner reaffirmed "dont turn on local AI while im still in the raid / wow". A fresh process and listener check found no local model/proxy processes and no listeners on 8080 or 11435. The ignored runtime hold is `workspace/codex-naxx/local-ai-hold.json`. Do not treat a WCL reset, completed capture or elapsed time as permission to resume inference.
