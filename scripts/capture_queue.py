"""Build the reviewed capture queue for the unattended Tower runner.

Usage: uv run python scripts/capture_queue.py plan
       uv run python scripts/capture_queue.py resolve --budget 40
       uv run python scripts/capture_queue.py emit
       uv run python scripts/capture_queue.py summary

`plan` is offline. It derives the raid/configuration universe from the coverage
matrix, classifies every run that already has registered real captures, and
mines public subject candidates from the rankings inside the raw archives
already in the repository. `resolve` is the only step that spends Warcraft
Logs points: it runs `necropsy resolve` for at most `--budget` candidates and
caches every answer, so a rerun never pays twice. `emit` writes the queue that
`scripts/capture_runner.py` loads, using only candidates whose current faction
was observed and matches the entry.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "tasks/raid-completion/coverage-matrix.csv"
REGISTER = ROOT / "tests/golden/raids/coverage.json"
PROVENANCE = ROOT / "tests/golden/raids/provenance.json"
RAW = ROOT / "tests/golden/raids/raw"
RESEARCH = ROOT / "tasks/raid-completion/research"
PLAN = RESEARCH / "capture-queue-plan.json"
RESOLUTIONS = RESEARCH / "capture-candidate-resolutions.json"
# The user's own characters, as region/server/name; never queued.
EXCLUDED = RESEARCH / "capture-excluded-characters.json"
QUEUE = ROOT / "tasks/raid-completion/capture-queue.json"

QUEUE_VERSION = 1
PARTITION = 1
MAX_CANDIDATES = 3
POOL_SIZE = 30
SITE = "https://vanilla.warcraftlogs.com"
# Report guild faction ids, checked against faction-locked classes (Paladin
# reports carry 0, Shaman reports carry 1). A hint for ordering only: a
# guild's faction is not the character's, so `resolve` decides.
GUILD_FACTION = {0: "Alliance", 1: "Horde"}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    temp.write_text(text, encoding="utf-8", newline="\n")
    temp.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def entry_id(raid: str, cls: str, category: str, metric: str, faction: str) -> str:
    return "-".join(_slug(part) for part in (raid, cls, category, metric, faction))


# -- universe and classification ------------------------------------------------


def universe(matrix: Path = MATRIX) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Every raid x legal configuration run, and each raid's encounters by id."""
    with matrix.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    runs: dict[tuple[str, ...], dict[str, Any]] = {}
    encounters: dict[str, dict[str, str]] = defaultdict(dict)
    for row in rows:
        encounters[row["raid"]][row["encounter_id"]] = row["boss"]
        key = (row["raid"], row["class_id"], row["category"], row["metric"], row["faction"])
        runs.setdefault(
            key,
            {
                "entry_id": entry_id(
                    row["raid"], row["class"], row["category"], row["metric"], row["faction"]
                ),
                "raid": row["raid"],
                "zone": int(row["zone_id"]),
                "class_id": int(row["class_id"]),
                "class": row["class"],
                "category": row["category"],
                "metric": row["metric"],
                "faction": row["faction"],
            },
        )
    return sorted(runs.values(), key=lambda r: r["entry_id"]), dict(encounters)


