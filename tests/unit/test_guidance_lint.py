"""The guidance lint catches each mistake earlier reviews rejected, and a clean
draft passes; it never certifies content."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts import guidance_lint as gl

URL = "https://warcraft.wiki.gg/wiki/Magmadar"
REVIEWS = {50664: {"url": URL, "retrieved": "2026-10-20", "keys": {"panic", "fear_ward"}}}
CATEGORIES = {c: "x" for c in gl.CATEGORIES}


def item(rule: str, text: str, **extra: Any) -> dict[str, Any]:
    return {
        "rule": rule,
        "section": "before",
        "classes": [7],
        "metrics": ["hps"],
        "source": URL,
        "retrieved": "2026-10-20",
        "text": text,
        "support": ["panic"],
    } | extra


LOADOUT = item("magmadar-priest-healer-loadout-applicability-v1", "No loadout change is named.")


def run(*items: dict[str, Any], class_id: int = 7, faction: str = "Alliance") -> list[str]:
    draft = {50664: {"items": [LOADOUT, *items], "categories": CATEGORIES}}
    return gl.lint(draft, class_id, faction, REVIEWS)


def test_a_clean_draft_has_no_findings() -> None:
    assert (
        run(item("magmadar-priest-range-v1", "Panic makes enemies flee in fear for 8 sec.")) == []
    )


def test_each_known_mistake_is_flagged() -> None:
    cases = {
        "Fear Ward without": "Priests should keep Fear Ward on the main tank.",
        "Wrath of Ragnaros targeting": "Wrath of Ragnaros targets a random player with a mana bar.",
        "90 second timer": "He returns after 90 seconds.",
        "Lucifron range claim": "Lucifron's debuffs have a range of 40 yards.",
        "removal capability": "Cleanse does not remove fear.",
        "no-positions boundary": "Stand at maximum range behind the tank.",
    }
    for expected, text in cases.items():
        findings = run(item("magmadar-priest-x-v1", text))
        assert any(expected in f for f in findings), (expected, findings)


def test_faction_roles_and_bindings_are_checked() -> None:
    horde = run(
        item("magmadar-shaman-x-v1", "The Paladin pulls with Divine Shield.", classes=[9]),
        class_id=9,
        faction="Horde",
    )
    assert any("Paladin role in Horde guidance" in f for f in horde)
    assert any("loadout-applicability" in f for f in horde)  # the Priest loadout item is wrong
    wrong = run(item("magmadar-priest-x-v1", "Panic is a fear.", classes=[6], support=["nope"]))
    assert any("classes [6]" in f for f in wrong)
    assert any("support keys not in the review: nope" in f for f in wrong)
    elsewhere = run(item("magmadar-priest-x-v1", "Panic is a fear.", source="https://x.invalid"))
    assert any("source is not the review URL" in f for f in elsewhere)


def test_missing_categories_and_loadout_items_are_flagged() -> None:
    findings = gl.lint({50664: {"items": [], "categories": {}}}, 7, "Alliance", REVIEWS)
    assert any("no priest loadout-applicability item" in f for f in findings)
    assert any("categories missing preparation" in f for f in findings)


def test_source_and_capability_conflicts_cannot_be_used_as_support(tmp_path: Path) -> None:
    path = tmp_path / "review.json"
    path.write_text(
        json.dumps(
            {
                "retrieval": {"date": "2026-10-20"},
                "sources": [
                    {
                        "encounter_id": 50664,
                        "url": URL,
                        "excerpts": {"panic": "Fear.", "contradiction": "Unsettled."},
                        "conflicts": [{"keys": ["contradiction"]}],
                        "capability_sources": [
                            {
                                "excerpts": {"fear_ward": "Unsettled capability."},
                                "conflicts": [{"keys": ["fear_ward"]}],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    reviews = gl.load_reviews([path])
    assert reviews[50664]["keys"] == {"panic"}
    draft = {
        50664: {
            "items": [LOADOUT, item("magmadar-priest-x-v1", "Claim.", support=["fear_ward"])],
            "categories": CATEGORIES,
        }
    }
    findings = gl.lint(draft, 7, "Alliance", reviews)
    assert any("support keys not in the review: fear_ward" in f for f in findings)
