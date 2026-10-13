"""Same-faction cohort selection from ranking pages.

Ranking rows here are SYNTHETIC, shaped like the recorded fixture's leaderboard rows
(name, class, spec, amount, hardModeLevel, size, report, guild, server).
"""

from __future__ import annotations

import dataclasses
import json
import random
from typing import Any

import httpx
import pytest

from necropsy.analysis.evidence import Faction
from necropsy.wcl import client as c
from necropsy.wcl.cohort import (
    CohortRefused,
    cohort_key,
    guild_faction,
    page_items,
    select,
    select_boss,
)
from necropsy.wcl.context import SUPPORTED_ZONE_ID, CharacterContext, Field, Partition
from necropsy.wcl.sites import SITES, VANILLA
from tests.wcl_fakes import FakeClock, Script, ok

ENCOUNTER = 51118


def _context(**over: Any) -> CharacterContext:
    part = Partition(3, "Phase 6", True, True)
    base: dict[str, Any] = {
        "character_id": Field(86583560, "observed", "t"),
        "canonical_id": Field(86583560, "observed", "t"),
        "name": Field("Haplina", "observed", "t"),
        "server": Field("Ashbringer", "observed", "t"),
        "region": Field("EU", "observed", "t"),
        "class_id": Field(3, "observed", "t"),
        "faction": Field(Faction.ALLIANCE, "observed", "t"),
        "raw_faction": {"id": 1, "name": "Alliance"},
        "zone_id": SUPPORTED_ZONE_ID,
        "zone_name": Field("Naxxramas", "observed", "t"),
        "partitions": (part,),
        "partition": part,
    }
    base.update(over)
    return CharacterContext(**base)


def _row(n: int, guild: Any = 0, **over: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "name": f"Hunter{n}",
        "class": "Hunter",
        "spec": "Marksmanship",
        "amount": 2000.0 - n,
        "hardModeLevel": 0,
        "size": 40,
        "report": {"code": f"R{n:04d}", "fightID": n},
        "server": {"id": 1, "name": "Whitemane", "region": "US"},
    }
    if guild is not None:
        row["guild"] = {"id": n, "name": "g", "faction": guild}
    row.update(over)
    return row


def _stream(*page_rows: list[dict[str, Any]]) -> Any:
    for page, rows in enumerate(page_rows, 1):
        for r in rows:
            yield (page, len(rows), r)


def _key() -> Any:
    return cohort_key(VANILLA, _context(), ENCOUNTER)


def test_key_records_every_dimension_with_how_it_is_applied() -> None:
    key = _key()
    assert key.difficulty.status == "enforced" and key.size.status == "recorded"
    assert key.spec.value == "all Hunter specs" and key.spec.status == "recorded"
    assert key.faction.value == "Alliance" and key.partition.value == 3
    assert "no game build" in (key.game.note or "")


@pytest.mark.parametrize(
    "over",
    [
        {"faction": Field(None, "unknown", "t")},
        {"partition": None},
        {"class_id": Field(4, "observed", "t")},
        {"class_id": Field(None, "unknown", "t")},
        {"zone_id": 1001},
    ],
)
def test_context_that_cannot_give_a_same_faction_cohort_is_refused(over: dict[str, Any]) -> None:
    with pytest.raises(CohortRefused):
        cohort_key(VANILLA, _context(**over), ENCOUNTER)


def test_unsupported_site_is_refused_before_any_query() -> None:
    with pytest.raises(Exception, match="not supported"):
        cohort_key(SITES["fresh.warcraftlogs.com"], _context(), ENCOUNTER)


@pytest.mark.parametrize(
    ("guild", "value", "level"),
    [
        (0, "Alliance", "inferred"),
        (1, "Horde", "inferred"),
        (True, None, "unknown"),
        (7, None, "unknown"),
        (None, None, "unknown"),
        ("0", None, "unknown"),
    ],
)
def test_guild_rule_only_infers(guild: Any, value: str | None, level: str) -> None:
    row = _row(1, guild=guild) if guild is not None else _row(1, guild=None)
    got = guild_faction(row)
    assert (got.value, got.level) == (value, level)


