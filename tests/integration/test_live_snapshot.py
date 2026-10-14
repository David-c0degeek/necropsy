"""Live acquisition → snapshot v1 → ingest → analysis.json, against a fake WCL server.

All WCL responses are SYNTHETIC (see tests/unit/test_wcl_acquire.py). No credentials,
no network.
"""

from __future__ import annotations

import json
import random
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import duckdb
import httpx
import pytest

from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import AnalysisDocument, build_document
from necropsy.report.render import build_view, render_playbook, render_report
from necropsy.snapshot.archive import ArchiveError, load_entries_manifest
from necropsy.snapshot.model import SnapshotError
from necropsy.snapshot.v1_writer import LIVE_DESCRIPTION, WriteError, write_snapshot
from necropsy.wcl import client as c
from necropsy.wcl.acquire import MixedRevision, Run, acquire, finalize_reports
from necropsy.wcl.cache import Cache
from necropsy.wcl.context import Field
from necropsy.wcl.sites import VANILLA
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _context
from tests.wcl_fakes import FakeClock


def test_balance_healing_metric_survives_acquisition_and_replay(tmp_path: Path) -> None:
    class DruidWcl(FakeWcl):
        def _rank(self, p: Player, amount: float) -> dict[str, Any]:
            return {**super()._rank(p, amount), "class": "Druid", "spec": "Balance"}

        def _report(self, p: Player, wanted: list[int] | None = None) -> dict[str, Any]:
            report = super()._report(p, wanted)
            for row in report["playerDetails"]["data"]["playerDetails"]["dps"]:
                row["type"] = "Druid"
            return report

    fake = DruidWcl(
        [Player(f"Ally{i}", subtype="Druid") for i in range(5)],
        Player("Haplina", subtype="Druid"),
    )
    context = replace(
        _context(),
        class_id=Field(2, "observed", "test"),
        ranking_category="Balance",
        ranking_metric="hps",
    )
    (tmp_path / "cache").mkdir()
    (tmp_path / "saved").mkdir()
    store = Cache(tmp_path / "cache")
    client = _client(fake)
    result = acquire(client, store, VANILLA, context, encounters=(PATCHWERK,))
    finalize_reports(
        Run(client, store, VANILLA, class_id=2, category="Balance", metric="hps"), result
    )
    written = write_snapshot(result, store, tmp_path / "saved", "druid")
    db = tmp_path / "druid.duckdb"
    ingest(written.archive, db)
    with duckdb.connect(str(db), read_only=True) as con:
        subject = build_document(con)["bosses"][0]["subject"]
    assert subject["ranking"]["category"] == "Balance"
    assert subject["ranking"]["metric"] == "hps"
    assert subject["ranking"]["category_score"] == 1500
    assert subject["druid"]["role"]["value"] is None
    queries = [request["query"] for request in fake.requests]
    assert all("metric: hps" in q for q in queries if "NecropsySubject" in q)
    assert all("playerMetric: hps" in q for q in queries if "NecropsyReport" in q)
    broken = _rewrite_marker(
        written, tmp_path / "wrong.zip", lambda d: d["subject"].update(ranking_metric="dps")
    )
    with pytest.raises(SnapshotError, match="incompatible"):
        ingest(broken, tmp_path / "wrong.duckdb")


def _client(fake: FakeWcl) -> c.WclClient:
    client = c.WclClient(
        VANILLA,
        lambda e: "secret-token",
        transport=httpx.MockTransport(fake),
        clock=FakeClock(),
        rng=random.Random(0),
    )
    client.last_rate = c.RateLimit(36000, 10.0, 1800)
    return client


def _players() -> tuple[list[Player], Player]:
    cohort = [Player(f"Ally{i}", actor_id=10 + i, pets=[100 + i]) for i in range(1, 7)]
    # Ally2 shares the subject's report (another fight); Ally3 its fight.
    cohort[1].report, cohort[1].fight = "RShared", 4
    cohort[2].report = "RShared"
    cohort[3].pet_list = False  # pets unknown for Ally4
    subject = Player("Haplina", actor_id=5, pets=[8], report="RShared")
    return cohort, subject


