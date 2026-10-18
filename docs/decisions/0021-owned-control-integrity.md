# Owned control application integrity

Status: accepted · 2026-10-18

Garr Warlock reports keep `playbook.control_applications`, one entry per
configured control policy. Read every event occurrence of the selected fight
directly, without an ability-name join, and validate literal raw against
normalized type, source, target, spell, time, fight and target instance before
any exclusion. Only a typed, agreeing row of another type, another positive
source, a non-policy spell or a known non-control recipient is excluded. Any
other contradiction, malformed payload, duplicate occurrence identity, instance
outside the selected `instanceCount`, or control NPC missing from the selected
enemy roster is unresolved. Legitimate occurrence copies remain separate.

The source must be the unique catalog Player of the subject class on the
selected friendly roster, and its SOURCE stream must be exactly one player
binding with no owner. Complete counts additionally require unrestricted
encounter event-set proof. A trusted SOURCE stream is not enough: another
merged stream can add an owned application identity that SOURCE never listed,
and a disjoint identity has no overlapping key to raise a multiplicity
mismatch.

Format 1 archives have no encounter All scope, so their counts are unknown.
This is a certainty correction of the earlier model, not a change of raw facts:
Rumplock's literal application of Banish18647 to Firesworn100, instance8, at
4258ms remains observed, and earlier independent counts and locators are
unchanged. Unresolved rows withhold the count while separately qualified
observations survive.

A qualified observation with a recorded instance supplies a review prompt naming
the add, instance and time, asking the player to confirm whether control on that
add is theirs and who provides backup before copying a damage reference opener.
A zero or unknown count alone supplies no prompt or criticism; a separately
qualified instance-bearing observation can supply the review prompt even when
the total is unknown. Missing instances
keep the observation without an instance-specific prompt. None of this
establishes an assignment, maintained uptime, reapplication, lost damage or a
utility score.
