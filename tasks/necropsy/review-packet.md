# Milestone A review packet

Status: the three mechanics/Sapphiron/partial-live decisions are **accepted by David on 2026-10-14**. Subjects 05/07 and the engineering gate are closed after review and checkpoint publication; David also explicitly approved final §8 personal-use sign-off on 2026-10-14 (reply: "approved").
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
| Hunter mechanics (05.7; includes deferred 01.7/04.8) | After reviewing the boss recommendations/weave matrix and detailed evidence, which findings need correction? Can the reviewed mechanics be accepted for this personal-use milestone? | Live pages above; historical pages below; existing recorded user corrections remain intact. | Accepted by David; subject 05 closing review recorded. |
| Historical Sapphiron | Accept exclusion of the old “No weaving” verdict because only two Alliance examples are available and the analysis rule requires three? The historical result therefore remains Unknown rather than being forced to No. | tests/golden/haplina_naxx/facts.yaml: sapphiron.weave-verdict; two-entry adoption evidence; original definitive playbook. | Accepted exclusion, now attributed in the fact register. |
| Partial live acceptance (07.11; proposed D046) | Accept the personal-use live result with all 15 bosses / five same-faction deep samples each, while four bosses retain explicit unknown pet ownership, or require complete ownership coverage before acceptance? | Original exit-4 receipt; 11 complete / Patchwerk, Loatheb, Anub'Rekhan and Instructor Razuvious partial; no missing minimum sample. | Accepted personal-use partial result; subject 07 closes while coverage remains partial. |
| Final §8 sign-off | Once the above decisions and engineering gate are resolved, accept Milestone A for personal Hunter/Naxxramas use with the documented limits? | Gate review, Hindsight, CI/build/golden evidence and live receipt. | APPROVED by David on 2026-10-14; personal-use scope. Archival/deletion remains human-owned. |

Historical review: [preserved-detail historical playbook](../../workspace/historical-kiss-20261014/playbook.html).
The user reference is `D:/Haplina_Naxx_Definitive_Playbook.html` (read-only).
PKCE remains deferred; no application distribution is authorized by Milestone A sign-off.
Plan deletion/archival remains human-owned after sign-off.

## Agent follow-through

- Engineering checks recorded: latest-commit independent replay 229 passed / 4 expected failures / exit 0; current build passed; latest Linux/Windows CI green; 148 local links and both plan structures verified. Claude's full record/plan review and checkpoint publication follow.
- Preserve the original snapshot/receipt and all supported unknowns.
- Update this packet and affected manual/gate records only from explicit user decisions.
- New plans are drafted using the c0degeek template; readiness/implementation remain TODO.


## Accepted decisions and accuracy audit

David: "Accepted all 3, unless we can ACTUALLY refine and improve their accuracy".
Interpretation: accept the currently documented evidence-bounded results; pursue
supported improvements when affirmative evidence exists. A failed search does not
justify assigning an owner, widening a historical sample, or guessing race.

Saved archive audit: 13 ownerless actor/fight entries (10 Battle Chicken and
3 Arcanite Dragonling); six recorded player summon events, zero exact links to
those actors. Friendly-pet and master actor ownership fields remain unusable.
Saved fight-bounded player streams cannot prove that an unlinked guardian belongs
to a different class. No runtime/coverage relaxation is justified by these findings.
Evidence: `workspace/kiss-qa-20261014/ownership-accuracy-audit.json`.

David additionally confirmed: "Correct, vanquished tentacle, battle chicken,
dragonlings, all can be part of the hunters toolkit". These are eligible Hunter
tools; eligibility never assigns one individual actor. Engineering guardians stay
separate from ordinary Hunter-pet analysis and remain eligible for correct ranked
attribution when ownership is proven. No ownerless tentacle was found in this
specific archive; that is not a general absence claim.

Race: the current verified Classic Era character API response and saved JSON lack
direct race data; observed racial evidence remains supported. Historical Sapphiron
has only two Alliance examples in its fixed cohort; live extra examples do not
retroactively change that historical sample. Preserve its accepted Unknown result.

Final §8 sign-off was not among the first three accepted items; David subsequently supplied the separate explicit reply "approved" on 2026-10-14.

Engineering checklist and closing Hindsight are recorded in the master plan; final peer review/publication backs the checkpoint. Final §8 personal-use sign-off is now approved; no remaining current-plan human decision. No distribution, archive deletion or new-plan implementation is implied.

Final state: Milestone A CLOSED for personal use, with the accepted documented limits. Follow-up plans remain at readiness TODO. Source calculations and original artifacts are unchanged. Retain this packet and plan; do not infer authorization for deletion, distribution or broader supported scope.