def test_saved_overall_score_does_not_create_a_foreign_event_sample(tmp_path: Path) -> None:
    (tmp_path / "cache").mkdir()
    (tmp_path / "saved").mkdir()
    cohort, subject = _players()
    cohort.insert(0, Player("HordeFirst", faction_code=0, guild=1))
    acquisition, store, run = _acquire(tmp_path, FakeWcl(cohort, subject))
    finalize_reports(run, acquisition)
    saved = write_snapshot(acquisition, store, tmp_path / "saved", stem="context")
    db = tmp_path / "context.duckdb"
    ingest(
        saved.archive,
        db,
        expected_sha256=saved.sha256,
        entries=load_entries_manifest(saved.entries),
    )
    with duckdb.connect(str(db), read_only=True) as con:
        doc = build_document(con)
    boss = next(b for b in doc["bosses"] if b["encounter_id"] == PATCHWERK)
    top = boss["benchmarks"]["overall_top"]
    assert top["player"] == "HordeFirst" and top["ranked_dps"] == 2000
    assert top["ranked_dps_evidence"]["level"] == "observed"
    assert top["basis"] == "leaderboard-metadata" and top["captured_at"]
    assert top["event_sample_acquired"] is False
    assert len(boss["cohort"]) == 5 and all(e["player"] != "HordeFirst" for e in boss["cohort"])
    assert boss["playbook"]["rapid_fire"]["rank_one"] is None


@pytest.mark.parametrize("partition", [True, 99, "malformed-json"])
def test_live_leaderboard_partition_is_bound_to_the_archive(
    written: Any, tmp_path: Path, partition: Any
) -> None:
    changed = tmp_path / "wrong-leaderboard.zip"
    with zipfile.ZipFile(written[2].archive) as source, zipfile.ZipFile(changed, "w") as target:
        for info in source.infolist():
            raw = source.read(info)
            if info.filename.startswith("leaderboards/"):
                data = json.loads(raw)
                if partition == "malformed-json":
                    data["pages"][0]["characterRankings"] = "{"
                else:
                    data["partition"] = partition
                raw = json.dumps(data).encode()
            target.writestr(info, raw)
    with pytest.raises(SnapshotError, match="leaderboard"):
        ingest(changed, tmp_path / "wrong.duckdb")


def test_live_json_scalar_leaderboard_pages_remain_readable(written: Any, tmp_path: Path) -> None:
    changed = tmp_path / "encoded-leaderboards.zip"
    with zipfile.ZipFile(written[2].archive) as source, zipfile.ZipFile(changed, "w") as target:
        for info in source.infolist():
            raw = source.read(info)
            if info.filename.startswith("leaderboards/"):
                data = json.loads(raw)
                for page in data["pages"]:
                    page["characterRankings"] = json.dumps(page["characterRankings"])
                raw = json.dumps(data).encode()
            target.writestr(info, raw)
    db = tmp_path / "encoded.duckdb"
    ingest(changed, db)
    with duckdb.connect(str(db), read_only=True) as con:
        row = con.execute("SELECT count(*) FROM rankings WHERE kind='leaderboard'").fetchone()
        assert row is not None and row[0] > 0


def _acquire(tmp: Path, fake: FakeWcl) -> tuple[Any, Cache, Run]:
    store = Cache(tmp / "cache")
    client = _client(fake)
    result = acquire(client, store, VANILLA, _context(), encounters=(PATCHWERK, 51120))
    run = Run(client, store, VANILLA)
    return result, store, run


@pytest.fixture
def written(tmp_path: Path) -> Any:
    (tmp_path / "cache").mkdir()
    (tmp_path / "out").mkdir()
    cohort, subject = _players()
    fake = FakeWcl(cohort, subject)
    result, store, run = _acquire(tmp_path, fake)
    finalize_reports(run, result)
    return result, store, write_snapshot(result, store, tmp_path / "out", "live"), tmp_path


