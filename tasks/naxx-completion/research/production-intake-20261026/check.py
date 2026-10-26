"""Replay the partial production archive classification without network access."""

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest
from necropsy.snapshot.v1 import open_snapshot

ROOT = Path(__file__).resolve().parents[4]
OLD = ROOT / "tests/golden/raids/raw/naxx-balance-v2-measurement/77619978-2006-20261023T152230.zip"
NEW = ROOT / "workspace/codex-naxx/production-intake-20261024/77619978-2006-20261024T121203.zip"
PINS = (
    "caa199389d11dab0d3c0678d086a352fb679d3e3cd133e62f2da0ecfef86dcb5",
    "837485a99ae96dfd644d410933f64947a0b4b236f47cd3dbff6cda5e6f293f5b",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    """Keep every verification guard active under python -O/PYTHONOPTIMIZE."""
    if not condition:
        raise AssertionError(message)


def keyed(value, path=""):
    """Normalize playerDetails role arrays by unique actor ID; keep other order."""
    if isinstance(value, dict):
        return {key: keyed(item, path + "/" + key) for key, item in value.items()}
    if isinstance(value, list):
        result = [keyed(item, path + "/[]") for item in value]
        if re.fullmatch(r"/data/playerDetails/(dps|healers|tanks)", path):
            require(
                all(isinstance(item, dict) and isinstance(item.get("id"), int) for item in result),
                "role array has missing or invalid actor IDs",
            )
            ids = [item["id"] for item in result]
            require(len(ids) == len(set(ids)), "ambiguous keyed array")
            return sorted(result, key=lambda item: item["id"])
        return result
    return value


def differences(left, right, path=""):
    if type(left) is not type(right):
        yield path
    elif isinstance(left, dict):
        for key in sorted(left.keys() | right.keys()):
            if key in left and key in right:
                yield from differences(left[key], right[key], path + "/" + key)
            else:
                yield path + "/" + key
    elif isinstance(left, list):
        if len(left) != len(right):
            yield path + "/length"
        else:
            for index, (first, second) in enumerate(zip(left, right, strict=True)):
                yield from differences(first, second, path + "/" + str(index))
    elif left != right:
        yield path


def compare():
    manifests = [load_entries_manifest(path.with_suffix(".entries")) for path in (OLD, NEW)]
    require(set(manifests[0]) == set(manifests[1]), "archive member sets differ")
    changed = []
    summaries = []
    with (
        VerifiedArchive(OLD, expected_sha256=PINS[0], entries=manifests[0]) as old,
        VerifiedArchive(NEW, expected_sha256=PINS[1], entries=manifests[1]) as new,
    ):
        for name in sorted(manifests[0]):
            left, right = old.read_bytes(name), new.read_bytes(name)
            if left == right:
                continue
            first, second = json.loads(left), json.loads(right)
            paths = list(differences(first, second))
            category = ""
            if name == "necropsy-snapshot.json":
                allowed = (
                    r"/bosses/\d+/(subject|cohort/\d+)/bundle_generation/sha256",
                    r"/bosses/\d+/selection/leaderboard_captured_at",
                    r"/report_sets/\d+/(sha256|cache_sha256)",
                )
                require(
                    all(any(re.fullmatch(pattern, path) for pattern in allowed) for path in paths),
                    "unexpected snapshot marker change",
                )
                category = "generation digests and leaderboard timestamps"
            elif name.startswith("leaderboards/"):
                require(
                    all(
                        re.fullmatch(
                            "/pages/\\d+/(captured_at|characterRankings/rankings/.*)", path
                        )
                        for path in paths
                    ),
                    "unexpected leaderboard structure change",
                )
                category = "leaderboard timestamps and refreshed rows; not promoted"
            elif name.startswith("reports/"):
                first = first.get("report", first.get("reportData", {}).get("report"))
                second = second.get("report", second.get("reportData", {}).get("report"))
                require(
                    isinstance(first, dict) and set(first) == set(second),
                    "report wrapper keys differ",
                )
                require(
                    all(
                        keyed(first[key]) == keyed(second[key])
                        for key in first
                        if key != "rankings"
                    ),
                    "report domain data changed beyond actor ordering",
                )
                paths = list(differences(first["rankings"], second["rankings"]))
                category = "actor ordering and refreshed rankings"
            elif name.startswith("user_rankings/"):
                require(
                    all(
                        re.fullmatch(
                            "/encounterRankings/ranks/\\d+/today(Percent|TotalParses)", path
                        )
                        for path in paths
                    ),
                    "unexpected user ranking change",
                )
                category = "current ranking percentiles and parse counts"
            else:
                raise AssertionError(f"unexpected changed domain member: {name}")
            changed.append(
                {
                    "member": name,
                    "prior_sha256": manifests[0][name].sha256,
                    "production_sha256": manifests[1][name].sha256,
                    "classification": category,
                    "changed_path_counts": dict(
                        sorted(
                            collections.Counter(
                                re.sub(r"/\d+(?=/|$)", "/[]", path) for path in paths
                            ).items()
                        )
                    ),
                }
            )
        for archive in (old, new):
            reader = open_snapshot(archive)
            descriptor = reader.descriptor()
            streams = []
            for ref in reader.expected_streams():
                result = reader.read_stream(ref)
                streams.append(
                    {
                        "report": ref.report_code,
                        "fight": ref.fight_id,
                        "role": ref.role.value,
                        "direction": ref.direction.value,
                        "actor": ref.actor_id,
                        "owner": ref.owner_actor_id,
                        "status": result.status.value,
                        "pages": result.pages,
                        "events": len(result.events),
                        "detail": result.detail,
                        "boundary_ambiguities": result.boundary_ambiguities,
                    }
                )
            summaries.append(
                {
                    "fights": len(descriptor.fights),
                    "participants": sum(len(fight.participants) for fight in descriptor.fights),
                    "reader_issues": reader.issues(),
                    "streams": streams,
                }
            )
    require(summaries[0] == summaries[1], "strict scope/actor selection changed")
    return {
        "kind": "Verified partial production intake; no new actor coverage",
        "inputs": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": pin,
                "bytes": path.stat().st_size,
                "entries_sha256": digest(path.with_suffix(".entries")),
            }
            for path, pin in zip((OLD, NEW), PINS, strict=True)
        ],
        "verified_members_per_archive": len(manifests[0]),
        "unchanged_members": len(manifests[0]) - len(changed),
        "changed_members": changed,
        "strict_scope_summary": summaries[1],
        "disposition": (
            "Retain production output; keep registered measurement sources "
            "and all cell statuses unchanged."
        ),
        "limits": [
            "Report ranking refreshes are recorded without re-ranking pinned cells.",
            "Four ownership-limited cohorts and missing primary KelThuzad faction "
            "remain unresolved.",
            "No new raw event member, selected actor or scope completeness improvement.",
            "No configuration completion, content approval, WCL call or Tower mutation.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    receipt = compare()
    if args.out:
        with args.out.open("x", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps(receipt, indent=2) + "\n")
    else:
        require(
            receipt == json.loads(Path(__file__).with_name("receipt.json").read_bytes()),
            "replayed receipt differs from retained receipt",
        )
    print(
        f"PASS: {receipt['verified_members_per_archive']} members per archive; "
        f"{len(receipt['changed_members'])} classified changes; strict scopes unchanged"
    )
