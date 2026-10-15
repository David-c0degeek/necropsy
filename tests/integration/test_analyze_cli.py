"""`necropsy analyze` end to end against a fake Warcraft Logs server.

SYNTHETIC responses (tests/unit/test_wcl_acquire.py); a fake token provider, never
the OS credential store; no network.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
import typer
from typer.testing import CliRunner

from necropsy.cli import app
from necropsy.wcl import acquire as acquire_mod
from necropsy.wcl import analyze as analyze_mod
from necropsy.wcl import cli as wcl_cli
from necropsy.wcl import client as c
from necropsy.wcl.context import Partition
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _context
from tests.wcl_fakes import FakeClock

URL = "https://vanilla.warcraftlogs.com/character/id/86583560"
SECRET = "sentinel-secret-token-value"


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"server": None, "tokens": 0, "endpoints": []}
    monkeypatch.setattr(acquire_mod, "boss_order", lambda: (PATCHWERK,))

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
    assert "No personal Marksmanship encounter" in page and "Ally1" in page
    assert '<details class="overall-comparison">' in page


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
    result = _run(tmp_path)
    assert result.exit_code == 4, result.output
    assert "Patchwerk: partial" in result.output and (tmp_path / "out" / "report.html").exists()


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
