"""The capture queue keeps only reviewed subjects that pass faction, identity and
metric checks, decides reuse per boss from saved snapshots, and never pays twice."""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
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
BOSSES = {"mc": {"1": "Lucifron", "2": "Magmadar"}}


def _snapshot(
    *, stopped: str | None = None, bosses: list[dict[str, Any]] | None = None, **subject: Any
) -> dict[str, Any]:
    return {
        "subject": {
            "class_id": 4,
            "ranking_category": "Fire",
            "ranking_metric": "dps",
            "faction": "Horde",
        }
        | subject,
        "zone": {"id": 2000, "partition": 1},
        "stopped": stopped,
        "bosses": bosses or [],
    }


def _boss(encounter: int, usable: int, complete: int, target: int = 5) -> dict[str, Any]:
    return {
        "encounter_id": encounter,
        "coverage": {"target": target, "usable_deep": usable, "complete": False, "reasons": ["x"]},
        "cohort": [{"status": "complete"}] * complete + [{"status": "partial"}],
        "subject": {"status": "unknown"},
    }


def _register(*encounters: int) -> dict[str, Any]:
    return {
        "records": [
            {
                "cell_id": f"mc/{e}/4/Fire/dps/Horde",
                "real_actor_source": {"archive": {"path": "a.zip", "sha256": "sha-a"}},
            }
            for e in encounters
        ]
    }


PROVENANCE = {"fixtures": [{"sha256": "sha-a", "url": "https://x.invalid/seed", "label": "a"}]}


def _decide(
    register: dict[str, Any], snapshot: dict[str, Any], provenance: dict[str, Any] = PROVENANCE
) -> dict[str, Any]:
    result = cq.dispositions([RUN], BOSSES, register, provenance, lambda _: snapshot)
    return result[RUN["entry_id"]]


def test_every_registered_boss_makes_a_run_capture_ready() -> None:
    assert _decide(_register(1, 2), _snapshot())["state"] == "capture-ready"


def test_a_complete_cohort_in_a_finished_snapshot_is_offline_reuse_with_its_limits() -> None:
    decided = _decide(_register(1), _snapshot(bosses=[_boss(2, 5, 5)]))
    assert decided["state"] == "capture-ready"
    reuse = decided["bosses"][1]
    assert (reuse["disposition"], reuse["locator"], reuse["limitations"]) == (
        "offline-reuse",
        "necropsy-snapshot.json:bosses[0]",
        ["x"],
    )


@pytest.mark.parametrize(
    "snapshot",
    [
        _snapshot(bosses=[_boss(2, 4, 4)]),
        _snapshot(bosses=[_boss(2, 5, 3)]),
        _snapshot(bosses=[_boss(2, 0, 0, target=0)]),
        _snapshot(stopped="BudgetExceeded", bosses=[_boss(2, 5, 5)]),
    ],
)
def test_an_incomplete_or_stopped_cohort_still_needs_capture(snapshot: dict[str, Any]) -> None:
    decided = _decide(_register(1), snapshot)
    assert (decided["state"], decided["needs_capture"]) == ("needs-capture", ["Magmadar"])


def test_missing_provenance_or_a_mismatched_identity_is_never_trusted() -> None:
    assert _decide(_register(1, 2), _snapshot(), {"fixtures": []})["state"] == "needs-capture"
    wrong = _decide(_register(1, 2), _snapshot(ranking_metric="hps"))
    assert wrong["needs_capture"] == ["Lucifron", "Magmadar"]
    assert "subject.ranking_metric 'hps' != 'dps'" in wrong["bosses"][0]["why"]


def test_runs_without_registered_captures_are_not_decided() -> None:
    assert cq.dispositions([RUN], BOSSES, {"records": []}, PROVENANCE, lambda _: {}) == {}


def _report_zip(path: Path, role: str) -> None:
    report = {
        "report": {
            "code": "R1",
            "visibility": "public",
            "zone": {"id": 2000},
            "rankings": {
                "data": [
                    {
                        "encounter": {"id": 1},
                        "guild": {"faction": 1},
                        "roles": {
                            role: {
                                "characters": [
                                    {
                                        "id": 7,
                                        "name": "N",
                                        "class": "Druid",
                                        "spec": "Balance",
                                        "server": {"name": "S", "region": "EU"},
                                    }
                                ]
                            }
                        },
                    }
                ]
            },
        }
    }
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("reports/R1/fight_1.json", json.dumps(report))


