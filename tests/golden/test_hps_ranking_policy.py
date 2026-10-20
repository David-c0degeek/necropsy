"""The scoped Holy Paladin HPS policies are re-proved from raw archive bytes.

Expected values come from the frozen oracle; every amount is re-enumerated here
from raw pages with exact rational arithmetic, without analyzer or metric code.
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

pytestmark = pytest.mark.golden
ROOT = Path(__file__).parent / "raids"
# Each scoped policy and the frozen oracle that its empirical basis cites.
ORACLES = {
    "mc-geddon-holy-paladin-hps-v1": ROOT / "hps-ranking-geddon-paladin.json",
    "mc-lucifron-holy-paladin-hps-v1": ROOT / "hps-ranking-lucifron-paladin.json",
    "mc-magmadar-holy-paladin-hps-v1": ROOT / "hps-ranking-magmadar-paladin.json",
    "mc-gehennas-holy-paladin-hps-v1": ROOT / "hps-ranking-gehennas-paladin.json",
    "mc-garr-holy-paladin-hps-v1": ROOT / "hps-ranking-garr-paladin.json",
    "mc-shazzrah-holy-paladin-hps-v1": ROOT / "hps-ranking-shazzrah-paladin.json",
    "mc-sulfuron-holy-paladin-hps-v1": ROOT / "hps-ranking-sulfuron-paladin.json",
    "mc-golemagg-holy-paladin-hps-v1": ROOT / "hps-ranking-golemagg-paladin.json",
    "mc-majordomo-holy-paladin-hps-v1": ROOT / "hps-ranking-majordomo-paladin.json",
}


def _oracle(rule: str) -> dict[str, Any]:
    oracle: dict[str, Any] = json.loads(ORACLES[rule].read_bytes())
    return oracle


def _rows(rule: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = _oracle(rule)["rows"]
    return rows


ALL_ROWS = [(rule, row) for rule in ORACLES for row in _rows(rule)]


def _policy(rule: str) -> dict[str, Any]:
    zone = load_rules("classic_era", "zones/mc")
    return next(p for p in zone["ranking_metric_policies"] if p["rule"] == rule)


def _read(z: zipfile.ZipFile, name: str) -> Any:
    # Published numbers stay text so their declared precision survives.
    return json.loads(z.read(name), parse_float=str)


def _realm(name: str | None) -> str | None:
    # masterData realms omit spaces ("PyrewoodVillage"); rankings keep them.
    return None if name is None else re.sub(r"\s+", "", name)


def _key(event: dict[str, Any]) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"))


def _stream_pages(
    z: zipfile.ZipFile,
    snapshot: dict[str, Any],
    fight: dict[str, Any],
    report: dict[str, Any],
    folder: str,
    actor: int,
    direction: str,
) -> list[dict[str, Any]]:
    """Pages bound to the snapshot's stream identity, in order, with a closed chain."""
    names = sorted(
        n for n in z.namelist() if re.fullmatch(re.escape(folder) + rf"/{direction}_\d+\.json", n)
    )
    streams = [
        s
        for s in snapshot["streams"]
        if (s["report"], s["fight"], s["actor_id"], s["direction"])
        == (report["code"], fight["id"], actor, direction)
    ]
    assert len(streams) == 1, (folder, direction)
    identity = streams[0]["identity"]
    assert identity["start_time"] == fight["startTime"] and identity["end_time"] == fight["endTime"]
    assert identity["revision"] == report["revision"] and identity["code"] == report["code"]
    assert names and streams[0]["pages"] == [hashlib.sha256(z.read(n)).hexdigest() for n in names]
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


def _outgoing(
    z: zipfile.ZipFile,
    snapshot: dict[str, Any],
    fight: dict[str, Any],
    report: dict[str, Any],
    folder: str,
    actor: int,
) -> list[dict[str, Any]]:
    """Maximum-multiplicity union of both directions; repeated events are retained."""
    counts: Counter[str] = Counter()
    events: dict[str, dict[str, Any]] = {}
    for direction in ("source", "target"):
        seen: Counter[str] = Counter()
        for event in _stream_pages(z, snapshot, fight, report, folder, actor, direction):
            events[_key(event)] = event
            seen[_key(event)] += 1
        counts |= seen
    return [
        events[k] for k, n in counts.items() for _ in range(n) if events[k].get("sourceID") == actor
    ]


