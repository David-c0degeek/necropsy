"""The live acceptance harness, exercised offline with synthetic runs (no credentials)."""

from __future__ import annotations

import io
import json
import random
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from necropsy.analysis.context import realm_key
from necropsy.report.offline import run_offline
from necropsy.wcl import acquire as acquire_mod
from necropsy.wcl import client as c
from necropsy.wcl.acceptance import (
    AcceptanceFailure,
    check_package,
    check_run,
    compare_with_history,
    credential_fields,
    write_receipt,
)
from necropsy.wcl.analyze import run_analyze
from tests.fixture_paths import subset_path
from tests.live.test_live_acceptance import live_settings
from tests.live.test_live_acceptance import test_live_analyze_acceptance as live_check
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _context
from tests.wcl_fakes import FakeClock

URL = "https://vanilla.warcraftlogs.com/character/id/86583560"


def _config(run_live: bool) -> Any:
    return SimpleNamespace(getoption=lambda name: run_live)


def test_the_live_test_needs_both_the_option_and_the_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NECROPSY_LIVE_URL", URL)
    assert live_settings(_config(False)) is None
    monkeypatch.delenv("NECROPSY_LIVE_URL")
    assert live_settings(_config(True)) is None
    monkeypatch.setenv("NECROPSY_LIVE_URL", URL)
    settings = live_settings(_config(True))
    assert settings is not None and settings["url"] == URL
    monkeypatch.setenv("NECROPSY_LIVE_WAIT_FOR_RESET", "1")
    settings = live_settings(_config(True))
    assert settings is not None and settings["wait_for_reset"] is True


def test_a_configured_shell_without_the_option_touches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from necropsy.wcl import cli as wcl_cli

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("credentials or network were touched")

    monkeypatch.setenv("NECROPSY_LIVE_URL", URL)
    monkeypatch.setattr(wcl_cli, "_tokens", forbidden)
    monkeypatch.setattr(wcl_cli, "_client", forbidden)
    with pytest.raises(pytest.skip.Exception):
        live_check(SimpleNamespace(config=_config(False)))  # type: ignore[arg-type]


@pytest.fixture
def run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    from necropsy.wcl import analyze as analyze_mod

    monkeypatch.setattr(acquire_mod, "boss_order", lambda: (PATCHWERK, 51120))
    monkeypatch.setattr(analyze_mod, "resolve", lambda *a, **k: _context())
    server = FakeWcl([Player(f"Ally{i}") for i in range(1, 31)], Player("Haplina"))

    def client(site: Any, provider: Any) -> c.WclClient:
        made = c.WclClient(
            site,
            provider,
            transport=httpx.MockTransport(server),
            clock=FakeClock(),
            rng=random.Random(0),
        )
        made.last_rate = c.RateLimit(36000, 10.0, 1800)
        return made

    outcome = run_analyze(
        URL,
        cache=tmp_path / "cache",
        out=tmp_path / "out",
        tokens=lambda: lambda endpoint: "t",
        client_factory=client,
        name="live",
    )
    return outcome, tmp_path / "out"


def test_check_run_verifies_snapshot_pages_and_package(run: Any) -> None:
    outcome, out = run
    w = outcome.snapshot
    checked = check_run(out, w.archive, w.entries, w.sha256)
    assert checked["document"]["mode"] == "live" and len(checked["package_sha256"]) == 64


def test_a_tampered_package_member_is_reported(run: Any, tmp_path: Path) -> None:
    _, out = run
    package = next(out.glob("necropsy-*.zip"))
    with zipfile.ZipFile(package) as src:
        members = {i.filename: src.read(i) for i in src.infolist()}
    members["report.html"] = members["report.html"] + b"<!-- changed -->"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as dst:
        for name, data in members.items():
            dst.writestr(name, data)
    bad = tmp_path / "bad.zip"
    bad.write_bytes(buffer.getvalue())
    assert check_package(bad) == ["report.html differs from the package manifest"]