@pytest.mark.parametrize(("role", "dps", "hps"), [("dps", 1, 0), ("healers", 0, 1)])
def test_mining_uses_only_the_role_that_carries_each_metric(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str, dps: int, hps: int
) -> None:
    monkeypatch.setattr(cq, "ROOT", tmp_path)
    _report_zip(tmp_path / "r.zip", role)
    balance = RUN | {"class_id": 2, "class": "Druid", "category": "Balance"}
    runs = [balance | {"entry_id": m, "metric": m} for m in ("dps", "hps")]
    mined = cq.mine(tmp_path, runs)
    assert (len(mined["dps"]), len(mined["hps"])) == (dps, hps)


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


def test_the_pool_puts_matching_earlier_subjects_first_then_faction_lean_and_skips_excluded() -> (
    None
):
    state = {
        "archives": [
            {"url": "https://x.invalid/seed", "path": "a", "sha256": "s", "identity_problems": []},
            {
                "url": "https://x.invalid/bad",
                "path": "b",
                "sha256": "t",
                "identity_problems": ["x"],
            },
        ]
    }
    mined = [
        _mined(1, 9, {"Alliance": 3}),
        _mined(2, 2, {"Horde": 1}),
        _mined(3, 5, {}),
        _mined(4, 9, {"Horde": 4}),
    ]
    pool = cq.rank_pool(RUN, mined, state, excluded={"4"})
    assert [c["url"] for c in pool] == [
        "https://x.invalid/seed",
        f"{cq.SITE}/character/id/2?zone=2000",
        f"{cq.SITE}/character/id/1?zone=2000",
        f"{cq.SITE}/character/id/3?zone=2000",
    ]


GOOD = {"faction": "Horde", "id": "7", "partition": "S0"}


@pytest.mark.parametrize(
    ("fields", "code", "accepted"),
    [
        (GOOD, 0, True),
        (GOOD | {"faction": "unknown"}, 0, False),
        (GOOD | {"faction": "Alliance"}, 0, False),
        (GOOD | {"needs a choice": "choose a partition"}, 0, False),
        (GOOD | {"partition": "unknown"}, 0, False),
        (GOOD | {"id": "8"}, 0, False),
        (GOOD, 1, False),
    ],
)
def test_only_the_same_character_with_an_observed_matching_faction_passes(
    fields: dict[str, str], code: int, accepted: bool
) -> None:
    assert cq.verdict(fields, code, "Horde", 7)[0] is accepted


def _ranked(**overrides: Any) -> dict[str, Any]:
    row = {"encounter": "Lucifron", "totalKills": 3, "bestAmount": 812.5, "spec": "Fire"}
    data = {"metric": "dps", "zone": 2000, "partition": 1, "rankings": [row]}
    for key, value in overrides.items():
        (row if key in row else data)[key] = value
    return {"rankings": data}


@pytest.mark.parametrize(
    ("answer", "accepted"),
    [
        (_ranked(), True),
        (_ranked(metric="hps"), False),
        (_ranked(partition=2), False),
        (_ranked(zone=2002), False),
        (_ranked(bestAmount=0), False),
        (_ranked(totalKills=0), False),
        (_ranked(spec="Frost"), False),
        ({"error": "WclError: boom"}, False),
    ],
)
def test_the_metric_gate_needs_a_positive_amount_for_this_spec_metric_and_partition(
    answer: dict[str, Any], accepted: bool
) -> None:
    assert cq.metric_verdict(answer, RUN)[0] is accepted


def test_resolve_output_is_parsed_line_by_line() -> None:
    out = "character:      Nago\nfaction:        Horde\nzone:           Molten Core\n"
    assert cq.parse_resolve(out) == {"character": "Nago", "faction": "Horde", "zone": "Molten Core"}