def test_a_live_snapshot_reaches_analysis_json(written: Any) -> None:
    _, _, out, tmp = written
    db = tmp / "live.duckdb"
    entries = load_entries_manifest(out.entries)
    ingest(out.archive, db, expected_sha256=out.sha256, entries=entries)
    con = duckdb.connect(str(db), read_only=True)
    try:
        document = build_document(con)
        statuses = dict(
            con.execute(
                "SELECT role || ':' || actor_name, status FROM stream_coverage "
                "WHERE role = 'pet-discovery'"
            ).fetchall()
        )
    finally:
        con.close()
    AnalysisDocument.model_validate(document)
    assert document["mode"] == "live"
    assert document["cohort"]["limitations"][0] == LIVE_DESCRIPTION
    assert document["snapshot"]["format"] == "necropsy-live-snapshot-v1"
    bosses = [b["encounter_id"] for b in document["acquisition"]["bosses"]]
    assert bosses == [PATCHWERK, 51120]  # the boss with no acquired fight stays visible
    # Ally4's pets were never proven: pet discovery is missing, not "no pet".
    assert statuses == {"pet-discovery:pets of Ally4": "missing"}
    patchwerk = next(b for b in document["bosses"] if b["encounter_id"] == PATCHWERK)
    assert patchwerk["subject"] is not None and len(patchwerk["cohort"]) == 5


def test_shared_report_fights_and_participants_survive_once(written: Any) -> None:
    _, _, out, _ = written
    with zipfile.ZipFile(out.archive) as archive:
        names = archive.namelist()
        marker = json.loads(archive.read("necropsy-snapshot.json"))
    assert names == sorted(names)
    assert "reports/RShared/bundle.json" in names
    shared = [f for f in marker["fights"] if f["reportID"] == "RShared"]
    assert sorted(f["fightID"] for f in shared) == [3, 4]
    people = sorted(p["player"] for f in shared for p in f["participants"])
    assert people == ["Ally2", "Ally3", "Haplina"]
    assert len(
        {
            (s["report"], s["fight"], s["role"], s["actor_id"], s["direction"])
            for s in marker["streams"]
        }
    ) == len(marker["streams"])
    assert not any("pets.json" in n and "Ally4" in n for n in names)


