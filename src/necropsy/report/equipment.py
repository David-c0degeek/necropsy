"""Shared recorded gear names and enchant resolution; unresolved IDs remain explicit."""

from __future__ import annotations

from typing import Any

from necropsy.analysis import gamedata
from necropsy.analysis.generic.catalog import ItemName


def enrich_gear(items: Any, names: dict[int, ItemName]) -> Any:
    if not isinstance(items, list):
        return items
    out = []
    for g in items:
        if not isinstance(g, dict):
            out.append(g)
            continue
        found = names.get(int(g["item_id"]))
        out.append(
            {
                **g,
                "name": None if found is None else found.name,
                "name_source": "none" if found is None else found.source,
                "name_note": None if found is None else found.note,
                "enchant_name": gamedata.enchant_names().get(int(g.get("permanent_enchant") or 0)),
                "temporary_enchant_name": gamedata.enchant_names().get(
                    int(g.get("temporary_enchant") or 0)
                ),
            }
        )
    return out
