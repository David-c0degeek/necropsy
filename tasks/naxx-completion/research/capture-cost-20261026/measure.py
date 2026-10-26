"""Measure which captured event pages a fight's encounter-All stream already holds.

Offline only: reads the registered measurement archive, the retained production
copy and the measurement run's request journal. Check mode (the default)
compares a fresh measurement with the committed receipt; ``--out FRESH`` writes
a new receipt and refuses to overwrite. No WCL call, analyzer or freezer import.

Every rule here describes an exact match for the observed rows of this one
corpus. It is not a statement of the API's general selection semantics.
"""

import argparse
import collections
import hashlib
import json
import statistics
import sys
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path

from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.raids.scope import configurations

ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = (
    ROOT / "tests/golden/raids/raw/naxx-balance-v2-measurement/77619978-2006-20261023T152230.zip"
)
ARCHIVE_SHA256 = "caa199389d11dab0d3c0678d086a352fb679d3e3cd133e62f2da0ecfef86dcb5"
PRODUCTION = (
    ROOT / "workspace/codex-naxx/production-intake-20261024/77619978-2006-20261024T121203.zip"
)
PRODUCTION_SHA256 = "837485a99ae96dfd644d410933f64947a0b4b236f47cd3dbff6cda5e6f293f5b"
JOURNAL = ROOT / "workspace/capture-cost-20261026/measurement-requests.tar.gz"
JOURNAL_SHA256 = "1beff26a118fb5d80fd86405c59f6bb423f49c5b314d1a9ccfc4c640689a9b5c"
QUEUE = ROOT / "tasks/naxx-completion/capture-queue.json"
QUEUE_PIN = ROOT / "tasks/naxx-completion/capture-queue.sha256"
RECEIPT = Path(__file__).with_name("receipt.json")
CRITICAL_HIT_TYPES = (2, 5, 17)
FACTIONS = {1: "Alliance", 0: "Horde"}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(event):
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def multiset(events):
    return collections.Counter(key(e) for e in events)


def subset(counter, predicate):
    return collections.Counter({k: n for k, n in counter.items() if predicate(json.loads(k))})


class Archive:
    def __init__(self, z):
        self.z = z
        self.names = z.namelist()
        self.marker = json.loads(z.read("necropsy-snapshot.json"))

    def pages(self, prefix, direction):
        names = sorted(
            n
            for n in self.names
            if n.startswith(prefix) and n.rsplit("/", 1)[-1].startswith(direction + "_")
        )
        require(names, f"no {direction} pages under {prefix}")
        return names

    def events(self, names):
        return [e for n in names for e in json.loads(self.z.read(n))["data"]]

    def report(self, code):
        return json.loads(self.z.read(f"reports/{code}/bundle.json"))["reportData"]["report"]


