"""`necropsy analyze` end to end against a fake Warcraft Logs server.

SYNTHETIC responses (tests/unit/test_wcl_acquire.py); a fake token provider, never
the OS credential store; no network.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
import typer
from typer.testing import CliRunner

from necropsy.cli import app
from necropsy.raids import RAIDS
from necropsy.snapshot.archive import VerifiedArchive
from necropsy.snapshot.v1 import open_snapshot
from necropsy.wcl import acquire as acquire_mod
from necropsy.wcl import analyze as analyze_mod
from necropsy.wcl import cli as wcl_cli
from necropsy.wcl import client as c
from necropsy.wcl import credentials
from necropsy.wcl.auth import LoginNeeded
from necropsy.wcl.context import Partition
from tests.integration.test_encounter_snapshot import EncounterWcl
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _context
from tests.wcl_fakes import FakeClock

URL = "https://vanilla.warcraftlogs.com/character/id/86583560"
SECRET = "sentinel-secret-token-value"


@pytest.fixture(autouse=True)
def _no_live_access(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test here may reach the real network or OS credential store, even after undo."""

    def refuse(*_: Any, **__: Any) -> Any:
        raise AssertionError("live network or credential access in an offline test")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)
    monkeypatch.setattr(credentials.CredentialStore, "open", refuse)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"server": None, "tokens": 0, "endpoints": []}
    monkeypatch.setattr(acquire_mod, "boss_order", lambda zone="naxxramas": (PATCHWERK,))

    def tokens() -> Any:
        state["tokens"] += 1
        return lambda endpoint: SECRET

    def client(site: Any, provider: Any) -> c.WclClient:
        made = c.WclClient(
            site,
            provider,
            transport=httpx.MockTransport(state["server"]),
            clock=FakeClock(),
            rng=random.Random(0),
        )
        made.last_rate = c.RateLimit(36000, 10.0, 1800)
        state["client"] = made
        return made

    def resolver(client: Any, ref: Any, *, partition: Any, endpoint: str) -> Any:
        state["endpoints"].append(endpoint)
        return state.get("context") or _context()

    monkeypatch.setattr(wcl_cli, "_tokens", tokens)
    monkeypatch.setattr(wcl_cli, "_client", client)
    monkeypatch.setattr(analyze_mod, "resolve", resolver)
    state["server"] = FakeWcl([Player(f"Ally{i}") for i in range(1, 31)], Player("Haplina"))
    return state


def _run(tmp: Path, *extra: str, out: str = "out") -> Any:
    args = ["analyze", URL, "--cache", str(tmp / "cache"), "--out", str(tmp / out), *extra]
    return CliRunner().invoke(app, args)


def test_a_complete_run_writes_snapshot_and_pages(tmp_path: Path, fake: dict[str, Any]) -> None:
    result = _run(tmp_path, "--name", "live")
    assert result.exit_code == 0, result.output
    out = tmp_path / "out"
    assert (out / "snapshot" / "live.zip").exists() and (out / "report.html").exists()
    document = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    assert document["mode"] == "live"
    assert "Patchwerk: complete" in result.output and "Next: open" in result.output
    assert SECRET not in result.output
    assert fake["endpoints"] == ["client"]


@pytest.mark.parametrize(
    "slug,partition,context_enabled",
    [
        ("mc", 1, True),
        ("mc", 2, True),
        ("bwl", 1, True),
        ("bwl", 2, True),
        ("aq40", 1, True),
        ("aq40", 2, True),
        ("naxxramas", 1, False),
        ("naxxramas", 3, False),
        ("mc", 3, False),
    ],
)
def test_normal_cli_selects_encounter_scopes_for_new_era_raids(
    tmp_path: Path,
    fake: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    slug: str,
    partition: int,
    context_enabled: bool,
) -> None:
    raid = next(r for r in RAIDS if r.slug == slug)
    encounter = {"mc": 50669, "bwl": 50631, "aq40": 50713, "naxxramas": PATCHWERK}[slug]

    class Server(EncounterWcl):
        def _report(self, player: Player, wanted: list[int] | None = None) -> dict[str, Any]:
            report = super()._report(player, wanted)
            for fight in report["fights"]:
                fight["encounterID"] = encounter
            return report

    context = _context()
    assert context.partition is not None
    chosen = replace(context.partition, id=partition)
    fake["context"] = replace(context, zone_id=raid.zone_id, partition=chosen, partitions=(chosen,))
    fake["server"] = Server([Player(f"Ally{i}") for i in range(30)], Player("Haplina"))
    monkeypatch.setattr(acquire_mod, "boss_order", lambda zone="naxxramas": (encounter,))
    result = _run(tmp_path, "--raid", slug, "--partition", str(partition), "--name", "scoped")
    assert result.exit_code == 0, result.output
    out = tmp_path / "out"
    with VerifiedArchive(out / "snapshot/scoped.zip") as archive:
        reader = open_snapshot(archive)
        assert reader.issues() == []
        assert reader.descriptor().format == (
            "necropsy-live-snapshot-v2" if context_enabled else "necropsy-live-snapshot-v1"
        )
        marker = archive.read_json("necropsy-snapshot.json")
        scopes = marker.get("encounter_streams", [])
        assert len(scopes) == (12 if context_enabled else 0)
        assert all(s["actor_id"] is None and s["direction"] == "all" for s in scopes)
    document = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    assert document["zone"]["id"] == raid.zone_id
    assert len(document["bosses"]) == 1
    assert (out / "report.html").is_file() and (out / "playbook.html").is_file()
    assert list(out.glob("necropsy-*.zip"))
    critical = [r for r in fake["server"].requests if r["variables"].get("filterExpression")]
    assert len(critical) == (6 if context_enabled else 0)


