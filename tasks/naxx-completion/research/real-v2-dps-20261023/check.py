"""Independent stdlib ZIP/Counter re-enumeration of accepted new-v2 DPS drafts."""

import argparse
import collections
import hashlib
import json
import zipfile
from fractions import Fraction
from pathlib import Path

root = Path.cwd()
work = root / "workspace/codex-naxx/measurement-20261022"
archive = (
    root / "tests/golden/raids/raw/naxx-balance-v2-measurement/77619978-2006-20261023T152230.zip"
)
checks = []
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--oracles", type=Path, default=Path(__file__).resolve().parent)
parser.add_argument("--expected", type=int, default=49)
args = parser.parse_args()
archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()


def key(row):
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


with zipfile.ZipFile(archive) as z:
    marker = json.loads(z.read("necropsy-snapshot.json"))
    for path in sorted(args.oracles.glob("*.oracle.json")):
        oracle = json.loads(path.read_bytes())
        spec = oracle["spec"]
        assert archive_sha == spec["sha256"]
        owner = spec["actor"]
        report = json.loads(z.read(f"reports/{spec['report']}/bundle.json"))["reportData"]["report"]
        fight = next(f for f in report["fights"] if f["id"] == spec["fight"])
        fight_owned = {p["id"] for p in fight["friendlyPets"] if p.get("petOwner") == owner}
        catalog_owned = {
            p["id"] for p in report["masterData"]["actors"] if p.get("petOwner") == owner
        }
        assert fight_owned == catalog_owned == set(oracle["owned_actor_ids"])
        known = {owner} | fight_owned
        observations = []
        raw_rows = {}
        locators = collections.defaultdict(list)
        for stream in marker["streams"]:
            if (stream["report"], stream["fight"]) != (spec["report"], spec["fight"]) or stream[
                "actor_id"
            ] not in known:
                continue
            prefix = f"events/{spec['report']}/fight_{spec['fight']}/"
            prefix += f"{stream['role']}_{stream['actor_id']}_"
            names = sorted(
                n
                for n in z.namelist()
                if n.startswith(prefix)
                and n.rsplit("/", 1)[-1].startswith(stream["direction"] + "_")
            )
            assert len(names) == len(stream["pages"])
            counter = collections.Counter()
            for name in names:
                for index, event in enumerate(json.loads(z.read(name))["data"]):
                    if event.get("type") != "damage" or event.get("sourceID") != stream["actor_id"]:
                        continue
                    assert (
                        type(event["sourceID"]) is int
                        and type(event["targetID"]) is int
                        and type(event["amount"]) is int
                        and event["amount"] >= 0
                    )
                    assert fight["startTime"] <= event["timestamp"] <= fight["endTime"]
                    canonical = key(event)
                    counter[canonical] += 1
                    raw_rows[canonical] = event
                    locators[canonical].append({"member": name, "index": index})
            observations.append(counter)
        merged = collections.Counter()
        for c in observations:
            merged |= c
        expected = collections.Counter({key(r["raw"]): r["multiplicity"] for r in oracle["events"]})
        assert merged == expected, path.name
        totals = {
            "raw": sum(raw_rows[k]["amount"] * n for k, n in merged.items()),
            "self": sum(
                raw_rows[k]["amount"] * n
                for k, n in merged.items()
                if raw_rows[k]["targetID"] in known
            ),
            "excluded": 0,
        }
        totals["ranked"] = totals["raw"] - totals["self"]
        assert totals == oracle["totals"], (path.name, totals, oracle["totals"])
        for event in oracle["events"]:
            expected_locators = collections.Counter(
                (item["member"], item["index"]) for item in event["locators"]
            )
            actual_locators = collections.Counter(
                (item["member"], item["index"]) for item in locators[key(event["raw"])]
            )
            assert expected_locators == actual_locators, path.name
        board = json.loads(z.read(spec["leaderboard_member"]), parse_float=str)
        page = next(p for p in board["pages"] if p["page"] == spec["page"])
        published = page["characterRankings"]["rankings"][spec["row"]]
        amount = str(published["amount"])
        duration = fight["endTime"] - fight["startTime"]
        assert published["duration"] == duration
        assert (
            published["report"]["code"],
            published["report"]["fightID"],
            published["name"],
            published["server"]["name"],
            published["class"],
            published["spec"],
        ) == (
            spec["report"],
            spec["fight"],
            spec["player"],
            spec["realm"],
            spec["class"],
            spec["category"],
        )
        residual = Fraction(totals["ranked"] * 1000, duration) - Fraction(amount)
        assert str(residual) == oracle["residual"] and amount == oracle["published"]
        decimals = len(amount.partition(".")[2])
        assert abs(residual) < Fraction(1, 10**decimals)
        checks.append(
            {
                "oracle": path.name,
                "oracle_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "raw_occurrences": sum(merged.values()),
                "known_owned_ids": sorted(fight_owned),
                "totals": totals,
                "all_raw_rows_and_locators_match": True,
                "published_raw_token": amount,
                "duration_ms": duration,
                "independent_fraction_residual": str(residual),
            }
        )
assert len(checks) == args.expected
result = {
    "kind": "Independent stdlib re-enumeration; no production/freezer imports",
    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "oracles_checked": len(checks),
    "checks": checks,
    "limits": [
        (
            "Exact raw arithmetic/witness agreement only; no cell policy, boss exclusions, "
            "source approval or performance grade."
        ),
        "All forty original refusals are retained; no ownership or exclusion repair.",
    ],
}
result["checker_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
print(json.dumps(result))
