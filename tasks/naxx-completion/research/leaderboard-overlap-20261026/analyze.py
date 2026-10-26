"""Offline: how often top leaderboard fights coincide across Naxx leaderboards.

Reads the pinned bundle from the 2026-10-26 sole-owner window (300 first pages,
20 class/spec/metric leaderboards x 15 bosses). Check mode (the default) compares
a fresh run with the committed receipt; ``--out FRESH`` writes a new receipt and
refuses to overwrite. No WCL call.

- Every page is verified against the bundle's SHA256SUMS and its saved request
  identity against the frozen worklist.
- Rows are kept only when their class and spec equal the page's leaderboard.
- A fight is the exact (report code, fightID) pair. Leaderboard rows carry no
  faction or guild here, so faction is unobserved; coincidence is faction-blind.
- A coincidence is not cohort eligibility: faction, ownership, the
  configuration's own row and stream completeness are not established.
"""

import argparse
import collections
import hashlib
import itertools
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BUNDLE = ROOT / "workspace/leaderboard-overlap-20261026/leaderboard-overlap-bundle.tar.gz"
BUNDLE_SHA256 = "11edd8eb6ec028330034bc8d11db116685706d817c508c547c5663cd9094806b"
RECEIPT = Path(__file__).with_name("receipt.json")
TOPS = (3, 5, 20, 100)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load():
    require(hashlib.sha256(BUNDLE.read_bytes()).hexdigest() == BUNDLE_SHA256, "bundle changed")
    with tarfile.open(BUNDLE) as tar:
        files = {
            m.name: tar.extractfile(m).read()
            for m in tar.getmembers()
            if m.isfile() and m.name.startswith("out/")
        }
    work = json.loads(files["out/worklist.json"])
    sums = dict(
        reversed(line.split("  ", 1))
        for line in files["out/SHA256SUMS"].decode("utf-8").splitlines()
    )
    pages = {}
    for item in work:
        raw = files.get(f"out/{item['file']}")
        require(raw is not None, f"missing page {item['file']}")
        require(sums.get(item["file"]) == hashlib.sha256(raw).hexdigest(), f"{item['file']} digest")
        record = json.loads(raw)
        require(record["identity"] == item["identity"], f"{item['file']} identity")
        board = record["data"]["worldData"]["encounter"]["characterRankings"]
        board = json.loads(board) if isinstance(board, str) else board
        pages[item["file"]] = (item, board)
    return work, pages


def analyze():
    work, pages = load()
    boards = sorted({(i["class"], i["spec"], i["metric"]) for i in work})
    bosses = sorted({i["encounter"] for i in work})
    rows_total = rows_kept = duplicates = 0
    ranked = {}  # (board, boss) -> fights of the kept rows, in rank order, repeats kept
    for item, board in pages.values():
        key = ((item["class"], item["spec"], item["metric"]), item["encounter"])
        ordered = []
        for row in board.get("rankings") or []:
            rows_total += 1
            if row.get("class") != item["class"] or row.get("spec") != item["spec"]:
                continue
            report = row.get("report") or {}
            fight = (report.get("code"), report.get("fightID"))
            if not isinstance(fight[0], str) or type(fight[1]) is not int:
                continue
            rows_kept += 1
            if fight in ordered:
                duplicates += 1
            ordered.append(fight)
        ranked[key] = ordered

    def first_distinct(fights, n):
        seen = []
        for fight in fights:
            if fight not in seen:
                seen.append(fight)
            if len(seen) == n:
                break
        return set(seen)

    def window(select):
        """Overlap of one per-(board, boss) fight selection across leaderboards."""
        result = {}
        for n in TOPS:
            slots = shared_slots = union = 0
            boards_sharing = collections.Counter()
            pair_counts = collections.Counter()
            per_boss = {}
            for boss in bosses:
                sets = {b: select(ranked[(b, boss)], n) for b in boards}
                owners = collections.defaultdict(set)
                for b, fights in sets.items():
                    for f in fights:
                        owners[f].add(b)
                multi = {f: o for f, o in owners.items() if len(o) > 1}
                union += len(owners)
                for b, fights in sets.items():
                    slots += len(fights)
                    shared = sum(1 for f in fights if len(owners[f]) > 1)
                    shared_slots += shared
                    boards_sharing[b] += shared
                for a, c in itertools.combinations(boards, 2):
                    pair_counts[(a, c)] += len(sets[a] & sets[c])
                per_boss[str(boss)] = {
                    "distinct_fights": len(owners),
                    "fights_in_2_or_more_leaderboards": len(multi),
                    "max_leaderboards_sharing_one_fight": max(
                        (len(o) for o in owners.values()), default=0
                    ),
                }
            result[str(n)] = {
                "board_boss_fight_slots": slots,
                "slots_whose_fight_is_in_another_leaderboard": shared_slots,
                "share_of_slots_shared": round(shared_slots / slots, 4) if slots else None,
                "distinct_boss_fights_across_leaderboards": union,
                "coalescable_fight_acquisitions": slots - union,
                "per_boss": per_boss,
                "top_pairs": [
                    {"a": "/".join(a), "b": "/".join(c), "shared_fights": k}
                    for (a, c), k in pair_counts.most_common(10)
                    if k
                ],
                "per_leaderboard_shared_slots": {"/".join(b): boards_sharing[b] for b in boards},
            }
        return result

    result_tops = {
        "top_ranked_rows": window(lambda fights, n: set(fights[:n])),
        "first_n_distinct_fights": window(first_distinct),
    }
    return {
        "kind": "Live leaderboard overlap, first pages; faction-blind exact fight coincidence",
        "bundle": {"path": BUNDLE.relative_to(ROOT).as_posix(), "sha256": BUNDLE_SHA256},
        "pages": len(pages),
        "leaderboards": len(boards),
        "bosses": len(bosses),
        "rows": {
            "total": rows_total,
            "kept_class_spec_and_fight": rows_kept,
            "duplicate_fight_within_leaderboard": duplicates,
        },
        "definitions": {
            "top_ranked_rows": "fights of the top N ranked rows (primary)",
            "first_n_distinct_fights": "first N distinct fights on the page (secondary)",
            "coalescable_fight_acquisitions": "slots minus distinct fights across leaderboards; "
            "an upper count of fight captures that could merge, not requests or points saved",
        },
        "by_window": result_tops,
        "limits": [
            "First pages only, one capture time per page (2026-10-26 18:52-18:54 UTC).",
            "Faction is not present in leaderboard rows; coincidence ignores faction.",
            "A shared fight is not an eligible comparison for either configuration.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = analyze()
    result["analyze_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    text = json.dumps(result, indent=1, ensure_ascii=False) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    else:
        require(RECEIPT.read_bytes() == text.encode("utf-8"), "receipt differs from a fresh run")
    sys.stdout.reconfigure(encoding="utf-8")
    print("WROTE" if args.out else "PASS")


if __name__ == "__main__":
    main()