def classify(
    runs: list[dict[str, Any]],
    encounters: dict[str, dict[str, str]],
    register: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Classify each run that has registered real captures; others are absent.

    usable: registered cells cover every encounter of the raid.
    partial-final: at least half covered and no archive stopped early, so the
      gaps are source limits or open analysis, not missing capture time.
    partial-resumable: an archive stopped early and nothing later finished.
    seed: a bounded capture of a few encounters; requeued as a full raid.
    Only usable and partial-final runs leave the queue.
    """
    fixtures = {f["sha256"]: f for f in provenance["fixtures"]}
    found: dict[str, dict[str, Any]] = defaultdict(lambda: {"archives": {}, "cells": set()})
    for record in register["records"]:
        source = record.get("real_actor_source")
        if not source:
            continue
        raid, encounter, class_id, category, metric, faction = record["cell_id"].split("/")
        run = next(
            r
            for r in runs
            if (r["raid"], str(r["class_id"]), r["category"], r["metric"], r["faction"])
            == (raid, class_id, category, metric, faction)
        )
        archive = source["archive"]
        fixture = fixtures.get(archive["sha256"], {})
        found[run["entry_id"]]["archives"][archive["path"]] = {
            "path": archive["path"],
            "sha256": archive["sha256"],
            "label": fixture.get("label"),
            "url": fixture.get("url"),
            "sources": fixture.get("sources"),
            "stopped": fixture.get("stopped"),
            "captured_date": fixture.get("captured_date"),
        }
        found[run["entry_id"]]["cells"].add(encounter)
    result: dict[str, dict[str, Any]] = {}
    for run in runs:
        if run["entry_id"] not in found:
            continue
        info = found[run["entry_id"]]
        bosses = encounters[run["raid"]]
        missing = sorted(set(bosses) - info["cells"])
        archives = sorted(info["archives"].values(), key=lambda a: a["path"])
        stopped = [a for a in archives if a["stopped"]]
        finished = [a for a in archives if not a["stopped"]]
        if not missing:
            state = "usable"
        elif len(info["cells"]) * 2 >= len(bosses) and not stopped:
            state = "partial-final"
        elif stopped and not finished:
            state = "partial-resumable"
        else:
            state = "seed"
        result[run["entry_id"]] = {
            "state": state,
            "registered_encounters": len(info["cells"]),
            "raid_encounters": len(bosses),
            "missing": [bosses[e] for e in missing],
            "archives": archives,
        }
    return result


# -- candidate mining --------------------------------------------------------------


def _public_reports(raw: Path) -> Any:
    for archive in sorted(raw.rglob("*.zip")):
        relative = archive.relative_to(ROOT).as_posix()
        with zipfile.ZipFile(archive) as bundle:
            for member in sorted(bundle.namelist()):
                if not (member.startswith("reports/") and member.endswith(".json")):
                    continue
                report = json.loads(bundle.read(member)).get("report") or {}
                if report.get("visibility") == "public":
                    yield relative, member, report


def mine(raw: Path, runs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Characters ranked as each run's class and spec in that raid's public reports."""
    wanted: dict[tuple[int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        wanted[(run["zone"], run["class"], run["category"])].append(run)
    pool: dict[tuple[int, str, str], dict[int, dict[str, Any]]] = defaultdict(dict)
    for archive, member, report in _public_reports(raw):
        zone = (report.get("zone") or {}).get("id")
        for index, ranking in enumerate((report.get("rankings") or {}).get("data") or []):
            hint = GUILD_FACTION.get((ranking.get("guild") or {}).get("faction", -1))
            encounter = (ranking.get("encounter") or {}).get("id")
            for role, group in (ranking.get("roles") or {}).items():
                for position, character in enumerate(group.get("characters") or []):
                    key = (zone, character.get("class"), character.get("spec"))
                    if key not in wanted or not isinstance(character.get("id"), int):
                        continue
                    seen = pool[key].setdefault(
                        character["id"],
                        {
                            "id": character["id"],
                            "name": character.get("name"),
                            "server": (character.get("server") or {}).get("name"),
                            "region": (character.get("server") or {}).get("region"),
                            "encounters": set(),
                            "reports": set(),
                            "faction_hints": Counter(),
                            "evidence": {
                                "archive": archive,
                                "member": member,
                                "locator": f"report.rankings.data[{index}].roles.{role}"
                                f".characters[{position}]",
                            },
                        },
                    )
                    seen["encounters"].add(encounter)
                    seen["reports"].add(report.get("code"))
                    if hint:
                        seen["faction_hints"][hint] += 1
    mined: dict[str, list[dict[str, Any]]] = {}
    for key, group in wanted.items():
        found = [
            {
                "id": c["id"],
                "name": c["name"],
                "server": c["server"],
                "region": c["region"],
                "encounters": len(c["encounters"]),
                "reports": len(c["reports"]),
                "faction_hints": dict(c["faction_hints"]),
                "evidence": c["evidence"],
            }
            for c in pool.get(key, {}).values()
        ]
        for run in group:
            mined[run["entry_id"]] = found
    return mined


def _excluded() -> set[str]:
    if not EXCLUDED.is_file():
        return set()
    return {str(item).lower() for item in _read_json(EXCLUDED)["characters"]}


def candidate_url(candidate: dict[str, Any], zone: int) -> str:
    return candidate.get("url") or f"{SITE}/character/id/{candidate['id']}?zone={zone}"


def rank_pool(
    run: dict[str, Any],
    mined: list[dict[str, Any]],
    classification: dict[str, Any] | None,
    excluded: set[str],
) -> list[dict[str, Any]]:
    """Order the resolve pool: an earlier seed subject first, then the strongest
    ranked characters whose report guilds lean to the entry's faction."""
    pool: list[dict[str, Any]] = []
    if classification and classification["state"] in {"seed", "partial-resumable"}:
        urls = sorted({a["url"] for a in classification["archives"] if a["url"]})
        pool += [{"url": url, "origin": "earlier capture subject"} for url in urls]

    def blocked(c: dict[str, Any]) -> bool:
        return (
            str(c["id"]) in excluded
            or f"{c['region']}/{c['server']}/{c['name']}".lower() in excluded
        )

    def order(c: dict[str, Any]) -> tuple[Any, ...]:
        hints = c["faction_hints"]
        lean = hints.get(run["faction"], 0) - sum(
            n for f, n in hints.items() if f != run["faction"]
        )
        return (-(lean > 0), -c["encounters"], -c["reports"], c["id"])

    for c in sorted((c for c in mined if not blocked(c)), key=order):
        pool.append(c | {"origin": "ranked in a public report already captured"})
    unique: dict[str, dict[str, Any]] = {}
    for c in pool:
        unique.setdefault(candidate_url(c, run["zone"]), c | {"url": candidate_url(c, run["zone"])})
    return list(unique.values())[:POOL_SIZE]


def build_plan() -> dict[str, Any]:
    runs, encounters = universe()
    classification = classify(runs, encounters, _read_json(REGISTER), _read_json(PROVENANCE))
    mined = mine(RAW, runs)
    excluded = _excluded()
    entries = []
    for run in runs:
        state = classification.get(run["entry_id"])
        queued = state is None or state["state"] in {"seed", "partial-resumable"}
        entries.append(
            run
            | {
                "classification": state or {"state": "absent"},
                "queued": queued,
                "pool": rank_pool(run, mined[run["entry_id"]], state, excluded) if queued else [],
                "mined_total": len(mined[run["entry_id"]]),
            }
        )
    for item in entries:
        for archive in item["classification"].get("archives", []):
            actual = _sha256(ROOT / archive["path"])
            if actual != archive["sha256"]:
                raise SystemExit(f"{archive['path']}: sha256 {actual} is not the registered one")
    return {
        "generated": datetime.now(UTC).isoformat(timespec="seconds"),
        "inputs": {
            p.relative_to(ROOT).as_posix(): _sha256(p) for p in (MATRIX, REGISTER, PROVENANCE)
        },
        "excluded_characters": len(excluded),
        "entries": entries,
    }


# -- resolution --------------------------------------------------------------------


def parse_resolve(stdout: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in stdout.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip():
            fields.setdefault(key.strip(), value.strip())
    return fields


def verdict(fields: dict[str, str], code: int, expected: str) -> tuple[bool, str]:
    if code != 0:
        return False, f"resolve exited {code}"
    if "needs a choice" in fields:
        return False, f"ambiguous: {fields['needs a choice']}"
    faction = fields.get("faction", "unknown")
    if faction != expected:
        return False, f"faction {faction}, entry needs {expected}"
    return True, "faction observed and matching"


def _accepts(answer: dict[str, Any], faction: str) -> tuple[bool, str]:
    return verdict(answer["fields"], answer["exit"], faction)


def _run_resolve(url: str) -> tuple[int, str, str]:
    done = subprocess.run(
        [
            "uv",
            "run",
            "necropsy",
            "resolve",
            url,
            "--partition",
            str(PARTITION),
            "--endpoint",
            "user",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    return done.returncode, done.stdout, done.stderr


def resolve(budget: int, runner: Callable[[str], tuple[int, str, str]] = _run_resolve) -> int:
    """Resolve pool candidates until each entry has enough accepted ones or the
    budget is spent. Cached answers are reused and cost nothing."""
    plan = _read_json(PLAN)
    cache: dict[str, Any] = _read_json(RESOLUTIONS) if RESOLUTIONS.is_file() else {}
    spent = 0
    for item in plan["entries"]:
        accepted = 0
        for candidate in item["pool"]:
            if accepted >= MAX_CANDIDATES:
                break
            key = candidate["url"]
            if key not in cache:
                if spent >= budget:
                    break
                code, stdout, stderr = runner(candidate["url"])
                spent += 1
                cache[key] = {
                    "resolved_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "exit": code,
                    "fields": parse_resolve(stdout),
                    "error": stderr.strip().splitlines()[-1:] if code else [],
                }
                _write_json(RESOLUTIONS, cache)
            accepted += _accepts(cache[key], item["faction"])[0]
    print(f"resolved {spent} new candidate(s); cache holds {len(cache)}")
    return 0


# -- emit and summary --------------------------------------------------------------


def queue_entries(
    plan: dict[str, Any], cache: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    entries, unfilled = [], []
    for item in plan["entries"]:
        if not item["queued"]:
            continue
        chosen = []
        for candidate in item["pool"]:
            answer = cache.get(candidate["url"])
            if answer and _accepts(answer, item["faction"])[0]:
                chosen.append((candidate, answer))
            if len(chosen) == MAX_CANDIDATES:
                break
        if not chosen:
            unfilled.append(item["entry_id"])
            continue
        entries.append(
            {
                "entry_id": item["entry_id"],
                "raid": item["raid"],
                "zone": item["zone"],
                "partition": PARTITION,
                "class_id": item["class_id"],
                "category": item["category"],
                "metric": item["metric"],
                "faction": item["faction"],
                "candidates": [c["url"] for c, _ in chosen],
                "candidate_evidence": [
                    {
                        "url": c["url"],
                        "character": a["fields"].get("character"),
                        "server": a["fields"].get("server"),
                        "resolved_faction": a["fields"].get("faction"),
                        "resolved_at": a["resolved_at"],
                        "origin": c["origin"],
                        "encounters_ranked": c.get("encounters"),
                        "evidence": c.get("evidence"),
                    }
                    for c, a in chosen
                ],
            }
        )
    return entries, unfilled


def emit() -> int:
    plan = _read_json(PLAN)
    cache = _read_json(RESOLUTIONS) if RESOLUTIONS.is_file() else {}
    entries, unfilled = queue_entries(plan, cache)
    _write_json(
        QUEUE,
        {
            "version": QUEUE_VERSION,
            "plan_sha256": _sha256(PLAN),
            "resolutions_sha256": _sha256(RESOLUTIONS) if RESOLUTIONS.is_file() else None,
            "entries": entries,
        },
    )
    print(f"wrote {len(entries)} entries to {QUEUE.relative_to(ROOT).as_posix()}")
    if unfilled:
        print(
            f"{len(unfilled)} queued run(s) have no accepted candidate yet: {', '.join(unfilled)}"
        )
    return 1 if unfilled else 0


def summary() -> int:
    plan = _read_json(PLAN)
    cache = _read_json(RESOLUTIONS) if RESOLUTIONS.is_file() else {}
    states = Counter(i["classification"]["state"] for i in plan["entries"])
    print(
        f"universe {len(plan['entries'])} runs: "
        + ", ".join(f"{k} {v}" for k, v in sorted(states.items()))
    )
    queued = sum(i["queued"] for i in plan["entries"])
    print(f"queued {queued}; excluded characters {plan['excluded_characters']}")
    for item in plan["entries"]:
        c = item["classification"]
        if c["state"] == "absent":
            continue
        missing = f" missing {', '.join(c['missing'])}" if c["missing"] else ""
        covered = f"{c['registered_encounters']}/{c['raid_encounters']}"
        print(f"  {c['state']:18} {item['entry_id']} {covered}{missing}")
    entries, unfilled = queue_entries(plan, cache)
    thin = [
        i["entry_id"] for i in plan["entries"] if i["queued"] and len(i["pool"]) < MAX_CANDIDATES
    ]
    reasons = Counter(_accepts(a, "Alliance")[1].split(",")[0] for a in cache.values())
    print(f"resolutions {len(cache)} ({dict(reasons)})")
    print(f"entries ready {len(entries)}; unfilled {len(unfilled)}")
    if thin:
        print(f"pools under {MAX_CANDIDATES}: {', '.join(thin)}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="offline: universe, classification, candidate pools")
    spend = commands.add_parser("resolve", help="online: confirm candidate factions (cached)")
    spend.add_argument("--budget", type=int, required=True, help="most new resolve calls")
    commands.add_parser("emit", help="write the runner queue")
    commands.add_parser("summary", help="print classification and readiness")
    args = parser.parse_args(argv)
    if args.command == "plan":
        _write_json(PLAN, build_plan())
        return summary()
    if args.command == "resolve":
        return resolve(args.budget)
    if args.command == "emit":
        return emit()
    return summary()


if __name__ == "__main__":
    sys.exit(main())
