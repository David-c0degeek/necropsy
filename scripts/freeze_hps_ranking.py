"""Freeze a scoped HPS ranking oracle for one boss from a raw capture.

Usage: uv run python scripts/freeze_hps_ranking.py FIXTURE ENCOUNTER RULE --out FILE
           [--class-name Paladin] [--slug NAME] [--replace]

FIXTURE is a provenance label (for example mc-holy-paladin-raid-context);
the contexts are its independent actor-fact cases for ENCOUNTER in
tests/golden/raids/facts.json (one subject, the rest comparisons), each of which
must be an actor of --class-name (default Paladin). RULE names the scope as
mc-<boss>-<category>-<class>-hps-v1; rows are named <boss>-<category>-<class>-<player>. For each
context it locates every published amount for that report, fight and player
in the archive: the subject's own ranking (user_rankings), the encounter
leaderboard pages and the report-fight healer rankings. It then measures the
actor's heal and absorbed amounts and its owned units with the raw helpers of
tests/golden/test_hps_ranking_policy.py, which read the archive with the
standard library only and import no analyzer or metric code.

A row whose published amounts do not all agree with the raw total over the
fight duration, within the last published decimal, is refused rather than
frozen. The oracle is a draft until the boss's fact and ranking review; the
golden test then re-proves every row from raw bytes, including the failure of
each wrong policy (overheal included, wrong duration, absorbed or owned units
dropped, another actor's amounts).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # run as a script: make the test helpers importable
    sys.path.insert(0, str(ROOT))

from tests.golden import test_hps_ranking_policy as raw  # noqa: E402

RAIDS = ROOT / "tests/golden/raids"
METHOD = (
    "Independent raw re-enumeration: maximum-multiplicity union of SOURCE and TARGET pages "
    "(sourceID == actor) plus listed owned units; exact rational arithmetic; published amounts "
    "kept as text. A row is consistent when |(heal + absorbed + owned-unit heal + absorbed) * "
    "1000 / duration - published| < 10^-(published decimals) and the ranking duration equals "
    "the fight duration. That bound reflects publication precision only; the upstream rounding "
    "mode is not established."
)


def contexts(fixture: str, encounter: int) -> list[dict[str, Any]]:
    cases = json.loads((RAIDS / "facts.json").read_text(encoding="utf-8"))["cases"]
    return [
        c for c in cases if c["fixture"] == fixture and c["expected"]["encounter_id"] == encounter
    ]


def candidates(z: Any, encounter: int, report: str, fight: int, name: str) -> list[dict[str, str]]:
    """Every published ranking entry for this report, fight and player, by locator."""
    found = []
    for member in z.namelist():
        if member.startswith(f"user_rankings/{encounter}_"):
            data = raw._read(z, member)
            if data.get("character") != name:
                continue
            for i, r in enumerate(data["encounterRankings"]["ranks"]):
                if (r["report"]["code"], r["report"]["fightID"]) == (report, fight):
                    entry = {"member": member, "locator": f"ranks[{i}]", "kind": "user_ranking"}
                    found.append(entry)
        elif member.startswith(f"leaderboards/{encounter}_"):
            for page in raw._read(z, member)["pages"]:
                for i, r in enumerate(page["characterRankings"]["rankings"]):
                    if (r["report"]["code"], r["report"]["fightID"], r["name"]) == (
                        report,
                        fight,
                        name,
                    ):
                        found.append(
                            {
                                "member": member,
                                "locator": f"pages[{page['page']}].rankings[{i}]",
                                "kind": "leaderboard",
                            }
                        )
    member = f"reports/{report}/fight_{fight}.json"
    data = raw._read(z, member)
    for i, block in enumerate(data["report"]["rankings"]["data"]):
        if block["fightID"] != fight:
            continue
        for j, r in enumerate(block["roles"]["healers"]["characters"]):
            if r["name"] == name:
                found.append(
                    {
                        "member": member,
                        "locator": f"report.rankings.data[{i}].roles.healers.characters[{j}]",
                        "kind": "report_fight_ranking",
                    }
                )
    return found


def freeze_row(
    case: dict[str, Any],
    slug: str,
    encounter: int,
    label: str = "holy-paladin",
    class_name: str = "Paladin",
) -> dict[str, Any]:
    path = RAIDS / case["archive"]
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != case["sha256"]:
        raise ValueError(f"{case['archive']}: archive differs from its fact case")
    z = zipfile.ZipFile(path)
    report = raw._read(z, f"reports/{case['report']}/fight_{case['fight']}.json")["report"]
    actor = next(a for a in report["masterData"]["actors"] if a["id"] == case["actor"])
    row: dict[str, Any] = {
        "id": f"{slug}-{label}-{actor['name'].lower()}",
        "purpose": "policy-scope",
        "archive": case["archive"],
        "sha256": sha,
        "report": case["report"],
        "fight": case["fight"],
        "actor": case["actor"],
        "name": actor["name"],
        "realm": actor["server"],
        "game_id": actor["gameID"],
        "encounter_id": encounter,
    }
    measured = raw._measure(row)
    if measured["me"]["subType"] != class_name:
        raise ValueError(f"{row['id']}: actor is not a {class_name}")
    total = (
        measured["owner"]["heal"]
        + measured["owner"]["absorbed"]
        + sum(u["heal"] + u["absorbed"] for u in measured["owned_units"])
    )
    rankings = []
    for ranking in candidates(z, encounter, case["report"], case["fight"], actor["name"]):
        published, duration = raw._published(z, ranking, row)
        if duration != measured["duration_ms"] or not raw._consistent(total, duration, published):
            raise ValueError(f"{row['id']}: {ranking['member']} {published} contradicts raw")
        residual = Fraction(total) * 1000 / duration - Fraction(published)
        rankings.append(
            {
                **ranking,
                "published": published,
                "duration_ms": duration,
                "residual": str(residual),
            }
        )
    if not rankings:
        raise ValueError(f"{row['id']}: no published ranking for this fight")
    row.update(
        duration_ms=measured["duration_ms"],
        owner=measured["owner"],
        owned_units=measured["owned_units"],
        rankings=rankings,
    )
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fixture")
    parser.add_argument("encounter", type=int)
    parser.add_argument("rule")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--slug", help="row id prefix (default: the rule's boss word)")
    parser.add_argument("--class-name", default="Paladin", help="the contexts' class subType")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    if args.out.exists() and not args.replace:
        print(f"refused: {args.out} exists; pass --replace", file=sys.stderr)
        return 2
    slug = args.slug or args.rule.split("-")[1]
    cases = contexts(args.fixture, args.encounter)
    if not cases:
        print("refused: no fact contexts for this fixture and encounter", file=sys.stderr)
        return 2
    try:
        label = "-".join(args.rule.split("-")[2:-2])
        rows = [freeze_row(c, slug, args.encounter, label, args.class_name) for c in cases]
    except (ValueError, AssertionError, KeyError, StopIteration) as error:
        print(f"refused: {error!r}", file=sys.stderr)
        return 2
    oracle = {"version": 1, "rule": args.rule, "method": METHOD, "rows": rows}
    args.out.write_bytes((json.dumps(oracle, indent=2, ensure_ascii=False) + "\n").encode())
    amounts = sum(len(r["rankings"]) for r in rows)
    print(f"{args.out}: {len(rows)} rows, {amounts} published amounts, all within the bound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