def streams(archive):
    """Per-kind page/event counts and how each actor/critical stream relates to All."""
    pages = collections.Counter()
    events = collections.Counter()
    target = collections.Counter()
    source = collections.Counter()
    source_residuals = []
    critical = collections.Counter()
    hit_types = collections.Counter()
    fights = {}
    for stream in archive.marker["streams"]:
        code, fight_id, actor = stream["report"], stream["fight"], stream["actor_id"]
        if (code, fight_id) not in fights:
            folder = f"events/{code}/fight_{fight_id}/encounter/"
            all_pages = archive.pages(folder, "all")
            fights[(code, fight_id)] = (all_pages, multiset(archive.events(all_pages)))
            critical_pages = archive.pages(folder, "critical")
            pages["encounter-all"] += len(all_pages)
            pages["critical"] += len(critical_pages)
            whole = fights[(code, fight_id)][1]
            events["encounter-all"] += sum(whole.values())
            observed = multiset(archive.events(critical_pages))
            events["critical"] += sum(observed.values())
            for k in whole:
                e = json.loads(k)
                if e.get("type") == "damage":
                    hit_types[(e.get("hitType"), observed[k] > 0)] += 1
            derived = subset(
                whole,
                lambda e: e.get("type") == "damage" and e.get("hitType") in CRITICAL_HIT_TYPES,
            )
            critical["equal" if derived == observed else "differs"] += 1
            critical["contained" if not observed - whole else "not contained"] += 1
        _, whole = fights[(code, fight_id)]
        folder = f"events/{code}/fight_{fight_id}/{stream['role']}_{actor}_"
        names = archive.pages(folder, stream["direction"])
        kind = f"{stream['role']}-{stream['direction']}"
        pages[kind] += len(names)
        observed = multiset(archive.events(names))
        events[kind] += sum(observed.values())
        if stream["direction"] == "target":
            target["equals All" if observed == whole else "differs from All"] += 1
            continue
        fight = next(f for f in archive.report(code)["fights"] if f["id"] == fight_id)
        listed = {p["id"] for p in fight["friendlyPets"] if p.get("petOwner") == actor}
        sources = {actor} | listed
        derived = subset(
            whole, lambda e, s=sources: e.get("sourceID") in s or e.get("targetID") in s
        )
        source["contained in All" if not observed - whole else "not contained"] += 1
        if derived == observed:
            source["equals rule"] += 1
            continue
        source["differs from rule"] += 1
        missing = observed - derived
        source_residuals.append(
            {
                "report": code,
                "fight": fight_id,
                "actor": actor,
                "role": stream["role"],
                "listed_owned_units": sorted(listed),
                "observed_rows_outside_rule": sum(missing.values()),
                "rule_rows_not_observed": sum((derived - observed).values()),
                "residual_target_ids": dict(
                    sorted(collections.Counter(json.loads(k)["targetID"] for k in missing).items())
                ),
                "residual_source_ids": dict(
                    sorted(collections.Counter(json.loads(k)["sourceID"] for k in missing).items())
                ),
            }
        )
    return {
        "fights": len(fights),
        "report_sets": len(archive.marker["report_sets"]),
        "stream_report_codes": len({s["report"] for s in archive.marker["streams"]}),
        "actor_streams": len(archive.marker["streams"]),
        "pages_by_kind": dict(sorted(pages.items())),
        "events_by_kind": dict(sorted(events.items())),
        "target_streams": dict(target),
        "source_streams": dict(source),
        "source_rule": ("sourceID or targetID in {actor} plus the fight's listed owned units"),
        "source_residuals": source_residuals,
        "critical_streams": dict(critical),
        "critical_rule": f"type == damage and hitType in {list(CRITICAL_HIT_TYPES)}",
        "damage_rows_by_hit_type_and_critical_membership": [
            {"hitType": h, "in_critical": c, "rows": n} for (h, c), n in sorted(hit_types.items())
        ],
    }, fights


