"""Offline diagnosis of the pet evidence behind comparison refusals (step 1 only).

For every same-faction comparison of every boss in one pinned capture, record its
current admission result from the committed register, then the pet facts that
decide DPS admission:

- unresolved pets: friendly pets of the selected fight without a resolvable
  owner. For each, activity inside the fight's certified encounter-All scope, as
  three separate counts (damage as source, any event as source, any event as
  source or target), plus candidate ownership evidence (summon events naming it,
  owner fields on any catalog generation). Counts are reported only when the
  archive opens strictly and that fight's encounter-All stream reads complete;
  otherwise the scope is unknown and nothing is counted.
- catalog-only pets: pets the report catalog assigns to the actor that the
  selected fight does not list, with the same activity counts.

Labels are diagnostic: candidate-resolvable, no-source-observations-in-certified-
scope, unresolved, scope-unknown. Nothing here admits a row, edits an archive,
writes pets.json or calls WCL. Run on Tower from the repository root:

  uv run python <this script> ARCHIVE --out FILE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest  # noqa: E402
from necropsy.snapshot.model import ActorRole  # noqa: E402
from necropsy.snapshot.v1 import open_snapshot  # noqa: E402

REGISTER = ROOT / "tasks/naxx-completion/followup-comparisons.json"


def _int(value: Any) -> int | None:
    return value if type(value) is int else None


def activity(events: list[dict[str, Any]] | None, pet: int) -> dict[str, Any]:
    if events is None:
        return {"scope": "unknown"}
    source = [e for e in events if _int(e.get("sourceID")) == pet]
    either = [e for e in events if pet in (_int(e.get("sourceID")), _int(e.get("targetID")))]
    summons = Counter(
        _int(e.get("sourceID"))
        for e in events
        if e.get("type") == "summon" and _int(e.get("targetID")) == pet
    )
    return {
        "scope": "certified",
        "damage_as_source": sum(1 for e in source if e.get("type") == "damage"),
        "any_as_source": len(source),
        "any_as_source_or_target": len(either),
        "summoned_by": {str(k): v for k, v in sorted(summons.items(), key=str)},
    }


def label(act: dict[str, Any], owners: set[int]) -> str:
    if act["scope"] != "certified":
        return "scope-unknown"
    if act["summoned_by"] or owners:
        return "candidate-resolvable"
    if act["any_as_source"] == 0:
        return "no-source-observations-in-certified-scope"
    return "unresolved"


def diagnose(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    entries_path = path.with_suffix(".entries")
    entries = load_entries_manifest(entries_path) if entries_path.is_file() else None
    register = json.loads(REGISTER.read_bytes())
    status: dict[tuple[str, int, str, str], tuple[str, str | None]] = {}
    for cell in register["cells"]:
        for kind in ("admitted", "refused", "unverified"):
            for r in cell[kind]:
                status[(r["report"], r["fight"], r["player"], r["realm"])] = (kind, r.get("reason"))
    rows: list[dict[str, Any]] = []
    with VerifiedArchive(path, entries=entries) as archive:
        reader = open_snapshot(archive)
        issues = [str(i) for i in reader.issues()]
        marker = archive.read_json("necropsy-snapshot.json")
        subject = marker["subject"]
        encounter_events: dict[tuple[str, int], list[dict[str, Any]] | None] = {}
        for ref in reader.expected_streams():
            if ref.role is ActorRole.ENCOUNTER:
                read = reader.read_stream(ref)
                complete = not issues and read.status.value == "complete"
                encounter_events[(ref.report_code, ref.fight_id)] = (
                    list(read.events) if complete else None
                )
        cohort = {
            (int(b["encounter_id"]), c["report"], c["fight"], c["player"]): c
            for b in marker["bosses"]
            for c in b.get("cohort") or ()
            if c.get("kind") == "cohort"
        }
        bundles: dict[str, dict[str, Any]] = {}
        for fight in marker["fights"]:
            code, fid = fight["reportID"], fight["fightID"]
            if code not in bundles:
                bundles[code] = archive.read_json(f"reports/{code}/bundle.json")["reportData"][
                    "report"
                ]
            report = bundles[code]
            actors = report["masterData"]["actors"]
            fmeta = next((f for f in report["fights"] if _int(f.get("id")) == fid), None)
            events = encounter_events.get((code, fid))
            for p in fight["participants"]:
                if p["kind"] == "you":
                    continue
                key = (int(p["encounterID"]), code, fid, p["player"])
                entry = cohort.get(key)
                row: dict[str, Any] = {
                    "encounter_id": key[0],
                    "boss": p.get("boss"),
                    "report": code,
                    "fight": fid,
                    "player": p["player"],
                    "realm": p["server"],
                    "register": dict(
                        zip(
                            ("result", "reason"),
                            status.get((code, fid, p["player"], p["server"]), ("absent", None)),
                            strict=True,
                        )
                    ),
                }
                if entry is None:
                    row["skipped"] = "not a same-faction cohort entry"
                    rows.append(row)
                    continue
                row["cohort"] = {
                    "pets": entry.get("pets"),
                    "confirmed_pets": entry.get("confirmed_pets"),
                    "pets_reason": entry.get("pets_reason"),
                }
                matches = [
                    a["id"]
                    for a in actors
                    if a.get("type") == "Player"
                    and (a.get("name"), a.get("server")) == (p["player"], p["server"])
                ]
                if len(matches) != 1 or fmeta is None:
                    row["skipped"] = (
                        "no unique report actor"
                        if len(matches) != 1
                        else "fight missing from report"
                    )
                    rows.append(row)
                    continue
                actor = matches[0]
                row["actor"] = actor
                row["encounter_scope"] = "certified" if events is not None else "unknown"
                fight_pets = {_int(fp.get("id")): fp for fp in fmeta.get("friendlyPets") or ()}
                catalog = {_int(a.get("id")): a for a in actors if a.get("type") == "Pet"}
                unresolved = []
                for pid, fp in sorted(fight_pets.items(), key=lambda kv: (kv[0] is None, kv[0])):
                    if pid is None:
                        continue
                    owner = _int(fp.get("petOwner"))
                    if owner is None:
                        owner = _int((catalog.get(pid) or {}).get("petOwner"))
                    if owner is not None:
                        continue
                    act = activity(events, pid)
                    owners = {
                        o
                        for o in (
                            _int(fp.get("petOwner")),
                            _int((catalog.get(pid) or {}).get("petOwner")),
                        )
                        if o is not None
                    }
                    unresolved.append(
                        {
                            "pet": pid,
                            "gameID": (catalog.get(pid) or {}).get("gameID"),
                            "name": (catalog.get(pid) or {}).get("name"),
                            "activity": act,
                            "catalog_owner_fields": sorted(owners),
                            "label": label(act, owners),
                        }
                    )
                row["unresolved_fight_pets"] = unresolved
                fight_owned = {
                    pid
                    for pid, fp in fight_pets.items()
                    if pid is not None and _int(fp.get("petOwner")) == actor
                }
                catalog_owned = {
                    pid
                    for pid, a in catalog.items()
                    if pid is not None and _int(a.get("petOwner")) == actor
                }
                row["fight_owned_pets"] = sorted(fight_owned)
                row["catalog_owned_pets"] = sorted(catalog_owned)
                row["catalog_only_pets"] = [
                    {
                        "pet": pid,
                        "name": catalog[pid].get("name"),
                        "in_fight_listing": pid in fight_pets,
                        "activity": activity(events, pid),
                    }
                    for pid in sorted(catalog_owned - fight_owned)
                ]
                rows.append(row)
    counts: Counter[str] = Counter()
    for r in rows:
        if "skipped" in r:
            counts[f"skipped: {r['skipped']}"] += 1
            continue
        counts[f"register {r['register']['result']}"] += 1
        for u in r["unresolved_fight_pets"]:
            counts[f"unresolved pet label {u['label']}"] += 1
        if r["catalog_only_pets"]:
            counts["rows with catalog-only pets"] += 1
    return {
        "kind": "Pet-evidence diagnosis for comparison admission; diagnostic only, no admission",
        "archive": {
            "path": path.as_posix(),
            "sha256": digest,
            "entries_sha256": hashlib.sha256(entries_path.read_bytes()).hexdigest()
            if entries
            else None,
        },
        "register_sha256": hashlib.sha256(REGISTER.read_bytes()).hexdigest(),
        "producer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "subject": {
            k: subject.get(k) for k in ("name", "server", "faction", "class_id", "ranking_category")
        },
        "strict_reader_issues": issues,
        "comparisons": len(rows),
        "counts": dict(sorted(counts.items())),
        "rows": rows,
        "limits": [
            "Labels are diagnostic and admit nothing; every row keeps its current register result.",
            "Activity counts exist only inside a strictly opened archive's complete "
            "encounter-All scope.",
            "Summon events and owner fields are candidate evidence, not resolved ownership.",
            "Published-amount residuals with or without a pet are not computed here.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = diagnose(args.archive)
    args.out.write_text(
        json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(result["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
