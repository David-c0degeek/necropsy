"""The capture queue keeps only reviewed, faction-observed subjects and never pays twice."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import capture_queue as cq
from scripts import capture_runner as cr

RUN: dict[str, Any] = {
    "entry_id": "mc-mage-fire-dps-horde",
    "raid": "mc",
    "zone": 2000,
    "class_id": 4,
    "class": "Mage",
    "category": "Fire",
    "metric": "dps",
    "faction": "Horde",
}
BOSSES = {"mc": {str(e): f"Boss {e}" for e in range(1, 11)}}


def _register(cells: dict[str, list[int]]) -> dict[str, Any]:
    records = []
    for sha, encounters in cells.items():
        for encounter in encounters:
            records.append(
                {
                    "cell_id": f"mc/{encounter}/4/Fire/dps/Horde",
                    "real_actor_source": {"archive": {"path": f"raw/{sha}.zip", "sha256": sha}},
                }
            )
    return {"records": records}


def _provenance(**stopped: str | None) -> dict[str, Any]:
    return {
        "fixtures": [
            {"sha256": sha, "url": f"https://x.invalid/{sha}", "sources": 6, "stopped": stop}
            for sha, stop in stopped.items()
        ]
    }


@pytest.mark.parametrize(
    ("cells", "stops", "state"),
    [
        ({"a": list(range(1, 11))}, {"a": None}, "usable"),
        ({"a": list(range(1, 10))}, {"a": None}, "partial-final"),
        ({"a": list(range(1, 10))}, {"a": "BudgetExceeded"}, "partial-resumable"),
        ({"a": [1]}, {"a": None}, "seed"),
        ({"a": [1, 2], "b": [3]}, {"a": None, "b": "BudgetExceeded"}, "seed"),
    ],
)
def test_registered_runs_are_classified_from_coverage_and_stops(
    cells: dict[str, list[int]], stops: dict[str, str | None], state: str
) -> None:
    result = cq.classify([RUN], BOSSES, _register(cells), _provenance(**stops))
    assert result[RUN["entry_id"]]["state"] == state


def test_runs_without_registered_captures_are_not_classified() -> None:
    assert cq.classify([RUN], BOSSES, {"records": []}, _provenance()) == {}


def _mined(cid: int, encounters: int, hints: dict[str, int]) -> dict[str, Any]:
    return {
        "id": cid,
        "name": f"N{cid}",
        "server": "S",
        "region": "EU",
        "encounters": encounters,
        "reports": encounters,
        "faction_hints": hints,
        "evidence": {},
    }


def test_the_pool_puts_the_seed_subject_first_then_faction_lean_and_skips_excluded() -> None:
    seed = {"state": "seed", "archives": [{"url": "https://x.invalid/seed"}]}
    mined = [
        _mined(1, 9, {"Alliance": 3}),
        _mined(2, 2, {"Horde": 1}),
        _mined(3, 5, {}),
        _mined(4, 9, {"Horde": 4}),
    ]
    pool = cq.rank_pool(RUN, mined, seed, excluded={"4"})
    assert [c["url"] for c in pool] == [
        "https://x.invalid/seed",
        f"{cq.SITE}/character/id/2?zone=2000",
        f"{cq.SITE}/character/id/1?zone=2000",
        f"{cq.SITE}/character/id/3?zone=2000",
    ]


@pytest.mark.parametrize(
    ("fields", "code", "accepted"),
    [
        ({"faction": "Horde"}, 0, True),
        ({"faction": "unknown"}, 0, False),
        ({"faction": "Alliance"}, 0, False),
        ({"faction": "Horde", "needs a choice": "choose a partition"}, 0, False),
        ({"faction": "Horde"}, 1, False),
    ],
)
def test_only_an_observed_matching_faction_is_accepted(
    fields: dict[str, str], code: int, accepted: bool
) -> None:
    assert cq.verdict(fields, code, "Horde")[0] is accepted


def test_resolve_output_is_parsed_line_by_line() -> None:
    out = "character:      Nago\nfaction:        Horde\nzone:           Molten Core\n"
    assert cq.parse_resolve(out) == {"character": "Nago", "faction": "Horde", "zone": "Molten Core"}


def _plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, urls: list[str]) -> None:
    plan = tmp_path / "plan.json"
    entry = RUN | {"queued": True, "pool": [{"url": u, "origin": "test"} for u in urls]}
    plan.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
    monkeypatch.setattr(cq, "PLAN", plan)
    monkeypatch.setattr(cq, "RESOLUTIONS", tmp_path / "resolutions.json")
    monkeypatch.setattr(cq, "QUEUE", tmp_path / "queue.json")
    monkeypatch.setattr(cq, "ROOT", tmp_path)


def test_resolve_respects_the_budget_and_never_pays_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    urls = [f"https://x.invalid/{n}" for n in range(5)]
    _plan(tmp_path, monkeypatch, urls)
    calls: list[str] = []

    def fake(url: str) -> tuple[int, str, str]:
        calls.append(url)
        return (
            0,
            f"character: {url[-1]}\nfaction: {'Horde' if url[-1] in '13' else 'unknown'}\n",
            "",
        )

    cq.resolve(2, runner=fake)
    assert calls == urls[:2]
    cq.resolve(10, runner=fake)
    assert calls == urls


def test_emitted_queue_loads_in_the_runner_with_accepted_candidates_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    urls = [f"https://x.invalid/{n}" for n in range(3)]
    _plan(tmp_path, monkeypatch, urls)
    cq.resolve(
        5, runner=lambda u: (0, f"faction: {'unknown' if u.endswith('0') else 'Horde'}\n", "")
    )
    assert cq.emit() == 0
    _, entries = cr.load_queue(tmp_path / "queue.json")
    assert [e.candidates for e in entries] == [tuple(urls[1:])]


def test_a_queued_run_without_an_accepted_candidate_is_reported_not_emitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _plan(tmp_path, monkeypatch, ["https://x.invalid/0"])
    cq.resolve(5, runner=lambda u: (0, "faction: unknown\n", ""))
    assert cq.emit() == 1
    assert json.loads((tmp_path / "queue.json").read_text(encoding="utf-8"))["entries"] == []