def test_an_empty_page_fails_the_acceptance(run: Any) -> None:
    outcome, out = run
    (out / "playbook.html").write_bytes(b"")
    w = outcome.snapshot
    with pytest.raises(AcceptanceFailure, match=r"playbook.html"):
        check_run(out, w.archive, w.entries, w.sha256)


def test_without_history_the_comparison_is_not_performed(run: Any) -> None:
    _, out = run
    live = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    report = compare_with_history(live, None)
    assert report["historical_comparison"].startswith("historical comparison not performed")
    assert [r["encounter_id"] for r in report["bosses"]] == [PATCHWERK, 51120]
    assert all(r["historical"] == "unknown (not compared)" for r in report["bosses"])
    assert report["bosses"][1]["coverage"]["complete"] is False


def test_metadata_rank_one_does_not_claim_acquired_event_context(run: Any) -> None:
    _, out = run
    live = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    top = {"player": "MetadataOnly", "ranked_dps": 2000, "event_sample_acquired": False}
    live["bosses"][0]["benchmarks"]["overall_top"] = top
    assert compare_with_history(live, None)["bosses"][0]["overall_first_acquired"] is False
    del top["event_sample_acquired"]  # earlier documents only contained acquired rank-one entries
    assert compare_with_history(live, None)["bosses"][0]["overall_first_acquired"] is True


def test_history_must_match_the_character_zone_and_partition(run: Any, tmp_path: Path) -> None:
    _, out = run
    live = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    run_offline(subset_path(), tmp_path / "hist", package=False)
    history = json.loads((tmp_path / "hist" / "analysis.json").read_text(encoding="utf-8"))
    assert history["mode"] == "historical"
    history["zone"]["partition"] = live["zone"]["partition"] + 1
    assert "another character" in compare_with_history(live, history)["historical_comparison"]
    history["zone"]["partition"] = live["zone"]["partition"]
    history["subject"]["id"] = live["subject"]["id"]
    report = compare_with_history(live, history)
    assert report["historical_comparison"] == "compared with the given historical analysis"
    rows = {r["encounter_id"]: r for r in report["bosses"]}
    historical_bosses = {b["encounter_id"] for b in history["bosses"]}
    for encounter, row in rows.items():
        if encounter in historical_bosses:
            assert set(row["historical"]) >= {"both", "only_live", "only_historical"}
        else:
            assert row["historical"].startswith("unavailable")


def test_receipts_never_replace_and_never_hold_credentials(tmp_path: Path) -> None:
    path = tmp_path / "live-acceptance.json"
    write_receipt(path, {"result": "partial"})
    with pytest.raises(AcceptanceFailure, match="never replaced"):
        write_receipt(path, {"result": "complete"})
    assert json.loads(path.read_text(encoding="utf-8")) == {"result": "partial"}
    with pytest.raises(AcceptanceFailure, match="credential"):
        write_receipt(tmp_path / "other.json", {"nested": [{"access_token": "x"}]})
    assert credential_fields({"a": {"Client_Secret": 1}}) == ["a.Client_Secret"]


def test_scanner_states_are_never_guessed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil
    import subprocess

    from necropsy.wcl import acceptance

    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert acceptance.secret_scan(tmp_path)["status"] == "unavailable"
    monkeypatch.setattr(shutil, "which", lambda name: "gitleaks")
    for code, status in ((0, "passed"), (1, "findings"), (2, "failed"), (126, "failed")):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, code=code, **k: subprocess.CompletedProcess(a, code, "", ""),
        )
        result = acceptance.secret_scan(tmp_path)
        assert result["status"] == status and "does not prove" in result["limit"]

    def boom(*a: Any, **k: Any) -> Any:
        raise OSError("no exec")

    monkeypatch.setattr(subprocess, "run", boom)
    assert acceptance.secret_scan(tmp_path)["status"] == "failed"


