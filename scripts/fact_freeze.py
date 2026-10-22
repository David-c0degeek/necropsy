"""Freeze independent raw facts from a capture archive, or check a frozen file.

Reads the archive with the standard library only and imports nothing from
necropsy (no analyzer, snapshot reader or check_raid_facts helper), so frozen
values stay independent of the code they later test. A freeze is a draft: each
cell's fact review still compares it with the raw events or another independent
source before it is cited.

    uv run python scripts/fact_freeze.py freeze SPEC.json --out FACTS.json [--replace]
    uv run python scripts/fact_freeze.py check FACTS.json

A spec names the archive (relative to the spec), its SHA-256, the contexts
(report, fight, actor, player, subject) and named queries:

    duration_ms                          fight length
    aura_transitions  ids                aura events on the actor (default apply/remove)
    npc_buff_windows  ids                buff apply/remove pairs per target, instance and ability
    casts             ids | {name: ids}  casts by the actor
    dispels           ids                explicit dispel rows by the actor, with recipients
    ability_damage    ids                fight-wide damage, from/to the actor, first locator

Options: "stream" is "all" (the fight's encounter All pages, the default) or
"actor" (the player's SOURCE and TARGET pages united by maximum multiplicity);
a missing stream is refused, never replaced by the other. "unit" is "s"
(seconds from the fight start to the millisecond, default) or "ms". Aura
transitions take "types" and "with_ability"; buff windows take "flat" for a
plain [[start, end]] list, refused unless exactly one target/instance/ability
is involved. Every value keeps the archive member and index of the events it
came from.

Dispels retain the removed ability, recipient, isBuff and raw instances. They
do not pair casts, infer friendliness, measure response times or grade opportunities.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import sys
import tempfile
import zipfile
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

TOOL_VERSION = 1
SPEC_KEYS = {"fixture", "archive", "sha256", "contexts", "queries", "note"}
CONTEXT_KEYS = {"report", "fight", "actor", "player", "subject"}
QUERY_KEYS = {"kind", "ids", "stream", "unit", "types", "with_ability", "flat"}
OPTIONS = {
    "duration_ms": {"kind"},
    "aura_transitions": {"kind", "ids", "stream", "unit", "types", "with_ability"},
    "npc_buff_windows": {"kind", "ids", "stream", "unit", "flat"},
    "casts": {"kind", "ids", "stream", "unit"},
    "dispels": {"kind", "ids", "stream", "unit"},
    "ability_damage": {"kind", "ids", "stream"},
}
KINDS = {
    "duration_ms",
    "aura_transitions",
    "npc_buff_windows",
    "casts",
    "dispels",
    "ability_damage",
}
IDENTITY_FIELDS = ("abilityGameID", "sourceID", "targetID", "sourceInstance", "targetInstance")
"""Raw identities the queries filter on: when present they must be exact integers
(sentinels such as -1 included), never coerced or silently filtered out."""
APPLY_REMOVE = ["applybuff", "applydebuff", "removebuff", "removedebuff"]
AURA_TYPES = {
    *APPLY_REMOVE,
    "applybuffstack",
    "applydebuffstack",
    "removebuffstack",
    "removedebuffstack",
    "refreshbuff",
    "refreshdebuff",
}

Event = dict[str, Any]
Located = tuple[Event, str, int]
"""An event with the archive member and the index within that page it came from."""


class FreezeError(ValueError):
    """The spec or the archive cannot establish the requested facts."""


def _int(value: Any, what: str) -> int:
    if type(value) is not int:
        raise FreezeError(f"{what} must be an integer, not {value!r}")
    return value


def _ids(value: Any) -> set[int]:
    ids = value if isinstance(value, list) else [value]
    if not ids:
        raise FreezeError("a query needs at least one ability id")
    return {_int(i, "an ability id") for i in ids}


def validate_spec(spec: Any) -> None:
    """Refuse unknown keys, kinds and option values before reading the archive."""
    if not isinstance(spec, dict) or set(spec) - SPEC_KEYS:
        raise FreezeError(f"unknown spec keys {sorted(set(spec) - SPEC_KEYS)}")
    for key in ("archive", "sha256", "contexts", "queries"):
        if key not in spec:
            raise FreezeError(f"the spec has no {key}")
    if not isinstance(spec["contexts"], list) or not spec["contexts"]:
        raise FreezeError("the spec needs at least one context")
    for ctx in spec["contexts"]:
        if not isinstance(ctx, dict) or set(ctx) != CONTEXT_KEYS:
            raise FreezeError(f"a context needs exactly {sorted(CONTEXT_KEYS)}")
        _int(ctx["fight"], "a context fight")
        _int(ctx["actor"], "a context actor")
        if not isinstance(ctx["report"], str) or not isinstance(ctx["player"], str):
            raise FreezeError("a context report and player must be strings")
        if type(ctx["subject"]) is not bool:
            raise FreezeError("a context subject must be true or false")
    if not isinstance(spec["queries"], dict) or not spec["queries"]:
        raise FreezeError("the spec needs at least one query")
    for name, q in spec["queries"].items():
        if name in CONTEXT_KEYS:
            raise FreezeError(f"query name {name!r} would overwrite a context field")
        if not isinstance(q, dict) or q.get("kind") not in KINDS or set(q) - OPTIONS[q["kind"]]:
            raise FreezeError(f"query {name!r} has an unknown kind or an option it cannot take")
        if q["kind"] != "duration_ms":
            ids = q.get("ids")
            if isinstance(ids, dict) and q["kind"] != "casts":
                raise FreezeError(f"query {name!r}: only casts take named id groups")
            for group in ids.values() if isinstance(ids, dict) else [ids]:
                _ids(group)
        for flag in ("flat", "with_ability"):
            if flag in q and type(q[flag]) is not bool:
                raise FreezeError(f"query {name!r}: {flag} must be true or false")
        if q.get("stream", "all") not in ("all", "actor"):
            raise FreezeError(f"query {name!r} has an unknown stream")
        if q.get("unit", "s") not in ("s", "ms"):
            raise FreezeError(f"query {name!r} has an unknown time unit")
        types = q.get("types", [])
        if not isinstance(types, list) or not all(isinstance(x, str) for x in types):
            raise FreezeError(f"query {name!r}: types must be a list of event types")
        if not set(types) <= AURA_TYPES:
            raise FreezeError(f"query {name!r} has unknown aura event types")


# -- raw streams --------------------------------------------------------------


def _pages(
    archive: zipfile.ZipFile, prefix: str, start: int, end: int, fight: int
) -> list[Located]:
    """One complete raw stream: contiguous pages, an advancing cursor that
    terminates on the last page, and events of this fight inside its bounds."""
    names = sorted(n for n in archive.namelist() if n.startswith(prefix))
    if not names or names != [f"{prefix}{i:03d}.json" for i in range(1, len(names) + 1)]:
        raise FreezeError(f"{prefix}*: the pages are missing or not contiguous")
    events: list[Located] = []
    cursor = start
    for index, name in enumerate(names):
        page = json.loads(archive.read(name))
        if not isinstance(page, dict) or "nextPageTimestamp" not in page:
            raise FreezeError(f"{name}: the page does not establish completion")
        data = page.get("data")
        if not isinstance(data, list) or not all(isinstance(e, dict) for e in data):
            raise FreezeError(f"{name}: malformed event data")
        for position, event in enumerate(data):
            stamp = event.get("timestamp")
            if type(stamp) is not int or not start <= stamp <= end:
                raise FreezeError(f"{name}[{position}]: timestamp outside the fight")
            if "fight" in event and (type(event["fight"]) is not int or event["fight"] != fight):
                raise FreezeError(f"{name}[{position}]: event of another fight")
            if type(event.get("type")) is not str:
                raise FreezeError(f"{name}[{position}]: event without a type")
            for field in IDENTITY_FIELDS:
                if event.get(field) is not None and type(event[field]) is not int:
                    raise FreezeError(f"{name}[{position}]: {field} is not an integer")
            events.append((event, name, position))
        following = page["nextPageTimestamp"]
        last = index == len(names) - 1
        if following is None:
            if not last:
                raise FreezeError(f"{name}: pages follow the terminal page")
        elif (
            last
            or type(following) not in (int, float)
            or not math.isfinite(following)
            or not cursor < following <= end
        ):
            raise FreezeError(f"{name}: the stream cursor is invalid or unterminated")
        else:
            cursor = following
    return events


def all_stream(
    archive: zipfile.ZipFile, report: str, fight: int, start: int, end: int
) -> list[Located]:
    """The fight's encounter All stream."""
    return _pages(archive, f"events/{report}/fight_{fight}/encounter/all_", start, end, fight)