def test_paging_goes_past_the_top_five_until_same_faction_targets() -> None:
    first = [_row(i, guild=1) for i in range(1, 4)] + [_row(i) for i in range(4, 6)]
    second = [_row(i) for i in range(6, 40)]
    sel = select(_stream(first, second), _key(), _context())
    assert [d.position for d in sel.deep] == [4, 5, 6, 7, 8]
    assert sel.other_faction == 3 and len(sel.metadata) == 25
    assert sel.stop == "targets met" and sel.complete
    assert sel.overall_first is not None and sel.overall_first.position == 1
    assert sel.overall_first not in sel.metadata


def test_same_faction_first_row_is_selected_exactly_once() -> None:
    sel = select(_stream([_row(i) for i in range(1, 40)]), _key(), _context())
    assert sel.deep[0] is sel.overall_first and sel.metadata.count(sel.overall_first) == 1


def test_positions_count_raw_rows_across_unequal_pages() -> None:
    short = [_row(1, guild=1), _row(2, guild=None)]
    full = [_row(i, guild=1) for i in range(3, 103)]
    last = [_row(i) for i in range(103, 120)]
    sel = select(_stream(short, full, last), _key(), _context())
    assert sel.deep[0].position == 103 and sel.deep[0].page == 3
    assert [p.rows for p in sel.pages] == [2, 100, 17]
    assert len(sel.unresolved) == 1


def test_duplicates_across_pages_cannot_fabricate_the_minimum() -> None:
    a, b = _row(1), _row(2)
    sel = select(_stream([a, b], [dict(a), dict(b), _row(3, guild=1)]), _key(), _context())
    assert len(sel.deep) == 2 and sel.duplicates == 2
    assert not sel.complete
    assert any("below the minimum of 3" in r for r in sel.partial_reasons)


def test_unknown_faction_is_never_counted_and_verify_overrides() -> None:
    rows = [_row(1, guild=None), _row(2, guild=0), _row(3, guild=None), _row(4, guild=None)]

    def verify(candidate: Any) -> Faction | None:
        return {"Hunter2": Faction.HORDE, "Hunter3": Faction.ALLIANCE}.get(candidate.name)

    sel = select(_stream(rows), _key(), _context(), verify)
    assert [d.name for d in sel.deep] == ["Hunter3"]
    assert sel.deep[0].faction.level == "observed"
    assert [x.name for x in sel.contradicted] == ["Hunter2"] and sel.other_faction == 1
    assert {u.name for u in sel.unresolved} == {"Hunter1", "Hunter4"}
    assert not sel.complete


def test_subject_mismatched_and_unbacked_rows_are_set_aside() -> None:
    rows = [
        _row(1, name="haplina", server={"name": "Ashbringer", "region": "EU"}),
        _row(2, hardModeLevel=1),
        _row(3, **{"class": "Warrior"}),
        _row(4, report={}),
        _row(5),
    ]
    sel = select(_stream(rows), _key(), _context())
    assert sel.subject_rows == 1 and len(sel.key_mismatch) == 2
    assert [x.name for x in sel.inaccessible] == ["Hunter4"]
    assert [d.name for d in sel.deep] == ["Hunter5"] and sel.stop == "no more pages"


def test_page_items_validate_shape() -> None:
    items, more, _ = page_items(json.dumps({"rankings": [_row(1)], "hasMorePages": True}), 1)
    assert more is True and items[0][1] == 1
    with pytest.raises(c.InvalidResponse):
        page_items({"nope": []}, 1)
    with pytest.raises(c.InvalidResponse):
        page_items("{not json", 1)


def _client(script: Script) -> c.WclClient:
    client = c.WclClient(
        VANILLA, lambda e: "t", transport=script.transport, clock=FakeClock(), rng=random.Random(0)
    )
    client.last_rate = c.RateLimit(3600, 10.0, 1200)
    return client


def _page(rows: list[dict[str, Any]], more: Any, encounter: int = ENCOUNTER) -> httpx.Response:
    rankings = {"rankings": rows, "hasMorePages": more}
    return ok({"worldData": {"encounter": {"id": encounter, "characterRankings": rankings}}})


