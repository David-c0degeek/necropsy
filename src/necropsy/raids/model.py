"""One independently selectable Classic Era raid and its packaged encounter rules."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Raid:
    slug: str
    zone_id: int
    name: str
    short_name: str
