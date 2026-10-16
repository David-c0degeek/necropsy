"""Class and ranking taxonomy; encounter duties remain separate evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from necropsy.analysis.class_catalog import CATEGORIES, category_for
from necropsy.analysis.class_catalog import CLASS_NAMES as CLASS_NAMES


class FightRole(StrEnum):
    FERAL = "feral-dps"
    BALANCE = "balance-dps"
    HEALER = "restoration"
    TANK = "feral-tank"
    HYBRID = "hybrid"
    UNCERTAIN = "uncertain"


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


def selected_spec(value: str | None) -> str | None:
    """User-facing spec names map to WCL categories without assigning encounter duty."""
    if value is None:
        return None
    if value.strip().casefold() in ("", "all"):
        return None
    names = {name.casefold(): name for name in DRUID_CATEGORIES}
    names.update({name.casefold(): name for cats in CATEGORIES.values() for name in cats})
    names.update({"dps": "DPS", "healer": "Healer"})
    names.update(
        {
            "tank": "Guardian",
            "boomkin": "Balance",
            "marksmanship": "Marksmanship",
            "mm": "Marksmanship",
        }
    )
    category = names.get(value.strip().casefold())
    if category is None:
        raise ValueError("choose a supported Classic Era WCL spec/category for this class")
    return category


def ranking_policy(
    class_id: int,
    category: str | None = None,
    metric: str | None = None,
) -> RankingPolicy:
    """Only verified Classic Era WCL categories; never infer one from talents."""
    if type(class_id) is not int or class_id not in CLASS_NAMES:
        raise ValueError("only Classic Era classes are supported")
    if class_id in CATEGORIES:
        category = category_for(class_id, category)
        choices = CATEGORIES[class_id]
        if category not in choices:
            raise ValueError(f"choose a {CLASS_NAMES[class_id]} category: {', '.join(choices)}")
        default_metric, role = choices[category]
        if metric not in (None, default_metric):
            raise ValueError(
                f"{CLASS_NAMES[class_id]} {category} uses ranking metric {default_metric}"
            )
        return RankingPolicy(class_id, category, default_metric, role)
    if class_id == 3:
        if category not in (None, "Marksmanship") or metric not in (None, "dps"):
            raise ValueError("Classic Era Hunter supports the WCL Marksmanship category and DPS")
        return RankingPolicy(3, category, "dps", "dps")
    if category not in DRUID_CATEGORIES:
        raise ValueError("choose a Druid --category: Balance, Feral, Guardian or Restoration")
    default_metric, role = DRUID_CATEGORIES[category]
    selected = metric or default_metric
    if selected == "hps" and category == "Balance":
        role = FightRole.HEALER
    elif selected != default_metric:
        raise ValueError("unsupported category/metric combination")
    return RankingPolicy(2, category, selected, role.value)


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
    """Eligibility dimensions must be known; build is optional recorded context."""

    class_id: int
    encounter_id: int
    faction: str
    build: str | None
    category: str
    role: FightRole
    metric: str
    partition: int
    game: str = "classic_era"
    zone: int = 2006
    difficulty: int = 3
    hard_mode: int = 0

    def __post_init__(self) -> None:
        policy = ranking_policy(self.class_id, self.category, self.metric)
        if (
            self.role.value != policy.role
            or self.metric != policy.metric
            or (self.build is not None and not self.build.strip())
            or self.faction not in ("Alliance", "Horde")
            or self.partition <= 0
            or self.game != "classic_era"
            or self.zone != 2006
            or self.difficulty != 3
            or self.hard_mode != 0
        ):
            raise ValueError("incomplete or incompatible role comparison dimensions")
