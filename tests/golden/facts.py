"""Golden-fact register: schema, loader and acceptance rules.

A fact is a single checkable statement about the frozen Haplina fixture. The
register says where each expectation came from and how far it has been checked:

- ``verified-against-raw``: confirmed against raw events in the fixture.
- ``oracle-only``: taken from the earlier ChatGPT-era outputs, not yet confirmed.
- ``disputed``: raw data and oracle disagree; needs a recorded resolution.

Acceptance requires every mandatory fact to be verified against raw data, and
every non-mandatory unverified fact to carry a recorded resolution. No fact is
accepted on its status alone; analyzer tests compare values within tolerance.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

REGISTER_PATH = Path(__file__).parent / "haplina_naxx" / "facts.yaml"


class FactStatus(StrEnum):
    VERIFIED_AGAINST_RAW = "verified-against-raw"
    ORACLE_ONLY = "oracle-only"
    DISPUTED = "disputed"


class FactMode(StrEnum):
    HISTORICAL = "historical"
    LIVE = "live"


class FactSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    file: str
    locator: str


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9-]+(\.[a-z0-9-]+)*$")
    statement: str = Field(min_length=10)
    mode: FactMode
    mandatory: bool
    status: FactStatus
    expected: Any
    tolerance: float | None = Field(default=None, ge=0)
    unit: str | None = None
    source: FactSource
    evidence: str | None = None
    resolution: str | None = None

    @model_validator(mode="after")
    def _disputed_needs_resolution(self) -> Fact:
        if self.status is FactStatus.DISPUTED and not self.resolution:
            raise ValueError(f"{self.id}: disputed facts need a resolution")
        if self.status is FactStatus.VERIFIED_AGAINST_RAW and not self.evidence:
            raise ValueError(f"{self.id}: verified facts must record their evidence")
        return self


class FactRegister(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    facts: tuple[Fact, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> FactRegister:
        ids = [f.id for f in self.facts]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate fact ids: {duplicates}")
        return self

    @property
    def mandatory(self) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if f.mandatory)

    def by_id(self, fact_id: str) -> Fact:
        for fact in self.facts:
            if fact.id == fact_id:
                return fact
        raise KeyError(fact_id)

    def acceptance_problems(self) -> list[str]:
        """Reasons the register does not yet satisfy milestone acceptance."""
        problems: list[str] = []
        if not self.mandatory:
            problems.append("no mandatory facts")
        for fact in self.facts:
            verified = fact.status is FactStatus.VERIFIED_AGAINST_RAW
            if fact.mandatory and not verified:
                problems.append(f"{fact.id}: mandatory fact is {fact.status.value}")
            elif not verified and not fact.resolution:
                problems.append(
                    f"{fact.id}: {fact.status.value} fact without a recorded resolution"
                )
        return problems


def load_register(path: Path = REGISTER_PATH) -> FactRegister:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return FactRegister.model_validate(data)
