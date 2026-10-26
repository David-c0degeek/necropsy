"""Build the C1 DPS policy matrix and policy evidence from the frozen v2 drafts.

Reads the retained real-v2 DPS inventory and oracles, the pinned measurement
archive's snapshot marker and the production Naxx zone rules. Writes nothing in
check mode (the default): it compares the committed matrix and evidence files
with a fresh build. ``--write`` creates them and refuses to overwrite.
No WCL call, analyzer, metric or freezer import.
"""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
DRAFTS = ROOT / "tasks/naxx-completion/research/real-v2-dps-20261023"
ARCHIVE = (
    ROOT / "tests/golden/raids/raw/naxx-balance-v2-measurement/77619978-2006-20261023T152230.zip"
)
ARCHIVE_SHA256 = "caa199389d11dab0d3c0678d086a352fb679d3e3cd133e62f2da0ecfef86dcb5"
ZONE = ROOT / "src/necropsy/rules/classic_era/zones/naxxramas.yaml"
MATRIX = Path(__file__).with_name("matrix.json")
EVIDENCE = ROOT / "tests/golden/raids"
SCOPE = {"class_id": 2, "category": "Balance", "metric": "dps", "faction": "Alliance"}
MIN_MATCHES = 3
SLUGS = {
    51107: "anubrekhan",
    51108: "gluth",
    51109: "gothik",
    51110: "faerlina",
    51111: "grobbulus",
    51112: "heigan",
    51113: "razuvious",
    51114: "kelthuzad",
    51115: "loatheb",
    51116: "maexxna",
    51117: "noth",
    51118: "patchwerk",
    51119: "sapphiron",
    51120: "thaddius",
    51121: "horsemen",
}
METHOD = (
    "Independent raw re-enumeration: maximum-multiplicity union of the actor's and its "
    "listed owned units' SOURCE and TARGET pages, damage events whose sourceID is that "
    "stream's own actor; damage to the owner or its owned units is subtracted; no target "
    "exclusions; exact rational arithmetic; published amounts kept as text. A row is "
    "consistent when |ranked * 1000 / duration - published| < 10^-(published decimals) "
    "and the ranking duration equals the fight duration. That bound reflects "
    "publication precision only; the upstream rounding mode is not established."
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def build():
    require(sha256(ARCHIVE) == ARCHIVE_SHA256, "measurement archive digest changed")
    zone = yaml.safe_load(ZONE.read_text(encoding="utf-8"))
    exclusions = {
        e["id"]: sorted(int(x["game_id"]) for x in e.get("ranking_exclusions") or ())
        for e in zone["encounters"]
    }
    inventory = json.loads((DRAFTS / "inventory.json").read_bytes())
    require(inventory["archive_sha256"] == ARCHIVE_SHA256, "inventory archive differs")
    with zipfile.ZipFile(ARCHIVE) as z:
        marker = json.loads(z.read("necropsy-snapshot.json"))
        catalogs = {}

        def catalog(code):
            if code not in catalogs:
                report = json.loads(z.read(f"reports/{code}/bundle.json"))["reportData"]["report"]
                catalogs[code] = {a["id"]: a.get("gameID") for a in report["masterData"]["actors"]}
            return catalogs[code]

        verdicts = {}
        for boss in marker["bosses"]:
            for actor in [*boss["cohort"], boss["subject"]]:
                verdict = actor.get("verdict") or {}
                verdicts[(boss["encounter_id"], actor["report"], actor["fight"])] = {
                    "kind": actor["kind"],
                    "faction": verdict.get("faction"),
                    "faction_status": verdict.get("status"),
                    "faction_reason": verdict.get("reason"),
                }
        names = {b["encounter_id"]: b["boss"] for b in marker["bosses"]}
        bosses = {e: {"boss": names[e], "attempts": []} for e in sorted(names)}
        for result in inventory["results"]:
            spec = result["spec"]
            encounter = spec["encounter"]
            who = verdicts.get((encounter, spec["report"], spec["fight"]))
            require(who is not None, f"{spec['report']}/{spec['fight']}: no snapshot actor")
            attempt = {
                "report": spec["report"],
                "fight": spec["fight"],
                "actor": spec["actor"],
                "player": spec["player"],
                "realm": spec["realm"],
                **who,
                "status": result["status"],
            }
            if result["status"] == "arithmetic-match":
                oracle_path = DRAFTS / f"{encounter}-{spec['report']}-{spec['fight']}.oracle.json"
                require(sha256(oracle_path) == result["oracle_sha256"], f"{oracle_path} changed")
                oracle = json.loads(oracle_path.read_bytes())
                ids = catalog(spec["report"])
                targets = {}
                for event in oracle["events"]:
                    if event["disposition"] != "ranked":
                        continue
                    game_id = ids.get(event["raw"]["targetID"])
                    require(game_id is not None, f"{oracle_path.name}: unresolved target")
                    amount = event["raw"]["amount"] * event["multiplicity"]
                    targets[game_id] = targets.get(game_id, 0) + amount
                attempt.update(
                    oracle=oracle_path.relative_to(ROOT).as_posix(),
                    oracle_sha256=result["oracle_sha256"],
                    leaderboard_member=spec["leaderboard_member"],
                    page=spec["page"],
                    row=spec["row"],
                    owned_actor_ids=oracle["owned_actor_ids"],
                    duration_ms=oracle["duration_ms"],
                    published=oracle["published"],
                    totals=oracle["totals"],
                    residual=oracle["residual"],
                    ranked_target_game_ids=len(targets),
                    excluded_target_damage=sum(
                        v for g, v in targets.items() if g in exclusions[encounter]
                    ),
                )
            else:
                # Only ownership evidence may refuse a row; any other refusal would be
                # an unexplained arithmetic disagreement and must not stay neutral.
                reason = result["reason"]
                require(
                    result["status"] == "refused"
                    and (
                        reason == "pet listings disagree"
                        or (reason.startswith('"There is no item named') and "pets.json" in reason)
                    ),
                    f"{spec['report']}/{spec['fight']}: non-ownership refusal {reason!r}",
                )
                attempt["reason"] = reason
            bosses[encounter]["attempts"].append(attempt)
    policies = {}
    for encounter, entry in bosses.items():
        attempts = entry["attempts"]
        in_scope = [
            a
            for a in attempts
            if a["faction"] == SCOPE["faction"] and a["faction_status"] == "observed"
        ]
        matched = [a for a in in_scope if a["status"] == "arithmetic-match"]
        contradictions = [a for a in matched if a["excluded_target_damage"]]
        refused = [a for a in in_scope if a["status"] != "arithmetic-match"]
        entry["dispositions"] = {
            "n": len(in_scope),
            "k": len(matched) - len(contradictions),
            "r": len(refused),
            "c": len(contradictions),
            "outside_scope": len(attempts) - len(in_scope),
        }
        entry["production_ranking_exclusions"] = exclusions[encounter]
        if exclusions[encounter]:
            entry["decision"] = "OPEN: production ranking exclusions untested by any admitted row"
        elif len(matched) < MIN_MATCHES:
            entry["decision"] = f"OPEN: {len(matched)} admitted matches, fewer than {MIN_MATCHES}"
        elif not any(a["kind"] != "subject" for a in matched):
            entry["decision"] = "OPEN: no non-subject admitted match"
        elif contradictions:
            entry["decision"] = "OPEN: contradiction retained"
        else:
            rule = f"naxx-{SLUGS[encounter]}-balance-druid-dps-v1"
            entry["decision"] = f"POLICY {rule}"
            policies[encounter] = {
                "version": 1,
                "rule": rule,
                "scope": {"encounter_id": encounter, **SCOPE},
                "method": METHOD,
                "archive": {
                    "path": ARCHIVE.relative_to(ROOT).as_posix(),
                    "sha256": ARCHIVE_SHA256,
                },
                "dispositions": entry["dispositions"],
                "rows": [
                    {
                        "id": f"{a['report']}-{a['fight']}-{a['actor']}",
                        "purpose": "policy-scope",
                        **a,
                    }
                    for a in matched
                ],
                "refusals": refused,
            }
    matrix = {
        "kind": "C1 cell-scoped DPS policy matrix; Druid Balance DPS Alliance, Naxxramas",
        "inputs": {
            "archive_sha256": ARCHIVE_SHA256,
            "inventory_sha256": sha256(DRAFTS / "inventory.json"),
            "builder_sha256": sha256(Path(__file__)),
        },
        "scope": SCOPE,
        "minimum_admitted_matches": MIN_MATCHES,
        "bosses": {str(e): v for e, v in bosses.items()},
        "limits": [
            "Raw-to-published arithmetic for exactly this cell scope; no engine emission, "
            "product score, grade or COMPLETE cell.",
            "Ownership refusals are unknown, never matches or contradictions.",
            "An empty target-exclusion set is positively exercised only where admitted rows "
            "damage more than one target game ID.",
        ],
    }
    files = {MATRIX: dump(matrix)}
    for encounter, policy in policies.items():
        files[EVIDENCE / f"dps-ranking-naxx-{SLUGS[encounter]}-balance-druid.json"] = dump(policy)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    files = build()
    for path, text in files.items():
        if args.write:
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        else:
            require(path.read_bytes() == text.encode("utf-8"), f"{path} differs from a fresh build")
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{'WROTE' if args.write else 'PASS'}: {len(files)} files")


if __name__ == "__main__":
    main()
