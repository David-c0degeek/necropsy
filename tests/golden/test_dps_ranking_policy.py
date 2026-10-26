"""The scoped Naxx DPS policies are re-proved from raw archive bytes.

Expected values come from the policy evidence; every amount is re-enumerated
here from raw pages with exact rational arithmetic, without analyzer, metric or
freezer code. Each wrong policy must fail where the row exercises it.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from necropsy.rules import load_rules
from scripts.check_raid_coverage import NO_PRODUCTION_EXCLUSIONS, POLICY_CONDITIONS

pytestmark = pytest.mark.golden
REPO = Path(__file__).parents[2]
ZONE = load_rules("classic_era", "zones/naxxramas")
POLICIES = {
    p["rule"]: p
    for p in ZONE["ranking_metric_policies"]
    if p["scope"]["metric"] == "dps" and p["rule"].startswith("naxx-")
}
MINIMUM_ADMITTED = 3
# The only admitted row with positive owned-unit damage: Frelserboom's Servant of
# Weldon Barov (actor 81) on Maexxna, so dropped owned damage is provable only here.
OWNED_WITNESS = ("g8f9nGyRTpNLMqWm", 9, 442)


def _evidence(rule: str) -> dict[str, Any]:
    evidence: dict[str, Any] = json.loads((REPO / POLICIES[rule]["evidence"]).read_bytes())
    return evidence


ALL_ROWS = [(rule, row) for rule in POLICIES for row in _evidence(rule)["rows"]]


def _encounter(encounter_id: int) -> dict[str, Any]:
    return next(e for e in ZONE["encounters"] if e["id"] == encounter_id)


def _read(z: zipfile.ZipFile, name: str) -> Any:
    # Published numbers stay text so their declared precision survives.
    return json.loads(z.read(name), parse_float=str)


def _key(event: dict[str, Any]) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"))


def _stream_pages(
    z: zipfile.ZipFile,
    snapshot: dict[str, Any],
    fight: dict[str, Any],
    report: dict[str, Any],
    stream: dict[str, Any],
) -> list[dict[str, Any]]:
    """Pages bound to the snapshot's stream identity, in order, with a closed chain."""
    folder = f"events/{report['code']}/fight_{fight['id']}/{stream['role']}_{stream['actor_id']}_"
    names = sorted(
        n
        for n in z.namelist()
        if n.startswith(folder)
        and re.fullmatch(rf"{re.escape(stream['direction'])}_\d+\.json", n.rsplit("/", 1)[-1])
    )
    identity = stream["identity"]
    assert identity["start_time"] == fight["startTime"] and identity["end_time"] == fight["endTime"]
    assert identity["revision"] == report["revision"] and identity["code"] == report["code"]
    assert names and stream["pages"] == [hashlib.sha256(z.read(n)).hexdigest() for n in names]
    rows: list[dict[str, Any]] = []
    floor = fight["startTime"]
    for index, name in enumerate(names):
        page = _read(z, name)
        last = index == len(names) - 1
        assert (page["nextPageTimestamp"] is None) is last, name
        assert all(floor <= e["timestamp"] <= fight["endTime"] for e in page["data"]), name
        if not last:
            floor = page["nextPageTimestamp"]
        rows.extend(page["data"])
    return rows


def _consistent(total: int, duration: int, published: str) -> bool:
    decimals = len(published.split(".")[1]) if "." in published else 0
    return abs(Fraction(total) * 1000 / duration - Fraction(published)) < Fraction(1, 10**decimals)


def _owned_units(
    listing: Any, fight: dict[str, Any], actors: dict[int, dict[str, Any]], actor: int
) -> set[int]:
    """The actor's owned units: an explicit listing that both catalogs confirm.

    A missing listing is unknown ownership, never an empty one; an empty list is
    accepted only when it is present and every catalog agrees.
    """
    assert isinstance(listing, list), "missing explicit owned-unit listing"
    ids = []
    for unit in listing:
        assert type(unit.get("id")) is int and unit["id"] > 0, unit
        assert type(unit.get("petOwner")) is int and unit["petOwner"] == actor, unit
        assert actors[unit["id"]].get("petOwner") == actor, unit
        assert actors[unit["id"]].get("gameID") == unit.get("gameID"), unit
        ids.append(unit["id"])
    assert len(ids) == len(set(ids)), "duplicate owned-unit listing"
    assert all(type(p.get("petOwner")) is int for p in fight["friendlyPets"])
    in_fight = {p["id"] for p in fight["friendlyPets"] if p["petOwner"] == actor}
    in_catalog = {a for a, v in actors.items() if v.get("petOwner") == actor}
    assert set(ids) == in_fight == in_catalog, "owned-unit listings disagree"
    return set(ids)


