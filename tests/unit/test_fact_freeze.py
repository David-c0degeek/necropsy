"""The fact-freeze tool reads only complete, correctly bound raw streams, keeps
NPC identities apart, and never treats a missing amount or endpoint as a value."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from scripts import fact_freeze as ff

REPORT, FIGHT, ACTOR, BOSS = "abcDEF123", 7, 17, 65
START, END = 1_000_000, 1_090_000
FIGHT_PREFIX = f"events/{REPORT}/fight_{FIGHT}"
ALL = f"{FIGHT_PREFIX}/encounter/all_"
SOURCE = f"{FIGHT_PREFIX}/player_{ACTOR}_Killian/source_"
TARGET = f"{FIGHT_PREFIX}/player_{ACTOR}_Killian/target_"


def ev(at: int, kind: str, ability: int, source: int, target: int, **extra: Any) -> dict[str, Any]:
    return {
        "timestamp": START + at,
        "type": kind,
        "abilityGameID": ability,
        "sourceID": source,
        "targetID": target,
        "fight": FIGHT,
        **extra,
    }


EVENTS = [
    ev(1_000, "applybuff", 19695, BOSS, BOSS),
    ev(2_000, "cast", 20216, ACTOR, -1),
    ev(3_500, "applydebuff", 20475, BOSS, ACTOR),
    ev(4_000, "damage", 20476, ACTOR, 39, amount=500),
    ev(5_000, "removebuff", 19695, BOSS, BOSS),
    ev(6_000, "damage", 20476, 25, ACTOR, amount=1159),
    ev(9_500, "removedebuff", 20475, BOSS, ACTOR),
    ev(12_000, "applybuff", 19695, BOSS, BOSS),
]


ENEMIES = [
    {"id": BOSS, "gameID": 12056, "instanceCount": 1},
    {"id": 80, "gameID": 11000, "instanceCount": 2},
    {"id": 81, "gameID": 11001, "instanceCount": 1},
]


def bundle(
    actor_name: str = "Killian", fights: int = 1, enemies: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    fight = {
        "id": FIGHT,
        "startTime": START,
        "endTime": END,
        "encounterID": 50668,
        "enemyNPCs": ENEMIES if enemies is None else enemies,
    }
    return {
        "reportData": {
            "report": {
                "code": REPORT,
                "fights": [fight] * fights,
                "masterData": {
                    "actors": [
                        {"id": ACTOR, "name": actor_name, "type": "Player"},
                        {"id": BOSS, "name": "Baron Geddon", "type": "NPC"},
                        {"id": 80, "name": "Flamewaker", "type": "NPC"},
                        {"id": 81, "name": "Firesworn", "type": "NPC"},
                    ]
                },
            }
        }
    }


def page(events: list[dict[str, Any]], following: Any = None) -> dict[str, Any]:
    return {"data": events, "nextPageTimestamp": following}


def make(
    tmp_path: Path,
    pages: dict[str, Any] | None = None,
    queries: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    extra: list[tuple[str, Any]] | None = None,
    player: str = "Killian",
) -> Path:
    """Write an archive and a spec; return the spec path."""
    members = {f"reports/{REPORT}/bundle.json": meta or bundle()}
    members.update(pages if pages is not None else {f"{ALL}001.json": page(EVENTS)})
    archive = tmp_path / "capture.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for name, data in [*members.items(), *(extra or [])]:
            zf.writestr(name, json.dumps(data))
    spec = {
        "fixture": "synthetic",
        "archive": "capture.zip",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "contexts": [
            {"report": REPORT, "fight": FIGHT, "actor": ACTOR, "player": player, "subject": True}
        ],
        "queries": queries
        or {
            "duration_ms": {"kind": "duration_ms"},
            "bomb": {"kind": "aura_transitions", "ids": [20475]},
            "inferno": {"kind": "npc_buff_windows", "ids": [19695], "flat": True},
            "favor": {"kind": "casts", "ids": [20216]},
            "named": {"kind": "casts", "ids": {"Divine Favor": [20216], "Divine Shield": [642]}},
            "explosions": {"kind": "ability_damage", "ids": [20476]},
        },
    }
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def run(spec: Path) -> dict[str, Any]:
    return ff.compute(json.loads(spec.read_bytes()), spec.parent)


def test_values_and_locators_come_from_the_raw_pages(tmp_path: Path) -> None:
    result = run(make(tmp_path))
    (ctx,) = result["contexts"]
    assert ctx["duration_ms"] == END - START
    assert ctx["bomb"] == [[3.5, "applydebuff"], [9.5, "removedebuff"]]
    assert ctx["inferno"] == [
        [1.0, 5.0],
        [12.0, None],
    ]  # the open window is never closed at the end
    assert ctx["favor"] == [2.0]
    assert ctx["named"] == {"Divine Favor": [2.0]}  # an ability never cast is absent, not []
    assert ctx["explosions"] == {
        "fight_events": 2,
        "fight_amount": 1659,
        "sources": [ACTOR, 25],
        "from_actor": {"events": 1, "amount": 500},
        "to_actor": {"events": 1, "amount": 1159},
        "first_locator": {
            "all_index": 3,
            "timestamp": START + 4_000,
            "source": ACTOR,
            "target": 39,
            "amount": 500,
        },
    }
    (where,) = result["locators"]
    assert where["bomb"] == [[f"{ALL}001.json", 2], [f"{ALL}001.json", 6]]
    assert where["explosions"] == [[f"{ALL}001.json", 3], [f"{ALL}001.json", 5]]
    assert result["tool"] == {"name": "scripts/fact_freeze.py", "version": ff.TOOL_VERSION}


def test_dispels_keep_raw_identity_instances_and_maximum_multiplicity(tmp_path: Path) -> None:
    first = ev(
        4000,
        "dispel",
        4987,
        ACTOR,
        80,
        extraAbilityGameID=20475,
        isBuff=False,
        sourceInstance=1,
        targetInstance=2,
    )
    second = ev(5000, "dispel", 4987, ACTOR, ACTOR, extraAbilityGameID=20475, isBuff=True)
    other = ev(6000, "dispel", 4987, BOSS, ACTOR)  # not the selected source
    cast = ev(4000, "cast", 4987, ACTOR, 80)
    removed = ev(4000, "removedebuff", 4987, ACTOR, 80)
    result = run(
        make(
            tmp_path,
            pages={
                f"{SOURCE}001.json": page([first, first, second, other, cast, removed]),
                f"{TARGET}001.json": page([first, second]),
            },
            queries={
                "dispels": {"kind": "dispels", "ids": [4987], "stream": "actor", "unit": "ms"}
            },
        )
    )
    rows = result["contexts"][0]["dispels"]
    assert rows == [
        {
            "time": 4000,
            "ability": 4987,
            "removed_ability": 20475,
            "recipient": 80,
            "is_buff": False,
            "source_instance": 1,
            "recipient_instance": 2,
        }
    ] * 2 + [
        {
            "time": 5000,
            "ability": 4987,
            "removed_ability": 20475,
            "recipient": ACTOR,
            "is_buff": True,
            "source_instance": None,
            "recipient_instance": None,
        }
    ]
    assert result["locators"][0]["dispels"] == [[f"{SOURCE}001.json", i] for i in (0, 1, 2)]


@pytest.mark.parametrize(
    "field,value",
    [
        ("extraAbilityGameID", None),
        ("extraAbilityGameID", True),
        ("extraAbilityGameID", 20475.0),
        ("extraAbilityGameID", 0),
        ("targetID", None),
        ("targetID", True),
        ("targetID", -1),
        ("isBuff", None),
        ("isBuff", 0),
        ("isBuff", "false"),
    ],
)
def test_dispel_identity_or_flag_is_not_defaulted(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    event = ev(4000, "dispel", 4987, ACTOR, BOSS, extraAbilityGameID=20475, isBuff=False)
    event[field] = value
    spec = make(
        tmp_path,
        pages={f"{ALL}001.json": page([event])},
        queries={"dispels": {"kind": "dispels", "ids": [4987]}},
    )
    with pytest.raises(ff.FreezeError):
        run(spec)


@pytest.mark.parametrize("catalog", ["missing", "duplicate", "float-id"])
def test_dispel_recipient_needs_one_exact_catalog_binding(tmp_path: Path, catalog: str) -> None:
    meta = bundle()
    actors = meta["reportData"]["report"]["masterData"]["actors"]
    if catalog == "missing":
        actors[:] = [a for a in actors if a["id"] != BOSS]
    elif catalog == "duplicate":
        actors.append({"id": BOSS, "type": "Player", "name": "Alias"})
    else:
        next(a for a in actors if a["id"] == BOSS)["id"] = float(BOSS)
    spec = make(
        tmp_path,
        meta=meta,
        pages={
            f"{ALL}001.json": page(
                [ev(4000, "dispel", 4987, ACTOR, BOSS, extraAbilityGameID=20475, isBuff=False)]
            )
        },
        queries={"dispels": {"kind": "dispels", "ids": [4987]}},
    )
    with pytest.raises(ff.FreezeError, match="recipient"):
        run(spec)


def test_dispel_scope_is_explicit_and_does_not_fall_back_to_actor(tmp_path: Path) -> None:
    event = ev(4000, "dispel", 4987, ACTOR, BOSS, extraAbilityGameID=20475, isBuff=False)
    spec = make(
        tmp_path,
        pages={f"{SOURCE}001.json": page([event]), f"{TARGET}001.json": page([event])},
        queries={"dispels": {"kind": "dispels", "ids": [4987]}},
    )
    with pytest.raises(ff.FreezeError):
        run(spec)


def test_check_passes_on_a_fresh_freeze_and_fails_on_an_edited_value(tmp_path: Path) -> None:
    spec = make(tmp_path)
    out = tmp_path / "facts.json"
    assert ff.main(["freeze", str(spec), "--out", str(out)]) == 0
    assert ff.main(["check", str(out)]) == 0
    facts = json.loads(out.read_bytes())
    facts["contexts"][0]["favor"] = [2]  # same number, different type
    out.write_text(json.dumps(facts), encoding="utf-8")
    assert ff.main(["check", str(out)]) == 1
    for version, tool_version in ((1, 999), (True, 1), (1.0, 1), (1, 1.0), (1, True)):
        facts["version"], facts["tool"]["version"] = version, tool_version
        out.write_text(json.dumps(facts), encoding="utf-8")
        assert ff.main(["check", str(out)]) == 2, (version, tool_version)


def test_freeze_refuses_to_overwrite_and_a_failed_replace_keeps_the_old_bytes(
    tmp_path: Path,
) -> None:
    spec = make(tmp_path)
    out = tmp_path / "facts.json"
    out.write_bytes(b"previous")
    assert ff.main(["freeze", str(spec), "--out", str(out)]) == 2
    assert out.read_bytes() == b"previous"
    broken = json.loads(spec.read_bytes())
    broken["sha256"] = "0" * 64
    spec.write_text(json.dumps(broken), encoding="utf-8")
    assert ff.main(["freeze", str(spec), "--out", str(out), "--replace"]) == 2
    assert out.read_bytes() == b"previous"
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".facts")] == []


def test_two_instances_stay_apart_and_cannot_be_flattened(tmp_path: Path) -> None:
    events = [
        ev(1_000, "applybuff", 800, 80, 80, targetInstance=1),
        ev(2_000, "applybuff", 800, 80, 80, targetInstance=2),
        ev(3_000, "removebuff", 800, 80, 80, targetInstance=1),
        ev(4_000, "removebuff", 801, 80, 80, targetInstance=2),  # another ability
        ev(5_000, "removebuff", 800, 80, 80, targetInstance=2),
        ev(6_000, "removebuff", 800, 81, 81),  # leading remove: start unknown
    ]
    queries = {"w": {"kind": "npc_buff_windows", "ids": [800, 801]}}
    spec = make(tmp_path, {f"{ALL}001.json": page(events)}, queries)
    (ctx,) = run(spec)["contexts"]
    assert ctx["w"] == [
        {"target": 80, "instance": 1, "ability": 800, "start": 1.0, "end": 3.0},
        {"target": 80, "instance": 2, "ability": 800, "start": 2.0, "end": 5.0},
        {"target": 80, "instance": 2, "ability": 801, "start": None, "end": 4.0},
        {"target": 81, "instance": None, "ability": 800, "start": None, "end": 6.0},
    ]
    flat = {"w": {"kind": "npc_buff_windows", "ids": [800, 801], "flat": True}}
    with pytest.raises(ff.FreezeError, match="merge 4 target identities"):
        run(make(tmp_path, {f"{ALL}001.json": page(events)}, flat))


def test_a_second_apply_leaves_the_first_window_open_ended(tmp_path: Path) -> None:
    events = [ev(1_000, "applybuff", 800, 81, 81), ev(2_000, "applybuff", 800, 81, 81)]
    queries = {"w": {"kind": "npc_buff_windows", "ids": [800], "flat": True, "unit": "ms"}}
    (ctx,) = run(make(tmp_path, {f"{ALL}001.json": page(events)}, queries))["contexts"]
    assert ctx["w"] == [[1_000, None], [2_000, None]]


def test_apply_and_remove_at_the_same_time_are_refused(tmp_path: Path) -> None:
    events = [ev(1_000, "applybuff", 800, 81, 81), ev(1_000, "removebuff", 800, 81, 81)]
    queries = {"w": {"kind": "npc_buff_windows", "ids": [800]}}
    with pytest.raises(ff.FreezeError, match="same time"):
        run(make(tmp_path, {f"{ALL}001.json": page(events)}, queries))


@pytest.mark.parametrize(
    ("events", "message"),
    [
        ([ev(1_000, "applybuff", 800, 80, 80)], "unnumbered transition on NPC 80 with 2 instances"),
        ([ev(1_000, "applybuff", 800, 80, 80, targetInstance=3)], "instance 3 is not recorded"),
        ([ev(1_000, "applybuff", 800, 80, ACTOR)], f"target {ACTOR} is not one recorded enemy"),
        ([ev(1_000, "applybuff", 800, 90, 90)], "target 90 is not one recorded enemy"),
        (
            [ev(3_000, "applybuff", 800, 81, 81), ev(1_000, "removebuff", 800, 81, 81)],
            "out of time order",
        ),
    ],
    ids=["unnumbered-multi", "unknown-instance", "player-target", "unlisted-npc", "out-of-order"],
)
def test_windows_need_a_proven_npc_identity_in_time_order(
    tmp_path: Path, events: list[dict[str, Any]], message: str
) -> None:
    queries = {"w": {"kind": "npc_buff_windows", "ids": [800]}}
    with pytest.raises(ff.FreezeError, match=message):
        run(make(tmp_path, {f"{ALL}001.json": page(events)}, queries))


def test_windows_out_of_order_across_pages_are_refused(tmp_path: Path) -> None:
    pages = {
        f"{ALL}001.json": page([ev(3_000, "applybuff", 800, 81, 81)], START + 3_000),
        f"{ALL}002.json": page([ev(2_500, "removebuff", 800, 81, 81)]),
    }
    queries = {"w": {"kind": "npc_buff_windows", "ids": [800]}}
    with pytest.raises(ff.FreezeError, match="out of time order"):
        run(make(tmp_path, pages, queries))


@pytest.mark.parametrize("kind", ["NPC", "Player"])
def test_a_second_catalog_record_for_the_npc_id_is_not_a_proven_identity(
    tmp_path: Path, kind: str
) -> None:
    meta = bundle()
    meta["reportData"]["report"]["masterData"]["actors"].append(
        {"id": 81, "name": "Other", "type": kind}
    )
    queries = {"w": {"kind": "npc_buff_windows", "ids": [800]}}
    events = [ev(1_000, "applybuff", 800, 81, 81), ev(2_000, "removebuff", 800, 81, 81)]
    with pytest.raises(ff.FreezeError, match="target 81 is not one recorded enemy"):
        run(make(tmp_path, {f"{ALL}001.json": page(events)}, queries, meta))


def test_absent_identities_stay_unknown_while_present_ones_must_be_integers(
    tmp_path: Path,
) -> None:
    cast = {k: v for k, v in EVENTS[1].items() if k != "targetID"}
    queries = {"c": {"kind": "casts", "ids": [20216]}}
    (ctx,) = run(make(tmp_path, {f"{ALL}001.json": page([cast])}, queries))["contexts"]
    assert ctx["c"] == [2.0]


def test_an_npc_listed_twice_among_the_enemies_is_not_a_proven_identity(tmp_path: Path) -> None:
    enemies = [*ENEMIES, {"id": 81, "gameID": 11001, "instanceCount": 1}]
    queries = {"w": {"kind": "npc_buff_windows", "ids": [800]}}
    events = [ev(1_000, "applybuff", 800, 81, 81)]
    with pytest.raises(ff.FreezeError, match="target 81 is not one recorded enemy"):
        run(make(tmp_path, {f"{ALL}001.json": page(events)}, queries, bundle(enemies=enemies)))


def test_the_archive_is_parsed_from_exactly_the_hashed_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = json.loads(make(tmp_path).read_bytes())
    hashed = (tmp_path / "capture.zip").read_bytes()
    longer = bundle()
    longer["reportData"]["report"]["fights"][0]["endTime"] = END + 1_000
    make(tmp_path, meta=longer)  # replaces the archive on disk after it was hashed
    original = Path.read_bytes

    def read_bytes(self: Path) -> bytes:
        return hashed if self.name == "capture.zip" else original(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    (ctx,) = ff.compute(spec, tmp_path)["contexts"]
    assert ctx["duration_ms"] == END - START


def test_actor_streams_unite_by_maximum_multiplicity(tmp_path: Path) -> None:
    heal = ev(1_000, "cast", 19943, ACTOR, ACTOR)
    repeat = ev(2_000, "cast", 25292, ACTOR, 3)
    pages = {
        f"{SOURCE}001.json": page([heal, repeat, repeat]),
        f"{TARGET}001.json": page([heal]),
    }
    queries = {"c": {"kind": "casts", "ids": [19943, 25292], "stream": "actor"}}
    (ctx,) = run(make(tmp_path, pages, queries))["contexts"]
    assert ctx["c"] == [1.0, 2.0, 2.0]


def test_a_missing_all_stream_is_refused_not_replaced_by_actor_streams(tmp_path: Path) -> None:
    pages = {f"{SOURCE}001.json": page(EVENTS), f"{TARGET}001.json": page([])}
    with pytest.raises(ff.FreezeError, match="missing or not contiguous"):
        run(make(tmp_path, pages))


@pytest.mark.parametrize(
    ("pages", "message"),
    [
        ({f"{ALL}001.json": page(EVENTS[:2], START + 3_000)}, "invalid or unterminated"),
        (
            {f"{ALL}001.json": page(EVENTS[:2], START + 3_000), f"{ALL}003.json": page([])},
            "not contiguous",
        ),
        (
            {f"{ALL}001.json": page(EVENTS[:2]), f"{ALL}002.json": page(EVENTS[2:])},
            "follow the terminal page",
        ),
        (
            {
                f"{ALL}001.json": page(EVENTS[:2], START + 3_000),
                f"{ALL}002.json": page(EVENTS[2:4], START + 3_000),
                f"{ALL}003.json": page(EVENTS[4:]),
            },
            "invalid or unterminated",
        ),
        ({f"{ALL}001.json": page(EVENTS[:2], END + 1)}, "invalid or unterminated"),
        ({f"{ALL}001.json": {"data": EVENTS}}, "does not establish completion"),
        ({f"{ALL}001.json": page([ev(-1, "cast", 1, ACTOR, 2)])}, "outside the fight"),
        ({f"{ALL}001.json": page([{**EVENTS[0], "timestamp": True}])}, "outside the fight"),
        ({f"{ALL}001.json": page([{**EVENTS[0], "fight": FIGHT + 1}])}, "another fight"),
        ({f"{ALL}001.json": page([{**EVENTS[0], "fight": float(FIGHT)}])}, "another fight"),
        (
            {f"{ALL}001.json": page([{**EVENTS[1], "abilityGameID": 20216.0}])},
            "abilityGameID is not",
        ),
        ({f"{ALL}001.json": page([{**EVENTS[1], "sourceID": float(ACTOR)}])}, "sourceID is not"),
        ({f"{ALL}001.json": page([{**EVENTS[1], "sourceID": str(ACTOR)}])}, "sourceID is not"),
        ({f"{ALL}001.json": page([{**EVENTS[1], "targetID": True}])}, "targetID is not"),
        ({f"{ALL}001.json": page([{**EVENTS[0], "targetInstance": "1"}])}, "targetInstance is not"),
        (
            {f"{ALL}001.json": page([{k: v for k, v in EVENTS[3].items() if k != "amount"}])},
            "amount missing",
        ),
    ],
    ids=[
        "open-cursor",
        "skipped-page",
        "after-terminal",
        "non-advancing",
        "cursor-past-end",
        "no-cursor",
        "before-start",
        "bool-timestamp",
        "other-fight",
        "float-event-fight",
        "float-ability",
        "float-source",
        "string-source",
        "bool-target",
        "string-instance",
        "no-amount",
    ],
)
def test_incomplete_or_foreign_streams_are_refused(
    tmp_path: Path, pages: dict[str, Any], message: str
) -> None:
    with pytest.raises(ff.FreezeError, match=message):
        run(make(tmp_path, pages))


def _aliased(field: str) -> dict[str, Any]:
    meta = bundle()
    report = meta["reportData"]["report"]
    if field == "fight":
        report["fights"][0]["id"] = float(FIGHT)
    else:
        report["masterData"]["actors"][0]["id"] = float(ACTOR)
    return meta


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"player": "Someone"}, "not 'Someone'"),
        ({"meta": bundle(fights=2)}, "not exactly one recorded fight"),
        ({"extra": [(f"{ALL}001.json", page([]))]}, "duplicate archive member"),
        ({"meta": _aliased("fight")}, "not exactly one recorded fight"),
        ({"meta": _aliased("actor")}, "is not exactly one player"),
    ],
    ids=["wrong-player", "ambiguous-fight", "duplicate-member", "float-fight-id", "float-actor-id"],
)
def test_context_and_archive_identity_must_be_unambiguous(
    tmp_path: Path, kwargs: dict[str, Any], message: str
) -> None:
    with pytest.warns(UserWarning) if "extra" in kwargs else _nothing():
        spec = make(tmp_path, **kwargs)
    with pytest.raises(ff.FreezeError, match=message):
        run(spec)


@pytest.mark.parametrize(
    "change",
    [
        {"queries": {"x": {"kind": "everything"}}},
        {"queries": {"x": {"kind": "casts", "ids": [1], "stream": "critical"}}},
        {"queries": {"x": {"kind": "casts", "ids": ["1"]}}},
        {"queries": {"x": {"kind": "casts", "ids": [1], "guess": True}}},
        {"extra_key": 1},
        {"contexts": [{"report": REPORT, "fight": FIGHT, "actor": ACTOR}]},
        {"queries": {"actor": {"kind": "duration_ms"}}},
        {"queries": {"x": {"kind": "npc_buff_windows", "ids": [1], "flat": 1}}},
        {"queries": {"x": {"kind": "aura_transitions", "ids": [1], "with_ability": "yes"}}},
        {"queries": {"x": {"kind": "casts", "ids": [1], "flat": True}}},
        {"queries": {"x": {"kind": "duration_ms", "ids": [1]}}},
        {"queries": {"x": {"kind": "ability_damage", "ids": {"a": [1]}}}},
        {"queries": {"x": {"kind": "aura_transitions", "ids": [1], "types": "applybuff"}}},
        {
            "contexts": [
                {"report": REPORT, "fight": 7.0, "actor": ACTOR, "player": "K", "subject": True}
            ]
        },
    ],
    ids=[
        "kind",
        "stream",
        "id-type",
        "option",
        "spec-key",
        "context-keys",
        "reserved-name",
        "non-bool-flat",
        "non-bool-ability",
        "option-for-other-kind",
        "ids-on-duration",
        "named-ids-on-damage",
        "types-not-list",
        "float-fight",
    ],
)
def test_invalid_specs_fail_before_reading_the_archive(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    spec = json.loads(make(tmp_path).read_bytes()) | change
    with pytest.raises(ff.FreezeError):
        ff.compute(spec, tmp_path)


def test_differences_count_types_and_missing_keys() -> None:
    assert ff.differences({"a": [1, None]}, {"a": [1, None]}) == []
    assert ff.differences({"a": 1}, {"a": 1.0}) == ["/a: 1 -> 1.0"]
    assert ff.differences({"a": 0}, {"a": False}) == ["/a: 0 -> false"]
    assert ff.differences({"a": 1}, {}) == ["/a: removed"]


class _nothing:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: object) -> None:
        return None