def actor_stream(
    archive: zipfile.ZipFile, report: str, fight: int, actor: int, start: int, end: int
) -> list[Located]:
    """The player's SOURCE and TARGET streams, united by maximum multiplicity.

    A self-targeted event appears in both directions; identical events repeated
    within one direction are real repeats and are kept.
    """
    prefix = f"events/{report}/fight_{fight}/player_{actor}_"
    folders = {n.rsplit("/", 1)[0] for n in archive.namelist() if n.startswith(prefix)}
    if len(folders) != 1:
        raise FreezeError(f"{report} fight {fight}: no single stream folder for player {actor}")
    folder = folders.pop()
    first: dict[str, list[Located]] = {}
    union: Counter[str] = Counter()
    for direction in ("source", "target"):
        counts: Counter[str] = Counter()
        for located in _pages(archive, f"{folder}/{direction}_", start, end, fight):
            key = json.dumps(located[0], sort_keys=True, separators=(",", ":"))
            first.setdefault(key, []).append(located)
            counts[key] += 1
        union |= counts
    merged = [first[key][i] for key, count in union.items() for i in range(count)]
    return sorted(merged, key=lambda located: located[0]["timestamp"])


# -- queries ------------------------------------------------------------------


def _clock(q: dict[str, Any], start: int) -> Callable[[int], int | float]:
    if q.get("unit", "s") == "ms":
        return lambda stamp: stamp - start
    return lambda stamp: round((stamp - start) / 1000, 3)


