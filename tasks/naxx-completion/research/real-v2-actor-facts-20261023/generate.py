"""Freeze positive selected-actor observations and cross-check raw multiplicity."""

import argparse
import hashlib
import json
import os
import sys
import zipfile
from collections import Counter
from pathlib import Path

root = Path.cwd()
sys.path.insert(0, str(root))
from scripts import fact_freeze as ff  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, required=True)
out = parser.parse_args().out.resolve()
if out.exists() or not out.is_relative_to(root / "workspace"):
    raise SystemExit("choose a fresh directory under workspace/")
intake_path = root / "tests/golden/raids/naxx-v2-intake.json"
catalog_path = root / "tests/golden/raids/naxx-capability-source-review.json"
intake = json.loads(intake_path.read_bytes())
catalog = json.loads(catalog_path.read_bytes())
archive = root / intake["archive"]["path"]
assert hashlib.sha256(archive.read_bytes()).hexdigest() == intake["archive"]["sha256"]
out.mkdir(parents=True)
types = ["applydebuff", "removedebuff", "applydebuffstack", "removedebuffstack", "refreshdebuff"]
rows = []


def canonical(event):
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def projection(event, kind, start):
    if kind == "casts":
        return event["timestamp"] - start
    if kind == "aura_transitions":
        return [event["timestamp"] - start, event["type"], event["abilityGameID"]]
    return {
        "time": event["timestamp"] - start,
        "ability": event["abilityGameID"],
        "removed_ability": event["extraAbilityGameID"],
        "recipient": event["targetID"],
        "is_buff": event["isBuff"],
        "source_instance": event.get("sourceInstance"),
        "recipient_instance": event.get("targetInstance"),
    }


with zipfile.ZipFile(archive) as z:
    marker = json.loads(z.read("necropsy-snapshot.json"))
    for selected in intake["updated_actor_sources"]:
        source = selected["new_actor_source"]
        code, fid, actor = source["report"], source["fight"], source["actor"]
        report = json.loads(z.read(f"reports/{code}/bundle.json"))["reportData"]["report"]
        player = next(a for a in report["masterData"]["actors"] if a["id"] == actor)["name"]
        fight = next(f for f in report["fights"] if f["id"] == fid)
        participant = next(
            p
            for f in marker["fights"]
            if (f["reportID"], f["fightID"]) == (code, fid)
            for p in f["participants"]
            if p["player"] == player
        )
        class_id = int(selected["cell_id"].split("/")[2])
        groups = {
            s["id"]: [s["spell_id"]]
            for s in catalog["sources"]
            if s.get("class_id") == class_id
            and type(s.get("spell_id")) is int
            and s["spell_id"] > 0
        }
        spell_ids = {i for ids in groups.values() for i in ids}
        prefix = f"events/{code}/fight_{fid}/player_{actor}_"
        folders = {n.rsplit("/", 1)[0] for n in z.namelist() if n.startswith(prefix)}
        assert len(folders) == 1
        folder = folders.pop()
        pages = {}
        union = Counter()
        for direction in ("source", "target"):
            counts = Counter()
            for member in sorted(n for n in z.namelist() if n.startswith(f"{folder}/{direction}_")):
                raw = z.read(member)
                pages[member] = hashlib.sha256(raw).hexdigest()
                for event in json.loads(raw)["data"]:
                    assert fight["startTime"] <= event["timestamp"] <= fight["endTime"]
                    if (
                        event.get("sourceID") == actor
                        and (
                            event["type"] == "dispel"
                            or (event["type"] == "cast" and event.get("abilityGameID") in spell_ids)
                        )
                    ) or (event.get("targetID") == actor and event["type"] in types):
                        counts[canonical(event)] += 1
            union |= counts
        queries = {}
        selected_rows = {}
        selectors = {
            "capability_casts_ms": lambda e, owner=actor: (
                e["type"] == "cast" and e.get("sourceID") == owner
            ),
            "personal_debuffs_ms": lambda e, owner=actor: (
                e["type"] in types and e.get("targetID") == owner
            ),
            "explicit_dispels": lambda e, owner=actor: (
                e["type"] == "dispel" and e.get("sourceID") == owner
            ),
        }
        for name, predicate in selectors.items():
            hits = Counter({k: n for k, n in union.items() if predicate(json.loads(k))})
            selected_rows[name] = hits
            if not hits:
                continue
            ids = sorted({json.loads(k)["abilityGameID"] for k in hits})
            assert all(type(i) is int and i > 0 for i in ids)
            kind = {
                "capability_casts_ms": "casts",
                "personal_debuffs_ms": "aura_transitions",
                "explicit_dispels": "dispels",
            }[name]
            queries[name] = {"kind": kind, "ids": ids, "stream": "actor", "unit": "ms"}
            if kind == "aura_transitions":
                queries[name].update(types=types, with_ability=True)
        row = {
            "cell_id": selected["cell_id"],
            "source": source,
            "actor_page_sha256": pages,
            "positive_counts": {name: sum(hits.values()) for name, hits in selected_rows.items()},
            "observed_catalog_groups": {
                name: ids
                for name, ids in groups.items()
                if any(
                    json.loads(k)["abilityGameID"] in ids
                    for k in selected_rows["capability_casts_ms"]
                )
            },
        }
        if not queries:
            row["status"] = "no selected positive rows; no absence inference"
            rows.append(row)
            continue
        spec = {
            "fixture": "real-v2-positive-selected-actor-draft",
            "archive": Path(os.path.relpath(archive, out)).as_posix(),
            "sha256": source["archive"]["sha256"],
            "note": (
                "Positive observations only; no ownership, absence, lifetime, opportunity or grade."
            ),
            "contexts": [
                {
                    "report": code,
                    "fight": fid,
                    "actor": actor,
                    "player": player,
                    "subject": participant["kind"] == "you",
                }
            ],
            "queries": queries,
        }
        facts = ff.compute(spec, out)
        for name, query in queries.items():
            expected = Counter()
            for key, count in selected_rows[name].items():
                expected[
                    canonical(projection(json.loads(key), query["kind"], fight["startTime"]))
                ] += count
            actual = facts["contexts"][0][name]
            assert Counter(canonical(value) for value in actual) == expected
            for value, (member, index) in zip(actual, facts["locators"][0][name], strict=True):
                event = json.loads(z.read(member))["data"][index]
                assert canonical(event) in selected_rows[name]
                assert projection(event, query["kind"], fight["startTime"]) == value
        slug = selected["cell_id"].replace("/", "-").lower()
        (out / f"{slug}.spec.json").write_bytes(ff._dump(spec))
        raw = ff._dump(facts)
        (out / f"{slug}.facts.json").write_bytes(raw)
        row.update(
            status="raw multiset and every retained witness agree",
            facts=f"{slug}.facts.json",
            facts_sha256=hashlib.sha256(raw).hexdigest(),
        )
        rows.append(row)
result = {
    "kind": (
        "Author independent raw enumeration versus fact-freeze; "
        "no reviewer approval or registration"
    ),
    "recipe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "intake_sha256": hashlib.sha256(intake_path.read_bytes()).hexdigest(),
    "catalog_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
    "fact_freeze_sha256": hashlib.sha256(Path(ff.__file__).read_bytes()).hexdigest(),
    "rows": rows,
    "totals": {name: sum(r["positive_counts"][name] for r in rows) for name in selectors},
}
(out / "inventory.json").write_bytes(ff._dump(result))
print(json.dumps(result["totals"]))
