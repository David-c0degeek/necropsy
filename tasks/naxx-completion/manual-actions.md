# Manual actions

| Box ID | Owner | Action | Source subject | Status | Deferral rationale |
|---|---|---|---|---|---|
| 00.1 | product-owner | Disable XMP in BIOS, restart; optional memtest | 00 | DONE 2026-10-21 (2133 MT/s verified; no memtest) | |
| 03.3 | product-owner | Approve Tower runner restart with the Naxx queue | 03 | DONE 2026-10-21: owner approval relayed verbatim in claude:16, pair session 20261021T120145Z-a4a14bde | Conditional: release 0.6.0 and its image, real v2 encounter/critical smoke, measured normal capture, and verified/pair-reviewed Naxx queue must all precede restart. Approval only; restart not executed. |
| 07.4 | product-owner | Product acceptance of Naxx completion | 07 | TODO | |
| 02.3 | product-owner | Lift the raid resource hold on local inference | 02 | DONE 2026-10-21: "local model approved now"; trial executed | Always use an available saved balanced tune, per subsequent owner instruction. WCL maintenance remains a separate hold. |