def _amount(event: dict[str, Any], field: str = "amount") -> int:
    value = event.get(field, 0)
    assert type(value) is int and value >= 0, (field, value)
    return value


def _measure(row: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / row["archive"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    z = zipfile.ZipFile(path)
    snapshot = json.loads(z.read("necropsy-snapshot.json"))
    report = _read(z, f"reports/{row['report']}/fight_{row['fight']}.json")["report"]
    (fight,) = (f for f in report["fights"] if f["id"] == row["fight"])
    assert fight["encounterID"] == row["encounter_id"] and fight["kill"] is True
    actors = {a["id"]: a for a in report["masterData"]["actors"]}
    me = actors[row["actor"]]
    assert (me["type"], me["name"], me["server"], me["gameID"]) == (
        "Player",
        row["name"],
        row["realm"],
        row["game_id"],
    )
    players = [
        a
        for a in actors.values()
        if a["type"] == "Player"
        and a["name"] == me["name"]
        and _realm(a["server"]) == _realm(me["server"])
    ]
    assert len(players) == 1, "name and realm must identify one report actor"
    assert row["actor"] in fight["friendlyPlayers"]

    prefix = f"events/{row['report']}/fight_{row['fight']}/"
    (folder,) = {
        n.rsplit("/", 1)[0] for n in z.namelist() if n.startswith(f"{prefix}player_{row['actor']}_")
    }
    owner = _outgoing(z, snapshot, fight, report, folder, row["actor"])

    # A known owned-unit listing is required; zero units is never assumed from class.
    assert f"{folder}/pets.json" in z.namelist()
    listing = _read(z, f"{folder}/pets.json")
    fight_pets = {p["id"]: p for p in fight["friendlyPets"]}
    units = []
    unit_events = []
    for unit in listing:
        assert unit["petOwner"] == row["actor"] and actors[unit["id"]]["petOwner"] == row["actor"]
        assert fight_pets[unit["id"]]["petOwner"] == row["actor"]
        (unit_folder,) = {
            n.rsplit("/", 1)[0] for n in z.namelist() if n.startswith(f"{prefix}pet_{unit['id']}_")
        }
        events = _outgoing(z, snapshot, fight, report, unit_folder, unit["id"])
        unit_events.extend(events)
        units.append(
            {
                "actor": unit["id"],
                "game_id": unit["gameID"],
                "heal": sum(_amount(e) for e in events if e["type"] == "heal"),
                "absorbed": sum(_amount(e) for e in events if e["type"] == "absorbed"),
            }
        )

    # Every counted effect lands on a friendly player or a friendly owned unit.
    friendly = set(fight["friendlyPlayers"]) | set(fight_pets)
    effects = [e for e in owner + unit_events if e["type"] in ("heal", "absorbed")]
    assert effects and all(e["targetID"] in friendly for e in effects)

    # Cross-scope proof: counted effects are a multiset subset of encounter All.
    encounter = [
        s
        for s in snapshot["encounter_streams"]
        if (s["report"], s["fight"], s["role"]) == (row["report"], row["fight"], "encounter")
    ]
    assert len(encounter) == 1
    all_names = sorted(
        n for n in z.namelist() if re.fullmatch(re.escape(prefix) + r"encounter/all_\d+\.json", n)
    )
    assert encounter[0]["pages"] == [hashlib.sha256(z.read(n)).hexdigest() for n in all_names]
    all_rows = Counter(_key(e) for n in all_names for e in _read(z, n)["data"])
    assert not Counter(_key(e) for e in effects) - all_rows

    return {
        "duration_ms": fight["endTime"] - fight["startTime"],
        "owner": {
            "heal": sum(_amount(e) for e in owner if e["type"] == "heal"),
            "absorbed": sum(_amount(e) for e in owner if e["type"] == "absorbed"),
            "overheal": sum(_amount(e, "overheal") for e in owner if e["type"] == "heal"),
        },
        "owned_units": units,
        "z": z,
        "me": me,
    }


def _published(z: zipfile.ZipFile, ranking: dict[str, Any], row: dict[str, Any]) -> tuple[str, int]:
    data = _read(z, ranking["member"])
    if ranking["kind"] == "leaderboard":
        page, index = _locator(r"pages\[(\d+)\]\.rankings\[(\d+)\]", ranking["locator"])
        (entry,) = (p for p in data["pages"] if p["page"] == page)
        r = entry["characterRankings"]["rankings"][index]
        name, realm = r["name"], r["server"]["name"]
        report, fight = r["report"]["code"], r["report"]["fightID"]
    elif ranking["kind"] == "user_ranking":
        (index,) = _locator(r"ranks\[(\d+)\]", ranking["locator"])
        r = data["encounterRankings"]["ranks"][index]
        name, realm = data["character"], None
        report, fight = r["report"]["code"], r["report"]["fightID"]
    else:
        i, j = _locator(
            r"report\.rankings\.data\[(\d+)\]\.roles\.healers\.characters\[(\d+)\]",
            ranking["locator"],
        )
        block = data["report"]["rankings"]["data"][i]
        r = {**block["roles"]["healers"]["characters"][j], "duration": block["duration"]}
        name, realm = r["name"], r["server"]["name"]
        report, fight = data["report"]["code"], block["fightID"]
    assert (report, fight, name) == (row["report"], row["fight"], row["name"])
    if realm is not None:
        assert _realm(realm) == _realm(row["realm"])
    return str(r["amount"]), int(r["duration"])


def _locator(pattern: str, text: str) -> tuple[int, ...]:
    match = re.fullmatch(pattern, text)
    assert match is not None, text
    return tuple(int(g) for g in match.groups())


def _consistent(total: int, duration: int, published: str) -> bool:
    decimals = len(published.split(".")[1]) if "." in published else 0
    return abs(Fraction(total) * 1000 / duration - Fraction(published)) < Fraction(1, 10**decimals)


@pytest.mark.parametrize("rule", list(ORACLES))
def test_policy_scope_matches_its_frozen_evidence(rule: str) -> None:
    policy = _policy(rule)
    assert policy["evidence"] == f"tests/golden/raids/{ORACLES[rule].name}"
    assert _oracle(rule)["rule"] == rule
    scoped = [r for r in _rows(rule) if r["purpose"] == "policy-scope"]
    assert len(scoped) == 6 and {r["encounter_id"] for r in scoped} == {
        policy["scope"]["encounter_id"]
    }


@pytest.mark.parametrize(
    ("rule", "row"), ALL_ROWS, ids=lambda v: v if isinstance(v, str) else v["id"]
)
def test_published_hps_matches_raw_owner_and_owned_unit_effects(
    rule: str, row: dict[str, Any]
) -> None:
    m = _measure(row)
    assert m["duration_ms"] == row["duration_ms"]
    assert m["owner"] == row["owner"] and m["owned_units"] == row["owned_units"]
    if row["purpose"] == "policy-scope":
        assert m["me"]["subType"] == "Paladin"
    units = sum(u["heal"] + u["absorbed"] for u in m["owned_units"])
    total = m["owner"]["heal"] + m["owner"]["absorbed"] + units
    others = [r for r in _rows(rule) if r["id"] != row["id"]]
    for ranking in row["rankings"]:
        published, duration = _published(m["z"], ranking, row)
        assert published == ranking["published"]
        assert duration == m["duration_ms"]
        residual = Fraction(total) * 1000 / duration - Fraction(published)
        assert str(residual) == ranking["residual"]
        assert _consistent(total, duration, published)
        # Each wrong policy must fail on its own.
        assert not _consistent(total + m["owner"]["overheal"], duration, published)
        assert not _consistent(total, duration + 1000, published)
        if m["owner"]["absorbed"]:
            assert not _consistent(total - m["owner"]["absorbed"], duration, published)
        if units:
            assert not _consistent(total - units, duration, published)
        wrong_owner = others[0]["owner"]["heal"] + others[0]["owner"]["absorbed"]
        assert not _consistent(wrong_owner, duration, published)