def test_live_pages_show_requested_scope_without_claiming_historical_cohort(written: Any) -> None:
    _, _, out, tmp = written
    db = tmp / "pages.duckdb"
    ingest(out.archive, db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        document = build_document(con)
    finally:
        con.close()
    # A stopped boss has no detailed analysis; its scope must still survive rendering.
    missing = document["acquisition"]["bosses"][1]
    missing["attempted"] = False
    missing["coverage"]["reasons"] = ["<script>unsafe</script>"]
    for render in (render_report, render_playbook):
        page = render(build_view(document, "synthetic"))
        assert "Live acquisition coverage" in page
        assert "Thaddius" in page and "Not attempted" in page
        assert 'href="#boss-51120"' not in page
        assert "Acquired comparison cohort" in page
        assert "recorded overall top five" not in page
        assert "in overall top five" not in page
        assert "metadata-only" in page.lower()
        assert "&lt;script&gt;unsafe&lt;/script&gt;" in page
        assert "<script>unsafe</script>" not in page
    # A saved historical document keeps its established presentation.
    document["mode"] = "historical"
    page = render_playbook(build_view(document, "synthetic"))
    assert "Live acquisition coverage" not in page
    assert "in overall top five" in page


def test_rewriting_is_deterministic_and_never_replaces(written: Any) -> None:
    result, store, out, tmp = written
    (tmp / "again").mkdir()
    again = write_snapshot(result, store, tmp / "again", "live")
    assert again.archive.read_bytes() == out.archive.read_bytes()
    assert again.sha256 == out.sha256
    before = out.archive.read_bytes()
    with pytest.raises(WriteError):
        write_snapshot(result, store, tmp / "out", "live")
    assert out.archive.read_bytes() == before


def test_a_tampered_member_is_refused(written: Any) -> None:
    _, _, out, tmp = written
    bad = tmp / "bad.zip"
    with zipfile.ZipFile(out.archive) as src, zipfile.ZipFile(bad, "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename.endswith("source_001.json"):
                data = data.replace(b"cast", b"heal")
            dst.writestr(info, data)
    with pytest.raises(ArchiveError):
        ingest(bad, tmp / "bad.duckdb", entries=load_entries_manifest(out.entries))
    # Without the manifest, the certified page digests still catch it.
    with pytest.raises(SnapshotError):
        ingest(bad, tmp / "bad2.duckdb")


def test_a_malformed_live_marker_never_falls_back(written: Any) -> None:
    _, _, out, tmp = written
    bad = tmp / "marker.zip"
    with zipfile.ZipFile(out.archive) as src, zipfile.ZipFile(bad, "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == "necropsy-snapshot.json":
                doc = json.loads(data)
                doc["formatVersion"] = 2
                data = json.dumps(doc).encode()
            dst.writestr(info, data)
    with pytest.raises(SnapshotError):
        ingest(bad, tmp / "marker.duckdb")


def test_unfinalized_or_mixed_revision_acquisitions_are_refused(tmp_path: Path) -> None:
    (tmp_path / "cache").mkdir()
    (tmp_path / "out").mkdir()
    cohort, subject = _players()
    fake = FakeWcl(cohort, subject)
    result, store, run = _acquire(tmp_path, fake)
    with pytest.raises(WriteError):
        write_snapshot(result, store, tmp_path / "out", "live")
    assert [p.name for p in (tmp_path / "out").iterdir() if not p.name.endswith(".lock")] == []
    fake.revisions["RShared"] = [9]  # the combined answer is a newer revision
    with pytest.raises(MixedRevision):
        finalize_reports(run, result)
    assert result.reports == {}


def test_pre_generation_live_snapshot_remains_readable(tmp_path: Path) -> None:
    base = Path(__file__).parents[1] / "fixtures" / "live_v1_format1"
    archive = base / "live-synthetic.zip"
    ingest(
        archive,
        tmp_path / "legacy-live.duckdb",
        entries=load_entries_manifest(base / "live-synthetic.entries"),
        expected_sha256=(base / "live-synthetic.sha256").read_text().split()[0],
    )
    con = duckdb.connect(str(tmp_path / "legacy-live.duckdb"), read_only=True)
    try:
        document = build_document(con)
    finally:
        con.close()
    assert document["mode"] == "live"
    assert len(document["acquisition"]["bosses"]) == 2


def _rewrite_marker(out: Any, dest: Path, change: Any) -> Path:
    with zipfile.ZipFile(out.archive) as src, zipfile.ZipFile(dest, "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == "necropsy-snapshot.json":
                doc = json.loads(data)
                change(doc)
                data = json.dumps(doc).encode()
            dst.writestr(info, data)
    return dest


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(formatVersion=True),
        lambda d: d["subject"].update(class_id=1),
        lambda d: d.update(cohort="anything"),
        lambda d: d["fights"][0].update(fightID=str(d["fights"][0]["fightID"])),
        lambda d: d["fights"][0]["participants"][0].update(player="Nobody"),
        lambda d: d["fights"][0]["participants"][0].update(boss="Gluth"),
        lambda d: d["subject"].update(faction="Horde"),
        lambda d: d["report_sets"][0].update(revision=99),
        lambda d: d["streams"][0]["identity"].update(endpoint="user"),
    ],
)
def test_the_live_marker_must_match_its_reports(written: Any, change: Any) -> None:
    _, _, out, tmp = written
    bad = _rewrite_marker(out, tmp / "bad.zip", change)
    with pytest.raises(SnapshotError):
        ingest(bad, tmp / "bad.duckdb")


def test_marker_keeps_stream_identity_meta_and_selection_verdicts(written: Any) -> None:
    _, _, out, _ = written
    with zipfile.ZipFile(out.archive) as archive:
        marker = json.loads(archive.read("necropsy-snapshot.json"))
    stream = marker["streams"][0]
    assert stream["identity"]["code"] == stream["report"] and "fetched_at" in stream["meta"]
    assert "account_points_between_readings" in stream["meta"]
    patchwerk = marker["bosses"][0]
    assert (
        patchwerk["selection"]["verdicts"]
        and patchwerk["cohort"][0]["verdict"]["status"] == "observed"
    )
    assert {m["faction_source"] for m in patchwerk["metadata"]} >= {"verify"}
    assert marker["report_sets"] and all(len(s["sha256"]) == 64 for s in marker["report_sets"])


def test_an_entry_missing_a_stream_is_refused_before_publishing(tmp_path: Path) -> None:
    (tmp_path / "cache").mkdir()
    (tmp_path / "out").mkdir()
    cohort, subject = _players()
    result, store, run = _acquire(tmp_path, FakeWcl(cohort, subject))
    finalize_reports(run, result)
    result.bosses[0].cohort[0].streams.pop()
    with pytest.raises(WriteError, match="player and pet streams"):
        write_snapshot(result, store, tmp_path / "out", "live")
    assert not list((tmp_path / "out").glob("live.*"))


def test_subject_rankings_returned_as_text_are_kept(tmp_path: Path) -> None:
    (tmp_path / "cache").mkdir()
    (tmp_path / "out").mkdir()
    cohort, subject = _players()
    result, store, run = _acquire(tmp_path, FakeWcl(cohort, subject))
    finalize_reports(run, result)
    raw = result.bosses[0].subject_raw
    result.bosses[0].subject_raw = json.dumps(raw)
    written = write_snapshot(result, store, tmp_path / "out", "live")
    with zipfile.ZipFile(written.archive) as archive:
        name = next(n for n in archive.namelist() if n.startswith("user_rankings/51118"))
        doc = json.loads(archive.read(name))
    assert doc["encounterRankings"] == raw and doc["encounterRankingsAsReturned"] == json.dumps(raw)


def test_a_failed_publication_removes_only_its_own_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from necropsy.snapshot import v1_writer

    (tmp_path / "cache").mkdir()
    (tmp_path / "out").mkdir()
    cohort, subject = _players()
    result, store, run = _acquire(tmp_path, FakeWcl(cohort, subject))
    finalize_reports(run, result)
    from necropsy.wcl.cache import publish as real

    calls = {"n": 0}

    def flaky(target: Path, body: bytes) -> str:
        calls["n"] += 1
        if calls["n"] == 2:
            # Someone replaces the archive we just published, then our next write fails.
            archive = tmp_path / "out" / "live.zip"
            archive.unlink()
            archive.write_bytes(b"someone else's file")
            raise OSError("disk full")
        return real(target, body)

    monkeypatch.setattr(v1_writer, "publish", flaky)
    with pytest.raises(OSError):
        write_snapshot(result, store, tmp_path / "out", "live")
    assert (tmp_path / "out" / "live.zip").read_bytes() == b"someone else's file"
    assert not (tmp_path / "out" / "live.entries").exists()


def test_a_concurrent_writer_is_refused(tmp_path: Path) -> None:
    import subprocess
    import sys

    from necropsy.wcl.cache import CacheBusy

    (tmp_path / "cache").mkdir()
    (tmp_path / "out").mkdir()
    cohort, subject = _players()
    result, store, run = _acquire(tmp_path, FakeWcl(cohort, subject))
    finalize_reports(run, result)
    holder = (
        "import sys, time\nfrom pathlib import Path\nfrom necropsy.wcl.cache import item_lock\n"
        "with item_lock(Path(sys.argv[1])):\n    print('locked', flush=True)\n    time.sleep(60)\n"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", holder, str(tmp_path / "out" / ".live.lock")],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None and child.stdout.readline().strip() == "locked"
        with pytest.raises(CacheBusy):
            write_snapshot(result, store, tmp_path / "out", "live")
    finally:
        child.kill()
        child.wait(timeout=30)
    assert not (tmp_path / "out" / "live.zip").exists()


def test_a_linked_output_directory_is_refused(tmp_path: Path) -> None:
    import sys

    (tmp_path / "cache").mkdir()
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "out"
    if sys.platform == "win32":
        import _winapi

        _winapi.CreateJunction(str(real), str(link))
    else:
        link.symlink_to(real, target_is_directory=True)
    cohort, subject = _players()
    result, store, run = _acquire(tmp_path, FakeWcl(cohort, subject))
    finalize_reports(run, result)
    with pytest.raises(WriteError, match="link"):
        write_snapshot(result, store, link, "live")
    assert list(real.iterdir()) == []


@pytest.mark.parametrize(
    "change",
    [
        lambda i: i.update(revision=999),
        lambda i: i.update(start_time=123456789.0),
        lambda i: i.update(site="fresh.warcraftlogs.com"),
        lambda i: i.update(data_type="Casts"),
        lambda i: i.update(limit="10000"),
        lambda i: i.update(query_version=2),
        lambda i: i.pop("translate"),
    ],
)
def test_stream_identity_must_be_the_exact_request(written: Any, change: Any) -> None:
    _, _, out, tmp = written
    bad = _rewrite_marker(out, tmp / "bad.zip", lambda d: change(d["streams"][0]["identity"]))
    with pytest.raises(SnapshotError):
        ingest(bad, tmp / "bad.duckdb")


def _rewrite(out: Any, dest: Path, edit: Any) -> Path:
    with zipfile.ZipFile(out.archive) as src:
        members = {i.filename: src.read(i) for i in src.infolist()}
    edit(members)
    with zipfile.ZipFile(dest, "w") as dst:
        for name in sorted(members):
            dst.writestr(name, members[name])
    return dest


def test_a_false_empty_pet_list_is_refused(written: Any) -> None:
    _, _, out, tmp = written

    def empty_pets(members: dict[str, bytes]) -> None:
        marker = json.loads(members["necropsy-snapshot.json"])
        for name in [n for n in members if n.endswith("/pets.json")]:
            members[name] = b"[]"
        for name in [n for n in members if "/pet_" in n]:
            del members[name]
        marker["streams"] = [s for s in marker["streams"] if s["role"] != "pet"]
        members["necropsy-snapshot.json"] = json.dumps(marker).encode()

    with pytest.raises(SnapshotError, match="pet list"):
        ingest(_rewrite(out, tmp / "pets.zip", empty_pets), tmp / "pets.duckdb")


def test_a_swapped_actor_record_is_refused(written: Any) -> None:
    _, _, out, tmp = written

    def swap(members: dict[str, bytes]) -> None:
        name = next(n for n in members if n.endswith("/selection.json") and "Ally1" in n)
        doc = json.loads(members[name])
        doc["actor"]["id"] = 999
        members[name] = json.dumps(doc).encode()

    with pytest.raises(SnapshotError):
        ingest(_rewrite(out, tmp / "swap.zip", swap), tmp / "swap.duckdb")


def _finalized(tmp_path: Path) -> tuple[Any, Cache]:
    (tmp_path / "cache").mkdir()
    (tmp_path / "out").mkdir()
    cohort, subject = _players()
    result, store, run = _acquire(tmp_path, FakeWcl(cohort, subject))
    finalize_reports(run, result)
    return result, store


@pytest.mark.parametrize("damage", ["name", "bounds", "amount", "zone", "requested"])
def test_malformed_acquisitions_publish_nothing(tmp_path: Path, damage: str) -> None:
    import dataclasses

    result, store = _finalized(tmp_path)
    entry = result.bosses[0].cohort[0]
    if damage == "name":
        entry.name = "Nobody"
    elif damage == "bounds":
        fight = result.reports[entry.report_code].report["fights"][0]
        fight["endTime"] = fight["endTime"] + 1
    elif damage == "amount":
        assert entry.candidate is not None
        entry.candidate.raw["amount"] = float("inf")
    elif damage == "zone":
        result.context = dataclasses.replace(result.context, zone_id=1001)
    else:
        result.requested = ()
    with pytest.raises(WriteError):
        write_snapshot(result, store, tmp_path / "out", "live")
    assert not list((tmp_path / "out").glob("live.*"))
