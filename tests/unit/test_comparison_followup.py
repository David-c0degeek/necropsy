"""The follow-up detector counts only admitted comparisons and keeps unknowns apart."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from scripts import comparison_followup as followup
from scripts.freeze_dps_ranking import ArithmeticMismatch

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


def _admit(
    names: set[str],
    seen: list[dict[str, Any]] | None = None,
    *,
    excluded: dict[str, int] | None = None,
    mismatch: set[str] | None = None,
) -> Any:
    def compute(spec: dict[str, Any], base: Path) -> dict[str, Any]:
        if seen is not None:
            seen.append(spec)
        if spec["player"] in (mismatch or set()):
            raise ArithmeticMismatch("published DPS contradicts raw")
        if spec["player"] not in names:
            raise ValueError("pet listings disagree")
        return {"totals": {"excluded": (excluded or {}).get(spec["player"], 0)}}

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


def test_exclusion_neutral_comparisons_admit_with_the_packaged_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[dict[str, Any]] = []
    _patch(monkeypatch, _admit({"Ally1", "Ally2", "Ally3"}, seen))
    cell = _cell(followup.cells(_archive(tmp_path)), ENCOUNTER_EXCLUDED)
    assert cell["admitted_distinct_players"] == 3 and not cell["needs_followup"]
    assert all(
        a["exclusion_neutral"] and a["applied_exclusions"] == [16360] for a in cell["admitted"]
    )
    gluth = [s["excluded_game_ids"] for s in seen if s["encounter"] == ENCOUNTER_EXCLUDED]
    plain = [s["excluded_game_ids"] for s in seen if s["encounter"] == ENCOUNTER_PLAIN]
    assert gluth == [[16360]] * 3 and plain == [[]] * 3  # the packaged list, never another


def test_excluded_damage_or_a_mismatch_under_the_list_stays_unverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(
        monkeypatch,
        _admit({"Ally1", "Ally2", "Ally3"}, excluded={"Ally1": 120}, mismatch={"Ally2"}),
    )
    cell = _cell(followup.cells(_archive(tmp_path)), ENCOUNTER_EXCLUDED)
    assert [a["player"] for a in cell["admitted"]] == ["Ally3"] and cell["refused"] == []
    by_player = {u["player"]: u for u in cell["unverified"]}
    assert by_player["Ally1"]["reason"] == "production exclusions exercised and untested"
    assert by_player["Ally1"]["excluded_damage"] == 120
    assert (
        by_player["Ally2"]["reason"]
        == "arithmetic mismatch under the untested production exclusions"
    )
    assert cell["needs_followup"] and cell["followup"] == "more-comparisons"


def test_a_mismatch_without_exclusions_and_evidence_failures_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(monkeypatch, _admit({"Ally1", "Ally3"}, mismatch={"Ally2"}))
    found = followup.cells(_archive(tmp_path))
    plain = _cell(found, ENCOUNTER_PLAIN)
    assert {r["player"]: r["reason"] for r in plain["refused"]} == {
        "Ally2": "published DPS contradicts raw"
    }
    gluth = _cell(found, ENCOUNTER_EXCLUDED)
    assert [u["player"] for u in gluth["unverified"]] == ["Ally2"]
    _patch(monkeypatch, _admit({"Ally1", "Ally2"}))
    (tmp_path / "second").mkdir()
    gluth = _cell(followup.cells(_archive(tmp_path / "second")), ENCOUNTER_EXCLUDED)
    assert {r["player"]: r["reason"] for r in gluth["refused"]} == {
        "Ally3": "pet listings disagree"
    }


def test_hps_stays_unverified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def never(spec: dict[str, Any], base: Path) -> dict[str, Any]:
        raise AssertionError("no admission may run for an unverified comparison")

    _patch(monkeypatch, never)
    for cell in followup.cells(_archive(tmp_path, metric="hps")):
        assert cell["followup"] == "admission-missing" and len(cell["unverified"]) == 3


def test_comparisons_sharing_one_fight_are_each_admitted_with_their_own_actor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[dict[str, Any]] = []
    _patch(monkeypatch, _admit({"Ally1", "Ally2", "Ally3"}, seen))
    cell = _cell(followup.cells(_archive(tmp_path, shared_fight=True)), ENCOUNTER_PLAIN)
    assert cell["admitted_distinct_players"] == 3 and cell["refused"] == []
    plain = [s["actor"] for s in seen if s["encounter"] == ENCOUNTER_PLAIN]
    assert sorted(plain) == [11, 12, 13]


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
