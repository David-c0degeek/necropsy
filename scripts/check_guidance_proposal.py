"""Replay the Naxx guidance recipes and compare their proposed integration, read-only.

This checks frozen bytes, legal coverage and projection through the existing
work-order verifier. It does not approve source paraphrases or publish content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from necropsy.raids.scope import coverage_cells  # noqa: E402
from scripts import guidance_lint as gl  # noqa: E402
from scripts.guidance_work_order import UNKNOWN, Order, source_for, verify  # noqa: E402


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _pinned(root: Path, name: str, digest: str) -> bytes:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("proposal input escapes the repository")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"proposal input pin differs: {name}")
    return raw


class UniqueLoader(yaml.SafeLoader):
    """Safe YAML with duplicate mappings refused, including nested item fields."""


def _mapping(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key, value in loader.construct_pairs(node, deep=True):
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = value
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def check(path: Path, root: Path = ROOT) -> dict[str, Any]:
    bundle = json.loads(path.read_bytes(), object_pairs_hook=_unique)
    source_raw = _pinned(root, bundle["source_path"], bundle["source_sha256"])
    json.loads(source_raw, object_pairs_hook=_unique)
    proposal_raw = _pinned(root, bundle["proposed_yaml_path"], bundle["proposed_yaml_sha256"])
    proposal = yaml.load(proposal_raw, Loader=UniqueLoader)
    expected_cells = {
        (
            c.encounter_id,
            c.configuration.class_id,
            c.configuration.category,
            c.configuration.metric,
            c.configuration.faction,
        )
        for c in coverage_cells()
        if c.raid == "naxxramas"
    }
    expected_bosses = {c[0] for c in expected_cells}
    if set(bundle["profiles"]) != {str(e) for e in expected_bosses}:
        raise ValueError("profiles must cover exactly the Naxx encounters")
    seen: set[tuple[int, int, str, str, str]] = set()
    order_ids: set[str] = set()
    expected: dict[int, Any] = {}
    withheld: set[tuple[int, str]] = set()
    for encounter in expected_bosses:
        keys = [p["key"] for p in bundle["profiles"][str(encounter)]]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate profile key")
        for profile in bundle["profiles"][str(encounter)]:
            if (
                profile["applies"] not in {"all", "hps", "tank-category"}
                or profile["category"] not in gl.CATEGORIES
                or profile["proposed_section"] not in {"before", "during", "raid"}
            ):
                raise ValueError("unknown profile applicability, category or section")
            if profile["applies"] == "tank-category":
                withheld.add((encounter, profile["key"]))
    for recipe in bundle["recipes"]:
        order = Order.model_validate(recipe["order"])
        cell: tuple[int, int, str, str, str] = (
            order.encounter_id,
            order.class_id,
            order.category,
            order.metric,
            order.faction,
        )
        if cell not in expected_cells or cell in seen or order.id in order_ids:
            raise ValueError("illegal or duplicate boss/configuration/order")
        seen.add(cell)
        order_ids.add(order.id)
        if (order.input.path, order.input.sha256) != (
            bundle["source_path"],
            bundle["source_sha256"],
        ):
            raise ValueError("order does not use the proposal's frozen source")
        source, date = source_for(order, root)
        profiles = [
            p
            for p in bundle["profiles"][str(order.encounter_id)]
            if p["applies"] == "all"
            or (p["applies"] == "hps" and order.metric == "hps")
            or (p["applies"] == "tank-category" and order.category in {"Guardian", "Protection"})
        ]
        if [p["key"] for p in profiles] != recipe["applicable_profile_keys"]:
            raise ValueError("recipe profile selection differs")
        categories: dict[str, Any] = {
            k: {"status": "unknown", "rules": [], "reason": UNKNOWN} for k in gl.CATEGORIES
        }
        items = []
        slug = re.sub(r"[^a-z0-9]+", "-", order.boss.lower()).strip("-")
        entry = expected.setdefault(
            order.encounter_id,
            {"boss": source["boss"], "source": source["url"], "retrieved": date, "items": []},
        )
        for profile in profiles:
            rule = f"{slug}-{gl.CLASS_TAGS[order.class_id]}-{profile['key']}-v1"
            item = {
                "rule": rule,
                "section": "strategy",
                "classes": [order.class_id],
                "metrics": [order.metric],
                "source": source["url"],
                "retrieved": date,
                "text": profile["text"],
                "support": profile["support"],
                "quotes": {k: source["excerpts"][k] for k in profile["support"]},
            }
            items.append(item)
            category = categories[profile["category"]]
            category.update(status="draft", reason="")
            category["rules"].append(rule)
            if profile["applies"] == "tank-category":
                continue
            rows = [r for r in entry["items"] if r["rule"] == rule]
            row = {k: item[k] for k in ("rule", "classes", "metrics", "text", "support")}
            row["section"] = profile["proposed_section"]
            if not rows:
                entry["items"].append(row)
            elif order.metric not in rows[0]["metrics"]:
                rows[0]["metrics"].append(order.metric)
        draft = {
            "order_id": order.id,
            "encounter_id": order.encounter_id,
            "boss": order.boss,
            "items": items,
            "categories": categories,
        }
        raw = (json.dumps(draft, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        if hashlib.sha256(raw).hexdigest() != recipe["draft_sha256"]:
            raise ValueError("reconstructed draft differs from its frozen digest")
        findings = verify(order, raw, root)
        if findings:
            raise ValueError(f"{order.id}: {findings}")
    if seen != expected_cells or bundle["drafts"] != len(seen):
        raise ValueError("recipes do not cover every legal Naxx cell exactly once")
    if {(w["encounter"], w["key"]) for w in bundle["withheld_profiles"]} != withheld:
        raise ValueError("withheld tank-only profiles differ")

    # YAML order has no semantic meaning; item order does not broaden applicability.
    def normalized(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "strategy": {
                e: {
                    **v,
                    "items": sorted(
                        [{**r, "metrics": sorted(r["metrics"])} for r in v["items"]],
                        key=lambda r: r["rule"],
                    ),
                }
                for e, v in data["strategy"].items()
            }
        }

    if normalized(proposal) != normalized({"strategy": expected}):
        raise ValueError("proposed integration differs from verified recipe projections")
    if set(proposal) != {"strategy"}:
        raise ValueError("proposal contains extra sections")
    for cell in seen:
        rows = expected[cell[0]]["items"]
        sections = {
            r["section"] for r in rows if cell[1] in r["classes"] and cell[3] in r["metrics"]
        }
        if sections != {"before", "during", "raid"}:
            raise ValueError("legal projection lacks strategy sections")
    return {
        "drafts": len(seen),
        "bosses": len(expected),
        "withheld_profiles": len(withheld),
        "content_review": "pending",
        "model_calls": 0,
        "writes": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(check(args.bundle)))
        return 0
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as error:
        print(f"guidance proposal refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
