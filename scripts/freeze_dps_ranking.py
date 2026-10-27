"""Freeze/check independent actor-scoped DPS arithmetic against one published row.

An explicit JSON spec pins a capture and identifies a leaderboard row and the
owner. Exclusions are inputs, never fitted. Output is research, not a validated
cell policy or proof of encounter-wide completeness. Uses no analyzer imports.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import sys
import zipfile
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import fact_freeze as pages  # noqa: E402

# Snapshot format 3 derives actor target streams only for these zones and Era
# partitions, from an encounter-All request with exactly these fields.
DERIVED_TARGET_ZONES = frozenset({2006})
ENCOUNTER_PARTITIONS = frozenset({1, 2})
ENCOUNTER_ALL_FIELDS = frozenset(
    {
        "actor_id",
        "code",
        "data_type",
        "direction",
        "end_time",
        "endpoint",
        "fight",
        "include_resources",
        "limit",
        "query_version",
        "revision",
        "role",
        "site",
        "start_time",
        "translate",
    }
)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


class ArithmeticMismatch(ValueError):
    """Every evidence check passed, but the published amount contradicts the raw
    ranked damage under the given exclusions. With an untested exclusion list this
    is a policy-dependent result, not proof that the evidence is wrong (D025)."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def invalid_constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON constant: {value}")


def finite_float(value: str) -> float:
    result = float(value)
    require(math.isfinite(result), "overflowing JSON number")
    return result


def read_json(raw: bytes, *, decimal_text: bool = False) -> Any:
    if decimal_text:
        return json.loads(
            raw, object_pairs_hook=pairs, parse_constant=invalid_constant, parse_float=str
        )
    return json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_constant=invalid_constant,
        parse_float=finite_float,
    )


def integer(value: Any, *, positive: bool = False) -> bool:
    return type(value) is int and value >= (1 if positive else 0)


def one(rows: list[Any], reason: str) -> Any:
    require(len(rows) == 1, reason)
    return rows[0]


def consistent(amount: int, duration: int, published: str) -> bool:
    require(duration > 0, "nonpositive duration")
    require(bool(re.fullmatch(r"\d+(?:\.\d+)?", published)), "invalid published decimal")
    decimals = len(published.partition(".")[2])
    return abs(Fraction(amount * 1000, duration) - Fraction(published)) < Fraction(1, 10**decimals)


def validate_spec(spec: dict[str, Any]) -> None:
    keys = {
        "archive",
        "sha256",
        "report",
        "fight",
        "actor",
        "player",
        "realm",
        "class",
        "category",
        "role",
        "encounter",
        "excluded_game_ids",
        "leaderboard_member",
        "page",
        "row",
    }
    require(isinstance(spec, dict) and set(spec) == keys, "spec keys differ from contract")
    require(bool(re.fullmatch(r"[0-9a-f]{64}", str(spec["sha256"]))), "invalid archive SHA")
    for key in ("fight", "actor", "encounter", "page"):
        require(integer(spec[key], positive=True), f"invalid {key}")
    require(integer(spec["row"]), "invalid row index")
    for key in ("archive", "report", "player", "realm", "class", "category", "leaderboard_member"):
        require(type(spec[key]) is str and bool(spec[key]), f"missing {key}")
    require(bool(re.fullmatch(r"[A-Za-z0-9]+", spec["report"])), "invalid report code")
    require(
        spec["role"] in {"balance-dps", "feral-dps", "feral-tank", "dps", "tank"},
        "unsupported DPS role; do not use healer ranking caches",
    )
    excluded = spec["excluded_game_ids"]
    require(
        isinstance(excluded, list)
        and all(integer(x, positive=True) for x in excluded)
        and len(excluded) == len(set(excluded)),
        "invalid or duplicate exclusion IDs",
    )


