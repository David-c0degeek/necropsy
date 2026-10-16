"""Synthetic cross-raid acquisition/replay and independent saved-run identities."""

from __future__ import annotations

from dataclasses import replace
from html import unescape
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.desktop.engine import describe_run
from necropsy.normalize.ingest import ingest
from necropsy.raids import RAIDS, encounters, with_raid
from necropsy.report.analysis_json import AnalysisDocument, build_document, dumps
from necropsy.report.render import build_view, render_playbook, render_report
from necropsy.snapshot.v1_writer import write_snapshot
from necropsy.tui.service import RunLibrary
from necropsy.wcl.acquire import Run, acquire, boss_order, finalize_reports
from necropsy.wcl.cache import Cache
from necropsy.wcl.cohort import CohortRefused, cohort_key
from necropsy.wcl.context import Field
from necropsy.wcl.sites import VANILLA
from necropsy.wcl.urls import BadCharacterUrl, parse_character_url
from tests.integration.test_live_snapshot import _client
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _context

URL = "https://vanilla.warcraftlogs.com/character/id/86583560"


@pytest.mark.parametrize("raid", RAIDS, ids=lambda r: r.slug)
@pytest.mark.parametrize("class_id,category", [(3, "Marksmanship"), (2, "Balance"), (11, "Fury")])
def test_each_raid_acquires_replays_and_renders_independently(
    tmp_path: Path, raid: Any, class_id: int, category: str
) -> None:
    encounter = encounters(raid)[0]
    class_name = {3: "Hunter", 2: "Druid", 11: "Warrior"}[class_id]

    class RaidWcl(FakeWcl):
        def _report(self, p: Player, wanted: list[int] | None = None) -> dict[str, Any]:
            report = super()._report(p, wanted)
            for fight in report["fights"]:
                fight["encounterID"] = encounter["id"]
            for row in report["playerDetails"]["data"]["playerDetails"]["dps"]:
                row["type"] = class_name
            return report

        def _rank(self, p: Player, amount: float) -> dict[str, Any]:
            return {**super()._rank(p, amount), "class": class_name, "spec": category}

    fake = RaidWcl(
        [Player(f"Ally{i}", subtype=class_name) for i in range(5)],
        Player("Haplina", subtype=class_name),
    )
    context = replace(
        _context(),
        zone_id=raid.zone_id,
        zone_name=Field(raid.name, "observed", "test"),
        class_id=Field(class_id, "observed", "test"),
        ranking_category=category,
    )
    (tmp_path / "cache").mkdir()
    client, store = _client(fake), Cache(tmp_path / "cache")
    result = acquire(client, store, VANILLA, context, encounters=(encounter["id"],))
    finalize_reports(Run(client, store, VANILLA, class_id=class_id, category=category), result)
    written = write_snapshot(result, store, tmp_path, raid.slug)
    db = tmp_path / "analysis.duckdb"
    ingest(written.archive, db)
    with duckdb.connect(str(db), read_only=True) as con:
        document = build_document(con)
    AnalysisDocument.model_validate(document)
    assert document["zone"]["id"] == raid.zone_id
    assert document["zone"]["name"] == raid.name
    assert [b["encounter_id"] for b in document["bosses"]] == [encounter["id"]]
    assert document["bosses"][0]["boss"] == encounter["name"]
    view = build_view(document, "0" * 64)
    assert raid.name in unescape(render_playbook(view))
    assert raid.name in unescape(render_report(view))
    if raid.slug != "naxxramas":
        assert any("no real-log" in note for note in document["cohort"]["limitations"])
        if class_id == 3:
            boss = document["bosses"][0]
            assert boss["rules"]["ranking_exclusion_rule"]["basis"] == "unvalidated"
            assert boss["subject"]["ranking"]["ranked"]["value"] is None
            assert boss["subject"]["ranking"]["ranked_dps_evidence"]["value"] == 1500
            assert "naxx-execution" not in str(boss["playbook"])
    (tmp_path / "analysis.json").write_text(dumps(document), encoding="utf-8")
    imported = RunLibrary(tmp_path / "library").load(tmp_path)
    assert imported.raid_id == raid.zone_id
    client.close()


def test_saved_analyses_retain_their_own_raid_after_reload(tmp_path: Path) -> None:
    library = RunLibrary(tmp_path)
    for raid in RAIDS:
        context = replace(
            _context(), zone_id=raid.zone_id, zone_name=Field(raid.name, "observed", "test")
        )
        run = library.create(URL, "Marksmanship", context)
        loaded = library.load(run.out)
        assert loaded.raid_id == raid.zone_id
        assert raid.name in loaded.title
        assert describe_run(loaded)["raid_name"] == raid.name
        assert parse_character_url(loaded.options["url"]).zone_id == raid.zone_id
    assert {r.raid_id for r in library.discover()} == {r.zone_id for r in RAIDS}