def test_history_is_checked_before_any_live_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from necropsy.wcl import cli as wcl_cli
    from necropsy.wcl.acceptance import load_history

    bad = tmp_path / "history.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(AcceptanceFailure):
        load_history(bad, 86583560, None)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("credentials or network were touched")

    monkeypatch.setattr(wcl_cli, "_tokens", forbidden)
    monkeypatch.setattr(wcl_cli, "_client", forbidden)
    monkeypatch.setenv("NECROPSY_LIVE_URL", URL)
    monkeypatch.setenv("NECROPSY_LIVE_HISTORY", str(bad))
    monkeypatch.setenv("NECROPSY_LIVE_OUT", str(tmp_path / "out"))
    monkeypatch.setenv("NECROPSY_LIVE_CACHE", str(tmp_path / "cache"))
    with pytest.raises(AcceptanceFailure):
        live_check(SimpleNamespace(config=_config(True)))  # type: ignore[arg-type]


def test_a_matching_history_loads(tmp_path: Path) -> None:
    from necropsy.wcl.acceptance import load_history

    run_offline(subset_path(), tmp_path / "hist", package=False)
    path = tmp_path / "hist" / "analysis.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    loaded = load_history(path, document["subject"]["id"], document["zone"]["partition"])
    assert loaded["mode"] == "historical"
    with pytest.raises(AcceptanceFailure, match="another character"):
        load_history(path, 1, None)


def _checked(run: Any, **kw: Any) -> Any:
    outcome, out = run
    w = outcome.snapshot
    return check_run(out, w.archive, w.entries, w.sha256, sha256_file=w.sha256_file, **kw)


def test_scope_and_identity_are_bound(run: Any) -> None:
    outcome, out = run
    assert _checked(run, requested=outcome.acquisition.requested)
    with pytest.raises(AcceptanceFailure, match="exactly the requested bosses"):
        _checked(run, requested=(PATCHWERK,))
    document = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    document["snapshot"]["archive_sha256"] = "0" * 64
    (out / "analysis.json").write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(AcceptanceFailure, match="not built from this snapshot"):
        _checked(run)


def test_a_wrong_sha256_companion_fails(run: Any) -> None:
    outcome, _ = run
    outcome.snapshot.sha256_file.write_text("deadbeef  live.zip\n", encoding="utf-8")
    with pytest.raises(AcceptanceFailure, match="digest"):
        _checked(run)


def test_a_package_from_another_analysis_fails(run: Any) -> None:
    _, out = run
    report = (out / "report.html").read_bytes()
    (out / "report.html").write_bytes(report + b"<!-- newer -->")
    with pytest.raises(AcceptanceFailure, match=r"not the current report.html"):
        _checked(run)


def test_historical_rows_of_another_faction_are_not_cohort(run: Any, tmp_path: Path) -> None:
    _, out = run
    live = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    run_offline(subset_path(), tmp_path / "hist", package=False, cross_faction=True)
    history = json.loads((tmp_path / "hist" / "analysis.json").read_text(encoding="utf-8"))
    history["subject"]["id"] = live["subject"]["id"]
    history["zone"]["partition"] = live["zone"]["partition"]
    report = compare_with_history(live, history)
    for row in report["bosses"]:
        if isinstance(row["historical"], dict):
            section = next(b for b in history["bosses"] if b["encounter_id"] == row["encounter_id"])
            mine = section["subject"]["environment"]["faction"]["value"]
            allowed = {
                f"{e['player']}-{realm_key(e['server'])}"
                for e in section["cohort"]
                if e["environment"]["faction"]["value"] == mine
            }
            assert set(row["historical"]["cohort_players"]) <= allowed
            assert row["historical"]["same_subject_fight"] in (True, False, None)