def compute(spec: dict[str, Any], base: Path) -> dict[str, Any]:
    validate_spec(spec)
    archive_path = base / spec["archive"]
    require(archive_path.stat().st_size <= 256 * 1024 * 1024, "archive size cap")
    raw = archive_path.read_bytes()
    require(digest(raw) == spec["sha256"], "archive SHA mismatch")
    used: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos = z.infolist()
        require(len({x.filename for x in infos}) == len(infos), "duplicate ZIP members")
        require(sum(x.file_size for x in infos) <= 2 * 1024**3, "expanded archive size cap")
        require(all(x.file_size <= 128 * 1024**2 for x in infos), "member size cap")

        def read(name: str, *, decimals: bool = False) -> Any:
            content = z.read(name)
            used[name] = digest(content)
            return read_json(content, decimal_text=decimals)

        marker = read("necropsy-snapshot.json")
        require(marker.get("kind") == "necropsy.live-snapshot", "not a live snapshot")
        require(
            type(marker.get("formatVersion")) is int and marker["formatVersion"] in (1, 2, 3),
            "unsupported snapshot version",
        )
        code, fid, owner = spec["report"], spec["fight"], spec["actor"]
        require(marker.get("endpoint") in {"user", "client"}, "unknown snapshot endpoint")
        selected = one(
            [
                f
                for f in marker["fights"]
                if f.get("reportID") == code
                and type(f.get("fightID")) is int
                and f["fightID"] == fid
            ],
            "fight not uniquely selected in snapshot",
        )
        one(
            [
                p
                for p in selected["participants"]
                if p.get("player") == spec["player"]
                and p.get("server") == spec["realm"]
                and p.get("spec") == spec["category"]
                and type(p.get("encounterID")) is int
                and p["encounterID"] == spec["encounter"]
            ],
            "participant not uniquely selected in snapshot",
        )
        boss = one(
            [
                b
                for b in marker["bosses"]
                if type(b.get("encounter_id")) is int and b["encounter_id"] == spec["encounter"]
            ],
            "encounter selection not unique",
        )
        for key, value in {
            "class_name": spec["class"],
            "spec": spec["category"],
            "role": spec["role"],
            "partition": 1,
        }.items():
            require(
                boss["key"][key] == {"status": "enforced", "value": value},
                f"snapshot selected {key} mismatch",
            )
        report = read(f"reports/{code}/bundle.json")["reportData"]["report"]
        require(
            report.get("code") == code and report.get("visibility") == "public",
            "wrong/private report",
        )
        require(integer(report.get("revision")), "invalid report revision")
        report_set = one(
            [r for r in marker["report_sets"] if r.get("report") == code], "report set not unique"
        )
        canonical_report = json.dumps(
            report, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        require(
            report_set.get("sha256") == digest(canonical_report)
            and type(report_set.get("revision")) is int
            and report_set["revision"] == report["revision"],
            "report set digest/revision mismatch",
        )
        fight = one(
            [f for f in report["fights"] if type(f.get("id")) is int and f["id"] == fid],
            "fight not unique",
        )
        require(
            type(fight.get("encounterID")) is int
            and fight["encounterID"] == spec["encounter"]
            and fight.get("kill") is True,
            "wrong encounter or not a kill",
        )
        start, end = fight["startTime"], fight["endTime"]
        require(integer(start) and integer(end) and end > start, "invalid fight bounds")
        catalog = report["masterData"]["actors"]
        require(all(type(a.get("id")) is int for a in catalog), "invalid catalog identity")
        actors = {a["id"]: a for a in catalog}
        require(len(actors) == len(catalog), "duplicate catalog identity")
        actor = actors[owner]
        require(
            (actor.get("type"), actor.get("name"), actor.get("server"), actor.get("subType"))
            == ("Player", spec["player"], spec["realm"], spec["class"]),
            "wrong owner identity",
        )
        require(
            all(integer(x, positive=True) for x in fight["friendlyPlayers"])
            and owner in fight["friendlyPlayers"],
            "owner absent from friendly players",
        )
        prefix = f"events/{code}/fight_{fid}/"

        def folder(actor_id: int, role: str) -> str:
            return str(
                one(
                    sorted(
                        {
                            n.rsplit("/", 1)[0]
                            for n in z.namelist()
                            if n.startswith(f"{prefix}{role}_{actor_id}_")
                        }
                    ),
                    f"no unique {role} folder for {actor_id}",
                )
            )

        def encounter_scope(
            code: str, fid: int, revision: object, start: int, end: int
        ) -> tuple[list[dict[str, Any]], list[str]]:
            """The fight's complete encounter-All events, certified from the marker proof."""
            proof = one(
                [
                    p
                    for p in marker.get("encounter_streams") or ()
                    if (p.get("report"), p.get("fight"), p.get("role")) == (code, fid, "encounter")
                ],
                "encounter scope not unique",
            )
            identity = proof.get("identity")
            require(
                proof.get("actor_id") is None
                and proof.get("direction") == "all"
                and isinstance(identity, dict)
                and set(identity) == ENCOUNTER_ALL_FIELDS,
                "encounter scope is not an exact encounter-All request",
            )
            expected = {
                "code": code,
                "fight": fid,
                "actor_id": None,
                "role": "encounter",
                "direction": "all",
                "revision": revision,
                "data_type": "All",
                "include_resources": True,
                "translate": True,
                "site": "vanilla.warcraftlogs.com",
                "endpoint": marker["endpoint"],
                "query_version": 1,
            }
            require(
                all(
                    type(identity.get(k)) is type(v) and identity[k] == v
                    for k, v in expected.items()
                )
                and integer(identity.get("limit"), positive=True)
                and identity.get("start_time") == start
                and identity.get("end_time") == end
                and type(identity.get("start_time")) in (int, float)
                and type(identity.get("end_time")) in (int, float),
                "encounter scope identity mismatch",
            )
            prefix = f"events/{code}/fight_{fid}/encounter/all_"
            names = sorted(n for n in z.namelist() if n.startswith(prefix))
            digests = [digest(z.read(n)) for n in names]
            require(bool(names) and proof.get("pages") == digests, "encounter scope pages differ")
            for name in names:
                read(name)  # reject duplicate keys/nonfinite constants before page validation
            return [event for event, _, _ in pages._pages(z, prefix, start, end, fid)], digests

        owner_folder = folder(owner, "player")
        listing = read(f"{owner_folder}/pets.json")
        require(isinstance(listing, list), "missing explicit pet listing")
        require(
            all(
                integer(p.get("id"), positive=True)
                and type(p.get("petOwner")) is int
                and p["petOwner"] == owner
                for p in listing
            ),
            "invalid pet listing",
        )
        pet_ids = [p["id"] for p in listing]
        require(len(set(pet_ids)) == len(pet_ids), "duplicate pet listing")
        fight_pets = fight["friendlyPets"]
        require(
            all(
                integer(p.get("id"), positive=True) and type(p.get("petOwner")) is int
                for p in fight_pets
            ),
            "unresolved fight pet ownership",
        )
        catalog_owned = {
            a["id"]
            for a in catalog
            if a.get("petOwner") == owner and type(a.get("petOwner")) is int
        }
        require(
            set(pet_ids) == {p["id"] for p in fight_pets if p["petOwner"] == owner}
            and set(pet_ids) <= catalog_owned,
            "pet listings disagree",
        )
        out_of_scope = []
        if catalog_owned != set(pet_ids):
            # A report-catalog pet the fight does not list is out of this fight's scope
            # only if the fight's certified encounter-All pages never name it (D022).
            listed = {p["id"] for p in fight_pets}
            extras = sorted(catalog_owned - set(pet_ids))
            require(not listed & set(extras), "pet listings disagree")
            scope, scope_pages = encounter_scope(code, fid, report["revision"], start, end)
            for pet in extras:
                require(
                    not any(pet in (e.get("sourceID"), e.get("targetID")) for e in scope),
                    "pet listings disagree",
                )
                out_of_scope.append(
                    {"pet": pet, "rule": "catalog-pet-absent-from-fight-v1", "pages": scope_pages}
                )
        for pet in listing:
            require(
                actors[pet["id"]].get("petOwner") == owner
                and type(actors[pet["id"]].get("petOwner")) is int
                and actors[pet["id"]].get("gameID") == pet.get("gameID"),
                "pet catalog mismatch",
            )

        observations: dict[str, list[dict[str, Any]]] = {}
        combined: Counter[str] = Counter()
        source_totals: dict[str, int] = {}
        for source in [owner, *pet_ids]:
            role = "player" if source == owner else "pet"
            stream_folder = owner_folder if source == owner else folder(source, role)
            merged: Counter[str] = Counter()
            for direction in ("source", "target"):
                proof = one(
                    [
                        p
                        for p in marker["streams"]
                        if (
                            p.get("report"),
                            p.get("fight"),
                            p.get("actor_id"),
                            p.get("role"),
                            p.get("direction"),
                        )
                        == (code, fid, source, role, direction)
                    ],
                    "stream proof not unique",
                )
                identity = proof["identity"]
                requested = {"actor_id": source, "role": role, "direction": direction}
                parent_names: list[str] = []
                if "derivation" in proof:
                    # A derived target stream was never requested: certify its parent,
                    # the same fight's encounter-All request, and require its bytes.
                    derivation = proof["derivation"]
                    require(
                        marker["formatVersion"] == 3
                        and direction == "target"
                        and identity is None
                        and isinstance(derivation, dict)
                        and set(derivation) == {"rule", "parent", "parent_pages"}
                        and derivation["rule"] == "target-equals-encounter-all-v1",
                        "invalid stream derivation",
                    )
                    parent = one(
                        [
                            p
                            for p in marker.get("encounter_streams") or ()
                            if (p.get("report"), p.get("fight"), p.get("role"))
                            == (code, fid, "encounter")
                        ],
                        "derivation parent not unique",
                    )
                    zone = marker.get("zone") or {}
                    require(
                        type(zone.get("id")) is int
                        and zone["id"] in DERIVED_TARGET_ZONES
                        and type(zone.get("partition")) is int
                        and zone["partition"] in ENCOUNTER_PARTITIONS,
                        "derived streams are not defined for this zone or partition",
                    )
                    require(
                        parent.get("actor_id") is None
                        and parent.get("direction") == "all"
                        and isinstance(parent.get("identity"), dict)
                        and set(parent["identity"]) == ENCOUNTER_ALL_FIELDS,
                        "derivation parent is not an exact encounter-All request",
                    )
                    require(
                        derivation["parent"] == parent["identity"]
                        and derivation["parent_pages"] == parent.get("pages") == proof["pages"],
                        "derivation names another request than its parent",
                    )
                    identity = parent["identity"]
                    requested = {"actor_id": None, "role": "encounter", "direction": "all"}
                    parent_names = [
                        f"events/{code}/fight_{fid}/encounter/all_{n:03d}.json"
                        for n in range(1, len(parent["pages"]) + 1)
                    ]
                    present = sorted(
                        n
                        for n in z.namelist()
                        if n.startswith(f"events/{code}/fight_{fid}/encounter/all_")
                    )
                    require(
                        present == parent_names
                        and parent["pages"] == [digest(z.read(n)) for n in parent_names],
                        "derivation parent pages are not exactly its listed pages",
                    )
                require(isinstance(identity, dict), "stream request identity missing")
                expected = {
                    "code": code,
                    "fight": fid,
                    **requested,
                    "revision": report["revision"],
                    "data_type": "All",
                    "include_resources": True,
                    "translate": True,
                    "site": "vanilla.warcraftlogs.com",
                    "endpoint": marker["endpoint"],
                    "query_version": 1,
                }
                require(
                    all(
                        type(identity.get(k)) is type(v) and identity[k] == v
                        for k, v in expected.items()
                    ),
                    "stream request identity mismatch",
                )
                require(
                    integer(identity.get("limit"), positive=True), "invalid stream request limit"
                )
                require(
                    identity.get("start_time") == start
                    and identity.get("end_time") == end
                    and type(identity.get("start_time")) in (int, float)
                    and type(identity.get("end_time")) in (int, float),
                    "stream bounds mismatch",
                )
                names = sorted(
                    n for n in z.namelist() if n.startswith(f"{stream_folder}/{direction}_")
                )
                require(
                    bool(names) and proof["pages"] == [digest(z.read(n)) for n in names],
                    "stream page hashes mismatch",
                )
                require(
                    not parent_names
                    or (
                        len(parent_names) == len(names)
                        and all(
                            z.read(a) == z.read(b) for a, b in zip(names, parent_names, strict=True)
                        )
                    ),
                    "derived pages are not their parent's bytes",
                )
                for name in names:
                    read(name)  # reject duplicate keys/nonfinite constants before page validation
                # Reuse the independent raw page validator, never the snapshot/analyzer reader.
                located = pages._pages(z, f"{stream_folder}/{direction}_", start, end, fid)
                counts: Counter[str] = Counter()
                for event, name, index in located:
                    if event.get("type") != "damage":
                        continue
                    require(type(event.get("sourceID")) is int, "damage source unresolved")
                    if event["sourceID"] != source:
                        continue
                    require(
                        type(event.get("targetID")) is int and event["targetID"] in actors,
                        "damage target unresolved",
                    )
                    require(
                        integer(event.get("amount")), "damage amount missing/noninteger/negative"
                    )
                    require(
                        integer(actors[event["targetID"]].get("gameID")),
                        "target game ID unresolved",
                    )
                    key = json.dumps(
                        event, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                    )
                    counts[key] += 1
                    observations.setdefault(key, []).append({"member": name, "index": index})
                merged |= counts
            source_totals[str(source)] = sum(
                read_json(k.encode())["amount"] * n for k, n in merged.items()
            )
            combined.update(merged)

        own = {owner, *pet_ids}
        totals = {"raw": 0, "self": 0, "excluded": 0, "ranked": 0}
        events = []
        for key, count in sorted(combined.items()):
            event = read_json(key.encode())
            target = event["targetID"]
            disposition = (
                "self"
                if target in own
                else (
                    "excluded"
                    if actors[target]["gameID"] in spec["excluded_game_ids"]
                    else "ranked"
                )
            )
            totals["raw"] += event["amount"] * count
            totals[disposition] += event["amount"] * count
            events.append(
                {
                    "raw": event,
                    "multiplicity": count,
                    "disposition": disposition,
                    "locators": observations[key],
                }
            )
        require(bool(events), "no observed outgoing damage")
        published_page = read(spec["leaderboard_member"], decimals=True)
        require(
            type(published_page.get("partition")) is int and published_page["partition"] == 1,
            "published partition mismatch",
        )
        require(
            type(published_page["encounter"]["id"]) is int
            and published_page["encounter"]["id"] == spec["encounter"],
            "leaderboard encounter mismatch",
        )
        page = one(
            [
                p
                for p in published_page["pages"]
                if p.get("page") == spec["page"] and type(p.get("page")) is int
            ],
            "leaderboard page not unique",
        )
        row = page["characterRankings"]["rankings"][spec["row"]]
        require(
            (
                row["report"]["code"],
                row["report"]["fightID"],
                row["name"],
                row["server"]["name"],
                row["class"],
                row["spec"],
            )
            == (code, fid, spec["player"], spec["realm"], spec["class"], spec["category"]),
            "published identity/category mismatch",
        )
        require(
            type(row["report"]["fightID"]) is int
            and type(row["duration"]) is int
            and row["duration"] == end - start,
            "published duration mismatch",
        )
        amount = row["amount"]
        require(type(amount) in (str, int), "invalid published amount")
        published = str(amount)
        if not consistent(totals["ranked"], end - start, published):
            raise ArithmeticMismatch("published DPS contradicts raw")
        result = {
            "version": 1,
            "status": "draft actor-scoped arithmetic; not a validated cell policy",
            "spec": spec,
            "duration_ms": end - start,
            "published": published,
            "residual": str(Fraction(totals["ranked"] * 1000, end - start) - Fraction(published)),
            "totals": totals,
            "source_damage": source_totals,
            "owned_actor_ids": pet_ids,
            "events": events,
            "members_used": used,
            "tool_sha256": digest(Path(__file__).read_bytes()),
            "page_validator_sha256": digest(Path(pages.__file__).read_bytes()),
            "limits": [
                "Actor streams only; no encounter-wide completeness or full snapshot eligibility.",
                "Exclusions are explicit inputs, never fitted; a match is not a cell policy.",
                "No inferred assignment, opportunity, phase, position or player grade.",
            ],
        }
        if out_of_scope:
            result["catalog_pets_out_of_scope"] = out_of_scope
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "check"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        data = read_json(args.input.read_bytes())
        if args.command == "check":
            result = compute(data["spec"], args.input.resolve().parent)
            changes = pages.differences(data, result)
            print("\n".join([*changes, f"{len(changes)} difference(s)"]))
            return int(bool(changes))
        require(args.out is not None, "freeze requires --out")
        out = args.out.resolve()
        require(not out.exists(), "output exists; use a fresh draft path")
        result = compute(data, args.input.resolve().parent)
        result["spec"]["archive"] = Path(
            os.path.relpath(args.input.resolve().parent / data["archive"], out.parent)
        ).as_posix()
        out.write_bytes((json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        print(f"froze {len(result['events'])} distinct raw damage rows")
        return 0
    except (ValueError, KeyError, IndexError, TypeError, OSError, zipfile.BadZipFile) as error:
        print(f"DPS freeze refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
