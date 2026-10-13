"""Developer tooling: extract Classic Era game data used by the analysis.

Not part of the shipped CLI and never run at analysis time. It downloads four
tables of the game's own client data for one pinned build from wago.tools
(Item, ItemSparse, ItemSet, SpellItemEnchantment, ItemEffect), keeps only the rows a
snapshot needs (every item and enchant worn by the snapshot's Hunters, item sets
containing those items, and the ammunition list), and writes them as package
rule data with their source and build.

  uv run python scripts/game_data.py <analysis.duckdb> [--cache DIR]

The output is committed; re-run it only to refresh the data from a new build.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

import duckdb
import yaml

BUILD = "1.15.9.70003"
PRODUCT = "wow_classic_era"
SOURCE = "https://wago.tools/db2/{table}/csv?build={build}"
OUT = Path(__file__).resolve().parents[1] / "src/necropsy/rules/classic_era/game_data.yaml"

WEAPON_SUBCLASS = {2: "bow", 3: "gun", 18: "crossbow", 19: "wand", 16: "thrown"}
AMMO_TYPE = {2: "arrow", 3: "bullet"}
SLOT = {
    1: "head",
    2: "neck",
    3: "shoulder",
    4: "shirt",
    5: "chest",
    6: "waist",
    7: "legs",
    8: "feet",
    9: "wrist",
    10: "hands",
    11: "finger",
    12: "trinket",
    13: "one-hand",
    14: "shield",
    15: "ranged",
    16: "back",
    17: "two-hand",
    19: "tabard",
    20: "chest",
    21: "main-hand",
    22: "off-hand",
    23: "held-in-off-hand",
    24: "ammo",
    25: "thrown",
    26: "ranged",
    28: "relic",
}
"""Item InventoryType to equipment slot name."""
AMMUNITION = (11284, 11285, 11630, 12654, 13377, 15997, 18042, 19316, 19317)
"""Endgame-relevant Classic Era ammunition (arrows and bullets) listed for advice."""


def _table(name: str, cache: Path | None) -> list[dict[str, str]]:
    path = None if cache is None else cache / f"{name}-{BUILD}.csv"
    if path is not None and path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        url = SOURCE.format(table=name, build=BUILD)
        request = urllib.request.Request(url, headers={"User-Agent": "necropsy-game-data/1"})
        with urllib.request.urlopen(request, timeout=120) as response:
            text = response.read().decode("utf-8")
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def _worn(con: duckdb.DuckDBPyConnection) -> tuple[set[int], set[int]]:
    items: set[int] = set()
    enchants: set[int] = set()
    rows = con.execute(
        """SELECT c.gear FROM combatant_info c
           JOIN benchmark_participants p ON p.report_code = c.report_code
            AND p.fight_id = c.fight_id
           JOIN actors a ON a.report_code = c.report_code AND a.actor_id = c.actor_id
            AND a.name = p.player"""
    ).fetchall()
    for (gear,) in rows:
        for g in json.loads(gear) if isinstance(gear, str) else gear:
            if g.get("id"):
                items.add(int(g["id"]))
            for key in ("permanentEnchant", "temporaryEnchant"):
                if g.get(key):
                    enchants.add(int(g[key]))
    return items, enchants


def build(db: Path, cache: Path | None) -> dict[str, Any]:
    con = duckdb.connect(str(db), read_only=True)
    worn_items, worn_enchants = _worn(con)
    con.close()
    item = {int(r["ID"]): r for r in _table("Item", cache)}
    sparse = {int(r["ID"]): r for r in _table("ItemSparse", cache)}
    sets = _table("ItemSet", cache)
    enchants = {int(r["ID"]): r for r in _table("SpellItemEnchantment", cache)}
    on_use: dict[int, dict[str, int]] = {}
    for r in _table("ItemEffect", cache):
        if r["TriggerType"] == "0" and int(r["ParentItemID"]) in worn_items:
            on_use[int(r["ParentItemID"])] = {
                "spell": int(r["SpellID"]),
                "cooldown_ms": int(r["CoolDownMSec"]),
                "category": int(r["SpellCategoryID"]),
                "category_cooldown_ms": int(r["CategoryCoolDownMSec"]),
            }
    wanted = worn_items | set(AMMUNITION)
    items_out = []
    for item_id in sorted(wanted):
        if item_id not in sparse:
            continue
        row = item.get(item_id, {})
        entry: dict[str, Any] = {"id": item_id, "name": sparse[item_id]["Display_lang"]}
        slot = SLOT.get(int(row.get("InventoryType") or 0))
        if slot:
            entry["slot"] = slot
        if row.get("ClassID") == "2":
            sub = int(row["SubclassID"])
            if sub in WEAPON_SUBCLASS:
                entry["ranged_type"] = WEAPON_SUBCLASS[sub]
                ammo = int(row.get("AmmunitionType") or 0)
                if ammo in AMMO_TYPE:
                    entry["uses_ammo"] = AMMO_TYPE[ammo]
        if row.get("ClassID") == "6":
            entry["ammo"] = AMMO_TYPE.get(int(row["SubclassID"]), "other")
        if item_id in on_use:
            entry["on_use"] = on_use[item_id]
        items_out.append(entry)
    sets_out = []
    for r in sets:
        members = [int(r[f"ItemID_{i}"]) for i in range(17) if r.get(f"ItemID_{i}", "0") != "0"]
        if members and set(members) & worn_items:
            sets_out.append({"id": int(r["ID"]), "name": r["Name_lang"], "items": sorted(members)})
    enchants_out = [
        {"id": e, "name": enchants[e]["Name_lang"]} for e in sorted(worn_enchants) if e in enchants
    ]
    return {
        "version": 1,
        "source": {
            "provider": "wago.tools DB2 exports of the game client data",
            "product": PRODUCT,
            "build": BUILD,
            "tables": ["Item", "ItemSparse", "ItemSet", "SpellItemEnchantment", "ItemEffect"],
            "url_template": SOURCE,
        },
        "items": items_out,
        "item_sets": sorted(sets_out, key=lambda s: s["id"]),
        "enchants": enchants_out,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db", type=Path, help="analysis database of the snapshot")
    parser.add_argument("--cache", type=Path, default=None, help="keep downloaded CSVs here")
    args = parser.parse_args(argv)
    data = build(args.db, args.cache)
    header = (
        "# Classic Era game data used by Necropsy, extracted by scripts/game_data.py.\n"
        f"# Source: the game's client data tables, build {BUILD} ({PRODUCT}), via wago.tools.\n"
        "# Only rows the snapshot's Hunters wear, their item sets, and endgame ammunition.\n"
    )
    OUT.write_text(
        header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"{OUT}: {len(data['items'])} items, {len(data['item_sets'])} sets, "
        f"{len(data['enchants'])} enchants"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