def test_select_boss_pages_until_done_and_records_the_rate() -> None:
    script = Script(
        _page([_row(i, guild=1) for i in range(1, 6)], True),
        _page([_row(i) for i in range(6, 40)], False),
    )
    sel = select_boss(_client(script), VANILLA, _context(), ENCOUNTER)
    assert len(sel.deep) == 5 and sel.stop == "targets met" and sel.rate is not None
    sent = script.bodies()
    assert [b["variables"]["page"] for b in sent] == [1, 2]
    assert all(b["variables"]["partition"] == 3 for b in sent)


def test_page_budget_is_a_partial_result_not_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from necropsy.wcl import cohort

    tight = {**cohort._cfg(), "max_pages": 1}
    monkeypatch.setattr(cohort, "_cfg", lambda: tight)
    script = Script(_page([_row(1, guild=1)], True))
    sel = select_boss(_client(script), VANILLA, _context(), ENCOUNTER)
    assert sel.stop == "page budget" and not sel.complete


def test_malformed_or_foreign_pages_fail() -> None:
    with pytest.raises(c.InvalidResponse):
        select_boss(_client(Script(_page([_row(1)], None))), VANILLA, _context(), ENCOUNTER)
    with pytest.raises(c.InvalidResponse):
        select_boss(_client(Script(_page([_row(1)], False, 1))), VANILLA, _context(), ENCOUNTER)
    same = _page([_row(1)], True)
    repeat = _page([_row(1)], True)
    with pytest.raises(c.InvalidResponse):
        select_boss(_client(Script(same, repeat)), VANILLA, _context(), ENCOUNTER)


def test_quota_and_permission_stop_with_their_reason_and_no_fallback() -> None:
    denied = httpx.Response(403)
    script = Script(denied)
    sel = select_boss(_client(script), VANILLA, _context(), ENCOUNTER)
    assert sel.stop.startswith("PermissionDenied") and not sel.complete
    assert len(script.requests) == 1
    spent = _client(Script())
    spent.last_rate = c.RateLimit(3600, 3590.0, 1200)
    sel = select_boss(spent, VANILLA, _context(), ENCOUNTER)
    assert sel.stop.startswith("BudgetExceeded") and sel.rate is not None


@pytest.mark.parametrize(
    ("answer", "level", "other"),
    [(Faction.ALLIANCE, "observed", 0), (Faction.HORDE, "observed", 1)],
)
def test_context_reference_follows_verification_of_the_first_row(
    answer: Faction, level: str, other: int
) -> None:
    sel = select(
        _stream([_row(1, guild=0), _row(2)]),
        _key(),
        _context(),
        lambda c: answer if c.name == "Hunter1" else None,
    )
    assert sel.overall_first is not None
    assert (sel.overall_first.faction.value, sel.overall_first.faction.level) == (
        answer.value,
        level,
    )
    assert sel.other_faction == other


@pytest.mark.parametrize(
    ("server", "is_subject"),
    [
        ({"name": "Pyrewood Village", "region": "EU"}, True),
        ({"name": "PyrewoodVillage", "region": "EU"}, True),
        ({"name": "pyrewood-village", "region": "eu"}, True),
        ({"name": "Pyrewood Villages", "region": "EU"}, False),
        ({"name": "Pyrewood Village", "region": "US"}, False),
    ],
)
def test_subject_is_matched_by_realm_key(server: dict[str, str], is_subject: bool) -> None:
    ctx = _context(server=Field("Pyrewood Village", "observed", "t"))
    key = cohort_key(VANILLA, ctx, ENCOUNTER)
    sel = select(_stream([_row(1, name="Haplina", server=server)]), key, ctx)
    assert sel.subject_rows == (1 if is_subject else 0)


