# Milestone A review packet

Status: engineering close-out prepared; human decisions below are **pending**.
No silence is treated as approval. Final sign-off follows the completed engineering gate.

Evidence: [updated live playbook](../../workspace/live-kiss-ranked-20261014/playbook.html),
[updated report](../../workspace/live-kiss-ranked-20261014/report.html),
[live validation scope](../../docs/live-validation.md),
[artifact verification](../../workspace/live-kiss-ranked-20261014/review-verification.json),
[original live receipt](../../workspace/live-check-v2-user-waited-20261014T144942Z/live-acceptance.json),
[latest CI](https://github.com/David-c0degeek/necropsy/actions/runs/38627210882).
Local evidence links are intentionally available only in this working tree;
the shipped validation guide records scope and hashes without requiring them.

| Decision | Exact review question | Evidence | Default if unanswered |
|---|---|---|---|
| Hunter mechanics (05.7; includes deferred 01.7/04.8) | After reviewing the boss recommendations/weave matrix and detailed evidence, which findings need correction? Can the reviewed mechanics be accepted for this personal-use milestone? | Live pages above; historical pages below; existing recorded user corrections remain intact. | Pending; do not mark subject 05 DONE. |
| Historical Sapphiron | Accept exclusion of the old “No weaving” verdict because only two Alliance examples are available and the analysis rule requires three? The historical result therefore remains Unknown rather than being forced to No. | tests/golden/haplina_naxx/facts.yaml: sapphiron.weave-verdict; two-entry adoption evidence; original definitive playbook. | Disputed and pending domain-sme attribution. |
| Partial live acceptance (07.11; proposed D046) | Accept the personal-use live result with all 15 bosses / five same-faction deep samples each, while four bosses retain explicit unknown pet ownership, or require complete ownership coverage before acceptance? | Original exit-4 receipt; 11 complete / Patchwerk, Loatheb, Anub'Rekhan and Instructor Razuvious partial; no missing minimum sample. | Pending; no subject 07 CLOSE or complete-coverage claim. |
| Final §8 sign-off | Once the above decisions and engineering gate are resolved, accept Milestone A for personal Hunter/Naxxramas use with the documented limits? | Gate review, Hindsight, CI/build/golden evidence and live receipt. | Pending; do not close/archive the plan. |

Historical review: [preserved-detail historical playbook](../../workspace/historical-kiss-20261014/playbook.html).
The user reference is `D:/Haplina_Naxx_Definitive_Playbook.html` (read-only).
PKCE remains deferred; no application distribution is authorized by Milestone A sign-off.
Plan deletion/archival remains human-owned after sign-off.

## Agent follow-through

- Engineering checks recorded: latest-commit independent replay 229 passed / 4 expected failures / exit 0; current build passed; latest Linux/Windows CI green; 148 local links and both plan structures verified. Claude's full record/plan review and checkpoint publication follow.
- Preserve the original snapshot/receipt and all supported unknowns.
- Update this packet and affected manual/gate records only from explicit user decisions.
- New plans are drafted using the c0degeek template; readiness/implementation remain TODO.
