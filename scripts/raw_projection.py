"""Independent raw derivation proof for freezer/oracle tools; no analyzer or projector imports."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any


def verify_projection(
    archive: Any,
    marker: dict[str, Any],
    proof: dict[str, Any],
    report: dict[str, Any],
) -> list[bytes]:
    """Prove parent identity, complete chain, original ownership and exact child bytes."""

    def require(value: Any, reason: str) -> None:
        if not value:
            raise ValueError(reason)

    def read(name: str) -> bytes:
        require(name in names, "raw projection proof member is missing")
        return bytes(archive.read(name) if hasattr(archive, "read") else archive.read_bytes(name))

    names = archive.namelist() if hasattr(archive, "namelist") else archive.names()
    derivation = proof.get("derivation")
    require(
        isinstance(derivation, dict) and proof.get("identity") is None and proof.get("meta") == {},
        "derived stream claims a request or costs",
    )
    assert isinstance(derivation, dict)
    rule = derivation.get("rule")
    source = rule == "source-owned-encounter-all-v1"
    critical = rule == "critical-hit-type-encounter-all-v1"
    target = rule == "target-equals-encounter-all-v1"
    require(target or source or critical, "unknown derivation rule")
    require(
        marker.get("formatVersion") == 4 or (target and marker.get("formatVersion") == 3),
        "derivation format mismatch",
    )
    require(
        set(derivation)
        == (
            {"rule", "parent", "parent_pages", "actor_ids"}
            if source
            else {"rule", "parent", "parent_pages"}
        ),
        "derivation fields differ",
    )
    require(
        (
            critical
            and proof["role"] == "critical"
            and proof["direction"] == "all"
            and proof["actor_id"] is None
        )
        or (
            (source or target)
            and proof["role"] in {"player", "pet"}
            and proof["direction"] == ("source" if source else "target")
            and type(proof["actor_id"]) is int
            and proof["actor_id"] > 0
        ),
        "projection scope differs",
    )
    code, fid = proof["report"], proof["fight"]
    require(
        type(marker["zone"]["id"]) is int
        and marker["zone"]["id"]
        in ({2000, 2002, 2005, 2006} if marker["formatVersion"] == 4 else {2006})
        and type(marker["zone"]["partition"]) is int
        and marker["zone"]["partition"] in (1, 2),
        "projection is not defined for this raid/partition",
    )
    parents = [
        p
        for p in marker["encounter_streams"]
        if (p["report"], p["fight"], p["role"]) == (code, fid, "encounter")
    ]
    require(len(parents) == 1, "projection has no unique parent")
    parent = parents[0]
    require(
        parent.get("derivation") is None
        and parent.get("actor_id") is None
        and parent.get("direction") == "all",
        "projection parent is not requested All",
    )
    identity = parent.get("identity")
    require(isinstance(identity, dict), "missing parent request")
    fights = [f for f in report["fights"] if f["id"] == fid]
    require(len(fights) == 1, "projection fight is not unique")
    fight = fights[0]
    expected = dict(
        site="vanilla.warcraftlogs.com",
        code=code,
        revision=report["revision"],
        fight=fid,
        actor_id=None,
        role="encounter",
        direction="all",
        data_type="All",
        limit=10000,
        include_resources=True,
        translate=True,
        query_version=1,
        endpoint=marker["endpoint"],
        start_time=float(fight["startTime"]),
        end_time=float(fight["endTime"]),
    )
    require(
        all(
            type(identity.get(k)) in (int, float) and math.isfinite(identity[k])
            for k in ("start_time", "end_time")
        ),
        "parent bounds are mistyped",
    )
    require(
        identity == expected and set(identity) == set(expected), "parent request identity differs"
    )
    require(
        all(
            type(identity[k]) is type(v)
            for k, v in expected.items()
            if k not in {"start_time", "end_time"}
        ),
        "parent request field types differ",
    )
    require(
        derivation["parent"] == identity and derivation["parent_pages"] == parent["pages"],
        "projection parent binding differs",
    )
    prefix = f"events/{code}/fight_{fid}/"
    parent_names = sorted(
        n for n in names if re.fullmatch(re.escape(prefix) + r"encounter/all_\d{3}\.json", n)
    )
    require(
        parent_names
        and parent_names
        == [f"{prefix}encounter/all_{i:03d}.json" for i in range(1, len(parent_names) + 1)],
        "parent pages not contiguous",
    )
    bodies = [read(n) for n in parent_names]
    require(
        [hashlib.sha256(b).hexdigest() for b in bodies] == parent["pages"],
        "parent page digests differ",
    )
    pages = [json.loads(b) for b in bodies]
    floor, end = fight["startTime"], fight["endTime"]
    for index, page in enumerate(pages):
        require(
            set(page) == {"data", "nextPageTimestamp"} and isinstance(page["data"], list),
            "invalid parent page",
        )
        require(
            all(
                isinstance(e, dict)
                and type(e.get("timestamp")) in (int, float)
                and math.isfinite(e["timestamp"])
                and floor <= e["timestamp"] <= end
                for e in page["data"]
            ),
            "parent event timestamps invalid",
        )
        cursor = page["nextPageTimestamp"]
        if index == len(pages) - 1:
            require(cursor is None, "parent not complete")
        else:
            require(
                type(cursor) in (int, float) and math.isfinite(cursor) and floor < cursor <= end,
                "parent cursor not progressive",
            )
            floor = cursor
    ids: set[int] = set()
    if source:
        original_name = f"reports/{code}/fight_{fid}.json"
        original_bytes = read(original_name)
        entries = [
            e
            for boss in marker["bosses"]
            for e in [boss.get("subject"), *(boss.get("cohort") or []), boss.get("cross_faction")]
            if e and e.get("status") == "complete" and (e["report"], e["fight"]) == (code, fid)
        ]
        generations = [e["bundle_generation"] for e in entries]
        require(
            generations
            and all(
                g["sha256"] == hashlib.sha256(original_bytes).hexdigest()
                and (g["report"], g["fight"], g["revision"]) == (code, fid, report["revision"])
                for g in generations
            ),
            "original acquisition digest differs",
        )
        original = json.loads(original_bytes)
        scoped = original["report"]
        require(
            original["endpoint"] == marker["endpoint"]
            and scoped["code"] == code
            and scoped["revision"] == report["revision"]
            and len(scoped["fights"]) == 1
            and scoped["fights"][0]["id"] == fid,
            "original acquisition scope differs",
        )
        require(
            all(
                scoped["fights"][0][k] == fight[k] for k in ("encounterID", "startTime", "endTime")
            ),
            "original fight bounds differ",
        )
        catalog = scoped["masterData"]["actors"]
        require(
            all(
                type(a.get("id")) is int
                and (a["id"] > 0 or (a["id"] == -1 and a.get("petOwner") is None))
                for a in catalog
            ),
            "invalid catalog ids",
        )
        owners = {a["id"]: a.get("petOwner") for a in catalog}
        require(len(owners) == len(catalog), "duplicate catalog actor")
        require(
            all(o is None or (type(o) is int and o > 0) for o in owners.values()),
            "invalid catalog ownership",
        )
        require(
            isinstance(scoped["fights"][0].get("friendlyPets"), list),
            "fight ownership listing missing",
        )
        seen_pets: set[int] = set()
        for pet in scoped["fights"][0]["friendlyPets"]:
            require(
                type(pet.get("id")) is int and pet["id"] > 0 and pet["id"] not in seen_pets,
                "duplicate or invalid fight unit",
            )
            seen_pets.add(pet["id"])
            require(pet["id"] in owners, "fight unit missing from catalog")
            require(
                type(pet.get("petOwner")) is int
                and pet["petOwner"] > 0
                and next(a for a in catalog if a["id"] == pet["id"]).get("type") == "Pet",
                "fight ownership completeness is unknown",
            )
            if pet.get("petOwner") is not None:
                require(owners[pet["id"]] in (None, pet["petOwner"]), "ownership conflict")
                owners[pet["id"]] = pet["petOwner"]
        require(proof["actor_id"] in owners, "source actor missing")
        ids = {proof["actor_id"]}
        while True:
            enlarged = ids | {i for i, o in owners.items() if o in ids}
            if enlarged == ids:
                break
            ids = enlarged
        for unit in ids:
            seen: set[int] = set()
            node = unit
            while node is not None:
                require(
                    type(node) is int and node in owners and node not in seen,
                    "invalid ownership chain",
                )
                seen.add(node)
                node = owners[node]
        root = proof["actor_id"]
        while owners[root] is not None:
            root = owners[root]
        root_actor = next(a for a in catalog if a["id"] == root)
        require(
            root_actor.get("type") == "Player"
            and any(
                e["player"] == root_actor.get("name") and isinstance(e.get("pets"), list)
                for e in entries
            ),
            "source ownership completeness is unknown",
        )
        require(
            sorted(ids) == derivation["actor_ids"]
            and all(type(i) is int and i > 0 for i in derivation["actor_ids"]),
            "derived actor ids differ from original ownership",
        )
    projected: list[bytes] = []
    for page in pages:
        if target:
            projected.append(bodies[len(projected)])
            continue
        if critical:
            require(
                all(
                    e.get("type") != "damage"
                    or (
                        type(e.get("hitType")) is int
                        and e["hitType"] in {0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 14, 15, 16, 17}
                    )
                    for e in page["data"]
                ),
                "critical projection has an unknown hit type",
            )
        rows = [
            e
            for e in page["data"]
            if target
            or (source and (e.get("sourceID") in ids or e.get("targetID") in ids))
            or (critical and e.get("type") == "damage" and e["hitType"] in {2, 5, 17})
        ]
        projected.append(
            json.dumps(
                {"data": rows, "nextPageTimestamp": page["nextPageTimestamp"]},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        )
    suffix = "critical" if critical else proof["direction"]
    expression = re.escape(prefix) + (
        r"encounter/critical_\d{3}\.json"
        if critical
        else rf"{proof['role']}_{proof['actor_id']}_[^/]+/{suffix}_\d{{3}}\.json"
    )
    children = sorted(n for n in names if re.fullmatch(expression, n))
    require(
        len(children) == len(projected)
        and [hashlib.sha256(read(n)).hexdigest() for n in children] == proof["pages"]
        and all(read(n) == b for n, b in zip(children, projected, strict=True)),
        "child is not the exact ordered projection",
    )
    return projected
