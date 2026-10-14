"""Class and ranking taxonomy; encounter duties remain separate evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class FightRole(StrEnum):
    FERAL = "feral-dps"
    BALANCE = "balance-dps"
    HEALER = "restoration"
    TANK = "feral-tank"
    HYBRID = "hybrid"
    UNCERTAIN = "uncertain"


CLASS_NAMES = {2: "Druid", 3: "Hunter"}


@dataclass(frozen=True, slots=True)
class RankingPolicy:
    class_id: int
    category: str | None
    metric: str
    role: str

    @property
    def class_name(self) -> str:
        return CLASS_NAMES[self.class_id]


DRUID_CATEGORIES = {
    "Balance": ("dps", FightRole.BALANCE),
    "Feral": ("dps", FightRole.FERAL),
    "Guardian": ("dps", FightRole.TANK),
    "Restoration": ("hps", FightRole.HEALER),
}


def ranking_policy(class_id: int, category: str | None = None) -> RankingPolicy:
    """Only verified Classic Era WCL categories; never infer one from talents."""
    if type(class_id) is not int or class_id not in CLASS_NAMES:
        raise ValueError("only Classic Era Hunter and Druid are supported")
    if class_id == 3:
        if category is not None:
            raise ValueError("Hunter selection retains its all-spec DPS policy")
        return RankingPolicy(3, None, "dps", "dps")
    if category not in DRUID_CATEGORIES:
        raise ValueError("choose a Druid --category: Balance, Feral, Guardian or Restoration")
    metric, role = DRUID_CATEGORIES[category]
    return RankingPolicy(2, category, metric, role.value)


@dataclass(frozen=True, slots=True)
class RoleOverride:
    """A user's declared assignment, never an observation or a ranking category."""

    role: FightRole
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, FightRole) or not self.reason.strip():
            raise ValueError("a role override needs a supported role and a reason")


def load_overrides(path: Path) -> dict[tuple[str, int], RoleOverride]:
    """Read explicit report/fight assignments; reject typos rather than ignore them."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("role overrides must be an object keyed by report/fight")
    result = {}
    for key, value in raw.items():
        if not isinstance(value, dict) or set(value) != {"role", "reason"}:
            raise ValueError(f"{key}: role override needs exactly role and reason")
        report, separator, fight = key.rpartition("/")
        if not report or not separator or not fight.isdecimal() or int(fight) <= 0:
            raise ValueError(f"invalid report/fight override key: {key}")
        if not isinstance(value["reason"], str):
            raise ValueError(f"{key}: override reason must be text")
        identity = (report, int(fight))
        if identity in result:
            raise ValueError(f"duplicate report/fight override: {key}")
        result[identity] = RoleOverride(FightRole(value["role"]), value["reason"])
    return result


@dataclass(frozen=True, slots=True)
class ComparisonKey:
    """Every dimension must be known; mixed duties have no aggregate baseline."""

    class_id: int
    encounter_id: int
    faction: str
    build: str
    category: str
    role: FightRole
    metric: str
    partition: int
    game: str = "classic_era"
    zone: int = 2006
    difficulty: int = 3
    hard_mode: int = 0

    def __post_init__(self) -> None:
        policy = ranking_policy(self.class_id, self.category)
        expected = DRUID_CATEGORIES.get(self.category)
        if (
            expected is None
            or self.role != expected[1]
            or self.metric != policy.metric
            or not self.build.strip()
            or self.faction not in ("Alliance", "Horde")
            or self.partition <= 0
            or self.game != "classic_era"
            or self.zone != 2006
            or self.difficulty != 3
            or self.hard_mode != 0
        ):
            raise ValueError("incomplete or incompatible role comparison dimensions")