def test_non_ascii_realms_keep_their_letters() -> None:
    ctx = _context(server=Field("Хроми", "observed", "t"))
    key = cohort_key(VANILLA, ctx, ENCOUNTER)
    rows = [
        _row(1, name="Haplina", server={"name": "Хроми", "region": "EU"}),
        _row(2, name="Haplina", server={"name": "Пламегор", "region": "EU"}),
    ]
    sel = select(_stream(rows), key, ctx)
    assert sel.subject_rows == 1 and [d.position for d in sel.deep] == [2]


@pytest.mark.parametrize("level", ["missing", None, False, 0.0, "0", 1])
def test_difficulty_must_be_the_integer_zero(level: Any) -> None:
    row = _row(1)
    if level == "missing":
        del row["hardModeLevel"]
    else:
        row["hardModeLevel"] = level
    sel = select(_stream([row]), _key(), _context())
    assert len(sel.key_mismatch) == 1 and not sel.deep


@pytest.mark.parametrize(
    "report",
    [
        {"code": "", "fightID": 1},
        {"code": "  ", "fightID": 1},
        {"code": "R", "fightID": 0},
        {"code": "R", "fightID": -1},
        {"code": "R", "fightID": True},
        {"code": 5, "fightID": 1},
    ],
)
def test_invalid_report_references_are_not_acquirable(report: dict[str, Any]) -> None:
    sel = select(_stream([_row(1, report=report)]), _key(), _context())
    assert len(sel.inaccessible) == 1 and not sel.deep


def _consumed() -> Any:
    raise AssertionError("rows were read before the key was checked")
    yield  # pragma: no cover


@pytest.mark.parametrize(
    "ctx",
    [
        _context(faction=Field(Faction.HORDE, "observed", "t")),
        _context(faction=Field(None, "unknown", "t")),
        _context(partition=Partition(4, "Other", False, True)),
        _context(class_id=Field(4, "observed", "t")),
    ],
)
def test_select_refuses_a_key_from_another_context_before_reading(ctx: CharacterContext) -> None:
    with pytest.raises(CohortRefused):
        select(_consumed(), _key(), ctx)


@pytest.mark.parametrize("encounter", [1, 99999, 0, -51118, True])
def test_only_supported_bosses_get_a_key(encounter: Any) -> None:
    with pytest.raises(CohortRefused):
        cohort_key(VANILLA, _context(), encounter)


def test_same_endpoints_with_different_middles_are_different_pages() -> None:
    a = [_row(1, guild=1), _row(2, guild=1), _row(3, guild=1)]
    b = [_row(1, guild=1), _row(9), _row(3, guild=1)]
    _, _, id_a = page_items({"rankings": a, "hasMorePages": True}, 1)
    _, _, id_b = page_items({"rankings": b, "hasMorePages": True}, 2)
    _, _, id_a2 = page_items({"rankings": [dict(r) for r in a], "hasMorePages": True}, 3)
    assert id_a != id_b and id_a == id_a2
    script = Script(_page(a, True), _page(b, False))
    sel = select_boss(_client(script), VANILLA, _context(), ENCOUNTER)
    assert [d.name for d in sel.deep] == ["Hunter9"] and sel.duplicates == 2


@pytest.mark.parametrize(
    "change",
    [
        {"site": ("fresh.warcraftlogs.com", "enforced", None)},
        {"site": ("evil.example", "enforced", None)},
        {"role": ("hps", "enforced", "metric dps")},
        {"spec": ("Survival", "enforced", None)},
        {"size": (40, "enforced", None)},
        {"difficulty": (False, "enforced", "hardModeLevel must be 0")},
        {"encounter": (99999, "enforced", None)},
        {"zone": (2006.0, "enforced", None)},
        {"game": ("classic_era", "enforced", None)},
    ],
)
def test_select_refuses_a_key_that_is_not_canonical(change: dict[str, Any]) -> None:
    from necropsy.wcl.cohort import Dimension

    ((name, (value, status, note)),) = change.items()
    key = dataclasses.replace(_key(), **{name: Dimension(value, status, note)})
    with pytest.raises(CohortRefused):
        select(_consumed(), key, _context())


def test_the_canonical_key_still_selects() -> None:
    sel = select(_stream([_row(1)]), _key(), _context())
    assert [d.position for d in sel.deep] == [1]