def journal(fights):
    """Request kinds as actually sent, server response identity and noisy point readings."""
    require(sha256(JOURNAL) == JOURNAL_SHA256, "journal archive changed")
    records = []
    with tarfile.open(JOURNAL) as tar:
        for member in tar.getmembers():
            if member.isfile() and member.name.endswith(".json"):
                handle = tar.extractfile(member)
                require(handle is not None, member.name)
                records.append(json.loads(handle.read()))
    records.sort(key=lambda r: r["captured_at"])

    def kind(record):
        query = record["identity"]["query"]
        operation = query.split("query ", 1)[1].split("(", 1)[0].strip()
        if operation != "NecropsyEvents":
            return operation
        v = record["identity"]["variables"]
        if v.get("filterExpression"):
            return "events-critical"
        if v.get("sourceID") is not None:
            return "events-actor-source"
        if v.get("targetID") is not None:
            return "events-actor-target"
        return "events-encounter-all"

    by_kind = collections.Counter(kind(r) for r in records)
    # Group event responses by fight and page start, so a target response can be
    # compared with the encounter-All response for the same page window.
    responses = collections.defaultdict(dict)
    for r in records:
        k = kind(r)
        if not k.startswith("events-"):
            continue
        v = r["identity"]["variables"]
        page = r["data"]["reportData"]["report"]["events"]
        window = (v["code"], tuple(v["fightIDs"]), v["startTime"], v["endTime"])
        responses[window].setdefault(k, []).append(key(page["data"]))
    target = collections.Counter()
    for kinds in responses.values():
        for body in kinds.get("events-actor-target", ()):
            target[
                "same data as All for that window"
                if body in kinds.get("events-encounter-all", ())
                else "differs or no All page"
            ] += 1
    deltas = collections.defaultdict(list)
    previous = None
    resets = 0
    for r in records:
        rate = r["data"].get("rateLimitData")
        if not rate:
            continue
        when = datetime.fromisoformat(r["captured_at"])
        if previous is not None:
            p_when, p_rate = previous
            elapsed = (when - p_when).total_seconds()
            same_window = rate["pointsSpentThisHour"] >= p_rate["pointsSpentThisHour"] and (
                elapsed < p_rate["pointsResetIn"]
            )
            if same_window:
                deltas[kind(r)].append(rate["pointsSpentThisHour"] - p_rate["pointsSpentThisHour"])
            else:
                resets += 1
        previous = (when, rate)
    points = {
        k: {
            "requests_with_delta": len(v),
            "sum": round(sum(v), 2),
            "median": round(statistics.median(v), 2),
            "max": round(max(v), 2),
            "positive": sum(1 for d in v if d > 0),
        }
        for k, v in sorted(deltas.items())
    }
    reports = [r for r in records if kind(r) == "NecropsyReport"]
    variables = collections.Counter(
        json.dumps(r["identity"]["variables"], sort_keys=True) for r in reports
    )
    identities = collections.Counter(json.dumps(r["identity"], sort_keys=True) for r in reports)
    scopes_by_variables = collections.defaultdict(list)
    for r in reports:
        scopes_by_variables[json.dumps(r["identity"]["variables"], sort_keys=True)].append(
            r["identity"]["scope"]
        )
    report_queries = {
        "requests": len(reports),
        "by_scope": dict(
            sorted(collections.Counter(r["identity"]["scope"] for r in reports).items())
        ),
        "distinct_reports": len({r["identity"]["variables"]["code"] for r in reports}),
        "distinct_variable_sets": len(variables),
        "distinct_full_identities": len(identities),
        "exact_identity_repeats": sum(n - 1 for n in identities.values()),
        "repeated_variable_sets_by_scopes": dict(
            sorted(
                collections.Counter(
                    "+".join(sorted(v)) for v in scopes_by_variables.values() if len(v) > 1
                ).items()
            )
        ),
        "note": (
            "Variables repeated across acquisition and finalization are independent answers by "
            "design (finalization re-reads the report); they are not reusable duplicates."
        ),
        "requests_by_fight_count": dict(
            sorted(
                collections.Counter(
                    len(r["identity"]["variables"].get("fightIDs") or []) for r in reports
                ).items()
            )
        ),
    }
    return {
        "records": len(records),
        "report_queries": report_queries,
        "requests_by_kind": dict(sorted(by_kind.items())),
        "actor_target_requests_sent_targetID": by_kind["events-actor-target"],
        "actor_target_responses": dict(target),
        "account_point_deltas_by_kind": points,
        "window_breaks_or_resets": resets,
        "points_note": (
            "Account-wide hourly readings between consecutive journal records; other spend, "
            "retries, cache reuse and the separate database allowance are not visible here. "
            "These are not per-request invoices."
        ),
    }


def sharing(archive):
    """Configurations other than the captured one with a published row in a captured fight."""
    legal = {(CLASS_NAMES[c.class_id], c.category, c.metric, c.faction) for c in configurations()}
    per_fight = []
    for code, fight_id in sorted({(s["report"], s["fight"]) for s in archive.marker["streams"]}):
        report = archive.report(code)
        details = {
            (p["name"], p["server"]): p
            for role in report["playerDetails"]["data"]["playerDetails"].values()
            for p in role
        }
        present = set()
        unknown_faction = 0
        for block in report["rankings"]["data"]:
            if block["fightID"] != fight_id:
                continue
            for role, metric in (("dps", "dps"), ("tanks", "dps"), ("healers", "hps")):
                for row in block["roles"][role]["characters"]:
                    detail = details.get((row["name"], row["server"]["name"]))
                    info = (detail or {}).get("combatantInfo") or {}
                    faction = FACTIONS.get(info.get("factionID"))
                    if faction is None:
                        unknown_faction += 1
                        continue
                    config = (row["class"], row["spec"], metric, faction)
                    if config in legal:
                        present.add(config)
        per_fight.append(
            {
                "report": code,
                "fight": fight_id,
                "configurations": len(present),
                "unknown_faction_rows": unknown_faction,
            }
        )
    counts = [f["configurations"] for f in per_fight]
    return {
        "legal_configurations": len(legal),
        "fights": len(per_fight),
        "configurations_with_a_published_row_per_fight": {
            "min": min(counts),
            "median": statistics.median(counts),
            "max": max(counts),
        },
        "note": (
            "A published row in a captured fight is potential reuse only: cohort selection, "
            "ownership, faction and stream completeness for that actor are not established here."
        ),
    }