def _where(located: Located) -> list[Any]:
    return [located[1], located[2]]


def _transitions(stream: list[Located], q: dict[str, Any], actor: int, start: int) -> Any:
    ids, at = _ids(q["ids"]), _clock(q, start)
    types = set(q.get("types", APPLY_REMOVE))
    picked = [
        x
        for x in stream
        if x[0].get("abilityGameID") in ids
        and x[0]["type"] in types
        and x[0].get("targetID") == actor
    ]
    value = [
        [at(e["timestamp"]), e["type"], *([e["abilityGameID"]] if q.get("with_ability") else [])]
        for e, _, _ in picked
    ]
    return value, [_where(x) for x in picked]


def _windows(stream: list[Located], q: dict[str, Any], start: int, npcs: dict[int, int]) -> Any:
    """Buff windows per target, instance and ability. An unmatched end stays null
    and is never closed at the fight end; a second apply leaves the first window
    open-ended rather than overwriting it.

    The target must be an NPC listed once among the fight's enemies. An unnumbered
    transition pairs only when that NPC had exactly one instance, and a numbered one
    must name a recorded instance. Transitions of one identity must be in time
    order. Anything else is refused rather than paired."""
    ids, at = _ids(q["ids"]), _clock(q, start)
    Endpoint = tuple[int, list[Any]] | None
    opened: dict[tuple[Any, ...], tuple[int, list[Any]]] = {}
    pairs: list[tuple[tuple[Any, ...], Endpoint, Endpoint]] = []
    seen: dict[tuple[Any, ...], set[str]] = {}
    last: dict[tuple[Any, ...], int] = {}
    for located in stream:
        e = located[0]
        if e.get("abilityGameID") not in ids or e["type"] not in ("applybuff", "removebuff"):
            continue
        where = f"{located[1]}[{located[2]}]"
        target = _int(e.get("targetID"), f"{where} targetID")
        if target not in npcs:
            raise FreezeError(
                f"{where}: target {target} is not one recorded enemy NPC of the fight"
            )
        instance = e.get("targetInstance")
        if instance is None:
            if npcs[target] != 1:
                raise FreezeError(
                    f"{where}: unnumbered transition on NPC {target} with {npcs[target]} instances"
                )
        elif not 1 <= _int(instance, f"{where} targetInstance") <= npcs[target]:
            raise FreezeError(f"{where}: instance {instance} is not recorded for NPC {target}")
        key = (target, instance, e["abilityGameID"])
        if e["timestamp"] < last.get(key, e["timestamp"]):
            raise FreezeError(f"{where}: transitions of one target are out of time order")
        last[key] = e["timestamp"]
        moment = seen.setdefault((*key, e["timestamp"]), set())
        if moment - {e["type"]}:
            raise FreezeError(f"{where}: apply and remove at the same time; order unknown")
        moment.add(e["type"])
        here = (e["timestamp"], _where(located))
        if e["type"] == "applybuff":
            if key in opened:  # applied again without a removal: the first end is unknown
                pairs.append((key, opened.pop(key), None))
            opened[key] = here
        else:
            pairs.append((key, opened.pop(key, None), here))
    pairs.extend((key, begin, None) for key, begin in opened.items())
    windows = [
        {
            "target": key[0],
            "instance": key[1],
            "ability": key[2],
            "start": None if begin is None else at(begin[0]),
            "end": None if finish is None else at(finish[0]),
            "locators": [point[1] for point in (begin, finish) if point is not None],
        }
        for key, begin, finish in pairs
    ]
    windows.sort(
        key=lambda w: (w["start"] is None, w["start"] or 0, w["end"] is None, w["end"] or 0)
    )
    locators = [w.pop("locators") for w in windows]
    if q.get("flat"):
        identities = {(w["target"], w["instance"], w["ability"]) for w in windows}
        if len(identities) > 1:
            raise FreezeError(f"flat windows would merge {len(identities)} target identities")
        return [[w["start"], w["end"]] for w in windows], locators
    return windows, locators


