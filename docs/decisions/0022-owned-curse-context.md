# Owned curse application context

Status: accepted · 2026-10-18

Garr Warlock reports keep optional `playbook.curse_applications`, produced by the
same occurrence engine as owned control applications (ADR0021) under a separate
`curses` policy kind. Every literal, roster, instance, SOURCE binding and
encounter event-set rule is unchanged; only the policy, labels, limitation and
prompt differ. Control output is byte-identical.

The Garr policy lists every Curse of Recklessness, Curse of the Elements and
Curse of Shadow rank (Wowhead Classic spell pages, checked 2026-10-18) applied
to Garr or Firesworn, and nothing else: the label and limitation name those
three curses, and other curses stay outside the count, so a zero is never a
general curse zero. Applications are recordings, not uptime, assignment or
evidence of raid benefit. Another Warlock's curse is not the player's. A zero
or unknown count alone supplies no prompt or criticism.

Each first qualified application per spell, target and recorded instance
supplies one review prompt naming the curse, target and time, asking the player
to confirm which curse the raid assigned before copying a reference curse
choice. An absent instance is shown as unrecorded. The prompt never recommends
a different curse.

Real acceptance: the subject of each of the three Garr Warlock archives was
independently enumerated from SOURCE pages, encounter All pages and the
maximum-multiplicity union before modelling. Every observation matches; format
1 counts are unknown and the format 2 count is complete. Other encounters stay
unconfigured until real evidence supports them.
