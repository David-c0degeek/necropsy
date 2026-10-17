"""Enumerate legal Era comparison obligations without inventing ranking pools."""

from dataclasses import dataclass

from necropsy.analysis.class_catalog import WCL_CATEGORIES
from necropsy.analysis.roles import ranking_policy
from necropsy.raids import RAIDS, encounters
from necropsy.rules import load_rules


@dataclass(frozen=True, order=True, slots=True)
class Configuration:
    class_id: int
    category: str
    metric: str
    faction: str


@dataclass(frozen=True, order=True, slots=True)
class CoverageCell:
    raid: str
    zone_id: int
    encounter_id: int
    boss: str
    variant: str
    configuration: Configuration

    @property
    def key(self) -> str:
        config = self.configuration
        return "/".join(
            map(
                str,
                (
                    self.raid,
                    self.encounter_id,
                    config.class_id,
                    config.category,
                    config.metric,
                    config.faction,
                ),
            )
        )


def configurations() -> tuple[Configuration, ...]:
    """Declared talent trees are context, never extra comparison categories."""
    result: list[Configuration] = []
    for class_id, categories in WCL_CATEGORIES.items():
        factions = (
            ("Alliance",)
            if class_id == 6
            else ("Horde",)
            if class_id == 9
            else (
                "Alliance",
                "Horde",
            )
        )
        for category in categories:
            metrics = (
                ("dps", "hps")
                if (class_id, category) == (2, "Balance")
                else (ranking_policy(class_id, category).metric,)
            )
            for metric in metrics:
                ranking_policy(class_id, category, metric)
                result.extend(Configuration(class_id, category, metric, f) for f in factions)
    return tuple(sorted(result))


def coverage_cells() -> tuple[CoverageCell, ...]:
    """Packaged scope, independent of development tracking or saved analyses."""
    data = load_rules("classic_era", "raid_scope")
    raids = {r.slug: r for r in RAIDS}
    result: list[CoverageCell] = []
    for slug, expected in data["raids"].items():
        raid = raids[slug]
        bosses = encounters(raid)
        if raid.zone_id != expected["zone_id"] or len(bosses) != expected["encounters"]:
            raise ValueError(f"{slug}: encounter catalog differs from supported scope")
        for boss in bosses:
            variant = str(expected.get("variants", {}).get(boss["id"], "standard"))
            result.extend(
                CoverageCell(slug, raid.zone_id, boss["id"], boss["name"], variant, config)
                for config in configurations()
            )
    return tuple(sorted(result))
