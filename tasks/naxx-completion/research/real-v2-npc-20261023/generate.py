"""Positive NPC observations from selected real-v2 All pages; no analyzer/rules imports."""

import argparse
import collections
import hashlib
import json
import zipfile
from pathlib import Path

root = Path.cwd()
work = root / "workspace/codex-naxx/measurement-20261022"
archive = (
    root / "tests/golden/raids/raw/naxx-balance-v2-measurement/77619978-2006-20261023T152230.zip"
)
intake = json.loads((root / "tests/golden/raids/naxx-v2-intake.json").read_bytes())
rows = []
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, required=True)
destination = parser.parse_args().out.resolve()
if not destination.is_relative_to(root / "workspace") or destination.exists():
    raise SystemExit("choose a fresh output file under workspace/")
assert hashlib.sha256(archive.read_bytes()).hexdigest() == intake["archive"]["sha256"]
assert len(intake["updated_actor_sources"]) == 15


def key(r):
    return json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


with zipfile.ZipFile(archive) as z:
    marker = json.loads(z.read("necropsy-snapshot.json"))
    for selected in intake["updated_actor_sources"]:
        src = selected["new_actor_source"]
        report_code = src["report"]
        fight_id = src["fight"]
        eid = int(selected["cell_id"].split("/")[1])
        bundle_name = f"reports/{report_code}/bundle.json"
        report = json.loads(z.read(bundle_name))["reportData"]["report"]
        assert report["visibility"] == "public"
        fight = next(f for f in report["fights"] if f["id"] == fight_id)
        assert fight["encounterID"] == eid and fight["kill"] is True
        start, end = fight["startTime"], fight["endTime"]
        catalog = {a["id"]: a for a in report["masterData"]["actors"]}
        assert len(catalog) == len(report["masterData"]["actors"])
        npcs = {}
        for npc in fight["enemyNPCs"]:
            actor = catalog[npc["id"]]
            assert (
                actor["type"] == "NPC"
                and type(actor["gameID"]) is int
                and actor["gameID"] == npc["gameID"]
            )
            npcs[npc["id"]] = {
                "game_id": actor["gameID"],
                "name": actor["name"],
                "instances": npc.get("instanceCount"),
                "pet_owner": actor.get("petOwner"),
            }
        proof = next(
            s
            for s in marker["encounter_streams"]
            if (s["report"], s["fight"], s["role"]) == (report_code, fight_id, "encounter")
        )
        assert proof["direction"] == "all" and proof["actor_id"] is None
        identity = proof["identity"]
        assert (
            identity["revision"] == report["revision"]
            and identity["start_time"] == start
            and identity["end_time"] == end
        )
        all_counter = collections.Counter()
        raw_rows = {}
        locators = collections.defaultdict(list)
        members = {bundle_name: hashlib.sha256(z.read(bundle_name)).hexdigest()}
        page_overlap = 0
        seen = set()
        for page_index, digest in enumerate(proof["pages"], 1):
            name = f"events/{report_code}/fight_{fight_id}/encounter/all_{page_index:03d}.json"
            raw = z.read(name)
            assert hashlib.sha256(raw).hexdigest() == digest
            members[name] = digest
            page = json.loads(raw)
            assert (page.get("nextPageTimestamp") is None) == (page_index == len(proof["pages"]))
            counter = collections.Counter()
            for index, event in enumerate(page["data"]):
                if event.get("sourceID") not in npcs or event.get("type") not in {
                    "cast",
                    "damage",
                    "applybuff",
                    "removebuff",
                    "refreshbuff",
                    "applybuffstack",
                    "removebuffstack",
                    "applydebuff",
                    "removedebuff",
                    "refreshdebuff",
                    "applydebuffstack",
                    "removedebuffstack",
                }:
                    continue
                assert (
                    type(event["sourceID"]) is int
                    and type(event["timestamp"]) is int
                    and start <= event["timestamp"] <= end
                )
                canonical = key(event)
                counter[canonical] += 1
                raw_rows[canonical] = event
                locators[canonical].append({"member": name, "index": index})
            page_overlap += len(seen & counter.keys())
            seen.update(counter)
            all_counter |= counter
        grouped = {}
        unbound = []
        cast_rows = []
        for canonical, multiplicity in all_counter.items():
            event = raw_rows[canonical]
            ability = event.get("abilityGameID")
            npc = npcs[event["sourceID"]]
            if type(ability) is not int or ability < 0:
                unbound.append(
                    {"raw": event, "multiplicity": multiplicity, "locators": locators[canonical]}
                )
                continue
            group_key = f"{event['sourceID']}:{ability}:{event['type']}"
            group = grouped.setdefault(
                group_key,
                {
                    "source_actor": event["sourceID"],
                    "source_game_id": npc["game_id"],
                    "ability_id": ability,
                    "event_type": event["type"],
                    "raw_occurrences": 0,
                    "first_ms": event["timestamp"] - start,
                    "last_ms": event["timestamp"] - start,
                    "first_locator": locators[canonical][0],
                },
            )
            group["raw_occurrences"] += multiplicity
            group["first_ms"] = min(group["first_ms"], event["timestamp"] - start)
            group["last_ms"] = max(group["last_ms"], event["timestamp"] - start)
            if event["type"] == "cast":
                cast_rows.append(
                    {
                        "source_actor": event["sourceID"],
                        "source_game_id": npc["game_id"],
                        "ability_id": ability,
                        "at_ms": event["timestamp"] - start,
                        "raw": event,
                        "multiplicity": multiplicity,
                        "locators": locators[canonical],
                    }
                )
        rows.append(
            {
                "cell_id": selected["cell_id"],
                "report": report_code,
                "revision": report["revision"],
                "fight": fight_id,
                "duration_ms": end - start,
                "selected_actor": src["actor"],
                "selected_source_kind": selected["source_kind"],
                "enemy_npc_catalog": npcs,
                "all_pages": len(proof["pages"]),
                "maximum_raw_occurrences": sum(all_counter.values()),
                "duplicate_canonical_rows_across_pages": page_overlap,
                "members_sha256": members,
                "positive_groups": list(grouped.values()),
                "casts": sorted(
                    cast_rows, key=lambda r: (r["at_ms"], r["source_actor"], r["ability_id"])
                ),
                "unbound_ability_events": unbound,
            }
        )
        print(eid, "NPC observations", sum(all_counter.values()), flush=True)