def _casts(stream: list[Located], q: dict[str, Any], actor: int, start: int) -> Any:
    at = _clock(q, start)

    def picked(ids: set[int]) -> list[Located]:
        return [
            x
            for x in stream
            if x[0]["type"] == "cast"
            and x[0].get("sourceID") == actor
            and x[0].get("abilityGameID") in ids
        ]

    if isinstance(q["ids"], dict):
        found = {name: picked(_ids(ids)) for name, ids in q["ids"].items()}
        found = {name: hits for name, hits in found.items() if hits}
        return (
            {name: [at(x[0]["timestamp"]) for x in hits] for name, hits in found.items()},
            {name: [_where(x) for x in hits] for name, hits in found.items()},
        )
    hits = picked(_ids(q["ids"]))
    return [at(x[0]["timestamp"]) for x in hits], [_where(x) for x in hits]


def _dispels(
    stream: list[Located],
    q: dict[str, Any],
    actor: int,
    start: int,
    catalog: list[dict[str, Any]],
) -> Any:
    """Explicit rows only; no cast pairing, aura reconstruction or assignment."""
    ids, at = _ids(q["ids"]), _clock(q, start)
    values, locators = [], []
    for located in stream:
        event = located[0]
        if (
            event["type"] != "dispel"
            or event.get("sourceID") != actor
            or event.get("abilityGameID") not in ids
        ):
            continue
        removed = _int(event.get("extraAbilityGameID"), "a removed ability id")
        recipient = _int(event.get("targetID"), "a dispel recipient id")
        if removed <= 0 or recipient <= 0:
            raise FreezeError("dispel removed ability and recipient ids must be positive")
        if type(event.get("isBuff")) is not bool:
            raise FreezeError("a dispel needs an explicit boolean isBuff")
        matching = [a for a in catalog if type(a.get("id")) is int and a["id"] == recipient]
        if len(matching) != 1:
            raise FreezeError("a dispel recipient must bind exactly one catalog actor")
        values.append(
            {
                "time": at(event["timestamp"]),
                "ability": event["abilityGameID"],
                "removed_ability": removed,
                "recipient": recipient,
                "is_buff": event["isBuff"],
                "source_instance": event.get("sourceInstance"),
                "recipient_instance": event.get("targetInstance"),
            }
        )
        locators.append(_where(located))
    return values, locators


