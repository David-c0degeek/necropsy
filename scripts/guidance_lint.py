"""Flag known guidance mistakes in a class draft before it goes to review.

Usage: uv run python scripts/guidance_lint.py DRAFT.yaml --class-id 7 --faction Alliance
           --review tests/golden/raids/mc-boss-source-review.json [--review ...]
           [--boss-review 50663=tests/golden/raids/lucifron-source-review.json ...]

A draft is the YAML a drafter writes before integration: encounter ids mapping
to {boss, items: [{rule, section, classes, metrics, source, retrieved, text,
support}], categories}. The lint is mechanical: every finding names a rule and a
reason, and a clean run means none of these known patterns occurred, never that
the guidance is correct. It checks that

- every support key exists in the cited boss's source review, and every item
  cites that review's URL with a date;
- items carry exactly the unit's class, and their rule ids name the boss;
- each boss has a loadout-applicability item and all eight categories;
- the text avoids claims that earlier reviews rejected: unqualified Fear Ward
  (Dwarf-only in Classic Era), another faction's class roles (Paladins for
  Horde, Shamans for Alliance), Wrath of Ragnaros target selection, guide timers
  without their phase context, "Lucifron's debuffs" range claims, removal
  capability stated from general knowledge, and positioning advice without the
  "positions are not recorded" boundary.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

CATEGORIES = (
    "preparation",
    "loadout",
    "opener_and_cooldowns",
    "execution",
    "resource",
    "utility",
    "avoidance",
    "raid_coordination",
)
CLASS_TAGS = {
    2: "druid",
    3: "hunter",
    4: "mage",
    6: "paladin",
    7: "priest",
    8: "rogue",
    9: "shaman",
    10: "warlock",
    11: "warrior",
}
# Advice to move or place yourself; a bare range or radius fact is not advice.
POSITIONING = re.compile(r"\b(stand|stands|standing|spot|spread|closest|move ahead)\b", re.I)
POSITION_BOUNDARY = re.compile(
    r"(do not|does not|no) record( any)? positions|records no positions", re.I
)
REMOVAL_CAPABILITY = re.compile(
    r"\b(cannot|can't|does not|doesn't|can|removes?|dispels?)\b"
    r"[^.]{0,40}\b(remove|dispel|cleanse|cure)",
    re.I,
)


def _keys(source: dict[str, Any]) -> set[str]:
    keys = set(source.get("excerpts") or {})
    for extra in source.get("capability_sources") or ():
        keys |= _keys(extra)
    for conflict in source.get("conflicts") or ():
        keys -= set(conflict.get("keys") or ())
    return keys


def load_reviews(paths: list[Path]) -> dict[int, dict[str, Any]]:
    """Encounter id -> {url, retrieved, keys} across the given source reviews."""
    found: dict[int, dict[str, Any]] = {}
    for path in paths:
        review = json.loads(path.read_text(encoding="utf-8"))
        date = (review.get("retrieval") or {}).get("date")
        for source in review.get("sources") or ():
            if "encounter_id" in source:
                found[source["encounter_id"]] = {
                    "url": source["url"],
                    "retrieved": date,
                    "keys": _keys(source),
                }
    return found


def load_boss_review(encounter: int, path: Path) -> dict[int, dict[str, Any]]:
    """A single-boss review: its wiki page is the citation, all excerpts support."""
    review = json.loads(path.read_text(encoding="utf-8"))
    sources = review.get("sources") or []
    wiki = next(s["url"] for s in sources if "warcraft.wiki.gg" in s["url"])
    keys = set().union(*(_keys(s) for s in sources))
    return {encounter: {"url": wiki, "retrieved": review["retrieval"]["date"], "keys": keys}}


def lint(
    draft: dict[int, Any],
    class_id: int,
    faction: str,
    reviews: dict[int, dict[str, Any]],
    *,
    require_healer_loadout: bool = True,
) -> list[str]:
    tag = CLASS_TAGS[class_id]
    findings: list[str] = []
    for encounter, boss in draft.items():
        review = reviews.get(encounter)
        items = boss.get("items") or []
        rules = {i.get("rule") for i in items}
        if require_healer_loadout and not any(
            r and r.endswith(f"-{tag}-healer-loadout-applicability-v1") for r in rules
        ):
            findings.append(f"{encounter}: no {tag} loadout-applicability item")
        missing = [c for c in CATEGORIES if c not in (boss.get("categories") or {})]
        if missing:
            findings.append(f"{encounter}: categories missing {', '.join(missing)}")
        for item in items:
            rule, text = str(item.get("rule")), str(item.get("text", ""))
            where = f"{encounter} {rule}"
            if item.get("classes") != [class_id]:
                findings.append(f"{where}: classes {item.get('classes')} is not [{class_id}]")
            if f"-{tag}-" not in rule:
                findings.append(f"{where}: rule id does not name the class tag {tag}")
            if review is None:
                findings.append(f"{where}: no source review covers encounter {encounter}")
            else:
                if item.get("source") != review["url"]:
                    findings.append(f"{where}: source is not the review URL {review['url']}")
                if review["retrieved"] and item.get("retrieved") != review["retrieved"]:
                    findings.append(
                        f"{where}: retrieved is not the review date {review['retrieved']}"
                    )
                unknown = [k for k in item.get("support") or () if k not in review["keys"]]
                if unknown:
                    findings.append(
                        f"{where}: support keys not in the review: {', '.join(unknown)}"
                    )
            if "Fear Ward" in text and "Dwarf" not in text:
                findings.append(f"{where}: Fear Ward without its Dwarf-only availability")
            if faction == "Horde" and re.search(r"\bPaladins?\b", text) and "Alliance" not in text:
                findings.append(
                    f"{where}: Paladin role in Horde guidance without an Alliance-only note"
                )
            if faction == "Alliance" and re.search(r"\bShamans?\b", text) and "Horde" not in text:
                findings.append(
                    f"{where}: Shaman role in Alliance guidance without a Horde-only note"
                )
            if re.search(
                r"Wrath of Ragnaros|targeted knockback|random player with a mana bar", text
            ):
                findings.append(f"{where}: Wrath of Ragnaros targeting conflicts with spell data")
            if re.search(r"\b90 seconds?\b", text) and "submerge" not in text.lower():
                findings.append(f"{where}: 90 second timer without its submerge context")
            if "Lucifron's debuffs" in text:
                findings.append(f"{where}: Lucifron range claim beyond the curse")
            if (
                REMOVAL_CAPABILITY.search(text)
                and "cited guide" not in text
                and "source" not in text
                and "excerpt" not in text
            ):
                findings.append(f"{where}: removal capability stated without the cited source")
            if POSITIONING.search(text) and not POSITION_BOUNDARY.search(text):
                findings.append(f"{where}: positioning advice without the no-positions boundary")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("draft", type=Path)
    parser.add_argument("--class-id", type=int, required=True)
    parser.add_argument("--faction", choices=("Alliance", "Horde"), required=True)
    parser.add_argument("--review", type=Path, action="append", default=[])
    parser.add_argument(
        "--boss-review",
        action="append",
        default=[],
        metavar="ENCOUNTER=PATH",
        help="a single-boss source review (Lucifron, Geddon)",
    )
    args = parser.parse_args(argv)
    draft = yaml.safe_load(args.draft.read_text(encoding="utf-8"))
    reviews = load_reviews(args.review)
    for pair in args.boss_review:
        encounter, path = pair.split("=", 1)
        reviews.update(load_boss_review(int(encounter), Path(path)))
    findings = lint(draft, args.class_id, args.faction, reviews)
    for line in findings:
        print(line)
    print(f"{len(findings)} finding(s); a clean run is not a content review")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
