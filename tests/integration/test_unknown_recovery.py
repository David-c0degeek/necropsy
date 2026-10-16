"""Actual acquire/export/read/ingest/render contract, with synthetic API data."""

from __future__ import annotations

import json
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import duckdb
import httpx
import pytest

from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import build_document
from necropsy.report.render import build_view, render_report
from necropsy.snapshot.model import SnapshotError
from necropsy.snapshot.v1_writer import write_snapshot
from necropsy.wcl.acquire import Run, acquire, finalize_reports
from necropsy.wcl.cache import Cache
from necropsy.wcl.sites import VANILLA
from tests.integration.test_live_snapshot import _client
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _context


class PartialPets(FakeWcl):
    def _report(self, p: Player, wanted: list[int] | None = None) -> dict[str, Any]:
        report = super()._report(p, wanted)
        for actor in report["masterData"]["actors"]:
            if actor.get("type") == "Player":
                actor["gameID"] = 100000 + actor["id"]
        report["masterData"]["actors"].extend(
            [
                {"id": 900, "type": "Pet", "gameID": 8836, "petOwner": None, "name": "Chicken"},
                {"id": 50, "type": "NPC", "gameID": 16028, "name": "Patchwerk"},
            ]
        )
        report["masterData"]["abilities"] = [{"gameID": 3009, "name": "Claw"}]
        for fight in report["fights"]:
            fight["friendlyPets"].append({"id": 900, "petOwner": None, "gameID": 8836})
        return report

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "NecropsyEvents" not in body["query"]:
            return super().__call__(request)
        self.requests.append(body)
        actor = body["variables"].get("sourceID")
        events = []
        if actor is not None:
            events = [
                {
                    "timestamp": 2000,
                    "type": "cast",
                    "sourceID": actor,
                    "targetID": 50,
                    "abilityGameID": 3009 if actor == 8 else 75,
                },
                {
                    "timestamp": 2001,
                    "type": "damage",
                    "sourceID": actor,
                    "targetID": 50,
                    "abilityGameID": 3009 if actor == 8 else 75,
                    "amount": 80,
                },
            ]
            if actor != 8:
                events.insert(
                    0,
                    {
                        "timestamp": 1000,
                        "type": "combatantinfo",
                        "sourceID": actor,
                        "auras": [],
                        "talents": [{"id": 20}, {"id": 31}, {"id": 0}],
                    },
                )
        return self._ok(
            {
                "reportData": {
                    "report": {
                        "revision": 4,
                        "events": {
                            "data": events,
                            "nextPageTimestamp": None,
                        },
                    }
                }
            }
        )


def _save(tmp: Path, fake: FakeWcl, category: str | None = None) -> Any:
    (tmp / "cache").mkdir()
    (tmp / "saved").mkdir()
    client, store = _client(fake), Cache(tmp / "cache")
    context = replace(_context(), ranking_category=category)
    acquisition = acquire(client, store, VANILLA, context, encounters=(PATCHWERK,))
    finalize_reports(Run(client, store, VANILLA, category=category), acquisition)
    return write_snapshot(acquisition, store, tmp / "saved", "recovered")


