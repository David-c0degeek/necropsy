"""The fact-freeze tool reproduces existing, independently reviewed raw oracles:
the pilot cell's Geddon mechanics and every frozen actor-effect context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import fact_freeze as ff

pytestmark = pytest.mark.golden
ROOT = Path(__file__).parent / "raids"
PILOT_SPEC = ROOT / "fact-specs" / "geddon-paladin-mechanics.spec.json"


def test_the_pilot_spec_reproduces_the_reviewed_geddon_oracle() -> None:
    spec = json.loads(PILOT_SPEC.read_bytes())
    oracle = json.loads((ROOT / "geddon-paladin-mechanics.json").read_bytes())
    assert (spec["fixture"], spec["sha256"]) == (oracle["fixture"], oracle["sha256"])
    result = ff.compute(spec, PILOT_SPEC.parent)
    queries = list(spec["queries"])
    assert len(result["contexts"]) == len(oracle["contexts"]) == 6
    for expected, actual in zip(oracle["contexts"], result["contexts"], strict=True):
        assert (
            ff.differences({k: expected[k] for k in queries}, {k: actual[k] for k in queries}) == []
        ), expected["player"]


def _effect_spec(case: dict[str, Any], stream: str) -> dict[str, Any]:
    return {
        "archive": case["archive"],
        "sha256": case["sha256"],
        "contexts": [
            {
                "report": case["report"],
                "fight": case["fight"],
                "actor": case["actor"],
                "player": case["player"],
                "subject": True,
            }
        ],
        "queries": {
            "duration_ms": {"kind": "duration_ms"},
            "transitions": {
                "kind": "aura_transitions",
                "ids": case["ability_ids"],
                "types": sorted(ff.AURA_TYPES),
                "unit": "ms",
                "with_ability": True,
                "stream": stream,
            },
        },
    }


EFFECTS = json.loads((ROOT / "effect-facts.json").read_bytes())["cases"]


@pytest.mark.parametrize("case", EFFECTS, ids=[c["id"] for c in EFFECTS])
def test_actor_effect_contexts_are_reproduced_from_each_available_stream(
    case: dict[str, Any],
) -> None:
    expected = case["expected"]
    (actor,) = ff.compute(_effect_spec(case, "actor"), ROOT)["contexts"]
    assert (
        ff.differences(
            [expected["duration_ms"], expected["transitions"]],
            [actor["duration_ms"], actor["transitions"]],
        )
        == []
    )
    try:
        (whole,) = ff.compute(_effect_spec(case, "all"), ROOT)["contexts"]
    except ff.FreezeError as error:
        # Older captures have no encounter All pages; the tool refuses rather
        # than falling back to the actor streams.
        assert "missing or not contiguous" in str(error)
        assert case["id"] == "geddon-feign-actor-effects-1"
        return
    assert ff.differences(actor["transitions"], whole["transitions"]) == []


@pytest.mark.parametrize("frozen", ["lucifron-paladin-mechanics.json"])
def test_frozen_files_still_match_their_raw_archives(frozen: str) -> None:
    assert ff.main(["check", str(ROOT / frozen)]) == 0