def _measure(archive: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    path = REPO / archive["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == archive["sha256"]
    with zipfile.ZipFile(path) as z:
        snapshot = json.loads(z.read("necropsy-snapshot.json"))
        report = _read(z, f"reports/{row['report']}/bundle.json")["reportData"]["report"]
        fight = next(f for f in report["fights"] if f["id"] == row["fight"])
        actor = row["actor"]
        actors = {a["id"]: a for a in report["masterData"]["actors"]}
        folders = {
            n.rsplit("/", 1)[0]
            for n in z.namelist()
            if n.startswith(f"events/{row['report']}/fight_{row['fight']}/player_{actor}_")
        }
        assert len(folders) == 1, folders
        listing_name = f"{folders.pop()}/pets.json"
        listing = _read(z, listing_name) if listing_name in z.namelist() else None
        owned = _owned_units(listing, fight, actors, actor)
        details = [
            p
            for role in report["playerDetails"]["data"]["playerDetails"].values()
            for p in role
            if p["id"] == actor
        ]
        known = {actor} | owned
        observations = []
        for stream in snapshot["streams"]:
            if (stream["report"], stream["fight"]) != (row["report"], row["fight"]):
                continue
            if stream["actor_id"] not in known:
                continue
            counter: Counter[str] = Counter()
            for event in _stream_pages(z, snapshot, fight, report, stream):
                if event.get("type") != "damage" or event.get("sourceID") != stream["actor_id"]:
                    continue
                assert type(event["targetID"]) is int and type(event["amount"]) is int
                assert event["amount"] >= 0
                counter[_key(event)] += 1
            observations.append(counter)
        directions = {
            (s["actor_id"], s["direction"])
            for s in snapshot["streams"]
            if (s["report"], s["fight"]) == (row["report"], row["fight"]) and s["actor_id"] in known
        }
        assert directions == {(a, d) for a in known for d in ("source", "target")}
        merged: Counter[str] = Counter()
        for counter in observations:
            merged |= counter  # maximum multiplicity: a row seen in both directions counts once
        events = [(json.loads(k), n) for k, n in merged.items()]
        board = _read(z, row["leaderboard_member"])
        page = next(p for p in board["pages"] if p["page"] == row["page"])
        published = page["characterRankings"]["rankings"][row["row"]]
    by_target: Counter[int] = Counter()
    by_source: Counter[int] = Counter()
    for event, n in events:
        by_source[event["sourceID"]] += event["amount"] * n
        if event["targetID"] not in known:
            by_target[actors[event["targetID"]].get("gameID")] += event["amount"] * n
    raw = sum(by_source.values())
    ranked = sum(by_target.values())
    return {
        "details": details,
        "owned": sorted(owned),
        "totals": {"raw": raw, "self": raw - ranked, "excluded": 0, "ranked": ranked},
        "owned_damage": sum(v for s, v in by_source.items() if s != actor),
        "by_target": by_target,
        "duration_ms": fight["endTime"] - fight["startTime"],
        "published": published,
    }


@pytest.mark.parametrize("rule", list(POLICIES))
def test_policy_scope_matches_its_frozen_evidence(rule: str) -> None:
    policy = POLICIES[rule]
    evidence = _evidence(rule)
    assert evidence["rule"] == rule and evidence["scope"] == policy["scope"]
    assert set(policy["conditions"]) == POLICY_CONDITIONS["dps"]
    # The no-exclusions condition holds in the production rules this policy sits beside.
    assert NO_PRODUCTION_EXCLUSIONS in policy["conditions"]
    assert not _encounter(policy["scope"]["encounter_id"]).get("ranking_exclusions")
    rows, refusals = evidence["rows"], evidence["refusals"]
    counts = evidence["dispositions"]
    assert counts["n"] == counts["k"] + counts["r"] + counts["c"]
    assert (counts["k"], counts["r"], counts["c"]) == (len(rows), len(refusals), 0)
    assert counts["k"] >= MINIMUM_ADMITTED
    assert any(r["kind"] != "subject" for r in rows)
    assert len({(r["report"], r["fight"], r["actor"]) for r in rows}) == len(rows)
    assert all(r["purpose"] == "policy-scope" for r in rows)
    for r in [*rows, *refusals]:
        assert (r["faction"], r["faction_status"]) == (policy["scope"]["faction"], "observed")
    assert f"{counts['k']} admitted of {counts['n']} in-scope" in policy["validated"]


@pytest.mark.parametrize(
    ("rule", "row"), ALL_ROWS, ids=lambda v: v if isinstance(v, str) else v["id"]
)
def test_published_dps_matches_raw_owner_and_owned_unit_damage(
    rule: str, row: dict[str, Any]
) -> None:
    policy = POLICIES[rule]
    m = _measure(_evidence(rule)["archive"], row)
    externals = load_rules("classic_era", "externals")["factions"]
    alliance = {int(k) for k, v in externals.items() if v == policy["scope"]["faction"]}
    assert m["details"] and all(d["type"] == "Druid" for d in m["details"])
    assert {d["combatantInfo"]["factionID"] for d in m["details"]} <= alliance
    assert {d["name"] for d in m["details"]} == {row["player"]}
    assert m["owned"] == row["owned_actor_ids"]
    assert m["totals"] == row["totals"]
    published = m["published"]
    assert (
        published["report"]["code"],
        published["report"]["fightID"],
        published["name"],
        published["server"]["name"],
        published["class"],
        published["spec"],
    ) == (row["report"], row["fight"], row["player"], row["realm"], "Druid", "Balance")
    amount, duration = str(published["amount"]), m["duration_ms"]
    assert int(published["duration"]) == duration == row["duration_ms"]
    assert amount == row["published"]
    ranked = m["totals"]["ranked"]
    assert str(Fraction(ranked) * 1000 / duration - Fraction(amount)) == row["residual"]
    assert _consistent(ranked, duration, amount)
    # Each wrong policy must fail on its own.
    assert not _consistent(ranked, duration + 1000, amount)
    if m["totals"]["self"]:
        assert not _consistent(m["totals"]["raw"], duration, amount)
    if m["owned_damage"]:
        assert not _consistent(ranked - m["owned_damage"], duration, amount)
    bosses = set(_encounter(policy["scope"]["encounter_id"])["boss_game_ids"])
    others = {g: v for g, v in m["by_target"].items() if g not in bosses and v}
    if others:
        largest = max(others.values())
        assert not _consistent(ranked - largest, duration, amount)


def test_every_wrong_policy_is_exercised_by_some_admitted_row() -> None:
    """Mutations that a row cannot exercise are named here instead of claimed."""
    measured = {
        (row["report"], row["fight"]): _measure(_evidence(rule)["archive"], row)
        for rule, row in ALL_ROWS
    }
    self_damage = [k for k, m in measured.items() if m["totals"]["self"]]
    owned = [(k, m["owned_damage"]) for k, m in measured.items() if m["owned_damage"]]
    assert owned == [(OWNED_WITNESS[:2], OWNED_WITNESS[2])]
    assert self_damage
    multi_target = [
        k for k, m in measured.items() if len([v for v in m["by_target"].values() if v]) > 1
    ]
    assert multi_target


def _witness_inputs() -> tuple[Any, dict[str, Any], dict[int, dict[str, Any]], int]:
    rule, row = next(
        (rule, row) for rule, row in ALL_ROWS if (row["report"], row["fight"]) == OWNED_WITNESS[:2]
    )
    archive = _evidence(rule)["archive"]
    with zipfile.ZipFile(REPO / archive["path"]) as z:
        report = _read(z, f"reports/{row['report']}/bundle.json")["reportData"]["report"]
        name = next(
            n
            for n in z.namelist()
            if n.startswith(f"events/{row['report']}/fight_{row['fight']}/player_{row['actor']}_")
            and n.endswith("/pets.json")
        )
        listing = _read(z, name)
    fight = next(f for f in report["fights"] if f["id"] == row["fight"])
    return listing, fight, {a["id"]: a for a in report["masterData"]["actors"]}, row["actor"]


def test_owned_units_come_from_an_explicit_agreeing_listing() -> None:
    listing, fight, actors, actor = _witness_inputs()
    assert _owned_units(listing, fight, actors, actor) == {81}
    foreign = [{**listing[0], "petOwner": actor + 1}]
    wrong_game = [{**listing[0], "gameID": listing[0]["gameID"] + 1}]
    for bad in (None, [], foreign, wrong_game, [*listing, *listing]):
        with pytest.raises(AssertionError):
            _owned_units(bad, fight, actors, actor)
