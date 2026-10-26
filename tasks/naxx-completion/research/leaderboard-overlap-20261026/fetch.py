"""Bounded live read: first leaderboard page per (class, spec, metric) x Naxx boss.

Runs inside the released capture image (necropsy 0.7.0) as the sole WCL owner,
while production is stopped. It imports only the installed package.

- The worklist (20 distinct leaderboards x 15 bosses, ordered) is frozen in
  OUT/worklist.json on the first run; a later run must find the identical list.
- Every response is saved verbatim (captured_at, request identity, data) and
  listed in OUT/SHA256SUMS. On resume a saved page is verified against that
  list before it is skipped; a mismatch stops the run.
- The client makes exactly one attempt per request (no retries, no reset wait).
  A fresh rate reading is taken before the first page; every later decision uses
  the rate data returned by the previous response. The run stops before a request
  when the remaining hourly points are at or below --floor. Query cost is not
  known in advance, so the floor limits further spending but is not a hard bound.
- Any error stops the run; the failure is appended to OUT/failures.jsonl with its
  time. Nothing is retried in this process.

Usage: python fetch.py OUT [--floor POINTS] [--max-requests N]
"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.raids import NAXXRAMAS, encounters
from necropsy.raids.scope import configurations
from necropsy.wcl.cli import RATE_QUERY, _auth
from necropsy.wcl.client import RATE_FIELDS, Policy, WclClient
from necropsy.wcl.urls import parse_character_url

PARTITION = 1
QUERY = """
query NecropsyOverlapLeaderboard($encounter: Int!, $partition: Int!, $cls: String!,
                                 $spec: String!) {{
  worldData {{
    encounter(id: $encounter) {{
      characterRankings(metric: {metric}, className: $cls, specName: $spec,
                        partition: $partition, page: 1)
    }}
  }}
  {rate}
}}
"""


def now() -> str:
    return datetime.now(UTC).isoformat()


def rate_dict(rate) -> dict:
    return {"limit": rate.limit_per_hour, "spent": rate.points_spent, "reset_in_s": rate.reset_in_s}


def worklist(host: str) -> list[dict]:
    """Each item carries the full request identity that its saved page must match."""
    boards = sorted({(CLASS_NAMES[c.class_id], c.category, c.metric) for c in configurations()})
    bosses = [int(e["id"]) for e in encounters(NAXXRAMAS)]
    return [
        {
            "file": f"{cls}-{spec}-{metric}-{boss}.json".lower(),
            "class": cls,
            "spec": spec,
            "metric": metric,
            "encounter": boss,
            "partition": PARTITION,
            "page": 1,
            "identity": {
                "site": host,
                "endpoint": "user",
                "query": QUERY.format(metric=metric, rate=RATE_FIELDS),
                "variables": {"encounter": boss, "partition": PARTITION, "cls": cls, "spec": spec},
            },
        }
        for cls, spec, metric in boards
        for boss in bosses
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--floor", type=int, default=600)
    parser.add_argument("--max-requests", type=int, default=300)
    args = parser.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    site = parse_character_url(
        f"https://vanilla.warcraftlogs.com/character/id/1?zone={NAXXRAMAS.zone_id}"
    ).site
    work = worklist(site.host)
    frozen = out / "worklist.json"
    if frozen.exists():
        if json.loads(frozen.read_bytes()) != work:
            print("STOP the frozen worklist differs from this build's worklist")
            return 2
    else:
        frozen.write_text(json.dumps(work, indent=1) + "\n", encoding="utf-8")
    sums = out / "SHA256SUMS"
    listed = {}
    if sums.exists():
        for line in sums.read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            listed[name] = digest
    # Validate every saved page before any live request: manifest digest and the
    # exact request identity the frozen worklist assigns to that file.
    for item in work:
        target = out / item["file"]
        if not target.exists():
            continue
        raw = target.read_bytes()
        if listed.get(item["file"]) != hashlib.sha256(raw).hexdigest():
            print(f"STOP saved page {item['file']} does not match SHA256SUMS")
            return 2
        if json.loads(raw).get("identity") != item["identity"]:
            print(f"STOP saved page {item['file']} has another request identity")
            return 2
    client = WclClient(site, _auth().token_for, policy=Policy(max_attempts=1, wait_for_reset=False))
    readings = out / "readings.jsonl"
    made = 0

    def log(path: Path, record: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    try:
        try:
            rate = client.query(RATE_QUERY, endpoint="user").rate
        except Exception as error:
            log(out / "failures.jsonl", {"at": now(), "stage": "rate", "error": repr(error)})
            print(f"STOP rate reading failed: {type(error).__name__}")
            return 2
        log(readings, {"at": now(), "kind": "rate-before-first", "rate": rate_dict(rate)})
        for item in work:
            target = out / item["file"]
            if target.exists():
                continue  # validated above
            if made >= args.max_requests:
                print(f"STOP max requests {made}")
                return 0
            if rate.remaining <= args.floor:
                print(f"STOP floor: {rate.remaining} remaining <= {args.floor}")
                log(readings, {"at": now(), "kind": "floor-stop", "rate": rate_dict(rate)})
                return 0
            identity = item["identity"]
            before = rate_dict(rate)
            try:
                result = client.query(
                    identity["query"], identity["variables"], endpoint=identity["endpoint"]
                )
            except Exception as error:
                log(
                    out / "failures.jsonl",
                    {"at": now(), "file": item["file"], "error": repr(error)},
                )
                print(f"STOP {item['file']}: {type(error).__name__}")
                return 2
            made += 1
            rate = result.rate
            record = {
                "captured_at": now(),
                "identity": identity,
                "data": result.data,
            }
            raw = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
            tmp = target.with_suffix(".tmp")
            tmp.write_bytes(raw)
            tmp.replace(target)
            with sums.open("a", encoding="utf-8") as handle:
                handle.write(f"{hashlib.sha256(raw).hexdigest()}  {item['file']}\n")
            log(
                readings,
                {
                    "at": record["captured_at"],
                    "file": item["file"],
                    "before": before,
                    "after": rate_dict(rate),
                },
            )
            print(f"{made} {item['file']} remaining={rate.remaining}")
    finally:
        client.close()
    print(f"DONE {made} request(s) this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
