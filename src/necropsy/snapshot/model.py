"""Format-independent description of a raw WCL snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class SnapshotError(Exception):
    """The snapshot content is inconsistent or cannot be interpreted."""


class SnapshotScope(StrEnum):
    FULL = "full"
    SUBSET = "subset"


class ActorRole(StrEnum):
    PLAYER = "player"
    PET = "pet"
    PET_DISCOVERY = "pet-discovery"


class Direction(StrEnum):
    SOURCE = "source"
    TARGET = "target"
    LISTING = "listing"


class StreamStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    MISSING = "missing"
    MALFORMED = "malformed"
    ERROR = "error"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Character(_Frozen):
    id: int
    name: str
    class_id: int
    server: str
    region: str


class Zone(_Frozen):
    id: int
    name: str
    partition: int


class Participant(_Frozen):
    """Why a fight is in the snapshot: the subject's own fight or a cohort entry."""

    kind: Literal["you", "top"]
    boss: str
    encounter_id: int
    player: str
    server: str | None
    leaderboard_position: int | None
    total: float | None
    duration_ms: int | None
    spec: str | None


class SelectedFight(_Frozen):
    report_code: str
    fight_id: int
    participants: tuple[Participant, ...]


class SnapshotDescriptor(_Frozen):
    format: str
    archive_sha256: str
    scope: SnapshotScope
    subject: Character
    zone: Zone
    cohort: str
    top_n: int
    fights: tuple[SelectedFight, ...]
    source_fight_count: int
    source_errors: tuple[dict[str, Any], ...]


class StreamRef(_Frozen):
    report_code: str
    fight_id: int
    actor_id: int | None
    actor_name: str
    role: ActorRole
    direction: Direction
    owner_actor_id: int | None = None


@dataclass(frozen=True, slots=True)
class StreamRead:
    """Events of one stream in file order, with how complete the fetch was.

    A plain dataclass rather than a validated model: streams carry up to
    hundreds of thousands of raw event dicts.
    """

    ref: StreamRef
    status: StreamStatus
    pages: int
    events: list[dict[str, Any]]
    boundary_ambiguities: int
    detail: str | None = None
