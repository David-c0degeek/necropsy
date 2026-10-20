"""Build the reviewed capture queue for the unattended Tower runner.

Usage: uv run python scripts/capture_queue.py plan
       uv run python scripts/capture_queue.py resolve --budget 40
       uv run python scripts/capture_queue.py leaderboard --budget 10   (then plan, resolve)
       uv run python scripts/capture_queue.py emit
       uv run python scripts/capture_queue.py verify [--snapshot]
       uv run python scripts/capture_queue.py summary

`plan` is offline. It derives the raid/configuration universe from the coverage
matrix, decides per boss whether a run already has reusable captured data, and
mines public subject candidates from the rankings inside the raw archives
already in the repository. `resolve` is the only step that spends Warcraft
Logs points: it checks each candidate's faction with `necropsy resolve` and
that WCL ranks the character for the entry's class, spec and metric, at most
`--budget` live calls, caching every answer so a rerun never pays twice.
`emit` writes the queue that `scripts/capture_runner.py` loads, and refuses to
replace it while any queued run lacks a fully checked candidate. `verify`
checks every pin against the committed Git blobs and the checkout, so it fails
once any input changes. `verify --snapshot` checks the queue a runner may be
executing: unchanged since the commit that wrote it, with every pin intact at
that commit; later coverage or provenance changes are reported as its age.

Capture-ready means no capture is needed; it never means a cell is COMPLETE.
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
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "tasks/raid-completion/coverage-matrix.csv"
REGISTER = ROOT / "tests/golden/raids/coverage.json"
PROVENANCE = ROOT / "tests/golden/raids/provenance.json"
RAW = ROOT / "tests/golden/raids/raw"
RESEARCH = ROOT / "tasks/raid-completion/research"
PLAN = RESEARCH / "capture-queue-plan.json"
RESOLUTIONS = RESEARCH / "capture-candidate-resolutions.json"
RANKINGS = RESEARCH / "capture-candidate-rankings.json"
LEADERBOARDS = RESEARCH / "capture-leaderboard-pages.json"
# The user's own characters, as region/server/name; never queued.
EXCLUDED = RESEARCH / "capture-excluded-characters.json"
QUEUE = ROOT / "tasks/raid-completion/capture-queue.json"
SNAPSHOT = "necropsy-snapshot.json"

QUEUE_VERSION = 1
PARTITION = 1
MAX_CANDIDATES = 3
POOL_SIZE = 30
SITE = "https://vanilla.warcraftlogs.com"
# Report guild faction ids, checked against faction-locked classes (Paladin
# reports carry 0, Shaman reports carry 1). A hint for ordering only: a
# guild's faction is not the character's, so `resolve` decides.
GUILD_FACTION = {0: "Alliance", 1: "Horde"}
# The report ranking role whose rows carry each metric.
METRIC_ROLES = {"dps": {"dps", "tanks"}, "hps": {"healers"}}


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


# -- universe and per-boss dispositions ---------------------------------------------


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


def read_snapshot(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as bundle:
        data: dict[str, Any] = json.loads(bundle.read(SNAPSHOT))
    return data


def identity_problems(run: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
    """Why a snapshot was not captured for this run's configuration, if it wasn't."""
    subject = snapshot.get("subject") or {}
    zone = snapshot.get("zone") or {}
    expected = {
        "subject.class_id": (subject.get("class_id"), run["class_id"]),
        "subject.ranking_category": (subject.get("ranking_category"), run["category"]),
        "subject.ranking_metric": (subject.get("ranking_metric"), run["metric"]),
        "subject.faction": (subject.get("faction"), run["faction"]),
        "zone.id": (zone.get("id"), run["zone"]),
        "zone.partition": (zone.get("partition"), PARTITION),
    }
    return [f"{k} {got!r} != {want!r}" for k, (got, want) in expected.items() if got != want]


def _complete_cohort(boss: dict[str, Any]) -> int:
    return sum(1 for entry in boss.get("cohort") or [] if entry.get("status") == "complete")


def _cohort_met(boss: dict[str, Any]) -> bool:
    """The comparison cohort reached its target with complete entries. A missing
    subject fight is a limitation of that boss, not missing capture."""
    coverage = boss.get("coverage") or {}
    target = coverage.get("target") or 0
    return target > 0 and (coverage.get("usable_deep") or 0) >= target <= _complete_cohort(boss)


def dispositions(
    runs: list[dict[str, Any]],
    encounters: dict[str, dict[str, str]],
    register: dict[str, Any],
    provenance: dict[str, Any],
    snapshots: Callable[[str], dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Decide, boss by boss, whether a run with registered captures needs more.

    registered: the cell already cites a real actor source from an archive
      with provenance and a matching snapshot identity.
    offline-reuse: not registered, but a finished matching snapshot holds that
      boss with complete cohort coverage. Registration and review stay open;
      only the capture is unnecessary.
    needs-capture: anything else, including missing provenance or an unknown
      or mismatched identity. One such boss puts the whole run in the queue.
    """
    fixtures = {f["sha256"]: f for f in provenance["fixtures"]}
    by_run = {
        (r["raid"], str(r["class_id"]), r["category"], r["metric"], r["faction"]): r for r in runs
    }
    found: dict[str, dict[str, Any]] = defaultdict(lambda: {"archives": {}, "cells": {}})
    for record in register["records"]:
        source = record.get("real_actor_source")
        if not source:
            continue
        raid, encounter, *config = record["cell_id"].split("/")
        run = by_run[(raid, *config)]
        archive = source["archive"]
        found[run["entry_id"]]["archives"][archive["path"]] = archive["sha256"]
        found[run["entry_id"]]["cells"][encounter] = archive["path"]
    result: dict[str, dict[str, Any]] = {}
    for run in runs:
        info = found.get(run["entry_id"])
        if info is None:
            continue
        archives: dict[str, dict[str, Any]] = {}
        for path, sha in sorted(info["archives"].items()):
            fixture = fixtures.get(sha)
            snapshot = snapshots(path)
            problems = identity_problems(run, snapshot)
            if fixture is None:
                problems.append("no provenance fixture")
            archives[path] = {
                "path": path,
                "sha256": sha,
                "label": fixture and fixture.get("label"),
                "url": fixture and fixture.get("url"),
                "stopped": snapshot.get("stopped"),
                "identity_problems": problems,
                "bosses": snapshot.get("bosses") or [],
            }
        bosses: list[dict[str, Any]] = []
        for encounter, name in encounters[run["raid"]].items():
            path = info["cells"].get(encounter)
            if path and not archives[path]["identity_problems"]:
                bosses.append({"boss": name, "disposition": "registered", "archive": path})
                continue
            reuse = next(
                (
                    {
                        "archive": a["path"],
                        "sha256": a["sha256"],
                        "locator": f"{SNAPSHOT}:bosses[{index}]",
                        "usable_deep": boss["coverage"]["usable_deep"],
                        "complete_cohort": _complete_cohort(boss),
                        "subject_status": (boss.get("subject") or {}).get("status"),
                        "limitations": list(dict.fromkeys(boss["coverage"].get("reasons") or []))[
                            :3
                        ],
                    }
                    for a in archives.values()
                    if not a["identity_problems"] and a["stopped"] is None
                    for index, boss in enumerate(a["bosses"])
                    if str(boss.get("encounter_id")) == encounter and _cohort_met(boss)
                ),
                None,
            )
            if reuse:
                bosses.append({"boss": name, "disposition": "offline-reuse"} | reuse)
            else:
                why = archives[path]["identity_problems"] if path else ["no reusable snapshot"]
                bosses.append({"boss": name, "disposition": "needs-capture", "why": why})
        needs = [b["boss"] for b in bosses if b["disposition"] == "needs-capture"]
        result[run["entry_id"]] = {
            "state": "needs-capture" if needs else "capture-ready",
            "needs_capture": needs,
            "bosses": bosses,
            "archives": [{k: v for k, v in a.items() if k != "bosses"} for a in archives.values()],
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
    """Characters ranked as each run's class and spec in that raid's public reports.

    A row counts toward a run only under the report role that carries its
    metric, so a damage row never stands in for healing."""
    wanted: dict[tuple[int, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        for role in METRIC_ROLES[run["metric"]]:
            wanted[(run["zone"], run["class"], run["category"], role)].append(run)
    pool: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for archive, member, report in _public_reports(raw):
        zone = (report.get("zone") or {}).get("id")
        for index, ranking in enumerate((report.get("rankings") or {}).get("data") or []):
            hint = GUILD_FACTION.get((ranking.get("guild") or {}).get("faction", -1))
            encounter = (ranking.get("encounter") or {}).get("id")
            for role, group in (ranking.get("roles") or {}).items():
                for position, character in enumerate(group.get("characters") or []):
                    key = (zone, character.get("class"), character.get("spec"), role)
                    if key not in wanted or not isinstance(character.get("id"), int):
                        continue
                    for run in wanted[key]:
                        seen = pool[run["entry_id"]].setdefault(
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
    return {
        run["entry_id"]: [
            c
            | {
                "encounters": len(c["encounters"]),
                "reports": len(c["reports"]),
                "faction_hints": dict(c["faction_hints"]),
            }
            for c in pool[run["entry_id"]].values()
        ]
        for run in runs
    }


def _excluded() -> set[str]:
    if not EXCLUDED.is_file():
        return set()
    return {str(item).lower() for item in _read_json(EXCLUDED)["characters"]}


def candidate_url(candidate: dict[str, Any], zone: int) -> str:
    return candidate.get("url") or f"{SITE}/character/id/{candidate['id']}?zone={zone}"


def rank_pool(
    run: dict[str, Any],
    mined: list[dict[str, Any]],
    state: dict[str, Any] | None,
    excluded: set[str],
) -> list[dict[str, Any]]:
    """Order the resolve pool: earlier subjects of this exact configuration first,
    then the strongest ranked characters whose report guilds lean to the
    entry's faction."""
    pool: list[dict[str, Any]] = []
    for archive in (state or {}).get("archives", []):
        if archive["url"] and not archive["identity_problems"]:
            pool.append(
                {
                    "url": archive["url"],
                    "origin": "earlier capture subject",
                    "metric_evidence": {"archive": archive["path"], "sha256": archive["sha256"]},
                }
            )

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


def leaderboard_key(run: dict[str, Any], encounter: str) -> str:
    return f"{run['zone']}|{run['class']}|{run['category']}|{run['metric']}|{encounter}"


def leaderboard_pool(
    run: dict[str, Any], encounters: dict[str, str], boards: dict[str, Any], excluded: set[str]
) -> list[dict[str, Any]]:
    """Characters on WCL's first leaderboard page for this spec and metric, used
    only where the mined pool ran dry. Realms without an ASCII slug are skipped."""
    found: dict[str, dict[str, Any]] = {}
    for encounter, boss in encounters.items():
        for row in boards.get(leaderboard_key(run, encounter)) or []:
            server, region, name = row["server"], row["region"], row["name"]
            if not (server.isascii() and region.lower() in {"us", "eu"}) or row["amount"] <= 0:
                continue
            if f"{region}/{server}/{name}".lower() in excluded:
                continue
            path = f"{region.lower()}/{_slug(server)}/{quote(name)}"
            url = f"{SITE}/character/{path}?zone={run['zone']}"
            found.setdefault(
                url,
                {
                    "url": url,
                    "origin": "WCL leaderboard, first page",
                    "evidence": {"boss": boss, "amount": row["amount"], "page": 1},
                },
            )
    return list(found.values())[:POOL_SIZE]


def build_plan() -> dict[str, Any]:
    runs, encounters = universe()
    for path in {a for r in _read_json(REGISTER)["records"] if (a := _archive_path(r))}:
        recorded = next(
            r["real_actor_source"]["archive"]["sha256"]
            for r in _read_json(REGISTER)["records"]
            if _archive_path(r) == path
        )
        if _sha256(ROOT / path) != recorded:
            raise SystemExit(f"{path}: sha256 is not the registered one")
    states = dispositions(
        runs,
        encounters,
        _read_json(REGISTER),
        _read_json(PROVENANCE),
        lambda path: read_snapshot(ROOT / path),
    )
    mined = mine(RAW, runs)
    excluded = _excluded()
    boards = _read_json(LEADERBOARDS) if LEADERBOARDS.is_file() else {}
    entries = []
    for run in runs:
        state = states.get(run["entry_id"])
        queued = state is None or state["state"] == "needs-capture"
        pool = rank_pool(run, mined[run["entry_id"]], state, excluded) if queued else []
        if queued:
            known = {c["url"] for c in pool}
            extra = leaderboard_pool(run, encounters[run["raid"]], boards, excluded)
            pool += [c for c in extra if c["url"] not in known]
        entries.append(
            run
            | {
                "disposition": state or {"state": "absent"},
                "queued": queued,
                "pool": pool,
                "mined_total": len(mined[run["entry_id"]]),
            }
        )
    return {
        "generated": datetime.now(UTC).isoformat(timespec="seconds"),
        "inputs": {
            p.relative_to(ROOT).as_posix(): _sha256(p) for p in (MATRIX, REGISTER, PROVENANCE)
        },
        "excluded_characters": len(excluded),
        "entries": entries,
    }


def _archive_path(record: dict[str, Any]) -> str | None:
    source = record.get("real_actor_source")
    return source["archive"]["path"] if source else None


# -- faction and metric checks -----------------------------------------------------


def parse_resolve(stdout: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in stdout.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip():
            fields.setdefault(key.strip(), value.strip())
    return fields


def verdict(
    fields: dict[str, str], code: int, expected: str, character_id: int | None = None
) -> tuple[bool, str]:
    if code != 0:
        return False, f"resolve exited {code}"
    if "needs a choice" in fields:
        return False, f"ambiguous: {fields['needs a choice']}"
    if fields.get("partition", "unknown") == "unknown":
        return False, "no partition resolved"
    if character_id is not None and fields.get("id") != str(character_id):
        return False, f"resolved id {fields.get('id')}, mined id {character_id}"
    faction = fields.get("faction", "unknown")
    if faction != expected:
        return False, f"faction {faction}, entry needs {expected}"
    return True, "faction observed and matching"


def metric_verdict(answer: dict[str, Any], item: dict[str, Any]) -> tuple[bool, str, list[str]]:
    """WCL must rank the character for this zone, partition, spec and metric with
    a positive amount on at least one boss. Kill counts alone are per spec, and
    a zero-amount rank exists for every spec, so neither proves the metric."""
    if "error" in answer:
        return False, f"rankings query failed: {answer['error']}", []
    data = answer["rankings"]
    if (data.get("metric"), data.get("zone"), data.get("partition")) != (
        item["metric"],
        item["zone"],
        PARTITION,
    ):
        return False, "rankings answered a different metric, zone or partition", []
    ranked = [
        r["encounter"]
        for r in data.get("rankings") or []
        if (r.get("totalKills") or 0) > 0
        and (r.get("bestAmount") or 0) > 0
        and r.get("spec") == item["category"]
    ]
    if not ranked:
        return False, f"no {item['category']} {item['metric']} amount on any boss", []
    return True, f"{item['metric']} ranked on {len(ranked)} boss(es)", ranked


def ranking_key(character_id: int | str, item: dict[str, Any]) -> str:
    return f"{character_id}|{item['zone']}|{item['class']}|{item['category']}|{item['metric']}"


def _run_resolve(url: str) -> tuple[int, str, str]:
    """`necropsy resolve` in process, so failures keep their type. A character
    WCL refuses is an answer (exit 1, cached); quota, network or sign-in
    trouble raises and stops the run without caching anything."""
    from necropsy.wcl.cli import _auth
    from necropsy.wcl.client import NotFound, PermissionDenied, WclClient
    from necropsy.wcl.context import describe
    from necropsy.wcl.context import resolve as resolve_character
    from necropsy.wcl.urls import parse_character_url

    ref = parse_character_url(url)
    client = WclClient(ref.site, _auth().token_for)
    try:
        context = resolve_character(client, ref, partition=PARTITION, endpoint="user")
    except (NotFound, PermissionDenied) as error:
        return 1, "", f"resolve failed: {error}"
    finally:
        client.close()
    lines = [f"{k}: {'unknown' if v is None else v}" for k, v in describe(context).items()]
    if context.faction.level != "observed":
        lines.append(f"faction note: {context.faction.note}")
    if context.ambiguity:
        lines.append(f"needs a choice: {context.ambiguity}")
    return 0, "\n".join(lines) + "\n", ""


def _query_rankings(character_id: int, item: dict[str, Any]) -> dict[str, Any]:
    from necropsy.wcl.cli import _auth
    from necropsy.wcl.client import RATE_FIELDS, WclClient
    from necropsy.wcl.urls import parse_character_url

    if item["metric"] not in METRIC_ROLES:
        raise ValueError(f"unsupported metric {item['metric']!r}")
    query = f"""
query NecropsyQueueRanking($id: Int!, $zone: Int!, $partition: Int!, $cls: String!,
                           $spec: String!) {{
  characterData {{
    character(id: $id) {{
      rankings: zoneRankings(zoneID: $zone, partition: $partition, metric: {item["metric"]},
                             className: $cls, specName: $spec)
    }}
  }}
  {RATE_FIELDS}
}}
"""
    site = parse_character_url(f"{SITE}/character/id/{character_id}?zone={item['zone']}").site
    client = WclClient(site, _auth().token_for)
    try:
        result = client.query(
            query,
            {
                "id": character_id,
                "zone": item["zone"],
                "partition": PARTITION,
                "cls": item["class"],
                "spec": item["category"],
            },
            endpoint="user",
        )
    finally:
        client.close()
    raw = ((result.data.get("characterData") or {}).get("character") or {}).get("rankings")
    data = json.loads(raw) if isinstance(raw, str) else raw or {}
    return {
        "metric": data.get("metric"),
        "zone": data.get("zone"),
        "partition": data.get("partition"),
        "rankings": [
            {
                "encounter": (r.get("encounter") or {}).get("name"),
                "totalKills": r.get("totalKills"),
                "bestAmount": r.get("bestAmount"),
                "spec": r.get("spec"),
            }
            for r in data.get("rankings") or []
        ],
    }


Resolver = Callable[[str], tuple[int, str, str]]
Ranker = Callable[[int, dict[str, Any]], dict[str, Any]]


def check(
    item: dict[str, Any],
    candidate: dict[str, Any],
    resolutions: dict[str, Any],
    rankings: dict[str, Any],
) -> tuple[bool | None, str]:
    """Both gates from cached answers; None while an answer is still missing."""
    answer = resolutions.get(candidate["url"])
    if answer is None:
        return None, "faction not checked"
    ok, why = verdict(answer["fields"], answer["exit"], item["faction"], candidate.get("id"))
    if not ok:
        return False, why
    if candidate.get("metric_evidence"):
        return True, "metric shown by an earlier capture of this configuration"
    ranked = rankings.get(ranking_key(answer["fields"]["id"], item))
    if ranked is None:
        return None, "metric not checked"
    ok, why, _ = metric_verdict(ranked, item)
    return ok, why


def resolve(
    budget: int, resolver: Resolver = _run_resolve, ranker: Ranker = _query_rankings
) -> int:
    """Check pool candidates until each entry has enough that pass both gates or
    the budget of live calls is spent. Cached answers cost nothing."""
    plan = _read_json(PLAN)
    resolutions: dict[str, Any] = _read_json(RESOLUTIONS) if RESOLUTIONS.is_file() else {}
    rankings: dict[str, Any] = _read_json(RANKINGS) if RANKINGS.is_file() else {}
    spent = 0
    for item in plan["entries"]:
        accepted = 0
        for candidate in item["pool"]:
            if accepted >= MAX_CANDIDATES or spent >= budget:
                break
            if candidate["url"] not in resolutions:
                try:
                    code, stdout, stderr = resolver(candidate["url"])
                except Exception as error:  # quota, network or auth: stop, cache nothing
                    print(f"stopped after {spent} live call(s): {type(error).__name__}: {error}")
                    return 2
                spent += 1
                resolutions[candidate["url"]] = {
                    "resolved_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "exit": code,
                    "fields": parse_resolve(stdout),
                    "error": stderr.strip().splitlines()[-1:] if code else [],
                }
                _write_json(RESOLUTIONS, resolutions)
            ok, why = check(item, candidate, resolutions, rankings)
            if ok is None and why == "metric not checked" and spent < budget:
                character_id = int(resolutions[candidate["url"]]["fields"]["id"])
                try:
                    answer: dict[str, Any] = {"rankings": ranker(character_id, item)}
                except Exception as error:  # quota, network or auth: stop, cache nothing
                    print(f"stopped after {spent} live call(s): {type(error).__name__}: {error}")
                    return 2
                spent += 1
                answer["checked_at"] = datetime.now(UTC).isoformat(timespec="seconds")
                rankings[ranking_key(character_id, item)] = answer
                _write_json(RANKINGS, rankings)
                ok, why = check(item, candidate, resolutions, rankings)
            accepted += ok is True
    print(f"made {spent} live call(s); {len(resolutions)} resolutions, {len(rankings)} rankings")
    return 0


# -- emit, verify and summary ------------------------------------------------------


def _query_leaderboard(run: dict[str, Any], encounter: str) -> list[dict[str, Any]]:
    from necropsy.wcl.cli import _auth
    from necropsy.wcl.client import RATE_FIELDS, WclClient
    from necropsy.wcl.urls import parse_character_url

    if run["metric"] not in METRIC_ROLES:
        raise ValueError(f"unsupported metric {run['metric']!r}")
    query = f"""
query NecropsyQueueLeaderboard($encounter: Int!, $partition: Int!, $cls: String!,
                               $spec: String!) {{
  worldData {{
    encounter(id: $encounter) {{
      characterRankings(metric: {run["metric"]}, className: $cls, specName: $spec,
                        partition: $partition, page: 1)
    }}
  }}
  {RATE_FIELDS}
}}
"""
    site = parse_character_url(f"{SITE}/character/id/1?zone={run['zone']}").site
    client = WclClient(site, _auth().token_for)
    try:
        result = client.query(
            query,
            {
                "encounter": int(encounter),
                "partition": PARTITION,
                "cls": run["class"],
                "spec": run["category"],
            },
            endpoint="user",
        )
    finally:
        client.close()
    raw = ((result.data.get("worldData") or {}).get("encounter") or {}).get("characterRankings")
    data = json.loads(raw) if isinstance(raw, str) else raw or {}
    return [
        {
            "name": r.get("name"),
            "server": (r.get("server") or {}).get("name") or "",
            "region": (r.get("server") or {}).get("region") or "",
            "amount": r.get("amount") or 0,
        }
        for r in data.get("rankings") or []
        if r.get("spec") == run["category"] and r.get("class") == run["class"] and r.get("name")
    ]


def leaderboard(
    budget: int, fetch: Callable[[dict[str, Any], str], list[dict[str, Any]]] = _query_leaderboard
) -> int:
    """Fetch first leaderboard pages, boss by boss, for queued runs whose pool is
    exhausted without a checked candidate, until each has a full pool. Run
    `plan` afterwards to merge them."""
    plan = _read_json(PLAN)
    _, encounters = universe()
    resolutions, rankings = _load_caches()
    boards: dict[str, Any] = _read_json(LEADERBOARDS) if LEADERBOARDS.is_file() else {}
    _, unfilled = queue_entries(plan, resolutions, rankings)
    spent = 0
    for item in plan["entries"]:
        if item["entry_id"] not in unfilled:
            continue
        if any(check(item, c, resolutions, rankings)[0] is None for c in item["pool"]):
            print(f"{item['entry_id']}: check its pool with `resolve` first")
            continue
        for encounter in encounters[item["raid"]]:
            if len(leaderboard_pool(item, encounters[item["raid"]], boards, set())) >= POOL_SIZE:
                break
            key = leaderboard_key(item, encounter)
            if key in boards:
                continue
            if spent >= budget:
                break
            try:
                boards[key] = fetch(item, encounter)
            except Exception as error:  # quota, network or auth: stop, cache nothing
                print(f"stopped after {spent} live call(s): {type(error).__name__}: {error}")
                return 2
            spent += 1
            _write_json(LEADERBOARDS, boards)
    print(f"made {spent} leaderboard call(s); {len(boards)} pages cached")
    return 0


def _load_caches() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        _read_json(RESOLUTIONS) if RESOLUTIONS.is_file() else {},
        _read_json(RANKINGS) if RANKINGS.is_file() else {},
    )


def queue_entries(
    plan: dict[str, Any], resolutions: dict[str, Any], rankings: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    entries, unfilled = [], []
    for item in plan["entries"]:
        if not item["queued"]:
            continue
        chosen = []
        for candidate in item["pool"]:
            ok, why = check(item, candidate, resolutions, rankings)
            if ok:
                chosen.append((candidate, resolutions[candidate["url"]], why))
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
                "class": item["class"],
                "category": item["category"],
                "metric": item["metric"],
                "faction": item["faction"],
                "candidates": [c["url"] for c, _, _ in chosen],
                "candidate_evidence": [
                    {
                        "url": c["url"],
                        "character": a["fields"].get("character"),
                        "character_id": a["fields"].get("id"),
                        "server": a["fields"].get("server"),
                        "resolved_faction": a["fields"].get("faction"),
                        "resolved_at": a["resolved_at"],
                        "metric_check": why,
                        "ranked_bosses": metric_verdict(
                            rankings[ranking_key(a["fields"]["id"], item)], item
                        )[2]
                        if not c.get("metric_evidence")
                        else None,
                        "origin": c["origin"],
                        "evidence": c.get("evidence") or c.get("metric_evidence"),
                    }
                    for c, a, why in chosen
                ],
            }
        )
    return entries, unfilled


def public_summary(plan: dict[str, Any], scheduled: int) -> dict[str, int]:
    """Only reviewed run counts; capture reuse never means a cell is complete."""
    ready = [item for item in plan["entries"] if not item["queued"]]
    offline = sum(
        any(b["disposition"] == "offline-reuse" for b in item["disposition"]["bosses"])
        for item in ready
    )
    summary = {
        "universe_runs": len(plan["entries"]),
        "scheduled_runs": scheduled,
        "capture_ready_runs": len(ready),
        "all_registered_runs": len(ready) - offline,
        "offline_reuse_runs": offline,
    }
    if summary["universe_runs"] != scheduled + len(ready):
        raise ValueError("the public summary does not account for every planned run")
    return summary


def emit() -> int:
    plan = _read_json(PLAN)
    resolutions, rankings = _load_caches()
    entries, unfilled = queue_entries(plan, resolutions, rankings)
    if unfilled:
        print(f"queue not written; {len(unfilled)} queued run(s) lack a checked candidate:")
        print("  " + ", ".join(unfilled))
        return 1
    _write_json(
        QUEUE,
        {
            "version": QUEUE_VERSION,
            "summary": public_summary(plan, len(entries)),
            "pins": {
                path.relative_to(ROOT).as_posix(): _sha256(path)
                for path in (PLAN, RESOLUTIONS, RANKINGS, LEADERBOARDS)
                if path.is_file()
            },
            "entries": entries,
        },
    )
    print(f"wrote {len(entries)} entries to {QUEUE.relative_to(ROOT).as_posix()}")
    return 0


def _git_blob(path: str, rev: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{rev}:{path}"], cwd=ROOT, capture_output=True, check=True
    ).stdout


def verify(rev: str = "HEAD") -> int:
    """Every pin must equal both the checked-out bytes and the committed blob."""
    queue = json.loads(_git_blob(QUEUE.relative_to(ROOT).as_posix(), rev))
    plan_path = PLAN.relative_to(ROOT).as_posix()
    pins = dict(queue["pins"])
    pins.update(json.loads(_git_blob(plan_path, rev))["inputs"])
    failures = []
    for path, pinned in sorted(pins.items()):
        blob = hashlib.sha256(_git_blob(path, rev)).hexdigest()
        local = _sha256(ROOT / path)
        if not pinned == blob == local:
            failures.append(f"{path}: pin {pinned[:12]} blob {blob[:12]} checkout {local[:12]}")
    for line in failures or [f"{len(pins)} pins match {rev} blobs and the checkout"]:
        print(line)
    return 1 if failures else 0


SHA256 = re.compile(r"[0-9a-f]{64}")


def _pin_map(raw: bytes, key: str, source: str) -> dict[str, str]:
    pins = json.loads(raw)[key]
    if not isinstance(pins, dict) or not pins:
        raise ValueError(f"{source}: {key} is not a non-empty mapping")
    for path, pinned in pins.items():
        if not isinstance(path, str) or not isinstance(pinned, str) or not SHA256.fullmatch(pinned):
            raise ValueError(f"{source}: malformed pin {path!r}")
    return pins


def verify_snapshot(rev: str = "HEAD") -> int:
    """The queue must still be the one emitted, with intact emit-time pins.

    Strict `verify` asks whether every input is still current; this asks whether
    the queue a runner may be executing is unchanged and was pinned correctly when
    it was written. The emit commit is the last commit that wrote the queue file.
    At that commit every pin, direct and transitive, must match its blob. The queue
    and its direct artifacts must still match at `rev` and in the checkout. Later
    changes to transitive plan inputs (coverage, provenance) are reported as
    snapshot age, not failures. Missing history or blobs and malformed pins fail.
    """
    queue_path = QUEUE.relative_to(ROOT).as_posix()
    plan_path = PLAN.relative_to(ROOT).as_posix()
    failures: list[str] = []
    aged: list[str] = []
    emit = ""
    try:
        emit = subprocess.run(
            ["git", "log", "-1", "--format=%H", rev, "--", queue_path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if not emit:
            raise ValueError(f"{queue_path}: no commit in {rev} history writes the queue")
        written = _git_blob(queue_path, emit)
        if not written == _git_blob(queue_path, rev) == (ROOT / queue_path).read_bytes():
            failures.append(f"{queue_path}: differs from its emit commit {emit[:12]}")
        direct = _pin_map(written, "pins", f"{queue_path}@{emit[:12]}")
        if plan_path not in direct:
            raise ValueError(f"{queue_path}@{emit[:12]}: plan {plan_path} is not pinned")
        transitive = _pin_map(_git_blob(plan_path, emit), "inputs", f"{plan_path}@{emit[:12]}")
        for path, pinned in sorted(direct.items()):
            at_emit = hashlib.sha256(_git_blob(path, emit)).hexdigest()
            now = hashlib.sha256(_git_blob(path, rev)).hexdigest()
            local = _sha256(ROOT / path)
            if not pinned == at_emit == now == local:
                failures.append(
                    f"{path}: pin {pinned[:12]} emit {at_emit[:12]} "
                    f"{rev} {now[:12]} checkout {local[:12]}"
                )
        for path, pinned in sorted(transitive.items()):
            at_emit = hashlib.sha256(_git_blob(path, emit)).hexdigest()
            if pinned != at_emit:
                failures.append(f"{path}: pin {pinned[:12]} emit blob {at_emit[:12]}")
            elif _sha256(ROOT / path) != pinned:
                aged.append(f"{path}: changed since emit {emit[:12]} (snapshot age)")
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError) as error:
        failures.append(f"snapshot unverifiable: {error}")
    for line in aged:
        print(line)
    for line in failures or [f"queue snapshot intact at emit {emit[:12]}"]:
        print(line)
    return 1 if failures else 0


def summary() -> int:
    plan = _read_json(PLAN)
    resolutions, rankings = _load_caches()
    states = Counter(i["disposition"]["state"] for i in plan["entries"])
    print(
        f"universe {len(plan['entries'])} runs: "
        + ", ".join(f"{k} {v}" for k, v in sorted(states.items()))
        + " (capture-ready is not COMPLETE)"
    )
    queued = sum(i["queued"] for i in plan["entries"])
    print(f"queued {queued}; excluded characters {plan['excluded_characters']}")
    for item in plan["entries"]:
        d = item["disposition"]
        if d["state"] == "absent":
            continue
        kinds = Counter(b["disposition"] for b in d["bosses"])
        reuse = [b["boss"] for b in d["bosses"] if b["disposition"] == "offline-reuse"]
        note = f" offline-reuse {', '.join(reuse)}" if reuse else ""
        print(f"  {d['state']:14} {item['entry_id']} {dict(kinds)}{note}")
    entries, unfilled = queue_entries(plan, resolutions, rankings)
    counts = Counter(len(e["candidates"]) for e in entries)
    print(f"resolutions {len(resolutions)}, rankings {len(rankings)}")
    print(
        f"entries ready {len(entries)} (by candidate count {dict(sorted(counts.items()))}); "
        f"unfilled {len(unfilled)}"
    )
    for e in entries:
        if len(e["candidates"]) < MAX_CANDIDATES:
            print(f"  {len(e['candidates'])} candidate(s): {e['entry_id']}")
    if unfilled:
        print(f"unfilled: {', '.join(unfilled)}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="offline: universe, dispositions, candidate pools")
    spend = commands.add_parser("resolve", help="online: faction and metric checks (cached)")
    spend.add_argument("--budget", type=int, required=True, help="most new live calls")
    boards = commands.add_parser("leaderboard", help="online: first pages for exhausted runs")
    boards.add_argument("--budget", type=int, required=True, help="most new page fetches")
    commands.add_parser("emit", help="write the runner queue, or refuse while runs are unfilled")
    pinned = commands.add_parser("verify", help="check pins against committed blobs")
    pinned.add_argument("--rev", default="HEAD")
    pinned.add_argument(
        "--snapshot",
        action="store_true",
        help="check the emitted queue's own pins, not the freshness of its inputs",
    )
    commands.add_parser("summary", help="print dispositions and readiness")
    args = parser.parse_args(argv)
    if args.command == "plan":
        _write_json(PLAN, build_plan())
        return summary()
    if args.command == "resolve":
        return resolve(args.budget)
    if args.command == "leaderboard":
        return leaderboard(args.budget)
    if args.command == "emit":
        return emit()
    if args.command == "verify":
        return verify_snapshot(args.rev) if args.snapshot else verify(args.rev)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
