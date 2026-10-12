"""Evidence model: every surfaced value says how it is known.

- OBSERVED: read directly from a WCL field or event.
- DERIVED: deterministic calculation over observed data.
- INFERRED: produced by a named rule that can be wrong.
- UNKNOWN: the data cannot support a value; the value is None.

Two kinds of claim:

- VALUE: a value read or computed from what is present ("this cast happened",
  "this field says 0").
- COMPLETE: a value that is only true if no event is missing: whole-fight
  totals, counts, cadences, and every claim of non-occurrence ("no Windfury
  proc", "zero deaths"). A COMPLETE claim must carry coverage references for the
  streams it read, all trusted; otherwise it can only be UNKNOWN.

Build values only through the factory functions; `__post_init__` re-checks the
rules so a direct constructor cannot bypass them.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

MAX_EVENT_REFS = 50


class EvidenceError(ValueError):
    """An Evidenced value violates the evidence rules."""


class EvidenceLevel(StrEnum):
    OBSERVED = "observed"
    DERIVED = "derived"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class Claim(StrEnum):
    VALUE = "value"
    COMPLETE = "complete"


class WindfuryStatus(StrEnum):
    CONFIRMED = "confirmed"
    NOT_OBSERVED = "not-observed"
    UNKNOWN = "unknown"


class RaceStatus(StrEnum):
    API_CONFIRMED = "api-confirmed"
    RACIAL_EVENT_CONFIRMED = "racial-event-confirmed"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class Faction(StrEnum):
    ALLIANCE = "Alliance"
    HORDE = "Horde"


ABSENCE_VALUES: frozenset[object] = frozenset({WindfuryStatus.NOT_OBSERVED})
"""Values that assert non-occurrence and are therefore always COMPLETE claims."""


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """Where a value came from: a table row, or a set of event occurrences."""

    report_code: str
    fight_id: int | None
    actor_id: int | None
    source: str
    event_ids: tuple[tuple[str, int], ...] = ()
    event_count: int = 0
    detail: str | None = None

    @classmethod
    def events(
        cls,
        report_code: str,
        fight_id: int,
        actor_id: int | None,
        occurrences: Iterable[tuple[str, int]],
        detail: str | None = None,
    ) -> EvidenceRef:
        """Reference event occurrences (event_uid, copy_index); keeps the first 50 and the count."""
        items = list(occurrences)
        return cls(
            report_code=report_code,
            fight_id=fight_id,
            actor_id=actor_id,
            source="events",
            event_ids=tuple(items[:MAX_EVENT_REFS]),
            event_count=len(items),
            detail=detail,
        )


@dataclass(frozen=True, slots=True)
class CoverageRef:
    """The coverage decision behind a COMPLETE claim, kept for audit."""

    report_code: str
    fight_id: int
    actor_id: int
    direction: str
    trusted: bool


@dataclass(frozen=True, slots=True)
class Evidenced[T]:
    value: T | None
    level: EvidenceLevel
    refs: tuple[EvidenceRef, ...] = ()
    rule_id: str | None = None
    params: tuple[tuple[str, Any], ...] = ()
    note: str | None = None
    claim: Claim = Claim.VALUE
    coverage: tuple[CoverageRef, ...] = ()

    def __post_init__(self) -> None:
        if self.level is EvidenceLevel.UNKNOWN:
            if self.value is not None:
                raise EvidenceError("UNKNOWN evidence cannot carry a value")
            return
        if self.value is None:
            raise EvidenceError(f"{self.level} evidence needs a value")
        if not self.refs:
            raise EvidenceError(f"{self.level} evidence needs at least one reference")
        if self.level is EvidenceLevel.INFERRED and not self.rule_id:
            raise EvidenceError("INFERRED evidence must name its rule")
        if any(self.value is v for v in ABSENCE_VALUES) and self.claim is not Claim.COMPLETE:
            raise EvidenceError(f"{self.value!r} asserts non-occurrence and must be COMPLETE")
        if self.claim is Claim.COMPLETE and (
            not self.coverage or not all(c.trusted for c in self.coverage)
        ):
            raise EvidenceError("a COMPLETE claim needs trusted coverage for every stream read")

    @property
    def known(self) -> bool:
        return self.level is not EvidenceLevel.UNKNOWN


def _params(params: dict[str, Any] | None) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted((params or {}).items()))


def observed[T](value: T, *refs: EvidenceRef, note: str | None = None) -> Evidenced[T]:
    return Evidenced(value, EvidenceLevel.OBSERVED, refs, note=note)


def derived[T](
    value: T,
    *refs: EvidenceRef,
    rule_id: str | None = None,
    params: dict[str, Any] | None = None,
    note: str | None = None,
) -> Evidenced[T]:
    return Evidenced(
        value, EvidenceLevel.DERIVED, refs, rule_id=rule_id, params=_params(params), note=note
    )


def inferred[T](
    value: T,
    *refs: EvidenceRef,
    rule_id: str,
    params: dict[str, Any] | None = None,
    note: str | None = None,
) -> Evidenced[T]:
    return Evidenced(
        value, EvidenceLevel.INFERRED, refs, rule_id=rule_id, params=_params(params), note=note
    )


def unknown[T](note: str, *refs: EvidenceRef, coverage: Sequence[CoverageRef] = ()) -> Evidenced[T]:
    return Evidenced(None, EvidenceLevel.UNKNOWN, refs, note=note, coverage=tuple(coverage))


def complete_or_unknown[T](
    value: T,
    coverage: Sequence[CoverageRef],
    *refs: EvidenceRef,
    rule_id: str | None = None,
    params: dict[str, Any] | None = None,
    note: str | None = None,
) -> Evidenced[T]:
    """A COMPLETE claim: known only if every stream it read is trusted."""
    if not coverage or not all(c.trusted for c in coverage):
        return unknown(
            "a stream this value depends on is incomplete or untrustworthy",
            *refs,
            coverage=coverage,
        )
    return Evidenced(
        value,
        EvidenceLevel.DERIVED,
        refs,
        rule_id=rule_id,
        params=_params(params),
        note=note,
        claim=Claim.COMPLETE,
        coverage=tuple(coverage),
    )