def _damage(stream: list[Located], q: dict[str, Any], actor: int) -> Any:
    ids = _ids(q["ids"])
    hits = [
        (index, x)
        for index, x in enumerate(stream)
        if x[0]["type"] == "damage" and x[0].get("abilityGameID") in ids
    ]
    for _, (e, name, position) in hits:
        amount = e.get("amount")
        if not isinstance(amount, int | float) or isinstance(amount, bool):
            raise FreezeError(f"{name}[{position}]: damage amount missing or invalid")
        if not math.isfinite(amount) or amount < 0:
            raise FreezeError(f"{name}[{position}]: damage amount missing or invalid")

    def side(field: str) -> dict[str, Any]:
        mine = [x[0] for _, x in hits if x[0].get(field) == actor]
        return {"events": len(mine), "amount": sum(e["amount"] for e in mine)}

    first = None
    if hits:
        index, (e, _, _) = hits[0]
        first = {
            "all_index" if q.get("stream", "all") == "all" else "stream_index": index,
            "timestamp": e["timestamp"],
            "source": e.get("sourceID"),
            "target": e.get("targetID"),
            "amount": e["amount"],
        }
    value = {
        "fight_events": len(hits),
        "fight_amount": sum(x[0]["amount"] for _, x in hits),
        "sources": sorted(
            {x[0].get("sourceID") for _, x in hits}, key=lambda s: (s is None, s or 0)
        ),
        "from_actor": side("sourceID"),
        "to_actor": side("targetID"),
        "first_locator": first,
    }
    return value, [_where(x) for _, x in hits]


# -- freeze and check ---------------------------------------------------------


def _fight(bundle: Any, ctx: dict[str, Any]) -> tuple[int, int, dict[int, int]]:
    """The fight's bounds and its enemy NPC instance counts, after binding report,
    fight and player to the raw metadata by integer identity (never an alias)."""
    report = bundle["reportData"]["report"]
    if report.get("code") != ctx["report"]:
        raise FreezeError(f"{ctx['report']}: the bundle belongs to report {report.get('code')!r}")
    fights = [f for f in report["fights"] if type(f.get("id")) is int and f["id"] == ctx["fight"]]
    if len(fights) != 1:
        raise FreezeError(
            f"{ctx['report']}: fight {ctx['fight']} is not exactly one recorded fight"
        )
    start = _int(fights[0].get("startTime"), "a fight start")
    end = _int(fights[0].get("endTime"), "a fight end")
    if not start < end:
        raise FreezeError(f"{ctx['report']} fight {ctx['fight']}: empty or reversed bounds")
    actors = [
        a
        for a in report["masterData"]["actors"]
        if type(a.get("id")) is int and a["id"] == ctx["actor"]
    ]
    if len(actors) != 1 or actors[0].get("type") != "Player":
        raise FreezeError(f"{ctx['report']}: actor {ctx['actor']} is not exactly one player")
    if actors[0].get("name") != ctx["player"]:
        raise FreezeError(
            f"{ctx['report']}: actor {ctx['actor']} is {actors[0].get('name')!r}, "
            f"not {ctx['player']!r}"
        )
    catalog = [a for a in report["masterData"]["actors"] if type(a.get("id")) is int]
    records = Counter(a["id"] for a in catalog)
    # An NPC binding needs exactly one catalog record, of type NPC: a second
    # record for the same id (NPC or Player) makes the identity ambiguous.
    npcs = {a["id"] for a in catalog if a.get("type") == "NPC" and records[a["id"]] == 1}
    listed = [n for n in fights[0].get("enemyNPCs") or [] if isinstance(n, dict)]
    ids = [n.get("id") for n in listed]
    instances = {
        n["id"]: n["instanceCount"]
        for n in listed
        if type(n.get("id")) is int
        and n["id"] in npcs
        and ids.count(n["id"]) == 1
        and type(n.get("instanceCount")) is int
        and n["instanceCount"] >= 1
    }
    return start, end, instances