def _plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pool: list[dict[str, Any]]) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps({"entries": [RUN | {"queued": True, "pool": pool}]}), encoding="utf-8"
    )
    for name, path in {
        "PLAN": plan,
        "RESOLUTIONS": tmp_path / "resolutions.json",
        "RANKINGS": tmp_path / "rankings.json",
        "LEADERBOARDS": tmp_path / "leaderboards.json",
        "QUEUE": tmp_path / "queue.json",
        "ROOT": tmp_path,
    }.items():
        monkeypatch.setattr(cq, name, path)


def _pool(*ids: int) -> list[dict[str, Any]]:
    return [{"id": i, "url": f"https://x.invalid/{i}", "origin": "test"} for i in ids]


def _resolver(horde: str) -> Any:
    def resolve(url: str) -> tuple[int, str, str]:
        cid = url.rsplit("/", 1)[1]
        faction = "Horde" if cid in horde else "unknown"
        return 0, f"id: {cid}\nfaction: {faction}\npartition: S0\n", ""

    return resolve


def _ranker(ranked: str, calls: list[int]) -> Any:
    def rank(cid: int, item: dict[str, Any]) -> dict[str, Any]:
        calls.append(cid)
        answer: dict[str, Any] = _ranked(bestAmount=500 if str(cid) in ranked else 0)
        return dict(answer["rankings"])

    return rank


def test_resolve_spends_on_metric_only_after_faction_and_never_pays_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _plan(tmp_path, monkeypatch, _pool(1, 2, 3, 4))
    ranked: list[int] = []
    cq.resolve(3, resolver=_resolver("134"), ranker=_ranker("34", ranked))
    assert ranked == [1]
    cq.resolve(50, resolver=_resolver("134"), ranker=_ranker("34", ranked))
    cq.resolve(50, resolver=_resolver("134"), ranker=_ranker("34", ranked))
    assert ranked == [1, 3, 4]
    assert cq.emit() == 0
    _, entries = cr.load_queue(tmp_path / "queue.json")
    assert entries[0].candidates == ("https://x.invalid/3", "https://x.invalid/4")


def test_an_earlier_subject_of_the_same_configuration_needs_no_ranking_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed = {"url": "https://x.invalid/9", "origin": "earlier", "metric_evidence": {"archive": "a"}}
    _plan(tmp_path, monkeypatch, [seed])
    ranked: list[int] = []
    cq.resolve(5, resolver=_resolver("9"), ranker=_ranker("", ranked))
    assert ranked == []
    assert cq.emit() == 0


def test_emit_refuses_and_keeps_the_previous_queue_while_a_run_is_unfilled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _plan(tmp_path, monkeypatch, _pool(1))
    previous = b'{"version": 1, "entries": []}\n'
    (tmp_path / "queue.json").write_bytes(previous)
    cq.resolve(5, resolver=_resolver("1"), ranker=_ranker("", []))
    assert cq.emit() == 1
    assert (tmp_path / "queue.json").read_bytes() == previous


def test_the_committed_queue_snapshot_is_intact() -> None:
    # Strict freshness (`verify`) fails once a cell closes while a queue is live;
    # the committed queue must still be the one emitted, with intact pins.
    assert cq.verify_snapshot() == 0


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, check=True, text=True)
    return done.stdout.strip()


def _commit(root: Path, files: dict[str, bytes]) -> str:
    for path, data in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_bytes(data)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "c")
    return _git(root, "rev-parse", "HEAD")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _emit(root: Path, coverage: bytes, cache: bytes) -> dict[str, bytes]:
    plan = json.dumps({"inputs": {"coverage.json": _sha(coverage)}}).encode()
    queue = json.dumps({"pins": {"plan.json": _sha(plan), "cache.json": _sha(cache)}}).encode()
    return {"coverage.json": coverage, "cache.json": cache, "plan.json": plan, "queue.json": queue}


@pytest.fixture
def emitted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "config", "core.autocrlf", "false")
    _commit(tmp_path, _emit(tmp_path, b"cov1\n", b"cache1\n"))
    for name, path in {
        "ROOT": tmp_path,
        "PLAN": tmp_path / "plan.json",
        "QUEUE": tmp_path / "queue.json",
    }.items():
        monkeypatch.setattr(cq, name, path)
    return tmp_path


