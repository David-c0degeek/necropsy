"""Offline estimate: how far captured Naxx fights could serve other configurations.

Reads the registered measurement archive only (89 fights picked for Druid Balance
DPS Alliance). Check mode (the default) compares a fresh run with the committed
receipt; ``--out FRESH`` writes a new receipt and refuses to overwrite. No WCL call.

Everything here is a conditional opportunity over a biased sample, never a
measured requirement for the other 33 configurations:

- A character is the rankings row's global WCL character ``id``. Its locator
  (name, server, region) and class must agree with every other row carrying that
  id; a conflicting id is unresolved and never counts as one character. Within a
  report the row binds to playerDetails by locator with a strict class check,
  and faction comes only from that combatantInfo.factionID. Report-local actor
  IDs are never merged across reports.
- The unit is report-scoped (one uploaded log), not a proven calendar raid; its
  start and end are retained. Guilds are context only.
- Ranks come from the DPS-metric rankings query. HPS configurations are
  presence-only: their rows carry no HPS rank.
"""

import argparse
import collections
import hashlib
import json
import sys
import tarfile
import zipfile
from pathlib import Path

from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.raids.scope import configurations

ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = (
    ROOT / "tests/golden/raids/raw/naxx-balance-v2-measurement/77619978-2006-20261023T152230.zip"
)
ARCHIVE_SHA256 = "caa199389d11dab0d3c0678d086a352fb679d3e3cd133e62f2da0ecfef86dcb5"
JOURNAL = ROOT / "workspace/capture-cost-20261026/measurement-requests.tar.gz"
JOURNAL_SHA256 = "1beff26a118fb5d80fd86405c59f6bb423f49c5b314d1a9ccfc4c640689a9b5c"
SUBJECT_ID = 77619978
"""The measurement's own subject character; never counted as reusable cohort material."""
RECEIPT = Path(__file__).with_name("receipt.json")
FACTIONS = {1: "Alliance", 0: "Horde"}
RANK_BUCKETS = (5, 20, 100, 1000)
BOSSES = 15
COHORT = 5


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def rank_value(text):
    """Rankings give integers or approximate strings such as "~5003"."""
    raw = str(text)
    approximate = raw.startswith("~")
    digits = raw.lstrip("~")
    return (int(digits), approximate) if digits.isdigit() else (None, approximate)


def config_key(config):
    return "/".join(config)


def observations():
    require(hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == ARCHIVE_SHA256, "archive changed")
    legal = {(CLASS_NAMES[c.class_id], c.category, c.metric, c.faction) for c in configurations()}
    with zipfile.ZipFile(ARCHIVE) as z:
        marker = json.loads(z.read("necropsy-snapshot.json"))
        fights = sorted({(s["report"], s["fight"]) for s in marker["streams"]})
        rows = []
        fight_encounters = {}
        for code, fight_id in fights:
            report = json.loads(z.read(f"reports/{code}/bundle.json"))["reportData"]["report"]
            details = collections.defaultdict(list)
            for role in report["playerDetails"]["data"]["playerDetails"].values():
                for player in role:
                    details[(player["name"], player["server"], player.get("region"))].append(player)
            blocks = [b for b in report["rankings"]["data"] if b["fightID"] == fight_id]
            require(len(blocks) == 1, f"{code}/{fight_id}: no unique rankings block")
            block = blocks[0]
            encounter = block["encounter"]["id"]
            fight_encounters[(code, fight_id)] = encounter
            guild = (block.get("guild") or {}).get("name")
            for role, metric in (("dps", "dps"), ("tanks", "dps"), ("healers", "hps")):
                for row in block["roles"][role]["characters"]:
                    server = row["server"]
                    locator = (row["name"], server["name"], server.get("region"))
                    matches = [p for p in details.get(locator, []) if p.get("type") == row["class"]]
                    codes = {(p.get("combatantInfo") or {}).get("factionID") for p in matches}
                    faction = FACTIONS.get(codes.pop()) if len(codes) == 1 else None
                    if faction is None:
                        rows.append({"excluded": "faction or identity not observed"})
                        continue
                    config = (row["class"], row["spec"], metric, faction)
                    if config not in legal:
                        rows.append({"excluded": "not a legal configuration"})
                        continue
                    rank, approximate = rank_value(row["rank"]) if metric == "dps" else (None, None)
                    if type(row.get("id")) is not int or len(matches) != 1:
                        rows.append({"excluded": "no unique global id and class-checked binding"})
                        continue
                    rows.append(
                        {
                            "report": code,
                            "report_span": (report["startTime"], report["endTime"]),
                            "fight": fight_id,
                            "encounter": encounter,
                            "guild": guild,
                            "character": row["id"],
                            "locator": (*locator, row["class"]),
                            "config": config,
                            "rank": rank,
                            "approximate_rank": approximate,
                            "rank_text": str(row["rank"]) if metric == "dps" else None,
                        }
                    )
    require(len(fight_encounters) == len(fights), "a fight has no encounter binding")
    return legal, fights, rows, fight_encounters


