"""List configuration and boss cells that need more valid comparison players.

A comparison is valid only when the existing ranking admission accepts it. For
DPS, that is `freeze_dps_ranking.compute` on the comparison's exact published
leaderboard row, so this detector and the freezer cannot drift apart. The
subject (kind `you`, or the same name on the same realm) never counts. Only
same-faction cohort entries whose faction the capture observed are comparisons;
the cross-faction ceiling never is, and an unobserved faction is unverified.
Each participant is resolved to its own report actor, so several selected
players in one fight are judged separately. Each cell keeps three separate counts: admitted,
refused (with the freezer's reason) and unverified, where no admission exists
yet (HPS archives without an HPS admission for their format, or encounters
whose production ranking exclusions no admitted evidence has tested). An
unverified comparison is never counted as zero valid players.

A cell needs follow-up when its admitted comparisons are fewer than the
packaged minimum (`live_cohort.min_same_faction`), whatever depth the archive
was captured at. Meeting the minimum never makes a cell complete.

Usage: uv run python scripts/comparison_followup.py ARCHIVE [ARCHIVE ...] --out FILE
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from necropsy.analysis.class_catalog import CLASS_NAMES  # noqa: E402
from necropsy.analysis.roles import ranking_policy  # noqa: E402
from necropsy.raids import raid_for_zone  # noqa: E402
from necropsy.rules import load_rules  # noqa: E402
from scripts import freeze_dps_ranking as dps  # noqa: E402

GAME = "classic_era"


def minimum() -> int:
    return int(load_rules(GAME, "benchmarks")["live_cohort"]["min_same_faction"])


def _exclusions(zone_id: int) -> dict[int, list[int]]:
    zone = load_rules(GAME, f"zones/{raid_for_zone(zone_id).slug}")
    return {
        int(e["id"]): [int(x["game_id"]) for x in e.get("ranking_exclusions") or ()]
        for e in zone["encounters"]
    }


def cells(archive: Path) -> list[dict[str, Any]]:
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive) as z:
        marker = json.loads(z.read("necropsy-snapshot.json"))
        boards = {
            int(n.split("/")[1].split("_")[0]): (n, json.loads(z.read(n)))
            for n in z.namelist()
            if n.startswith("leaderboards/") and n.endswith(".json")
        }
    subject = marker["subject"]
    cls = CLASS_NAMES[subject["class_id"]]
    category = subject.get("ranking_category")
    metric = subject.get("ranking_metric", "dps")
    policy = ranking_policy(subject["class_id"], category, metric)
    exclusions = _exclusions(marker["zone"]["id"])
    by_boss: dict[int, dict[str, Any]] = {}
    for boss in marker["bosses"]:
        by_boss[int(boss["encounter_id"])] = {
            "configuration": {
                "class": cls,
                "category": category,
                "metric": metric,
                "faction": subject["faction"],
            },
            "encounter_id": int(boss["encounter_id"]),
            "boss": boss["boss"],
            "archive": {"path": archive.as_posix(), "sha256": digest},
            "archive_depth": marker["top_n"],
            "admitted": [],
            "refused": [],
            "unverified": [],
        }
    # Same-faction cohort membership as the capture observed it, per boss. The
    # cross-faction ceiling is recorded separately and is never a comparison.
    cohort_faction = {
        (int(boss["encounter_id"]), c["report"], c["fight"], c["player"]): (c.get("verdict") or {})
        for boss in marker["bosses"]
        for c in boss.get("cohort") or ()
        if c.get("kind") == "cohort"
    }
    with zipfile.ZipFile(archive) as z:
        actors = {
            code: json.loads(z.read(f"reports/{code}/bundle.json"))["reportData"]["report"][
                "masterData"
            ]["actors"]
            for code in {f["reportID"] for f in marker["fights"]}
        }
    scratch = tempfile.TemporaryDirectory(prefix="followup-")
    work = Path(scratch.name)
    for fight in marker["fights"]:
        players = {
            s["actor_id"]
            for s in marker["streams"]
            if s["role"] == "player"
            and (s["report"], s["fight"]) == (fight["reportID"], fight["fightID"])
        }
        for participant in fight["participants"]:
            if participant["kind"] == "you" or (participant["player"], participant["server"]) == (
                subject["name"],
                subject["server"],
            ):
                continue  # the subject is never a comparison
            encounter = int(participant["encounterID"])
            cell = by_boss.get(encounter)
            if cell is None:
                continue
            who = {
                "report": fight["reportID"],
                "fight": fight["fightID"],
                "player": participant["player"],
                "realm": participant["server"],
            }
            verdict = cohort_faction.get(
                (encounter, fight["reportID"], fight["fightID"], participant["player"])
            )
            if verdict is None:
                continue  # not a same-faction cohort entry, e.g. the cross-faction ceiling
            if verdict.get("status") != "observed" or verdict.get("faction") is None:
                cell["unverified"].append(who | {"reason": "comparison faction not observed"})
                continue
            if verdict["faction"] != subject["faction"]:
                continue  # an observed other-faction player is never a comparison
            if metric != "dps":
                cell["unverified"].append(who | {"reason": "no HPS admission for this archive"})
                continue
            if exclusions.get(encounter):
                cell["unverified"].append(
                    who | {"reason": "production ranking exclusions untested by admitted evidence"}
                )
                continue
            # A fight may hold several selected players; resolve this one's actor.
            matches = [
                a["id"]
                for a in actors[fight["reportID"]]
                if a.get("type") == "Player"
                and (a.get("name"), a.get("server"), a.get("subType"))
                == (participant["player"], participant["server"], cls)
            ]
            if len(matches) != 1 or matches[0] not in players:
                cell["refused"].append(who | {"reason": "no unique selected player stream"})
                continue
            name, board = boards[encounter]
            rows = [
                (page["page"], i)
                for page in board["pages"]
                for i, r in enumerate(page["characterRankings"]["rankings"])
                if (
                    r["report"]["code"],
                    r["report"]["fightID"],
                    r["name"],
                    r["server"]["name"],
                    r["class"],
                    r["spec"],
                )
                == (
                    fight["reportID"],
                    fight["fightID"],
                    participant["player"],
                    participant["server"],
                    cls,
                    category,
                )
            ]
            if len(rows) != 1:
                cell["refused"].append(who | {"reason": "no unique matching published row"})
                continue
            spec = {
                "archive": archive.resolve().as_posix(),
                "sha256": digest,
                "report": fight["reportID"],
                "fight": fight["fightID"],
                "actor": matches[0],
                "player": participant["player"],
                "realm": participant["server"],
                "class": cls,
                "category": category,
                "role": policy.role,
                "encounter": encounter,
                "excluded_game_ids": [],
                "leaderboard_member": name,
                "page": rows[0][0],
                "row": rows[0][1],
            }
            try:
                dps.compute(spec, work)
            except (ValueError, KeyError, TypeError) as error:
                cell["refused"].append(who | {"reason": str(error)})
                continue
            cell["admitted"].append(who)
    scratch.cleanup()
    floor = minimum()
    out = []
    for cell in by_boss.values():
        distinct = {(a["player"], a["realm"]) for a in cell["admitted"]}
        cell["admitted_distinct_players"] = len(distinct)
        cell["minimum"] = floor
        cell["needs_followup"] = len(distinct) < floor
        if not cell["needs_followup"]:
            cell["followup"] = None
            cell["reason"] = None
        elif cell["unverified"] and not cell["admitted"] and not cell["refused"]:
            # Nothing was judged: an admission is missing, not a comparison shortage.
            cell["followup"] = "admission-missing"
            cell["reason"] = "unverified: no admission available yet"
        else:
            cell["followup"] = "more-comparisons"
            cell["reason"] = f"{len(distinct)} admitted comparisons, fewer than {floor}"
        out.append(cell)
    return sorted(out, key=lambda c: (c["configuration"]["class"], c["encounter_id"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    found = [cell for archive in args.archives for cell in cells(archive)]
    register = {
        "kind": "Comparison follow-up register; conditional on admitted evidence only",
        "minimum": minimum(),
        "cells": found,
        "needs_followup": sum(1 for c in found if c["needs_followup"]),
        "limits": [
            "Meeting the minimum does not make a cell complete.",
            "Unverified comparisons are not counted as zero valid players.",
            "Archive paths are as given on the command line.",
        ],
    }
    text = json.dumps(register, indent=1, ensure_ascii=False) + "\n"
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"{register['needs_followup']} of {len(found)} cells need follow-up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