def _context(
    archive: zipfile.ZipFile, queries: dict[str, Any], ctx: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """One context's values and their raw locators."""
    report, fight, actor = ctx["report"], ctx["fight"], ctx["actor"]
    bundle = json.loads(archive.read(f"reports/{report}/bundle.json"))
    start, end, npcs = _fight(bundle, ctx)
    streams: dict[str, list[Located]] = {}
    values: dict[str, Any] = {}
    where: dict[str, Any] = {"report": report, "fight": fight, "actor": actor}
    for name, q in queries.items():
        kind, scope = q["kind"], q.get("stream", "all")
        if kind == "duration_ms":
            values[name], where[name] = end - start, []
            continue
        if scope not in streams:
            streams[scope] = (
                all_stream(archive, report, fight, start, end)
                if scope == "all"
                else actor_stream(archive, report, fight, actor, start, end)
            )
        events = streams[scope]
        if kind == "aura_transitions":
            values[name], where[name] = _transitions(events, q, actor, start)
        elif kind == "npc_buff_windows":
            values[name], where[name] = _windows(events, q, start, npcs)
        elif kind == "casts":
            values[name], where[name] = _casts(events, q, actor, start)
        elif kind == "dispels":
            values[name], where[name] = _dispels(
                events, q, actor, start, bundle["reportData"]["report"]["masterData"]["actors"]
            )
        else:
            values[name], where[name] = _damage(events, q, actor)
    return {**ctx, **values}, where


def compute(spec: dict[str, Any], base: Path) -> dict[str, Any]:
    """Every query's value and locators for every context, from the raw archive alone."""
    validate_spec(spec)
    raw = (base / spec["archive"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec["sha256"]:
        raise FreezeError(f"{spec['archive']}: the archive does not match the spec SHA-256")
    contexts, locators = [], []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:  # parse exactly the hashed bytes
        members = archive.namelist()
        if len(members) != len(set(members)):
            raise FreezeError(f"{spec['archive']}: duplicate archive member names")
        for ctx in spec["contexts"]:
            values, where = _context(archive, spec["queries"], ctx)
            contexts.append(values)
            locators.append(where)
    return {
        "version": 1,
        "tool": {"name": "scripts/fact_freeze.py", "version": TOOL_VERSION},
        "spec": spec,
        "contexts": contexts,
        "locators": locators,
    }


def _dump(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def differences(old: Any, new: Any, path: str = "") -> list[str]:
    """Every value that differs, by JSON path; types count (1 and 1.0 and True differ)."""
    if isinstance(old, dict) and isinstance(new, dict):
        found: list[str] = []
        for key in sorted(set(old) | set(new), key=str):
            if key not in old or key not in new:
                found.append(f"{path}/{key}: {'added' if key not in old else 'removed'}")
            else:
                found.extend(differences(old[key], new[key], f"{path}/{key}"))
        return found
    if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        return [
            d
            for i, pair in enumerate(zip(old, new, strict=True))
            for d in differences(*pair, f"{path}[{i}]")
        ]
    if type(old) is type(new) and old == new:
        return []
    return [f"{path}: {json.dumps(old)[:120]} -> {json.dumps(new)[:120]}"]


def _replace(path: Path, data: bytes) -> None:
    """Write next to the target and rename, so a failure keeps the previous bytes."""
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze", help="compute facts from a reviewed spec")
    freeze.add_argument("spec", type=Path)
    freeze.add_argument("--out", type=Path, required=True)
    freeze.add_argument("--replace", action="store_true", help="replace an existing facts file")
    check = sub.add_parser("check", help="recompute a frozen file from raw and compare")
    check.add_argument("facts", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            frozen = json.loads(args.facts.read_bytes())
            tool = {"name": "scripts/fact_freeze.py", "version": TOOL_VERSION}
            version, recorded = frozen.get("version"), frozen.get("tool")
            if (
                type(version) is not int
                or version != 1
                or not isinstance(recorded, dict)
                or type(recorded.get("version")) is not int
                or recorded != tool
            ):
                raise FreezeError(f"{args.facts}: not a version 1 file of this tool version")
            result = compute(frozen["spec"], args.facts.resolve().parent)
            changes = differences(
                {k: frozen.get(k) for k in ("tool", "contexts", "locators")},
                {k: result[k] for k in ("tool", "contexts", "locators")},
            )
            print("\n".join([*changes, f"{len(changes)} difference(s)"]))
            return 1 if changes else 0
        spec = json.loads(args.spec.read_bytes())
        out = args.out.resolve()
        relocated = os.path.relpath(args.spec.resolve().parent / spec["archive"], out.parent)
        result = compute(spec, args.spec.resolve().parent)
        result["spec"] = {**spec, "archive": Path(relocated).as_posix()}
        if out.exists():
            changes = differences(json.loads(out.read_bytes()).get("contexts"), result["contexts"])
            print("\n".join(changes) if changes else "no value changes against the existing file")
            if not args.replace:
                print(f"refused: {out} exists; review the differences, then pass --replace")
                return 2
        _replace(out, _dump(result))
        print(f"froze {len(result['contexts'])} context(s) into {args.out}")
        return 0
    except (FreezeError, KeyError, TypeError, OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"fact freeze refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