def measured_costs():
    """Request counts by kind for this one capture, and report-query grouping."""
    require(hashlib.sha256(JOURNAL.read_bytes()).hexdigest() == JOURNAL_SHA256, "journal changed")
    records = []
    with tarfile.open(JOURNAL) as tar:
        for member in tar.getmembers():
            if member.isfile() and member.name.endswith(".json"):
                handle = tar.extractfile(member)
                require(handle is not None, member.name)
                record = json.loads(handle.read())
                report = ((record.get("data") or {}).get("reportData") or {}).get("report") or {}
                records.append(record["identity"] | {"observed_revision": report.get("revision")})

    def kind(identity):
        operation = identity["query"].split("query ", 1)[1].split("(", 1)[0].strip()
        if operation != "NecropsyEvents":
            return operation
        v = identity["variables"]
        if v.get("filterExpression"):
            return "events-critical"
        if v.get("sourceID") is not None:
            return "events-actor-source"
        if v.get("targetID") is not None:
            return "events-actor-target"
        return "events-encounter-all"

    by_kind = collections.Counter((kind(i), i["scope"]) for i in records)
    groups = collections.defaultdict(set)
    for i in records:
        if kind(i) == "NecropsyReport":
            # Everything but the fight list must match: the full request context,
            # every other variable, and the revision the answer actually reported.
            context = {k: v for k, v in i["variables"].items() if k != "fightIDs"}
            groups[i["scope"]].add(
                (
                    i["site"],
                    i["endpoint"],
                    i["query"],
                    json.dumps(context, sort_keys=True),
                    i["observed_revision"],
                )
            )
    return {
        "journal": {"path": JOURNAL.relative_to(ROOT).as_posix(), "sha256": JOURNAL_SHA256},
        "records": len(records),
        "requests_by_kind_and_scope": {f"{k}/{s}": n for (k, s), n in sorted(by_kind.items())},
        "report_queries_by_scope": {s: by_kind[("NecropsyReport", s)] for s in sorted(groups)},
        "report_groups_by_scope_context_and_observed_revision": {
            s: len(g) for s, g in sorted(groups.items())
        },
        "grouping_note": "a grouping opportunity within each scope only; acquisition and "
        "finalization stay independent, and merged answers are not proved equivalent",
        "actor_target_requests_avoided_by_0_7_0": by_kind[("events-actor-target", "acquisition")],
        "points": "not modelled: account-wide readings, hidden database allowance",
    }