def test_a_later_coverage_change_ages_the_snapshot_but_fails_strict_freshness(
    emitted: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(emitted, {"coverage.json": b"cov2\n"})
    assert cq.verify_snapshot() == 0
    assert "coverage.json: changed since emit" in capsys.readouterr().out
    assert cq.verify() == 1


@pytest.mark.parametrize(
    "drift",
    [
        {"queue.json": b"{}\n"},
        {"cache.json": b"cache2\n"},
        {"plan.json": b'{"inputs": {"coverage.json": "' + b"0" * 64 + b'"}}'},
    ],
)
def test_queue_or_direct_artifact_drift_fails_the_snapshot(
    emitted: Path, drift: dict[str, bytes]
) -> None:
    _commit(emitted, drift)
    assert cq.verify_snapshot() == 1


def test_an_uncommitted_direct_artifact_edit_fails_the_snapshot(emitted: Path) -> None:
    (emitted / "cache.json").write_bytes(b"edited\n")
    assert cq.verify_snapshot() == 1


@pytest.mark.parametrize(
    "plan",
    [
        b'{"inputs": {"coverage.json": "' + b"0" * 64 + b'"}}',
        b'{"inputs": {"coverage.json": "short"}}',
        b'{"inputs": {}}',
        b"not json",
    ],
)
def test_corrupt_emit_time_pins_fail_closed(emitted: Path, plan: bytes) -> None:
    queue = json.dumps({"pins": {"plan.json": _sha(plan), "cache.json": _sha(b"cache1\n")}})
    _commit(emitted, {"plan.json": plan, "queue.json": queue.encode()})
    assert cq.verify_snapshot() == 1


def test_a_pinned_file_missing_at_the_emit_commit_fails_closed(emitted: Path) -> None:
    queue = json.dumps(
        {"pins": {"plan.json": _sha((emitted / "plan.json").read_bytes()), "absent.json": "0" * 64}}
    )
    _commit(emitted, {"queue.json": queue.encode()})
    assert cq.verify_snapshot() == 1


def test_no_queue_history_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    _commit(tmp_path, {"other.txt": b"x\n"})
    monkeypatch.setattr(cq, "ROOT", tmp_path)
    monkeypatch.setattr(cq, "PLAN", tmp_path / "plan.json")
    monkeypatch.setattr(cq, "QUEUE", tmp_path / "queue.json")
    assert cq.verify_snapshot() == 1


def test_a_new_emit_is_checked_at_its_own_commit(
    emitted: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(emitted, {"coverage.json": b"cov2\n"})
    second = _commit(emitted, _emit(emitted, b"cov2\n", b"cache1\n"))
    assert cq.verify_snapshot() == 0
    out = capsys.readouterr().out
    assert f"intact at emit {second[:12]}" in out
    assert "changed since emit" not in out


def test_a_quota_or_network_failure_stops_the_run_and_caches_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _plan(tmp_path, monkeypatch, _pool(1, 2))

    def broken(*_: Any) -> Any:
        raise TimeoutError("quota")

    assert cq.resolve(5, resolver=broken, ranker=_ranker("1", [])) == 2
    assert not (tmp_path / "resolutions.json").exists()
    assert cq.resolve(5, resolver=_resolver("1"), ranker=broken) == 2
    assert not (tmp_path / "rankings.json").exists()


def test_leaderboard_rows_become_name_urls_for_ascii_us_eu_realms_with_an_amount() -> None:
    rows = [
        {"name": "Xavíus", "server": "Pyrewood Village", "region": "EU", "amount": 312.3},
        {"name": "Zero", "server": "Firemaw", "region": "EU", "amount": 0},
        {"name": "Far", "server": "哈霍兰", "region": "CN", "amount": 200},
        {"name": "Mine", "server": "Firemaw", "region": "EU", "amount": 90},
    ]
    boards = {cq.leaderboard_key(RUN, "1"): rows}
    pool = cq.leaderboard_pool(RUN, {"1": "Lucifron"}, boards, {"eu/firemaw/mine"})
    assert [c["url"] for c in pool] == [
        f"{cq.SITE}/character/eu/pyrewood-village/Xav%C3%ADus?zone=2000"
    ]
    assert pool[0]["evidence"] == {"boss": "Lucifron", "amount": 312.3, "page": 1}