@pytest.mark.parametrize("raid", RAIDS[1:], ids=lambda r: r.slug)
def test_cross_raid_encounters_are_refused(raid: Any) -> None:
    context = replace(_context(), zone_id=raid.zone_id)
    with pytest.raises(CohortRefused, match="not a supported boss"):
        cohort_key(VANILLA, context, PATCHWERK)
    assert PATCHWERK not in boss_order(raid.slug)


@pytest.mark.parametrize("query", ["zone=1", "zone=", "zone=2000&zone=2005", "zone=abc"])
def test_ambiguous_or_unsupported_raid_url_is_refused(query: str) -> None:
    with pytest.raises(BadCharacterUrl):
        parse_character_url(f"{URL}?{query}")


def test_raid_url_preserves_other_url_context_and_default() -> None:
    assert parse_character_url(URL).zone_id == 2006
    selected = with_raid(URL + "?partition=1#boss", 2000)
    assert "partition=1" in selected and selected.endswith("#boss")
    assert parse_character_url(selected).zone_id == 2000


@pytest.mark.parametrize("raid", RAIDS, ids=lambda r: r.slug)
def test_cli_raid_option_persists_in_the_url(raid: Any) -> None:
    from necropsy.wcl.cli import _raid_url

    assert parse_character_url(_raid_url(URL, raid.slug)).zone_id == raid.zone_id


def test_cli_refuses_unknown_raid_before_reading_credentials(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from necropsy.cli import app

    result = CliRunner().invoke(
        app,
        [
            "analyze",
            URL,
            "--raid",
            "unknown",
            "--cache",
            str(tmp_path / "cache"),
            "--out",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code == 2
    assert "choose naxxramas, aq40, bwl or mc" in result.output
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("raid", RAIDS, ids=lambda r: r.slug)
def test_resolution_requests_the_selected_raid_and_its_partitions(raid: Any) -> None:
    from necropsy.wcl.client import WclClient
    from necropsy.wcl.context import resolve
    from tests.unit.test_wcl_context import ZONE, _character, _rankings
    from tests.wcl_fakes import FakeClock, Script, ok

    script = Script(
        ok(
            {
                "characterData": {"character": _character()},
                "worldData": {
                    "zone": {**ZONE, "id": raid.zone_id, "name": raid.name},
                },
            }
        ),
        ok({"characterData": {"character": {"p1": _rankings(4), "p2": _rankings(0)}}}),
    )
    client = WclClient(
        VANILLA, lambda _: "synthetic", transport=script.transport, clock=FakeClock()
    )
    try:
        context = resolve(client, parse_character_url(with_raid(URL, raid.zone_id)))
    finally:
        client.close()
    assert context.zone_id == raid.zone_id
    assert context.zone_name.value == raid.name
    assert context.partition is not None and context.partition.id == 1
    assert [body["variables"]["zone"] for body in script.bodies()] == [raid.zone_id] * 2


def test_terminal_raid_selection_and_saved_raid_filters(tmp_path: Path) -> None:
    import asyncio

    from textual.widgets import Input, Select

    from necropsy.tui.app import NecropsyApp
    from necropsy.tui.service import AnalysisService

    class Service(AnalysisService):
        def identify(self, url: str, *args: Any, **kwargs: Any) -> Any:
            from necropsy.raids import raid_for_zone

            raid = raid_for_zone(parse_character_url(url).zone_id)
            return replace(
                _context(), zone_id=raid.zone_id, zone_name=Field(raid.name, "observed", "test")
            )

    async def scenario() -> None:
        library = RunLibrary(tmp_path)
        for raid in RAIDS:
            library.create(URL, "Marksmanship", replace(_context(), zone_id=raid.zone_id))
        app = NecropsyApp(library, Service())
        async with app.run_test(size=(100, 50)) as pilot:
            app.query_one("#character-url", Input).value = URL
            for raid in RAIDS:
                app.query_one("#raid", Select).value = str(raid.zone_id)
                await pilot.pause()
                app.start_operation("identify")
                await app.workers.wait_for_complete()
                await pilot.pause()
                assert app.context is not None and app.context.zone_id == raid.zone_id
                assert parse_character_url(app.character_url).zone_id == raid.zone_id
                app.query_one("#saved-raid", Select).value = str(raid.zone_id)
                await pilot.pause()
                assert [r.raid_id for r in app.saved] == [raid.zone_id]
            app.query_one("#saved-raid", Select).value = "all"
            await pilot.pause()
            assert len(app.saved) == 4

    asyncio.run(scenario())
