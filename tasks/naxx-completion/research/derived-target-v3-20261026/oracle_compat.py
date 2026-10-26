"""Strict-check differences of every committed DPS oracle under one tree's freezer.

Usage: uv run python oracle_compat.py --tree TREE --out OUT.json
TREE is a checkout whose scripts/freeze_dps_ranking.py is imported; the oracles
are always the committed ones of this repository. No WCL call; writes only OUT.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.tree.resolve()))
    from scripts import freeze_dps_ranking as dps

    oracles = sorted(
        p.relative_to(ROOT).as_posix()
        for p in ROOT.glob("tasks/naxx-completion/research/**/*.oracle.json")
    )
    result = {}
    for name in oracles:
        path = ROOT / name
        data = dps.read_json(path.read_bytes())
        fresh = dps.compute(data["spec"], path.parent)
        result[name] = sorted(c.split(":", 1)[0] for c in dps.pages.differences(data, fresh))
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({"tree": str(args.tree), "oracles": result}, indent=1) + "\n")
    print(f"{len(result)} oracles")


if __name__ == "__main__":
    main()