def test_normal_encounter_context_quota_resume_preserves_completed_scopes(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context()
    assert context.partition is not None
    chosen = replace(context.partition, id=1)
    fake["context"] = replace(context, zone_id=2000, partition=chosen, partitions=(chosen,))
    server = EncounterWcl([Player(f"Ally{i}") for i in range(30)], Player("Haplina"))
    monkeypatch.setattr(acquire_mod, "boss_order", lambda zone="naxxramas": (50669,))
    blocked = True
    unrestricted_requests = 0

    def interrupted(request: httpx.Request) -> httpx.Response:
        nonlocal unrestricted_requests
        body = json.loads(request.content)
        variables = body["variables"]
        if "NecropsyEvents" in body["query"] and variables["code"] == "RHaplina":
            if blocked and variables.get("filterExpression"):
                return httpx.Response(
                    200,
                    json={
                        "data": {
                            "rateLimitData": {
                                "limitPerHour": 36000,
                                "pointsSpentThisHour": 36000,
                                "pointsResetIn": 20,
                            }
                        },
                        "errors": [{"message": "rate limit exceeded"}],
                    },
                )
            if (
                variables.get("sourceID") is None
                and variables.get("targetID") is None
                and not variables.get("filterExpression")
            ):
                unrestricted_requests += 1
        return server(request)

    fake["server"] = interrupted
    first = _run(tmp_path, "--raid", "mc", "--partition", "1", "--name", "interrupted")
    assert first.exit_code == 4, first.output
    assert "RateLimited" in first.output
    assert unrestricted_requests == 1
    assert list((tmp_path / "cache").rglob("client_encounter_all/stream.json"))
    assert not list((tmp_path / "cache").rglob("client_critical_all/stream.json"))
    first_archive = tmp_path / "out/snapshot/interrupted.zip"
    original = first_archive.read_bytes()
    with VerifiedArchive(first_archive) as archive:
        assert archive.read_json("necropsy-snapshot.json")["fights"] == []
    blocked = False
    second = _run(tmp_path, "--raid", "mc", "--partition", "1", "--resume")
    assert second.exit_code == 0, second.output
    assert unrestricted_requests == 1  # completed All scope is reused after the stop
    assert first_archive.read_bytes() == original
    resumed = list((tmp_path / "out/.necropsy-run/snapshots").glob("*/*.zip"))
    assert len(resumed) == 1
    with VerifiedArchive(resumed[0]) as archive:
        assert open_snapshot(archive).issues() == []
        assert len(archive.read_json("necropsy-snapshot.json")["encounter_streams"]) == 12


def test_declared_tree_survives_snapshot_replay_without_changing_query_pool(
    tmp_path: Path,
    fake: dict[str, Any],
) -> None:
    from necropsy.report.offline import run_offline

    result = _run(
        tmp_path, "--name", "declared", "--category", "Marksmanship", "--talent-tree", "Survival"
    )
    assert result.exit_code == 0, result.output
    out = tmp_path / "out"
    original = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    assert original["taxonomy"]["declared_talent_tree"] == "Survival"
    assert original["taxonomy"]["comparison_pool"]["slug"] == "Marksmanship"
    assert original["acquisition"]["declared_talent_tree"] == "Survival"
    queries = [r["query"] for r in fake["server"].requests if "NecropsyLeaderboard" in r["query"]]
    assert queries and all('specName: "Marksmanship"' in q for q in queries)
    assert all('specName: "Survival"' not in q for q in queries)
    run_offline(out / "snapshot/declared.zip", tmp_path / "replay")
    replay = json.loads((tmp_path / "replay/analysis.json").read_text(encoding="utf-8"))
    assert replay["taxonomy"] == original["taxonomy"]
    page = (tmp_path / "replay/report.html").read_text(encoding="utf-8")
    assert "Survival" in page and "does not narrow the leaderboard" in page
    changed = _run(tmp_path, "--resume", "--talent-tree", "Beast Mastery")
    assert changed.exit_code == 1 and "resume options differ" in changed.output
    # A declaration for another class is also refused at the archive boundary.
    import zipfile

    from necropsy.snapshot.model import SnapshotError

    bad = tmp_path / "invalid-declaration.zip"
    with (
        zipfile.ZipFile(out / "snapshot/declared.zip") as source,
        zipfile.ZipFile(bad, "w") as target,
    ):
        for name in source.namelist():
            body = source.read(name)
            if name == "necropsy-snapshot.json":
                marker = json.loads(body)
                marker["subject"]["talent_tree"] = "Combat"
                body = json.dumps(marker).encode()
            target.writestr(name, body)
    with pytest.raises(SnapshotError, match="Hunter talent tree"):
        run_offline(bad, tmp_path / "bad-replay")


def test_talent_tree_for_another_class_is_refused_before_acquisition(
    tmp_path: Path,
    fake: dict[str, Any],
) -> None:
    result = _run(tmp_path, "--talent-tree", "Combat")
    assert result.exit_code == 1 and "Hunter talent tree" in result.output
    assert not fake["server"].requests


def test_public_sign_in_drives_user_acquisition(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from necropsy.wcl.auth import PkceAttempt
    from tests.unit.test_wcl_auth import CODE, _auth, _token_ok
    from tests.wcl_fakes import Script

    script = Script(_token_ok())
    auth, _ = _auth(script)
    auth.complete_public_sign_in(PkceAttempt("synthetic-app"), CODE)
    monkeypatch.setattr(wcl_cli, "_tokens", lambda: auth.token_for)
    result = _run(tmp_path, "--endpoint", "user", "--name", "public")
    assert result.exit_code == 0, result.output
    assert fake["endpoints"] == ["user"]
    assert len(script.requests) == 1  # never mints a confidential client token
    assert (tmp_path / "out/snapshot/public.zip").is_file()
    assert (tmp_path / "out/report.html").is_file()
    document = json.loads((tmp_path / "out/analysis.json").read_text(encoding="utf-8"))
    assert document["acquisition"]["endpoint"] == "user"


def test_public_sign_in_refuses_client_acquisition(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from necropsy.wcl.auth import PkceAttempt
    from tests.unit.test_wcl_auth import CODE, _auth, _token_ok
    from tests.wcl_fakes import Script

    script = Script(_token_ok())
    auth, _ = _auth(script)
    auth.complete_public_sign_in(PkceAttempt("synthetic-app"), CODE)
    monkeypatch.setattr(wcl_cli, "_tokens", lambda: auth.token_for)
    result = _run(tmp_path)
    assert result.exit_code == 1 and "--endpoint user" in result.output
    assert not fake["server"].requests and len(script.requests) == 1


def test_explicit_hunter_spec_and_faction_select_the_main_lookup(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    result = _run(tmp_path, "--spec", "Marksmanship", "--faction", "Alliance")
    assert result.exit_code == 0, result.output
    doc = json.loads((tmp_path / "out/analysis.json").read_text(encoding="utf-8"))
    assert doc["acquisition"]["selected_category"] == "Marksmanship"
    leaderboards = [r for r in fake["server"].requests if "NecropsyLeaderboard" in r["query"]]
    assert leaderboards and all('specName: "Marksmanship"' in r["query"] for r in leaderboards)


def test_wrong_faction_is_refused_before_acquiring_reports(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    result = _run(tmp_path, "--spec", "Marksmanship", "--faction", "Horde")
    assert result.exit_code == 1 and "differs from the character" in result.output
    assert not fake["server"].requests


def test_selected_hunter_without_personal_fights_keeps_a_faction_leader_playbook(
    tmp_path: Path,
    fake: dict[str, Any],
) -> None:
    class NoPersonalWcl(FakeWcl):
        def __call__(self, request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            if "NecropsySubject" in body["query"]:
                self.requests.append(body)
                return self._ok(
                    {"characterData": {"character": {"encounterRankings": {"ranks": []}}}}
                )
            return super().__call__(request)

    fake["server"] = NoPersonalWcl([Player(f"Ally{i}") for i in range(1, 31)], Player("Haplina"))
    result = _run(tmp_path, "--spec", "Marksmanship", "--faction", "Alliance")
    assert result.exit_code == 4, result.output
    doc = json.loads((tmp_path / "out/analysis.json").read_text(encoding="utf-8"))
    assert doc["bosses"][0]["subject"] is None and not doc["bosses"][0]["recommendations"]
    page = (tmp_path / "out/playbook.html").read_text(encoding="utf-8")
    assert "No matching personal fight" in page and "Ally1" in page
    assert 'href="report.html#boss-' in page
    report = (tmp_path / "out/report.html").read_text(encoding="utf-8")
    assert "No personal Marksmanship encounter" in report
    assert '<details class="overall-comparison">' in report


def test_interactive_lookup_asks_for_faction_and_spec(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    questions = []

    def prompt(question: str, **kwargs: Any) -> str:
        questions.append(question)
        return "Alliance" if "faction" in question else "Marksmanship"

    monkeypatch.setattr(wcl_cli, "sys", SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True)))
    monkeypatch.setattr(typer, "prompt", prompt)
    result = _run(tmp_path)
    assert result.exit_code == 0, result.output
    assert len(questions) == 2 and "faction" in questions[0] and "Spec" in questions[1]


def test_interactive_hunter_can_keep_legacy_all_spec_lookup(
    tmp_path: Path,
    fake: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    def prompt(question: str, **kwargs: Any) -> str:
        return "Alliance" if "faction" in question else kwargs["default"]

    monkeypatch.setattr(wcl_cli, "sys", SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True)))
    monkeypatch.setattr(typer, "prompt", prompt)
    result = _run(tmp_path)
    assert result.exit_code == 0, result.output
    leaderboards = [r for r in fake["server"].requests if "NecropsyLeaderboard" in r["query"]]
    assert leaderboards and all("specName:" not in r["query"] for r in leaderboards)


@pytest.mark.parametrize(
    "args",
    [
        ["--spec", "Tank", "--category", "Balance"],
        ["--spec", "invalid"],
    ],
)
def test_spec_selection_is_validated_before_credentials(
    tmp_path: Path,
    fake: dict[str, Any],
    args: list[str],
) -> None:
    result = _run(tmp_path, *args)
    assert result.exit_code == 1
    assert fake["tokens"] == 0
    assert (
        "different ranking categories" in result.output or "supported Classic Era" in result.output
    )


def test_partial_coverage_exits_4_with_the_report_written(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    fake["server"] = FakeWcl([Player(f"Ally{i}") for i in range(1, 7)], Player("Haplina"))
    result = _run(tmp_path, "--talent-tree", "Beast Mastery")
    assert result.exit_code == 4, result.output
    assert "Patchwerk: partial" in result.output and (tmp_path / "out" / "report.html").exists()
    assert "To retry incomplete acquisition, resume with:" in result.output
    assert "After the hourly reset" not in result.output
    assert "--talent-tree" in result.output and "Beast Mastery" in result.output


def test_the_user_endpoint_is_used_everywhere(tmp_path: Path, fake: dict[str, Any]) -> None:
    result = _run(tmp_path, "--endpoint", "user")
    assert result.exit_code == 0, result.output
    assert fake["endpoints"] == ["user"]
    assert fake["server"].urls and all("/api/v2/user" in u for u in fake["server"].urls)


def test_reset_wait_option_does_not_change_a_shared_factory_policy(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = wcl_cli._client
    shared = c.Policy()

    def factory(site: Any, provider: Any) -> c.WclClient:
        made = original(site, provider)
        made.policy = shared
        return made

    monkeypatch.setattr(wcl_cli, "_client", factory)
    first = _run(tmp_path, "--wait-for-reset")
    first_client = fake["client"]
    assert first.exit_code == 0 and first_client.policy.wait_for_reset
    assert not shared.wait_for_reset
    second = _run(tmp_path, out="out-second")
    assert second.exit_code == 0 and not fake["client"].policy.wait_for_reset
    assert first_client.policy.wait_for_reset and not shared.wait_for_reset


def test_a_needed_partition_choice_exits_2_and_writes_nothing(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    import dataclasses

    parts = (Partition(3, "Phase 6", True, True), Partition(4, "Phase 7", False, True))
    fake["context"] = dataclasses.replace(
        _context(), partition=None, partitions=parts, ambiguity="choose a partition"
    )
    result = _run(tmp_path)
    assert result.exit_code == 2
    assert "partition 3: Phase 6 (has rankings)" in result.output
    assert not (tmp_path / "out" / "snapshot").exists()


@pytest.mark.parametrize(
    "extra",
    [("--endpoint", "admin"), ("--partition", "0"), ("--name", "../x"), ("--name", ".hidden")],
)
def test_bad_options_are_refused_before_credentials(
    tmp_path: Path, fake: dict[str, Any], extra: tuple[str, str]
) -> None:
    result = _run(tmp_path, *extra)
    assert result.exit_code == 1
    assert fake["tokens"] == 0


def test_a_bad_url_is_refused_before_credentials(tmp_path: Path, fake: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        app,
        [
            "analyze",
            "https://evil.example/character/id/1",
            "--cache",
            str(tmp_path / "c"),
            "--out",
            str(tmp_path / "o"),
        ],
    )
    assert result.exit_code == 1 and fake["tokens"] == 0


def test_an_existing_analysis_is_never_replaced(tmp_path: Path, fake: dict[str, Any]) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "report.html").write_text("earlier", encoding="utf-8")
    result = _run(tmp_path)
    assert result.exit_code == 1 and "choose a new output directory" in result.output
    assert (out / "report.html").read_text(encoding="utf-8") == "earlier"
    assert fake["tokens"] == 0


def test_a_linked_output_directory_is_refused(tmp_path: Path, fake: dict[str, Any]) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "out"
    if sys.platform == "win32":
        import _winapi

        _winapi.CreateJunction(str(real), str(link))
    else:
        link.symlink_to(real, target_is_directory=True)
    result = _run(tmp_path)
    assert result.exit_code == 1 and "link" in result.output and fake["tokens"] == 0


def test_a_second_run_on_the_same_output_is_refused(tmp_path: Path, fake: dict[str, Any]) -> None:
    out = tmp_path / "out"
    out.mkdir()
    holder = (
        "import sys, time\nfrom pathlib import Path\nfrom necropsy.wcl.cache import item_lock\n"
        "with item_lock(Path(sys.argv[1])):\n    print('locked', flush=True)\n    time.sleep(60)\n"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", holder, str(out / ".necropsy-analyze.lock")],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None and child.stdout.readline().strip() == "locked"
        result = _run(tmp_path)
    finally:
        child.kill()
        child.wait(timeout=30)
    assert result.exit_code == 1 and "another process" in result.output


def test_a_finalization_stop_exits_3_with_nothing_written(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def stop(run: Any, acquisition: Any) -> Any:
        raise acquire_mod.RunStopped("BudgetExceeded during combined report")

    monkeypatch.setattr(analyze_mod, "finalize_reports", stop)
    result = _run(tmp_path)
    assert result.exit_code == 3 and "no snapshot or report" in result.output
    assert not (tmp_path / "out" / "report.html").exists()
    assert not list((tmp_path / "out").glob("snapshot/*.zip"))


def test_a_mixed_revision_exits_1(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def mixed(run: Any, acquisition: Any) -> Any:
        raise acquire_mod.MixedRevision("report RAlly1 entries span revisions [4, 5]")

    monkeypatch.setattr(analyze_mod, "finalize_reports", mixed)
    result = _run(tmp_path)
    assert result.exit_code == 1 and "rerun" in result.output


@pytest.mark.parametrize("wait", [False, True])
def test_finalization_can_wait_once_then_publish_verified_outputs(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch, wait: bool
) -> None:
    original = acquire_mod.finalize_reports

    def near_budget(run: Any, acquisition: Any) -> Any:
        run.client.last_rate = c.RateLimit(36000, 32000, 2)
        run.client.last_rate_at = run.client.clock.monotonic()
        return original(run, acquisition)

    monkeypatch.setattr(analyze_mod, "finalize_reports", near_budget)
    result = _run(tmp_path, "--endpoint", "user", *(("--wait-for-reset",) if wait else ()))
    client = fake["client"]
    if wait:
        assert result.exit_code == 0, result.output
        assert (tmp_path / "out" / "report.html").exists()
        assert list((tmp_path / "out" / "snapshot").glob("*.zip"))
        assert client.reset_wait["elapsed_wait_s"] == 3
        assert "hourly reset wait: 3 seconds" in result.output
        assert sum("NecropsySubject" in r["query"] for r in fake["server"].requests) == 1
        assert sum("NecropsyLeaderboard" in r["query"] for r in fake["server"].requests) == 1
        assert all("/api/v2/user" in url for url in fake["server"].urls)
    else:
        assert result.exit_code == 3 and "no snapshot or report" in result.output
        assert client.reset_wait is None
        assert not (tmp_path / "out" / "report.html").exists()


def test_a_report_failure_keeps_the_snapshot_and_prints_recovery(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: Any, **kwargs: Any) -> Any:
        raise OSError("disk full")

    monkeypatch.setattr(analyze_mod, "run_offline", broken)
    result = _run(tmp_path, "--name", "live", out="out dir")
    assert result.exit_code == 1
    assert (tmp_path / "out dir" / "snapshot" / "live.zip").exists()
    assert "finish offline with: necropsy offline" in result.output
    assert '"' in result.output or "'" in result.output  # the path with a space is quoted


def test_a_revision_change_during_reset_wait_refuses_all_outputs(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = acquire_mod.finalize_reports

    def near_budget(run: Any, acquisition: Any) -> Any:
        run.client.last_rate = c.RateLimit(36000, 32000, 2)
        run.client.last_rate_at = run.client.clock.monotonic()
        sleep = run.client.clock.sleep

        def revised(seconds: float) -> None:
            sleep(seconds)
            fake["server"].revisions["RAlly1"] = [5]

        monkeypatch.setattr(run.client.clock, "sleep", revised)
        return original(run, acquisition)

    monkeypatch.setattr(analyze_mod, "finalize_reports", near_budget)
    result = _run(tmp_path, "--wait-for-reset", "--endpoint", "user")
    assert result.exit_code == 1 and "revision" in result.output and "rerun" in result.output
    assert fake["client"].reset_wait["elapsed_wait_s"] == 3
    assert not (tmp_path / "out" / "report.html").exists()
    assert not list((tmp_path / "out").glob("snapshot/*.zip"))


def test_cross_faction_reaches_the_analysis(tmp_path: Path, fake: dict[str, Any]) -> None:
    horde = Player("Orcy", faction_code=0, guild=1, actor_id=7)
    fake["server"] = FakeWcl(
        [horde, *[Player(f"Ally{i}") for i in range(1, 31)]], Player("Haplina")
    )
    result = _run(tmp_path, "--cross-faction")
    assert result.exit_code in (0, 4), result.output
    document = json.loads((tmp_path / "out" / "analysis.json").read_text(encoding="utf-8"))
    assert document["options"]["cross_faction"] is True
    patchwerk = next(b for b in document["bosses"] if b["encounter_id"] == PATCHWERK)
    assert patchwerk["benchmarks"]["cross_faction"] is not None


def test_recovery_keeps_the_original_options(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: Any, **kwargs: Any) -> Any:
        raise OSError("disk full")

    monkeypatch.setattr(analyze_mod, "run_offline", broken)
    result = _run(tmp_path, "--cross-faction", "--no-package")
    assert result.exit_code == 1
    line = next(x for x in result.output.splitlines() if "finish offline with:" in x)
    assert "--cross-faction" in line and "--no-package" in line


@pytest.mark.parametrize(
    ("arg", "quoted"),
    [
        ("C:/plain/path.zip", "C:/plain/path.zip"),
        ("C:/out dir/x.zip", "'C:/out dir/x.zip'"),
        ("C:/it's/x", "'C:/it''s/x'"),
        ("C:/$HOME/x", "'C:/$HOME/x'"),
        ("C:/a`b/x", "'C:/a`b/x'"),
        ("C:/a&b/x", "'C:/a&b/x'"),
        (r"C:\Users\me\out", r"C:\Users\me\out"),
        (r"C:\my out\x.zip", r"'C:\my out\x.zip'"),
    ],
)
def test_recovery_commands_are_powershell_safe(arg: str, quoted: str) -> None:
    assert analyze_mod.powershell_quote(arg) == quoted
    assert analyze_mod.shell_command(["necropsy", arg], windows=True) == f"necropsy {quoted}"


def test_recovery_commands_are_posix_safe() -> None:
    import shlex

    args = ["necropsy", "offline", "/tmp/it's $HOME/x.zip"]
    assert shlex.split(analyze_mod.shell_command(args, windows=False)) == args


def test_progress_is_visible_before_network_and_in_phase_order(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    stages: list[str] = []
    original_update = wcl_cli._Activity.update
    server: FakeWcl = fake["server"]

    def update(activity: Any, message: str) -> None:
        stages.append(message)
        original_update(activity, message)

    def checked(request: httpx.Request) -> httpx.Response:
        assert "Resolving character, faction and partition" in stages
        assert any("Patchwerk" in stage for stage in stages)
        return server(request)

    monkeypatch.setattr(wcl_cli._Activity, "update", update)
    fake["server"] = checked
    result = _run(tmp_path)
    assert result.exit_code == 0, result.output
    assert stages[0] == "Loading Warcraft Logs credentials"
    assert stages[-3:] == [
        "Finalizing acquired reports",
        "Writing snapshot",
        "Analyzing snapshot and writing report, playbook and package",
    ]
    assert "(1/1 bosses)" in result.stderr
    assert "\x1b" not in result.stderr


def test_resume_keeps_partial_output_and_reuses_successful_requests(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = acquire_mod.finalize_reports

    def stop_after_acquiring(run: Any, acquisition: Any) -> Any:
        acquisition.stopped = "BudgetExceeded: quota reached"
        return original(run, acquisition)

    monkeypatch.setattr(analyze_mod, "finalize_reports", stop_after_acquiring)
    first = _run(tmp_path, "--spec", "Marksmanship", "--faction", "Alliance", "--name", "saved")
    assert first.exit_code == 4, first.output
    assert "--resume" in first.output
    old_snapshot = tmp_path / "out/snapshot/saved.zip"
    old_bytes = old_snapshot.read_bytes()
    before = len(fake["server"].requests)
    monkeypatch.setattr(analyze_mod, "finalize_reports", original)
    # Interactive selections and the snapshot name are restored without prompting.
    second = _run(tmp_path, "--resume")
    assert second.exit_code == 0, second.output
    assert "reused" in second.output
    assert len(fake["server"].requests) == before
    assert old_snapshot.read_bytes() == old_bytes
    assert len(list((tmp_path / "out/.necropsy-run/snapshots").glob("*/*.zip"))) == 1
    assert SECRET not in "".join(
        p.read_text() for p in (tmp_path / "out/.necropsy-run/requests").glob("*.json")
    )


def test_resume_after_quota_stop_partway_through_event_pagination(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    server: FakeWcl = fake["server"]
    blocked = True
    successful_first_pages = 0

    def paginated(request: httpx.Request) -> httpx.Response:
        nonlocal successful_first_pages
        body = json.loads(request.content)
        var = body["variables"]
        if "NecropsyEvents" in body["query"] and var["code"] == "RHaplina":
            if var["startTime"] == 1000:
                successful_first_pages += 1
                return server._ok(
                    {
                        "reportData": {
                            "report": {
                                "revision": 4,
                                "events": {
                                    "data": [{"timestamp": 1500, "type": "cast"}],
                                    "nextPageTimestamp": 2000,
                                },
                            }
                        }
                    }
                )
            if blocked:
                return httpx.Response(
                    200,
                    json={
                        "data": {
                            "rateLimitData": {
                                "limitPerHour": 36000,
                                "pointsSpentThisHour": 36000,
                                "pointsResetIn": 20,
                            }
                        },
                        "errors": [{"message": "rate limit exceeded"}],
                    },
                )
        return server(request)

    fake["server"] = paginated
    first = _run(tmp_path)
    assert first.exit_code == 4, first.output
    assert "RateLimited" in first.output
    assert successful_first_pages == 1
    assert (tmp_path / "out/report.html").exists()
    blocked = False  # the next invocation has a fresh hourly reading
    second = _run(tmp_path, "--resume")
    assert second.exit_code == 0, second.output
    # Source and target each fetch page one once; the interrupted source page is reused.
    assert successful_first_pages == 2
    assert (tmp_path / "out/report.html").is_file()


def test_resume_refuses_changed_options_or_modified_outputs_before_credentials(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    first = _run(tmp_path)
    assert first.exit_code == 0, first.output
    tokens = fake["tokens"]
    changed = _run(tmp_path, "--resume", "--cross-faction")
    assert changed.exit_code == 1 and "options differ" in changed.output
    assert fake["tokens"] == tokens
    report = tmp_path / "out/report.html"
    report.write_text("user edits")
    modified = _run(tmp_path, "--resume")
    assert modified.exit_code == 1 and "saved output changed" in modified.output
    assert report.read_text() == "user edits"
    assert fake["tokens"] == tokens


def test_resume_recovers_after_interrupted_publication(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from necropsy.report.offline import run_offline

    original = run_offline

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise OSError("disk full")

    monkeypatch.setattr(analyze_mod, "run_offline", broken)
    first = _run(tmp_path)
    assert first.exit_code == 1
    old_snapshots = list((tmp_path / "out/snapshot").glob("*.zip"))
    assert len(old_snapshots) == 1
    before = len(fake["server"].requests)
    monkeypatch.setattr(analyze_mod, "run_offline", original)
    second = _run(tmp_path, "--resume")
    assert second.exit_code == 0, second.output
    assert len(fake["server"].requests) == before
    assert old_snapshots[0].is_file()


def test_resume_reuses_reports_finalized_before_a_quota_stop(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = acquire_mod.finalize_reports
    finalized: list[str] = []

    def interrupted(run: Any, acquisition: Any) -> Any:
        query = run.client.query

        def limited(text: str, variables: Any = None, **kwargs: Any) -> Any:
            if finalized:
                raise c.BudgetExceeded("hourly quota reached")
            result = query(text, variables, **kwargs)
            finalized.append(variables["code"])
            return result

        run.client.query = limited
        return original(run, acquisition)

    monkeypatch.setattr(analyze_mod, "finalize_reports", interrupted)
    first = _run(tmp_path)
    assert first.exit_code == 3, first.output
    before = len(fake["server"].requests)
    monkeypatch.setattr(analyze_mod, "finalize_reports", original)
    second = _run(tmp_path, "--resume")
    assert second.exit_code == 0, second.output
    new_requests = fake["server"].requests[before:]
    assert new_requests
    assert all("NecropsyReport" in request["query"] for request in new_requests)
    assert all(request["variables"]["code"] != finalized[0] for request in new_requests)


def test_refused_context_can_be_corrected_without_a_resume(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    wrong = _run(tmp_path, "--faction", "Horde")
    assert wrong.exit_code == 1
    corrected = _run(tmp_path, "--faction", "Alliance")
    assert corrected.exit_code == 0, corrected.output


def test_interruption_saves_requests_and_cleans_up_the_activity_display(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    server: FakeWcl = fake["server"]
    interrupted = False

    def cancel(request: httpx.Request) -> httpx.Response:
        nonlocal interrupted
        if "NecropsyEvents" in json.loads(request.content)["query"]:
            interrupted = True
            raise KeyboardInterrupt
        return server(request)

    fake["server"] = cancel
    first = _run(tmp_path)
    assert interrupted and first.exit_code == 130, first.output
    assert "--resume" in first.output
    before = len(server.requests)
    fake["server"] = server
    second = _run(tmp_path, "--resume")
    assert second.exit_code == 0, second.output
    assert not any("NecropsySubject" in r["query"] for r in server.requests[before:])


# --outcome-json: real run outcomes classified for unattended runners.


def _outcome(tmp_path: Path, *args: str) -> tuple[Any, dict[str, Any]]:
    path = tmp_path / "outcome.json"
    result = _run(tmp_path, *args, "--outcome-json", str(path))
    return result, json.loads(path.read_text(encoding="utf-8"))


def _utc(value: str) -> datetime:
    when = datetime.fromisoformat(value)
    offset = when.utcoffset()
    assert offset is not None and offset.total_seconds() == 0
    return when


def test_a_complete_run_reports_none_with_its_snapshot(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    result, outcome = _outcome(tmp_path, "--name", "live")
    assert result.exit_code == 0 and outcome["exit_code"] == 0
    assert outcome["stop_class"] == "none" and outcome["incomplete_bosses"] == 0
    archive = Path(outcome["snapshot"]["archive"])
    assert archive.name == "live.zip" and len(outcome["snapshot"]["sha256"]) == 64
    _utc(outcome["reset_at_utc"])
    assert outcome["checkpoint_sha256"] is not None


def test_a_final_partial_without_a_stop_is_a_source_limit(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    fake["server"] = FakeWcl([Player(f"Ally{i}") for i in range(1, 7)], Player("Haplina"))
    result, outcome = _outcome(tmp_path, "--talent-tree", "Beast Mastery")
    assert result.exit_code == 4 and outcome["exit_code"] == 4
    assert outcome["stop_class"] == "source-limit" and outcome["incomplete_bosses"] == 1
    assert outcome["snapshot"] is not None


def test_a_rate_limit_during_acquisition_is_a_quota_reset_stop_with_its_reset_time(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context()
    assert context.partition is not None
    chosen = replace(context.partition, id=1)
    fake["context"] = replace(context, zone_id=2000, partition=chosen, partitions=(chosen,))
    server = EncounterWcl([Player(f"Ally{i}") for i in range(30)], Player("Haplina"))
    monkeypatch.setattr(acquire_mod, "boss_order", lambda zone="naxxramas": (50669,))

    def limited(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        variables = body["variables"]
        if "NecropsyEvents" in body["query"] and variables["code"] == "RHaplina":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "rateLimitData": {
                            "limitPerHour": 36000,
                            "pointsSpentThisHour": 36000,
                            "pointsResetIn": 20,
                        }
                    },
                    "errors": [{"message": "rate limit exceeded"}],
                },
            )
        return server(request)

    fake["server"] = limited
    result, outcome = _outcome(tmp_path, "--raid", "mc", "--partition", "1")
    assert result.exit_code == 4 and outcome["exit_code"] == 4
    assert outcome["stop_class"] == "quota-reset"
    _utc(outcome["reset_at_utc"])
    assert outcome["checkpoint_sha256"] is not None


def test_a_ranking_metadata_stop_keeps_the_reserve_and_says_so(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def stopped(*_: Any, **__: Any) -> None:
        raise acquire_mod.RunStopped("BudgetExceeded during leaderboard")

    monkeypatch.setattr(acquire_mod, "_acquire_rankings", stopped)
    monkeypatch.setattr(acquire_mod, "boss_order", lambda zone="naxxramas": (PATCHWERK, 51119))
    fake["server"] = FakeWcl([Player(f"Ally{i}") for i in range(1, 31)], Player("Haplina"))
    result, outcome = _outcome(tmp_path, "--spec", "Marksmanship", "--faction", "Alliance")
    assert result.exit_code == 4, result.output
    assert outcome["stop_class"] == "quota-reserve"


def test_a_finalization_stop_is_a_quota_reset_without_a_snapshot(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def stop(run: Any, acquisition: Any) -> Any:
        raise acquire_mod.RunStopped("BudgetExceeded during combined report")

    monkeypatch.setattr(analyze_mod, "finalize_reports", stop)
    result, outcome = _outcome(tmp_path)
    assert result.exit_code == 3 and outcome["exit_code"] == 3
    assert outcome["stop_class"] == "quota-reset" and outcome["snapshot"] is None
    _utc(outcome["reset_at_utc"])


def test_a_partition_choice_and_a_faction_mismatch_are_refusals(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    parts = (Partition(3, "Phase 6", True, True), Partition(4, "Phase 7", False, True))
    fake["context"] = replace(
        _context(), partition=None, partitions=parts, ambiguity="choose a partition"
    )
    result, outcome = _outcome(tmp_path)
    assert result.exit_code == 2 and outcome["stop_class"] == "refused"
    assert outcome["reset_at_utc"] is None
    fake.pop("context")
    result, outcome = _outcome(tmp_path, "--spec", "Marksmanship", "--faction", "Horde")
    assert result.exit_code == 1 and outcome["stop_class"] == "refused"


def test_a_sign_in_failure_is_auth(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_sign_in() -> Any:
        raise LoginNeeded("sign in again")

    monkeypatch.setattr(wcl_cli, "_tokens", no_sign_in)
    result, outcome = _outcome(tmp_path)
    assert result.exit_code == 1 and outcome["stop_class"] == "auth"


def test_a_server_failure_is_transient(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    fake["server"] = down
    monkeypatch.setattr(analyze_mod, "resolve", _resolve_through_client)
    result, outcome = _outcome(tmp_path)
    assert result.exit_code == 1 and outcome["stop_class"] == "transient", result.output


def _resolve_through_client(client: Any, ref: Any, *, partition: Any, endpoint: str) -> Any:
    client.query("query NecropsyProbe { rateLimitData { limitPerHour } }", endpoint=endpoint)
    raise AssertionError("the server failure must stop the run")


def test_an_unexpected_failure_is_recorded_as_an_error(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_: Any, **__: Any) -> Any:
        raise KeyError("unexpected")

    monkeypatch.setattr(analyze_mod, "acquire", broken)
    path = tmp_path / "outcome.json"
    result = _run(tmp_path, "--outcome-json", str(path))
    assert result.exit_code == 1 and isinstance(result.exception, KeyError)
    assert json.loads(path.read_text(encoding="utf-8"))["stop_class"] == "error"


def test_without_the_option_no_outcome_file_is_written(
    tmp_path: Path, fake: dict[str, Any]
) -> None:
    assert _run(tmp_path).exit_code == 0
    assert not list(tmp_path.glob("*.json"))


def test_quota_exhaustion_while_resolving_is_a_quota_reset_with_its_reset_time(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def exhausted(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": {
                    "rateLimitData": {
                        "limitPerHour": 36000,
                        "pointsSpentThisHour": 36000,
                        "pointsResetIn": 1800,
                    }
                },
                "errors": [{"message": "rate limit exceeded"}],
            },
        )

    fake["server"] = exhausted
    monkeypatch.setattr(analyze_mod, "resolve", _resolve_through_client)
    result, outcome = _outcome(tmp_path)
    assert result.exit_code == 1 and outcome["exit_code"] == 1
    assert outcome["stop_class"] == "quota-reset"
    clock = fake["client"].clock
    assert _utc(outcome["reset_at_utc"]) == clock.now() + timedelta(seconds=1800)


def test_a_report_failure_after_publication_records_the_saved_snapshot(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise OSError("disk full")

    monkeypatch.setattr(analyze_mod, "run_offline", broken)
    result, outcome = _outcome(tmp_path, "--name", "live")
    assert result.exit_code == 1 and outcome["stop_class"] == "error"
    archive = tmp_path / "out" / "snapshot" / "live.zip"
    assert Path(outcome["snapshot"]["archive"]) == archive
    assert outcome["snapshot"]["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()


def test_an_unreadable_checkpoint_never_changes_the_native_result(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path.read_bytes

    def guarded(self: Path) -> bytes:
        if self.name == "run.json" and self.parent.name == ".necropsy-run":
            raise PermissionError("denied")
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    path = tmp_path / "outcome.json"
    result = _run(tmp_path, "--outcome-json", str(path))
    assert result.exit_code == 0 and "could not write --outcome-json" in result.output
    assert not path.exists()


def test_a_failed_receipt_write_keeps_the_original_failure(
    tmp_path: Path, fake: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_: Any, **__: Any) -> Any:
        raise KeyError("unexpected")

    def unwritable(self: Path, *_: Any, **__: Any) -> int:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(analyze_mod, "acquire", broken)
    monkeypatch.setattr(Path, "write_text", unwritable)
    result = _run(tmp_path, "--outcome-json", str(tmp_path / "outcome.json"))
    assert result.exit_code == 1 and isinstance(result.exception, KeyError)
    assert not (tmp_path / "outcome.json").exists()
