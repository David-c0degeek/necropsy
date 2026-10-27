"""The follow-up detector counts only admitted comparisons and keeps unknowns apart."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from scripts import comparison_followup as followup

ENCOUNTER_PLAIN = 51118  # Patchwerk: no production ranking exclusions
ENCOUNTER_EXCLUDED = 51108  # Gluth: production exclusions (Zombie Chow)


def _archive(
    tmp_path: Path,
    metric: str = "dps",
    players: int = 4,
    *,
    shared_fight: bool = False,
    extra: list[dict[str, Any]] | None = None,
) -> Path:
    """A minimal capture: per boss the subject plus PLAYERS-1 same-faction comparisons.

    shared_fight puts every comparison of a boss into one report/fight. Each
    EXTRA participant is {"name", "realm", "verdict" (or None for not in the
    cohort), "encounter"} and gets its own report.
    """
    fights: list[dict[str, Any]] = []
    streams: list[dict[str, Any]] = []
    rows: dict[int, list[dict[str, Any]]] = {ENCOUNTER_PLAIN: [], ENCOUNTER_EXCLUDED: []}
    actors: dict[str, list[dict[str, Any]]] = {}
    cohort: dict[int, list[dict[str, Any]]] = {ENCOUNTER_PLAIN: [], ENCOUNTER_EXCLUDED: []}

    def add(
        encounter: int,
        code: str,
        name: str,
        realm: str,
        kind: str,
        verdict: dict[str, Any] | None,
        actor_id: int,
    ) -> None:
        fight = next((f for f in fights if f["reportID"] == code), None)
        if fight is None:
            fight = {"reportID": code, "fightID": 1, "participants": []}
            fights.append(fight)
        fight["participants"].append(
            {"player": name, "server": realm, "encounterID": encounter, "kind": kind}
        )
        actors.setdefault(code, []).append(
            {"id": actor_id, "type": "Player", "name": name, "server": realm, "subType": "Druid"}
        )
        streams.append({"role": "player", "report": code, "fight": 1, "actor_id": actor_id})
        rows[encounter].append(
            {
                "report": {"code": code, "fightID": 1},
                "name": name,
                "server": {"name": realm},
                "class": "Druid",
                "spec": "Balance",
            }
        )
        if verdict is not None:
            cohort[encounter].append(
                {"kind": "cohort", "report": code, "fight": 1, "player": name, "verdict": verdict}
            )

    observed = {"status": "observed", "faction": "Alliance"}
    for encounter in (ENCOUNTER_PLAIN, ENCOUNTER_EXCLUDED):
        add(encounter, f"S{encounter}", "Subject", "Realm", "you", None, 1)
        for i in range(1, players):
            code = f"C{encounter}" if shared_fight else f"R{encounter}{i}"
            add(encounter, code, f"Ally{i}", "Realm", "top", observed, 10 + i)
    for n, e in enumerate(extra or ()):
        add(e["encounter"], f"X{n}", e["name"], e["realm"], "top", e["verdict"], 50 + n)
    marker = {
        "subject": {
            "class_id": 2,
            "name": "Subject",
            "server": "Realm",
            "faction": "Alliance",
            "ranking_category": "Balance",
            "ranking_metric": metric,
        },
        "zone": {"id": 2006},
        "top_n": 5,
        "bosses": [
            {
                "encounter_id": ENCOUNTER_PLAIN,
                "boss": "Patchwerk",
                "cohort": cohort[ENCOUNTER_PLAIN],
            },
            {
                "encounter_id": ENCOUNTER_EXCLUDED,
                "boss": "Gluth",
                "cohort": cohort[ENCOUNTER_EXCLUDED],
            },
        ],
        "fights": fights,
        "streams": streams,
    }
    path = tmp_path / "capture.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("necropsy-snapshot.json", json.dumps(marker))
        for code, listed in actors.items():
            bundle = {"reportData": {"report": {"masterData": {"actors": listed}}}}
            z.writestr(f"reports/{code}/bundle.json", json.dumps(bundle))
        for encounter in (ENCOUNTER_PLAIN, ENCOUNTER_EXCLUDED):
            page = {"page": 1, "characterRankings": {"rankings": rows[encounter]}}
            z.writestr(f"leaderboards/{encounter}_Boss.json", json.dumps({"pages": [page]}))
    return path


def _admit(names: set[str], seen: list[dict[str, Any]] | None = None) -> Any:
    def compute(spec: dict[str, Any], base: Path) -> dict[str, Any]:
        if seen is not None:
            seen.append(spec)
        if spec["player"] not in names:
            raise ValueError("pet listings disagree")
        return {}

    return compute


def _cell(found: list[dict[str, Any]], encounter: int) -> dict[str, Any]:
    return next(c for c in found if c["encounter_id"] == encounter)


def _patch(monkeypatch: pytest.MonkeyPatch, compute: Any) -> None:
    monkeypatch.setattr("scripts.comparison_followup.dps.compute", compute)


def test_admitted_comparisons_exclude_the_subject_and_use_the_packaged_minimum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(monkeypatch, _admit({"Subject", "Ally1", "Ally2", "Ally3"}))
    cell = _cell(followup.cells(_archive(tmp_path)), ENCOUNTER_PLAIN)
    assert cell["admitted_distinct_players"] == 3  # the admitted subject never counts
    assert cell["minimum"] == 3 and cell["archive_depth"] == 5
    assert not cell["needs_followup"] and cell["followup"] is None


def test_too_few_admitted_comparisons_need_more_comparisons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(monkeypatch, _admit({"Ally1"}))
    cell = _cell(followup.cells(_archive(tmp_path)), ENCOUNTER_PLAIN)
    assert cell["admitted_distinct_players"] == 1 and len(cell["refused"]) == 2
    assert cell["refused"][0]["reason"] == "pet listings disagree"
    assert cell["needs_followup"] and cell["followup"] == "more-comparisons"


def test_untested_exclusions_and_hps_are_unverified_not_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def never(spec: dict[str, Any], base: Path) -> dict[str, Any]:
        raise AssertionError("no admission may run for an unverified comparison")

    _patch(monkeypatch, _admit({"Ally1", "Ally2", "Ally3"}))
    excluded = _cell(followup.cells(_archive(tmp_path)), ENCOUNTER_EXCLUDED)
    assert excluded["admitted"] == [] and excluded["refused"] == []
    assert len(excluded["unverified"]) == 3 and excluded["followup"] == "admission-missing"
    _patch(monkeypatch, never)
    (tmp_path / "hps").mkdir()
    for cell in followup.cells(_archive(tmp_path / "hps", metric="hps")):
        assert cell["followup"] == "admission-missing" and len(cell["unverified"]) == 3


def test_comparisons_sharing_one_fight_are_each_admitted_with_their_own_actor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[dict[str, Any]] = []
    _patch(monkeypatch, _admit({"Ally1", "Ally2", "Ally3"}, seen))
    cell = _cell(followup.cells(_archive(tmp_path, shared_fight=True)), ENCOUNTER_PLAIN)
    assert cell["admitted_distinct_players"] == 3 and cell["refused"] == []
    assert sorted(s["actor"] for s in seen) == [11, 12, 13]


def test_a_namesake_of_the_subject_on_another_realm_is_a_comparison(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    namesake = {
        "name": "Subject",
        "realm": "Elsewhere",
        "verdict": {"status": "observed", "faction": "Alliance"},
        "encounter": ENCOUNTER_PLAIN,
    }
    _patch(monkeypatch, _admit({"Subject"}))
    cell = _cell(followup.cells(_archive(tmp_path, players=1, extra=[namesake])), ENCOUNTER_PLAIN)
    assert [(a["player"], a["realm"]) for a in cell["admitted"]] == [("Subject", "Elsewhere")]


def test_the_cross_faction_ceiling_and_unknown_factions_never_meet_the_minimum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ceiling = {"name": "Topgun", "realm": "Realm", "verdict": None, "encounter": ENCOUNTER_PLAIN}
    horde = {
        "name": "Hordey",
        "realm": "Realm",
        "verdict": {"status": "observed", "faction": "Horde"},
        "encounter": ENCOUNTER_PLAIN,
    }
    unknown = {
        "name": "Mystery",
        "realm": "Realm",
        "verdict": {"status": "unknown", "faction": None},
        "encounter": ENCOUNTER_PLAIN,
    }
    _patch(monkeypatch, _admit({"Ally1", "Ally2", "Topgun", "Hordey", "Mystery"}))
    archive = _archive(tmp_path, players=3, extra=[ceiling, horde, unknown])
    cell = _cell(followup.cells(archive), ENCOUNTER_PLAIN)
    assert cell["admitted_distinct_players"] == 2
    assert [u["player"] for u in cell["unverified"]] == ["Mystery"]
    assert cell["needs_followup"] and cell["followup"] == "more-comparisons"