def test_subject_fight_equality_is_unknown_without_both_fights(run: Any, tmp_path: Path) -> None:
    _, out = run
    live = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    run_offline(subset_path(), tmp_path / "hist", package=False)
    history = json.loads((tmp_path / "hist" / "analysis.json").read_text(encoding="utf-8"))
    history["subject"]["id"] = live["subject"]["id"]
    history["zone"]["partition"] = live["zone"]["partition"]
    for b in live["acquisition"]["bosses"]:
        b["subject"] = None
    for b in history["bosses"]:
        b["encounter_id"] = PATCHWERK if b is history["bosses"][0] else b["encounter_id"]
    report = compare_with_history(live, history)
    compared = [r for r in report["bosses"] if isinstance(r["historical"], dict)]
    assert compared and all(r["historical"]["same_subject_fight"] is None for r in compared)


def test_a_baseline_for_another_partition_stops_before_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from necropsy.wcl import analyze as analyze_mod
    from necropsy.wcl.acceptance import history_matches_context

    monkeypatch.setattr(analyze_mod, "resolve", lambda *a, **k: _context())
    server = FakeWcl([Player(f"Ally{i}") for i in range(1, 6)], Player("Haplina"))

    def client(site: Any, provider: Any) -> c.WclClient:
        return c.WclClient(
            site,
            provider,
            transport=httpx.MockTransport(server),
            clock=FakeClock(),
            rng=random.Random(0),
        )

    history = {"subject": {"id": 86583560}, "zone": {"id": 2006, "partition": 99}}
    with pytest.raises(AcceptanceFailure, match="another zone or partition"):
        run_analyze(
            URL,
            cache=tmp_path / "cache",
            out=tmp_path / "out",
            tokens=lambda: lambda endpoint: "t",
            client_factory=client,
            before_acquire=lambda context: history_matches_context(history, context),
        )
    assert server.requests == []  # resolution was faked; no acquisition request was made


def test_without_a_faction_basis_cohort_overlap_is_unknown(run: Any, tmp_path: Path) -> None:
    _, out = run
    live = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    live["acquisition"]["subject_faction"] = None
    run_offline(subset_path(), tmp_path / "hist", package=False)
    history = json.loads((tmp_path / "hist" / "analysis.json").read_text(encoding="utf-8"))
    history["subject"]["id"] = live["subject"]["id"]
    history["zone"]["partition"] = live["zone"]["partition"]
    report = compare_with_history(live, history)
    compared = [r for r in report["bosses"] if isinstance(r["historical"], dict)]
    assert all(r["live_deep_players"] is None for r in report["bosses"])
    assert all(r["historical"]["cohort_overlap"].startswith("unknown") for r in compared)


def _package(tmp_path: Path, members: list[tuple[str, bytes]]) -> Path:
    path = tmp_path / "pkg.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members:
            archive.writestr(name, data)
    path.write_bytes(buffer.getvalue())
    return path


def test_duplicate_or_malformed_package_records_are_refused(tmp_path: Path) -> None:
    import hashlib
    import warnings

    body = b"x"
    good = {"path": "a.txt", "bytes": 1, "sha256": hashlib.sha256(body).hexdigest()}
    manifest = json.dumps({"files": [good, good]}).encode()
    assert (
        "twice"
        in check_package(_package(tmp_path, [("manifest.json", manifest), ("a.txt", body)]))[0]
    )
    bad = json.dumps(
        {"files": [{"path": "a.txt", "bytes": "1", "sha256": good["sha256"]}]}
    ).encode()
    assert (
        "malformed"
        in check_package(_package(tmp_path, [("manifest.json", bad), ("a.txt", body)]))[0]
    )
    ok = json.dumps({"files": [good]}).encode()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dup = _package(tmp_path, [("manifest.json", ok), ("a.txt", body), ("a.txt", b"y")])
    assert "twice" in check_package(dup)[0]
    assert check_package(_package(tmp_path, [("manifest.json", ok), ("a.txt", body)])) == []