def estimate():
    legal, fights, rows, fight_encounters = observations()
    kept = [r for r in rows if "excluded" not in r]
    # A global id is resolved only when every row carrying it has one locator and class.
    locators = collections.defaultdict(set)
    for r in kept:
        locators[r["character"]].add(r["locator"])
    conflicting = {c for c, v in locators.items() if len(v) > 1}
    for r in kept:
        r["resolved"] = r["character"] not in conflicting
    excluded = collections.Counter(r["excluded"] for r in rows if "excluded" in r)
    # Per fight: configurations present, and present at a DPS rank within each bucket.
    per_fight = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in kept:
        per_fight[(r["report"], r["fight"])][r["config"]].append((r["rank"], r["approximate_rank"]))
    fight_rows = []
    for key in fights:
        present = per_fight.get(key, {})
        entry = {
            "report": key[0],
            "fight": key[1],
            "observed_eligible_configurations": len(present),
        }
        for bucket in RANK_BUCKETS:
            entry[f"exact_dps_rank_le_{bucket}"] = sum(
                1
                for ranks in present.values()
                if any(x is not None and not a and x <= bucket for x, a in ranks)
            )
            entry[f"approximate_inclusive_dps_rank_le_{bucket}"] = sum(
                1
                for ranks in present.values()
                if any(x is not None and x <= bucket for x, _ in ranks)
            )
        fight_rows.append(entry)
    # Per boss x configuration: captured fights with the configuration present,
    # and distinct characters at a DPS rank within each bucket (cohort material).
    # Every sampled fight is bound to its boss from its own rankings block,
    # independently of whether any of its rows survive the eligibility filters.
    fights_per_boss = collections.Counter(fight_encounters.values())
    observed_per_boss = collections.Counter(
        fight_encounters[k] for k in {(r["report"], r["fight"]) for r in kept}
    )
    matrix = {}
    for config in sorted(legal):
        cells = {}
        for encounter in sorted(fights_per_boss):
            mine = [r for r in kept if r["config"] == config and r["encounter"] == encounter]
            cell = {"fights_present": len({(r["report"], r["fight"]) for r in mine})}
            if config[2] == "dps":
                others = [r for r in mine if r["character"] != SUBJECT_ID]
                for bucket in RANK_BUCKETS:
                    cell[f"characters_exact_rank_le_{bucket}"] = len(
                        {
                            r["character"]
                            for r in others
                            if r["rank"] is not None
                            and not r["approximate_rank"]
                            and r["rank"] <= bucket
                        }
                    )
                    cell[f"characters_approximate_inclusive_rank_le_{bucket}"] = len(
                        {
                            r["character"]
                            for r in others
                            if r["rank"] is not None and r["rank"] <= bucket
                        }
                    )
            cells[str(encounter)] = cell
        matrix[config_key(config)] = cells
    # Same-character subject coverage, per report and across reports.
    single_session = collections.defaultdict(set)
    across = collections.defaultdict(set)
    for r in (r for r in kept if r["resolved"]):
        single_session[(r["config"], r["character"], r["report"])].add(r["encounter"])
        across[(r["config"], r["character"])].add(r["encounter"])
    subjects = {}
    for config in sorted(legal):
        best_single = max(
            (len(v) for (c, _, _), v in single_session.items() if c == config), default=0
        )
        best_across = max((len(v) for (c, _), v in across.items() if c == config), default=0)
        subjects[config_key(config)] = {
            "best_bosses_one_report_scope": best_single,
            "best_bosses_same_global_id_across_reports": best_across,
            "global_ids_all_15_one_report_scope": sum(
                1 for (c, _, _), v in single_session.items() if c == config and len(v) == BOSSES
            ),
        }
    # Conditional cohort opportunity: (config, boss) cells with at least COHORT
    # distinct same-configuration characters within a DPS rank bucket.
    dps_cells = sum(1 for c in legal if c[2] == "dps") * len(fights_per_boss)
    cohort = {}
    for kind in ("exact", "approximate_inclusive"):
        for bucket in RANK_BUCKETS:
            key = f"characters_{kind}_rank_le_{bucket}"
            counts = [
                cell.get(key, 0)
                for config, cells in matrix.items()
                if config.split("/")[2] == "dps"
                for cell in cells.values()
            ]
            cohort[f"{kind}_le_{bucket}"] = {
                "cells_with_threshold_presence": sum(1 for c in counts if c >= COHORT),
                "slot_share_with_presence": round(
                    sum(min(COHORT, c) for c in counts) / (COHORT * dps_cells), 4
                ),
            }
    return {
        "kind": "Offline fight-centric opportunity estimate; conditional, biased sample",
        "archive": {"path": ARCHIVE.relative_to(ROOT).as_posix(), "sha256": ARCHIVE_SHA256},
        "sample": {
            "fights": len(fights),
            "reports": len({k[0] for k in fights}),
            "fights_per_boss": {str(k): v for k, v in sorted(fights_per_boss.items())},
            "fights_with_observed_configuration_per_boss": {
                str(k): observed_per_boss.get(k, 0) for k in sorted(fights_per_boss)
            },
            "fights_without_observed_configuration": len(fights) - sum(observed_per_boss.values()),
            "selection_bias": "fights chosen for Druid Balance DPS Alliance subject and cohort",
        },
        "rows": {"kept": len(kept), "excluded": dict(sorted(excluded.items()))},
        "global_ids": {
            "distinct": len(locators),
            "conflicting_locator_or_class": len(conflicting),
            "spans_kept_per_report": True,
        },
        "legal_configurations": len(legal),
        "configurations_observed": len({r["config"] for r in kept}),
        "nominal_actor_boss_slots": {
            "value": len(legal) * (1 + COHORT) * BOSSES,
            "meaning": "configurations x (subject + cohort) x bosses; not fights or requests",
        },
        "rank_text": {
            "exact": sum(1 for r in kept if r["rank_text"] and not r["approximate_rank"]),
            "approximate": sum(1 for r in kept if r["approximate_rank"]),
        },
        "per_fight": fight_rows,
        "boss_configuration_matrix": matrix,
        "subject_coverage": subjects,
        "cohort_presence_threshold": {
            "condition": "distinct same-configuration characters (the measurement subject "
            "excluded) present in captured fights for that boss within a DPS rank bucket; "
            f"cells count {COHORT} or more, slot share counts up to {COHORT} per cell",
            "not_eligibility": "selection, faction-qualified ranking row, ownership, metric and "
            "stream completeness are not proved for any of these characters",
            "dps_configuration_boss_cells": dps_cells,
            "by_bucket": cohort,
        },
        "measured_costs": measured_costs(),
        "subject_coverage_limit": (
            "Report bundles hold only the selected fights (1-3 per report here), so a single "
            "session's full-clear coverage cannot be measured from this archive; the per-report "
            "figures are a floor set by selection, not a property of the raids."
        ),
        "limits": [
            "One configuration's capture; other configurations' leaderboards were not read.",
            "Rank is the DPS-metric global rank; it is not cohort eligibility (same faction, "
            "ownership, the configuration's own ranking row and stream completeness).",
            "HPS configurations are presence-only.",
            "Reports are separate sessions; guilds are context only.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = estimate()
    result["estimate_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
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
