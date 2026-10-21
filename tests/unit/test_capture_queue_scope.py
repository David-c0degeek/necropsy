"""A scoped queue cannot consume parked work or mistake actor evidence for context."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from scripts import capture_queue as cq
from tests.unit.test_capture_queue import (
    BOSSES,
    PROVENANCE,
    RUN,
    _boss,
    _commit,
    _git,
    _register,
    _report_zip,
    _sha,
    _snapshot,
)


def test_default_and_explicit_universes_do_not_mix_parked_and_new_raids() -> None:
    legacy, legacy_bosses = cq.universe()
    naxx, naxx_bosses = cq.universe(raids=("naxxramas",))
    assert len(legacy) == 102
    assert set(legacy_bosses) == {"mc", "bwl", "aq40"}
    assert len(naxx) == 34
    assert len(naxx_bosses["naxxramas"]) == 15
    assert all(r["raid"] == "naxxramas" and r["zone"] == 2006 for r in naxx)
    assert {r["entry_id"] for r in legacy}.isdisjoint(r["entry_id"] for r in naxx)
    with pytest.raises(ValueError, match="absent from matrix"):
        cq.universe(raids=("unknown",))


def test_scoped_paths_require_all_inputs_and_cannot_overwrite_parked_artifacts() -> None:
    with pytest.raises(ValueError, match="together"):
        cq.queue_context("naxxramas")
    with pytest.raises(ValueError, match="unknown raid"):
        cq.queue_context("unknown", cq.ROOT / "workspace/new", cq.ROOT / "workspace/q.json")
    with pytest.raises(ValueError, match="separate"):
        cq.queue_context("naxxramas", cq.RESEARCH, cq.ROOT / "workspace/q.json")
    with pytest.raises(ValueError, match="separate"):
        cq.queue_context("naxxramas", cq.ROOT / "workspace/new", cq.QUEUE)
    ctx = cq.queue_context("naxxramas", Path("workspace/new"), Path("workspace/q.json"))
    assert ctx.plan.is_absolute() and ctx.queue.is_absolute()
    assert cq.queue_context().queue == cq.QUEUE


def test_other_raid_records_are_ignored_before_configuration_lookup() -> None:
    record = {"cell_id": "naxxramas/51118/invalid", "real_actor_source": {"archive": {}}}
    assert cq.dispositions([RUN], BOSSES, {"records": [record]}, PROVENANCE, lambda _: {}) == {}
    record["cell_id"] = "mc/1/invalid"
    with pytest.raises(KeyError):
        cq.dispositions([RUN], BOSSES, {"records": [record]}, PROVENANCE, lambda _: {})


def test_registered_actor_and_complete_cohort_do_not_replace_encounter_coverage() -> None:
    result = cq.dispositions(
        [RUN],
        BOSSES,
        _register(1),
        PROVENANCE,
        lambda _: _snapshot(bosses=[_boss(2, 5, 5)]),
        lambda _p, _h: set(),
    )[RUN["entry_id"]]
    assert result["state"] == "needs-capture"
    assert result["needs_capture"] == ["Lucifron", "Magmadar"]
    assert all("v2" in b["why"][-1] for b in result["bosses"])
    json.dumps(result)  # Dispositions are persisted in the plan.


def test_verified_scope_for_one_boss_does_not_suppress_another() -> None:
    result = cq.dispositions(
        [RUN],
        BOSSES,
        _register(1, 2),
        PROVENANCE,
        lambda _: _snapshot(),
        lambda _p, _h: {1},
    )[RUN["entry_id"]]
    assert result["needs_capture"] == ["Magmadar"]
    assert result["bosses"][0]["disposition"] == "registered"


def test_owner_exclusion_also_applies_to_previously_captured_subjects() -> None:
    url = cq.SITE + "/character/eu/firemaw/Haplina?zone=2006"
    state = {"archives": [{"url": url, "identity_problems": [], "path": "a", "sha256": "h"}]}
    assert cq.rank_pool(RUN, [], state, {"eu/firemaw/haplina"}) == []


@pytest.mark.parametrize(
    "mutation", ["other_raid", "missing", "duplicate", "owner", "candidate_duplicate"]
)
def test_scoped_plan_rejects_contamination_before_live_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    ctx = cq.queue_context("naxxramas", cq.ROOT / "workspace/new", cq.ROOT / "workspace/q.json")
    ctx = replace(ctx, plan=tmp_path / "plan.json", excluded=tmp_path / "excluded.json")
    ctx.excluded.write_text(json.dumps({"characters": ["eu/firemaw/haplina"]}))
    runs, _ = cq.universe(raids=ctx.raids)
    entries = [r | {"queued": True, "pool": []} for r in runs]
    if mutation == "other_raid":
        entries[0]["raid"] = "mc"
    elif mutation == "missing":
        entries.pop()
    elif mutation == "duplicate":
        entries[-1] = entries[0]
    else:
        url = cq.SITE + "/character/eu/firemaw/Haplina?zone=2006"
        entries[0]["pool"] = [{"url": url}] * (2 if mutation == "candidate_duplicate" else 1)
    ctx.plan.write_text(json.dumps({"raids": ["naxxramas"], "entries": entries}))

    def forbidden(*_: Any) -> Any:
        pytest.fail("contaminated plan reached a live resolver")

    with pytest.raises(ValueError):
        cq.resolve(10, resolver=forbidden, ranker=forbidden, context=ctx)


@pytest.mark.parametrize("amount", [0, -1, None])
def test_mining_does_not_treat_an_empty_metric_rank_as_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, amount: int | None
) -> None:
    import zipfile

    monkeypatch.setattr(cq, "ROOT", tmp_path)
    path = tmp_path / "r.zip"
    _report_zip(path, "dps")
    with zipfile.ZipFile(path) as bundle:
        report = json.loads(bundle.read("reports/R1/fight_1.json"))
    report["report"]["rankings"]["data"][0]["roles"]["dps"]["characters"][0]["amount"] = amount
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("reports/R1/fight_1.json", json.dumps(report))
    run = RUN | {"class_id": 2, "class": "Druid", "category": "Balance"}
    assert cq.mine(tmp_path, [run])[run["entry_id"]] == []


def test_nested_report_wrappers_and_duplicate_bundles_keep_one_witness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import zipfile

    monkeypatch.setattr(cq, "ROOT", tmp_path)
    path = tmp_path / "r.zip"
    _report_zip(path, "dps")
    with zipfile.ZipFile(path) as bundle:
        report = json.loads(bundle.read("reports/R1/fight_1.json"))
    with zipfile.ZipFile(path, "w") as bundle:
        for fight in (1, 2):
            bundle.writestr(f"reports/R1/fight_{fight}.json", json.dumps({"reportData": report}))
    run = RUN | {"class_id": 2, "class": "Druid", "category": "Balance"}
    candidate = cq.mine((path, path), [run])[run["entry_id"]][0]
    assert candidate["faction_hints"] == {"Horde": 1}
    assert candidate["reports"] == 1
    assert candidate["evidence"]["locator"].startswith("reportData.report.rankings")


def test_scoped_resolve_emit_and_both_verifiers_use_the_same_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = cq.queue_context("naxxramas", cq.ROOT / "workspace/new", cq.ROOT / "workspace/q.json")
    ctx = replace(
        ctx,
        plan=tmp_path / "plan.json",
        resolutions=tmp_path / "resolutions.json",
        rankings=tmp_path / "rankings.json",
        leaderboards=tmp_path / "boards.json",
        excluded=tmp_path / "excluded.json",
        queue=tmp_path / "queue.json",
    )
    runs, _ = cq.universe(raids=ctx.raids)
    entries = [
        r
        | {
            "queued": True,
            "pool": [{"id": i + 1, "url": f"https://x.invalid/{i + 1}", "origin": "test"}],
        }
        for i, r in enumerate(runs)
    ]
    ctx.excluded.write_bytes(b'{"characters": []}\n')
    ctx.plan.write_text(
        json.dumps(
            {
                "raids": ["naxxramas"],
                "inputs": {"excluded.json": _sha(ctx.excluded.read_bytes())},
                "entries": entries,
            }
        ),
        encoding="utf-8",
    )
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "config", "core.autocrlf", "false")
    monkeypatch.setattr(cq, "ROOT", tmp_path)
    calls: list[str] = []

    def resolve(url: str) -> tuple[int, str, str]:
        cid = int(url.rsplit("/", 1)[1])
        calls.append(url)
        return 0, f"id: {cid}\nfaction: {runs[cid - 1]['faction']}\npartition: S0\n", ""

    def rank(cid: int, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "metric": item["metric"],
            "zone": 2006,
            "partition": 1,
            "rankings": [
                {
                    "encounter": "Patchwerk",
                    "totalKills": 1,
                    "bestAmount": 100,
                    "spec": item["category"],
                }
            ],
        }

    assert cq.resolve(68, resolver=resolve, ranker=rank, context=ctx) == 0
    assert len(calls) == 34
    assert cq.resolve(68, resolver=resolve, ranker=rank, context=ctx) == 0
    assert len(calls) == 34  # Cached reruns do not query again.
    assert cq.emit(ctx) == 0
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "capture")
    assert cq.verify(context=ctx) == 0
    assert cq.verify_snapshot(context=ctx) == 0
    queue = json.loads(ctx.queue.read_bytes())
    queue["entries"][0]["raid"] = "mc"
    _commit(tmp_path, {"queue.json": json.dumps(queue).encode()})
    assert cq.verify_snapshot(context=ctx) == 1


def test_lfs_pins_verify_hydrated_bytes_instead_of_pointer_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    body = b"hydrated archive bytes"
    pointer = (
        f"version https://git-lfs.github.com/spec/v1\noid sha256:{_sha(body)}\nsize {len(body)}\n"
    ).encode()
    plan = json.dumps({"inputs": {"raw.zip": _sha(body)}}).encode()
    queue = json.dumps({"pins": {"plan.json": _sha(plan)}}).encode()
    _commit(tmp_path, {"raw.zip": pointer, "plan.json": plan, "queue.json": queue})
    monkeypatch.setattr(cq, "ROOT", tmp_path)
    monkeypatch.setattr(cq, "PLAN", tmp_path / "plan.json")
    monkeypatch.setattr(cq, "QUEUE", tmp_path / "queue.json")
    (tmp_path / "raw.zip").write_bytes(body)
    assert cq.verify() == 0
    (tmp_path / "raw.zip").write_bytes(b"changed archive")
    assert cq.verify() == 1


@pytest.mark.parametrize("mutation", ["negative_fight", "wrong_partition", "different_encounter"])
def test_mining_requires_a_matching_positive_partition_one_kill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    import zipfile

    monkeypatch.setattr(cq, "ROOT", tmp_path)
    path = tmp_path / "r.zip"
    _report_zip(path, "dps")
    with zipfile.ZipFile(path) as bundle:
        report = json.loads(bundle.read("reports/R1/fight_1.json"))
    ranking = report["report"]["rankings"]["data"][0]
    if mutation == "negative_fight":
        ranking["fightID"] = -1
    elif mutation == "wrong_partition":
        ranking["partition"] = 2
    else:
        ranking["encounter"]["id"] = 2
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("reports/R1/fight_1.json", json.dumps(report))
    run = RUN | {"class_id": 2, "class": "Druid", "category": "Balance"}
    assert cq.mine(path, [run])[run["entry_id"]] == []
