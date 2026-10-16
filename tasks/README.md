# Task status

Reconciled 2026-10-16 against plan sign-offs, manual-action records, current branch state and GitHub open issues/pull requests. Historical progress paragraphs describe their original handoffs; final sign-offs supersede them.

| Work | Status | Record |
|---|---|---|
| Hunter/Naxxramas foundation | Complete; accepted | [Necropsy plan](Necropsy-Plan.md) |
| Public PKCE and installable CLI | Complete; accepted and released | [Distribution plan](Distribution-Plan.md) |
| Druid analysis | Complete; accepted with documented evidence limits | [Class expansion plan](ClassExpansion-Plan.md) |
| Remaining Classic Era classes | Complete; accepted with documented evidence limits | [All classes plan](AllClasses-Plan.md) |
| Game talent trees and WCL categories | Closed by David; implemented and verified on `improve-class-taxonomy` | [Class taxonomy plan](ClassTaxonomy-Plan.md) |
| Product UX and desktop shell | Implemented; native/manual acceptance limits remain | [UX](product-ux.md), [desktop](desktop-gui.md) |
| GUI-first installation | Complete; released | [Installation work](gui-default-install.md) |
| Healer corrections | Complete; released in 0.3.1 | [Healer corrections](healer-analysis-fixes.md) |
| Saved-source unknown recovery | Complete on main | [Recovery record](necropsy/unknown-recovery.md) |

No active implementation plan or unresolved required human action was found. GitHub had no open issues or pull requests at reconciliation. Taxonomy integration into main and any subsequent release remain outstanding delivery choices, outside its completed implementation scope. Latest published release observed: 0.3.1.

## Remaining opportunities

These are documented follow-ups, not started implementation plans or blockers to the accepted milestones.

- Broader real-log class/encounter validation, especially a usable real Holy Priest healing fixture. Existing acceptance did not establish universal rotation or assignment correctness. See [class validation boundaries](../docs/class-analysis.md#contracts-and-validation).
- Manual native GUI acceptance: real-account sign-in/acquisition, vaults, dialogs, keyboard/scaling and close/resume across target platforms; Windows offline checks and all-platform packaging checks already exist. See [desktop boundaries](../docs/desktop.md#verification-and-platform-boundaries).
- Signed/notarized native distribution. See [installation work](gui-default-install.md).
- Assistive-technology review and Firefox/WebKit report coverage. See [UX follow-ups](product-ux.md#deliberate-boundaries-and-remaining-work).
- Additional raids and game variants. See [roadmap](../docs/roadmap.md).
- Optional deeper build research: exact WCL classifier rules, full talent allocations and bounded searches for leaders of unranked builds remain outside current taxonomy support. See [taxonomy contract](../docs/decisions/0012-game-build-and-wcl-category.md).

The unchecked public-client box in the original live-acquisition subject is deliberately retained as a historical deferral; [Distribution manual actions](distribution/manual-actions.md) records its completed successor. It is not an outstanding registration task.

Completed plans are retained as evidence. Branch cleanup and plan archival have not been performed.