def _subject(saved: Any, db: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    ingest(saved.archive, db)
    with duckdb.connect(str(db), read_only=True) as con:
        doc = build_document(con)
    return doc, doc["bosses"][0]["subject"]


def test_partial_pet_ownership_survives_every_pipeline_boundary(tmp_path: Path) -> None:
    fake = PartialPets(
        [Player(f"Ally{i}", pets=[8] if i == 0 else []) for i in range(5)],
        Player("Haplina", pets=[8]),
    )
    saved = _save(tmp_path, fake)
    doc, subject = _subject(saved, tmp_path / "analysis.duckdb")
    assert subject["pets_listed"] is False
    assert subject["ranking"]["ranked"]["value"] is None  # All-pet total is still incomplete.
    assert subject["ranking"]["ranked_dps"] == 1500  # Independent WCL ranking score.
    pet = subject["hunter"]["hunter_pets"][0]
    assert pet["actor_id"] == 8 and pet["damage"]["value"] == 80
    assert subject["hunter"]["pet_roster_complete"] is True
    assert subject["hunter"]["total_pet_dps"]["value"] == 10
    assert doc["bosses"][0]["playbook"]["pet"]["no_hunter_pet"] is False
    families = doc["bosses"][0]["benchmarks"]["baseline"]["pet_families"]
    assert families["listing_missing"] == 0
    html = render_report(build_view(doc, "a" * 64))
    assert "Unknown pet listing" not in html
    assert "Possible families:" in html
    with zipfile.ZipFile(saved.archive) as archive:
        marker = json.loads(archive.read("necropsy-snapshot.json"))
        assert not any(s["actor_id"] == 900 for s in marker["streams"])
        assert any(n.endswith("confirmed_pets.json") for n in archive.namelist())
        assert any(n.endswith("fight_3.json") for n in archive.namelist())


@pytest.mark.parametrize("category", [None, "Marksmanship"])
def test_saved_overall_leader_works_for_legacy_and_selected_spec(
    tmp_path: Path,
    category: str | None,
) -> None:
    fake = FakeWcl(
        [Player("HordeFirst", faction_code=0, guild=1), *[Player(f"Ally{i}") for i in range(5)]],
        Player("Haplina"),
    )
    saved = _save(tmp_path, fake, category)
    doc, _ = _subject(saved, tmp_path / "leader.duckdb")
    top = doc["bosses"][0]["benchmarks"]["overall_top"]
    assert top["player"] == "HordeFirst" and top["ranked_dps"] == 2000
    assert top["basis"] == "leaderboard-metadata" and not top["event_sample_acquired"]
    assert all(e["player"] != "HordeFirst" for e in doc["bosses"][0]["cohort"])


class Prelude(PartialPets):
    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        query, var = body["query"], body["variables"]
        if "NecropsyCombatantContext" in query:
            self.requests.append(body)
            data = [
                {
                    "timestamp": 500,
                    "type": "combatantinfo",
                    "sourceID": var["sourceID"],
                    "fight": 3,
                    "talents": [{"id": 20}, {"id": 31}, {"id": 0}],
                    "auras": [
                        {"ability": 23768, "source": var["sourceID"], "name": "Sayge"},
                        {"ability": 3045, "source": var["sourceID"]},
                    ],
                }
            ]
        elif "NecropsyCombatantPrelude" in query:
            self.requests.append(body)
            assert "fightIDs" not in var  # The prelude can be assigned to another fight.
            assert f"target.id = {100000 + var['targetID']}" in var["filterExpression"]
            data = [
                {
                    "timestamp": 750,
                    "type": "removebuff",
                    "sourceID": var["targetID"],
                    "targetID": var["targetID"],
                    "abilityGameID": 3045,
                    "fight": 2,
                }
            ]
        else:
            response = super().__call__(request)
            if "NecropsyEvents" in query:
                raw = response.json()
                page = raw["data"]["reportData"]["report"]["events"]
                page["data"] = [e for e in page["data"] if e["type"] != "combatantinfo"]
                return httpx.Response(200, json=raw)
            return response
        return self._ok(
            {
                "reportData": {
                    "report": {
                        "revision": 4,
                        "events": {
                            "data": data,
                            "nextPageTimestamp": None,
                        },
                    }
                }
            }
        )


def test_earlier_snapshot_and_prelude_restore_starting_state_without_damage_leak(
    tmp_path: Path,
) -> None:
    saved = _save(tmp_path, Prelude([Player(f"Ally{i}") for i in range(5)], Player("Haplina")))
    doc, subject = _subject(saved, tmp_path / "context.duckdb")
    assert subject["environment"]["talents"]["value"] == "20/31/0"
    assert subject["environment"]["darkmoon_faire"]["value"] == "Sayge's Dark Fortune of Damage"
    assert subject["environment"]["starting_auras"]["rule"] == "combatant-prelude-auras-v1"
    assert subject["hunter"]["rapid_fire_uptime_s"]["value"] == 0
    assert subject["ranking"]["raw"]["value"] is None  # Unresolved all-pet ownership persists.
    with duckdb.connect(str(tmp_path / "context.duckdb"), read_only=True) as con:
        assert con.execute("SELECT min(timestamp) FROM events").fetchone() == (2000,)
    assert "20/31/0" in render_report(build_view(doc, "a" * 64))
    corrupt = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(saved.archive) as source, zipfile.ZipFile(corrupt, "w") as target:
        for info in source.infolist():
            raw = source.read(info)
            if info.filename.endswith("combatant_context.json"):
                context = json.loads(raw)
                context["actor"] = 900
                raw = json.dumps(context).encode()
            target.writestr(info, raw)
    with pytest.raises(SnapshotError, match="context digest"):
        ingest(corrupt, tmp_path / "corrupt.duckdb")


def test_invalid_optional_context_keeps_verified_fight(tmp_path: Path) -> None:
    class BadPrelude(Prelude):
        def __call__(self, request: httpx.Request) -> httpx.Response:
            response = super().__call__(request)
            if "NecropsyCombatantPrelude" in json.loads(request.content)["query"]:
                raw = response.json()
                raw["data"]["reportData"]["report"]["events"]["data"][0]["targetID"] = 999
                return httpx.Response(200, json=raw)
            return response

    saved = _save(tmp_path, BadPrelude([Player(f"Ally{i}") for i in range(5)], Player("Haplina")))
    doc, subject = _subject(saved, tmp_path / "bad-context.duckdb")
    assert subject is not None and subject["hunter"]["shots"]["auto_shot"]["casts"]["value"]
    assert subject["environment"]["starting_auras"]["value"] is None
    assert "combatant context unavailable" in " ".join(doc["cohort"]["limitations"])