receipt = {
    "kind": (
        "Positive NPC-source observations from 15 hash-bound complete All contexts; "
        "no rules/analyzer imports"
    ),
    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "contexts": rows,
    "scope": (
        "One selected context per boss: 14 primary and a separately verified "
        "comparison actor for Kel'Thuzad."
    ),
    "limits": [
        (
            "Only numeric source membership in raw enemyNPCs/masterData is established; "
            "names do not prove a mechanic, immunity, assignment or ownership."
        ),
        (
            "Counts use maximum canonical multiplicity across page observations; "
            "overlap and raw instance ambiguity remain explicit."
        ),
        (
            "Relative time is measured from recorded fight bounds, "
            "not an inferred full-pull or phase start."
        ),
        (
            "No absence, aura lifetime, target opportunity, fixed cadence, player grade, "
            "source conflict resolution or validated cell follows."
        ),
        (
            "Per-stream integrity/completeness comes from the separately committed full "
            "archive/scope inventory; these are positive observations only."
        ),
    ],
}
destination.parent.mkdir(parents=True, exist_ok=True)
receipt["recipe_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
receipt["intake_sha256"] = hashlib.sha256(
    (root / "tests/golden/raids/naxx-v2-intake.json").read_bytes()
).hexdigest()
with destination.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(receipt, indent=2) + "\n")
print("Contexts", len(rows), "casts", sum(len(r["casts"]) for r in rows))
