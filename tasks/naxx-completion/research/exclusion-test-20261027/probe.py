"""Are the production ranking exclusions testable under the D022 freezer? (diagnostic)

For every attempt (subject and comparisons) at the five Naxx bosses with
production `ranking_exclusions`, in one pinned capture, run the DPS freezer
twice on the exact published row: with the production exclusion game IDs as
explicit inputs, and with none. Record each outcome, the damage to excluded
targets, and whether the exclusion set changes the result. Nothing is fitted:
the exclusion list is the zone rule's, unchanged. Writes one JSON receipt.

  uv run python <this script> ARCHIVE --out FILE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from necropsy.analysis.class_catalog import CLASS_NAMES  # noqa: E402
from necropsy.analysis.roles import ranking_policy  # noqa: E402
from necropsy.raids import raid_for_zone  # noqa: E402
from necropsy.rules import load_rules  # noqa: E402
from scripts import freeze_dps_ranking as dps  # noqa: E402


def attempt(spec: dict[str, Any], work: Path) -> dict[str, Any]:
    try:
        r = dps.compute(spec, work)
    except (ValueError, KeyError, TypeError) as error:
        return {"result": "refused", "reason": str(error)}
    return {"result": "admitted", "totals": r["totals"], "residual": r["residual"]}


def probe(archive: Path) -> dict[str, Any]:
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive) as z:
        marker = json.loads(z.read("necropsy-snapshot.json"))
        boards = {
            int(n.split("/")[1].split("_")[0]): (n, json.loads(z.read(n)))
            for n in z.namelist()
            if n.startswith("leaderboards/") and n.endswith(".json")
        }
        actors = {
            f["reportID"]: json.loads(z.read(f"reports/{f['reportID']}/bundle.json"))["reportData"][
                "report"
            ]["masterData"]["actors"]
            for f in marker["fights"]
        }
    subject = marker["subject"]
    cls = CLASS_NAMES[subject["class_id"]]
    category = subject.get("ranking_category")
    policy = ranking_policy(subject["class_id"], category, subject.get("ranking_metric", "dps"))
    zone = load_rules("classic_era", f"zones/{raid_for_zone(marker['zone']['id']).slug}")
    exclusions = {
        int(e["id"]): sorted(int(x["game_id"]) for x in e["ranking_exclusions"])
        for e in zone["encounters"]
        if e.get("ranking_exclusions")
    }
    rows = []
    with tempfile.TemporaryDirectory(prefix="exclusion-probe-") as scratch:
        for fight in marker["fights"]:
            for p in fight["participants"]:
                encounter = int(p["encounterID"])
                if encounter not in exclusions:
                    continue
                who = {
                    "encounter": encounter,
                    "boss": p.get("boss"),
                    "kind": p["kind"],
                    "player": p["player"],
                    "realm": p["server"],
                    "report": fight["reportID"],
                    "fight": fight["fightID"],
                }
                matches = [
                    a["id"]
                    for a in actors[fight["reportID"]]
                    if a.get("type") == "Player"
                    and (a.get("name"), a.get("server"), a.get("subType"))
                    == (p["player"], p["server"], cls)
                ]
                name, board = boards[encounter]
                located = [
                    (page["page"], i)
                    for page in board["pages"]
                    for i, r in enumerate(page["characterRankings"]["rankings"])
                    if (r["report"]["code"], r["report"]["fightID"], r["name"], r["server"]["name"])
                    == (fight["reportID"], fight["fightID"], p["player"], p["server"])
                ]
                if len(matches) != 1 or len(located) != 1:
                    rows.append(who | {"skipped": "no unique actor or published row"})
                    continue
                spec = {
                    "archive": archive.resolve().as_posix(),
                    "sha256": digest,
                    "report": fight["reportID"],
                    "fight": fight["fightID"],
                    "actor": matches[0],
                    "player": p["player"],
                    "realm": p["server"],
                    "class": cls,
                    "category": category,
                    "role": policy.role,
                    "encounter": encounter,
                    "excluded_game_ids": exclusions[encounter],
                    "leaderboard_member": name,
                    "page": located[0][0],
                    "row": located[0][1],
                }
                with_ex = attempt(spec, Path(scratch))
                without = attempt(spec | {"excluded_game_ids": []}, Path(scratch))
                rows.append(
                    who
                    | {
                        "production_exclusions": exclusions[encounter],
                        "with_exclusions": with_ex,
                        "without_exclusions": without,
                        "excluded_damage": (with_ex.get("totals") or {}).get("excluded"),
                        "exclusions_decide": with_ex["result"] != without["result"],
                    }
                )
    return {
        "kind": "Production ranking exclusion probe under the D022 freezer; diagnostic only",
        "archive": {"path": archive.as_posix(), "sha256": digest},
        "producer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "freezer_sha256": hashlib.sha256(Path(dps.__file__).read_bytes()).hexdigest(),
        "rows": rows,
        "limits": [
            "Exclusion lists are the zone rule's production lists, never fitted per row.",
            "An admitted row with zero excluded damage does not test the exclusion.",
            "One configuration (the archive's subject cell) only.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = probe(args.archive)
    text = json.dumps(result, indent=1, ensure_ascii=False) + "\n"
    args.out.write_text(text, encoding="utf-8", newline="\n")
    for r in result["rows"]:
        if "skipped" in r:
            print(r["boss"], r["player"], "skipped:", r["skipped"])
            continue
        print(
            f"{r['boss'][:16]:16} {r['kind']:5} {r['player'][:14]:14} "
            f"with={r['with_exclusions']['result']:8} "
            f"without={r['without_exclusions']['result']:8} "
            f"excluded_damage={r['excluded_damage']} decides={r['exclusions_decide']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