def queue_overlap():
    """Character overlap across the pinned queue's entries; fights are chosen at capture."""
    require(sha256(QUEUE) == QUEUE_PIN.read_text().split()[0], "queue pin mismatch")
    queue = json.loads(QUEUE.read_bytes())
    entries = collections.defaultdict(set)
    for entry in queue["entries"]:
        for candidate in entry["candidate_evidence"]:
            entries[candidate["character_id"]].add(entry["entry_id"])
    shared = {c: sorted(e) for c, e in entries.items() if len(e) > 1}
    return {
        "queue": {"path": QUEUE.relative_to(ROOT).as_posix(), "sha256": sha256(QUEUE)},
        "entries": len(queue["entries"]),
        "candidates": sum(len(e["candidate_evidence"]) for e in queue["entries"]),
        "distinct_characters": len(entries),
        "characters_in_more_than_one_entry": len(shared),
        "shared": shared,
        "unmeasured": (
            "Report/fight overlap across entries: the queue pins characters, and the fights "
            "are selected from leaderboards at capture time, so future acquisition overlap "
            "cannot be measured from the queue."
        ),
    }


def production_copy(archive):
    require(sha256(PRODUCTION) == PRODUCTION_SHA256, "production copy changed")
    with zipfile.ZipFile(PRODUCTION) as z:
        names = [n for n in archive.names if n.startswith("events/")]
        same = sum(z.read(n) == archive.z.read(n) for n in names)
    return {
        "event_members": len(names),
        "byte_identical": same,
        "note": "A second serialization of the same acquired events, not an independent sample.",
    }


def measure():
    require(sha256(ARCHIVE) == ARCHIVE_SHA256, "measurement archive changed")
    with zipfile.ZipFile(ARCHIVE) as z:
        archive = Archive(z)
        stream_result, fights = streams(archive)
        result = {
            "kind": "Offline capture-cost measurement; no WCL call, capture or engine change",
            "inputs": {
                "archive": {"path": ARCHIVE.relative_to(ROOT).as_posix(), "sha256": ARCHIVE_SHA256},
                "production_copy": {
                    "path": PRODUCTION.relative_to(ROOT).as_posix(),
                    "sha256": PRODUCTION_SHA256,
                },
                "journal": {"path": JOURNAL.relative_to(ROOT).as_posix(), "sha256": JOURNAL_SHA256},
            },
            "streams": stream_result,
            "journal": journal(fights),
            "queue_overlap": queue_overlap(),
            "captured_fight_survey": sharing(archive),
            "production_copy": production_copy(archive),
        }
    pages = result["streams"]["pages_by_kind"]
    total = sum(pages.values())
    target_pages = pages.get("player-target", 0) + pages.get("pet-target", 0)
    source_pages = pages.get("player-source", 0) + pages.get("pet-source", 0)
    result["page_shares"] = {
        "event_pages": total,
        "actor_target_pages_identical_to_All": target_pages,
        "actor_source_pages": source_pages,
        "critical_pages": pages.get("critical", 0),
        "note": (
            "Page shares of this one corpus; points depend on hidden per-request costs and "
            "the separate database allowance."
        ),
    }
    result["limits"] = [
        (
            f"One archive: one configuration, {result['streams']['fights']} fights, "
            f"{result['streams']['report_sets']} report sets."
        ),
        "Rules are exact matches for these observed rows, never certified API semantics.",
        "No acquisition, snapshot, reader or engine change follows without a separate plan.",
    ]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = measure()
    result["measure_sha256"] = sha256(Path(__file__))
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    else:
        require(
            RECEIPT.read_bytes() == text.encode("utf-8"), "receipt differs from a fresh measurement"
        )
    sys.stdout.reconfigure(encoding="utf-8")
    print("WROTE" if args.out else "PASS")


if __name__ == "__main__":
    main()
