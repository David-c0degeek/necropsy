"""Independent raw-event survey of fight reuse and possible stream projections.

No API calls, analyzer imports, archive edits or acceptance updates. Each input
is bound to its SHA256 and member manifest. Projection equality is an observation
of these inputs, not a guarantee of the API's general filtering semantics.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any

from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest

ROOT = Path(__file__).resolve().parents[4]


def canonical(event: Any) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def survey(paths: list[Path]) -> dict[str, Any]:
    inputs = []
    union: dict[tuple[str, str, int, int], set[str]] = collections.defaultdict(set)
    counts: collections.Counter[str] = collections.Counter()
    failures = []
    for path in paths:
        path = path.resolve()
        expected = path.with_suffix(".sha256").read_text().split()[0]
        members = load_entries_manifest(path.with_suffix(".entries"))
        with VerifiedArchive(path, expected_sha256=expected, entries=members) as archive:
            marker = archive.read_json("necropsy-snapshot.json")
            subject = marker["subject"]
            config = "/".join(
                str(subject.get(k))
                for k in ("class_id", "ranking_category", "ranking_metric", "faction")
            )
            local: collections.Counter[str] = collections.Counter()
            inputs.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": archive.sha256,
                    "configuration": config,
                    "counts": local,
                }
            )
            sets = marker["report_sets"]
            local["singleton_report_sets"] = sum(len(s["fight_ids"]) == 1 for s in sets)
            local["multi_fight_report_sets"] = len(sets) - local["singleton_report_sets"]
            encounters = {
                (s["report"], s["fight"]): s
                for s in marker["encounter_streams"]
                if s["role"] == "encounter"
            }
            for (code, fight_id), proof in encounters.items():
                identity = proof["identity"]
                key = (identity["site"], code, identity["revision"], fight_id)
                union[key].add(config)
                local["fights"] += 1
                prefix = f"events/{code}/fight_{fight_id}/"

                def events(names: list[str]) -> list[dict[str, Any]]:
                    return [e for name in names for e in archive.read_json(name)["data"]]

                whole_names = [
                    f"{prefix}encounter/all_{n:03d}.json" for n in range(1, len(proof["pages"]) + 1)
                ]
                whole = [(canonical(e), e) for e in events(whole_names)]
                local["whole_fight_pages"] += len(whole_names)
                local["whole_fight_events"] += len(whole)
                critical = next(
                    s
                    for s in marker["encounter_streams"]
                    if (s["report"], s["fight"], s["role"]) == (code, fight_id, "critical")
                )
                critical_names = [
                    f"{prefix}encounter/critical_{n:03d}.json"
                    for n in range(1, len(critical["pages"]) + 1)
                ]
                critical_rows = [canonical(e) for e in events(critical_names)]
                projected_rows = [
                    raw
                    for raw, e in whole
                    if e.get("type") == "damage" and e.get("hitType") in (2, 5, 17)
                ]
                actual = collections.Counter(critical_rows)
                projected = collections.Counter(projected_rows)
                local["critical_projection_order_equal"] += critical_rows == projected_rows
                local["critical_pages"] += len(critical_names)
                local[
                    "critical_projection_equal"
                    if actual == projected
                    else "critical_projection_mismatch"
                ] += 1
                report = archive.read_json(f"reports/{code}/bundle.json")["reportData"]["report"]
                fight = next(f for f in report["fights"] if f["id"] == fight_id)
                for stream in marker["streams"]:
                    if (stream["report"], stream["fight"], stream["direction"]) != (
                        code,
                        fight_id,
                        "source",
                    ):
                        continue
                    actor = stream["actor_id"]
                    owned = {
                        p["id"] for p in fight.get("friendlyPets", []) if p.get("petOwner") == actor
                    }
                    ids = {actor} | owned
                    folders = [
                        name
                        for name in members
                        if name.startswith(f"{prefix}{stream['role']}_{actor}_")
                        and "/source_" in name
                    ]
                    source_rows = [canonical(e) for e in events(sorted(folders))]
                    actual = collections.Counter(source_rows)
                    projected = collections.Counter(
                        raw
                        for raw, e in whole
                        if e.get("sourceID") in ids or e.get("targetID") in ids
                    )
                    equal = actual == projected
                    local["source_projection_equal" if equal else "source_projection_mismatch"] += 1
                    local["source_pages"] += len(folders)
                    # WCL includes report-catalog owned units absent from friendlyPets.
                    catalog_ids = set(ids)
                    while True:
                        previous = len(catalog_ids)
                        catalog_ids.update(
                            a["id"]
                            for a in report["masterData"]["actors"]
                            if a.get("petOwner") in catalog_ids
                        )
                        if len(catalog_ids) == previous:
                            break
                    catalog_rows = [
                        raw
                        for raw, e in whole
                        if e.get("sourceID") in catalog_ids or e.get("targetID") in catalog_ids
                    ]
                    catalog_equal = actual == collections.Counter(catalog_rows)
                    local[
                        "catalog_source_projection_equal"
                        if catalog_equal
                        else "catalog_source_projection_mismatch"
                    ] += 1
                    local["catalog_source_projection_order_equal"] += source_rows == catalog_rows
                    if not equal:
                        failures.append(
                            {
                                "archive": path.name,
                                "report": code,
                                "fight": fight_id,
                                "role": stream["role"],
                                "actor": actor,
                                "source_rows_outside_projection": sum(
                                    (actual - projected).values()
                                ),
                                "projection_rows_not_requested": sum((projected - actual).values()),
                            }
                        )
            counts.update(local)
    return {
        "kind": "Offline raw-event survey; no API call or cell acceptance",
        "inputs": inputs,
        "totals": dict(counts),
        "distinct_fights": len(union),
        "fight_occurrences": counts["fights"],
        "duplicate_fight_occurrences": counts["fights"] - len(union),
        "cross_configuration_fights": sum(len(configs) > 1 for configs in union.values()),
        "source_projection_failures": failures,
        "source_projection_rule": "sourceID or targetID in actor plus listed owned friendlyPets",
        "catalog_source_projection_rule": (
            "sourceID or targetID in actor plus transitively owned report-catalog and fight units"
        ),
        "critical_projection_rule": "type=damage and hitType in [2,5,17]",
        "limits": [
            "Historical captures differ in time and cohort depth; this is not a fresh campaign.",
            "These projections are empirical candidates, not enabled derivation rules.",
            "A participant in a top player's fight is not automatically a top comparison.",
            "Copies of a fight share encounter data but may have different ranking evidence.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--extra-archive", type=Path, action="append", default=[])
    args = parser.parse_args()
    paths = sorted((ROOT / "tests/golden/raids/raw/naxx-production-20261031").glob("*.zip"))
    paths.extend(args.extra_archive)
    result = survey(paths)
    result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "totals",
                    "distinct_fights",
                    "duplicate_fight_occurrences",
                    "cross_configuration_fights",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
