"""Re-enumerate the frozen observations with the separate fact-freeze page parser."""

import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

root = Path.cwd()
sys.path.insert(0, str(root))

from scripts import fact_freeze  # noqa: E402

path = Path(__file__).with_name("observations.json")
facts = json.loads(path.read_bytes())
assert (
    facts["recipe_sha256"] == hashlib.sha256(path.with_name("generate.py").read_bytes()).hexdigest()
)
assert (
    facts["intake_sha256"]
    == hashlib.sha256((root / "tests/golden/raids/naxx-v2-intake.json").read_bytes()).hexdigest()
)
archive = root / (
    "tests/golden/raids/raw/naxx-balance-v2-measurement/77619978-2006-20261023T152230.zip"
)
assert hashlib.sha256(archive.read_bytes()).hexdigest() == facts["archive_sha256"]
types = {
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
}
contexts = casts_checked = occurrences_checked = 0


def canonical(event):
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


with zipfile.ZipFile(archive) as bundle:
    for context in facts["contexts"]:
        report = json.loads(bundle.read(f"reports/{context['report']}/bundle.json"))["reportData"][
            "report"
        ]
        fight = next(f for f in report["fights"] if f["id"] == context["fight"])
        start, end = fight["startTime"], fight["endTime"]
        actors = {a["id"]: a for a in report["masterData"]["actors"]}
        npcs = {n["id"] for n in fight["enemyNPCs"]}
        assert npcs == {int(n) for n in context["enemy_npc_catalog"]}
        for npc in npcs:
            assert actors[npc]["type"] == "NPC"
            assert actors[npc]["gameID"] == context["enemy_npc_catalog"][str(npc)]["game_id"]
        events = [
            item
            for item in fact_freeze.all_stream(
                bundle, context["report"], context["fight"], start, end
            )
            if item[0].get("sourceID") in npcs and item[0]["type"] in types
        ]
        assert len(events) == context["maximum_raw_occurrences"]
        observed = Counter(canonical(event) for event, _, _ in events if event["type"] == "cast")
        expected = Counter({canonical(row["raw"]): row["multiplicity"] for row in context["casts"]})
        assert observed == expected
        grouped = Counter()
        times = {}
        unbound = Counter()
        for event, _, _ in events:
            ability = event.get("abilityGameID")
            if type(ability) is not int or ability < 0:
                unbound[canonical(event)] += 1
                continue
            key = (event["sourceID"], ability, event["type"])
            grouped[key] += 1
            times.setdefault(key, []).append(event["timestamp"] - start)
        assert unbound == Counter(
            {
                canonical(row["raw"]): row["multiplicity"]
                for row in context["unbound_ability_events"]
            }
        )
        assert grouped == Counter(
            {
                (row["source_actor"], row["ability_id"], row["event_type"]): row["raw_occurrences"]
                for row in context["positive_groups"]
            }
        )
        for row in context["positive_groups"]:
            key = (row["source_actor"], row["ability_id"], row["event_type"])
            assert (row["first_ms"], row["last_ms"]) == (min(times[key]), max(times[key]))
        witness_pages = {}
        for row in context["casts"]:
            for locator in row["locators"]:
                member = locator["member"]
                if member not in witness_pages:
                    witness_pages[member] = json.loads(bundle.read(member))["data"]
                event = witness_pages[member][locator["index"]]
                assert event == row["raw"]
        contexts += 1
        casts_checked += sum(observed.values())
        occurrences_checked += len(events)

assert contexts == 15
print(
    json.dumps(
        {
            "contexts_checked": contexts,
            "cast_occurrences_checked": casts_checked,
            "raw_occurrences_checked": occurrences_checked,
            "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "page_validator_sha256": hashlib.sha256(
                Path(fact_freeze.__file__).read_bytes()
            ).hexdigest(),
            "scope": "Separate parser agreement only; no domain acceptance.",
        }
    )
)
