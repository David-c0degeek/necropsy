"""Projections against recorded API responses, plus a complete old-to-v4 validation fixture.

Inputs are unchanged, hash-pinned captures. A converted temporary archive is a
constructed validation fixture, never a new capture or accepted content source.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest
from necropsy.snapshot.v1 import open_snapshot
from necropsy.wcl.cache import canonical_bytes
from necropsy.wcl.derive import (
    CRITICAL_RULE,
    SOURCE_RULE,
    TARGET_RULE,
    DerivationUnsupported,
    project_pages,
    source_actor_ids,
)
from scripts.raw_projection import verify_projection

pytestmark = pytest.mark.golden
ROOT = Path(__file__).parents[2]
INPUTS = json.loads((ROOT / "tests/golden/raids/projection-corpus.json").read_bytes())["inputs"]


def page_names(names: list[str], proof: dict[str, Any]) -> list[str]:
    prefix = f"events/{proof['report']}/fight_{proof['fight']}/"
    if proof["role"] in {"encounter", "critical"}:
        kind = "all" if proof["role"] == "encounter" else "critical"
        return sorted(n for n in names if n.startswith(prefix + f"encounter/{kind}_"))
    return sorted(
        n
        for n in names
        if n.startswith(prefix + f"{proof['role']}_{proof['actor_id']}_")
        and "/" + proof["direction"] + "_" in n
    )


@pytest.mark.parametrize("spec", INPUTS, ids=lambda s: s["configuration"])
def test_versioned_projection_matches_recorded_api_order_and_multiplicity(
    spec: dict[str, Any],
) -> None:
    path = ROOT / spec["path"]
    with VerifiedArchive(
        path,
        expected_sha256=spec["sha256"],
        entries=load_entries_manifest(path.with_suffix(".entries")),
    ) as z:
        marker = z.read_json("necropsy-snapshot.json")
        names = z.names()
        counts = {"source": 0, "critical": 0}
        for parent in marker["encounter_streams"]:
            if parent["role"] != "encounter":
                continue
            code, fid = parent["report"], parent["fight"]
            pages = [z.read_json(n) for n in page_names(names, parent)]
            report = z.read_json(f"reports/{code}/fight_{fid}.json")["report"]
            proofs = [
                p
                for p in (*marker["streams"], *marker["encounter_streams"])
                if (p["report"], p["fight"]) == (code, fid)
                and (p["role"] == "critical" or p["direction"] == "source")
            ]
            for proof in proofs:
                role = "critical" if proof["role"] == "critical" else "source"
                try:
                    ids = (
                        None
                        if role == "critical"
                        else source_actor_ids(report, fid, proof["actor_id"])
                    )
                    projected = project_pages(
                        pages, CRITICAL_RULE if role == "critical" else SOURCE_RULE, actor_ids=ids
                    )
                except DerivationUnsupported:
                    assert (
                        proof["identity"] is not None
                    )  # unsupported inputs retain requested evidence
                    continue
                original = [e for n in page_names(names, proof) for e in z.read_json(n)["data"]]
                assert [e for p in projected for e in p["data"]] == original
                counts[role] += 1
        assert counts["source"] > 0 and counts["critical"] > 0


@pytest.mark.parametrize(
    "spec",
    [i for i in INPUTS if "65603754-" in i["path"] or "naxx-production" not in i["path"]],
    ids=lambda s: s["configuration"],
)
def test_full_v4_archive_round_trip_matches_original_requested_streams(
    tmp_path: Path, spec: dict[str, Any]
) -> None:
    path = ROOT / spec["path"]
    with VerifiedArchive(
        path,
        expected_sha256=spec["sha256"],
        entries=load_entries_manifest(path.with_suffix(".entries")),
    ) as old:
        before = open_snapshot(old)
        marker = old.read_json("necropsy-snapshot.json")
        members = {n: old.read_bytes(n) for n in old.names()}
        names = list(members)
        changed = 0
        for proof in (*marker["streams"], *marker["encounter_streams"]):
            target = proof["direction"] == "target" and marker["zone"]["id"] != 2006
            if not (proof["role"] == "critical" or proof["direction"] == "source" or target):
                continue
            code, fid = proof["report"], proof["fight"]
            parent = next(
                p
                for p in marker["encounter_streams"]
                if (p["report"], p["fight"], p["role"]) == (code, fid, "encounter")
            )
            report = old.read_json(f"reports/{code}/fight_{fid}.json")["report"]
            critical = proof["role"] == "critical"
            try:
                ids = (
                    None if critical or target else source_actor_ids(report, fid, proof["actor_id"])
                )
                if not critical and not target:
                    # Match native acquisition's conservative completeness guard.
                    actors = {a["id"]: a for a in report["masterData"]["actors"]}
                    owners = {a["id"]: a.get("petOwner") for a in actors.values()}
                    owners.update(
                        {
                            p["id"]: p["petOwner"]
                            for p in report["fights"][0]["friendlyPets"]
                            if p.get("petOwner")
                        }
                    )
                    root = proof["actor_id"]
                    while owners[root] is not None:
                        root = owners[root]
                    entries = [
                        e
                        for b in marker["bosses"]
                        for e in [
                            b.get("subject"),
                            *(b.get("cohort") or []),
                            b.get("cross_faction"),
                        ]
                        if e and (e["report"], e["fight"]) == (code, fid)
                    ]
                    if not any(
                        e["player"] == actors[root]["name"] and isinstance(e.get("pets"), list)
                        for e in entries
                    ):
                        continue
                projected = project_pages(
                    [old.read_json(n) for n in page_names(names, parent)],
                    CRITICAL_RULE if critical else TARGET_RULE if target else SOURCE_RULE,
                    actor_ids=ids,
                )
            except DerivationUnsupported:
                continue
            old_names = page_names(names, proof)
            assert [e for p in projected for e in p["data"]] == [
                e for n in old_names for e in old.read_json(n)["data"]
            ]
            folder = old_names[0].rsplit("/", 1)[0]
            for n in old_names:
                del members[n]
            bodies = [canonical_bytes(p) for p in projected]
            if target:
                bodies = [old.read_bytes(n) for n in page_names(names, parent)]
            prefix = "critical" if critical else "target" if target else "source"
            for i, body in enumerate(bodies, 1):
                members[f"{folder}/{prefix}_{i:03d}.json"] = body
            proof.update(
                identity=None,
                meta={},
                pages=[hashlib.sha256(b).hexdigest() for b in bodies],
                derivation={
                    "rule": CRITICAL_RULE if critical else TARGET_RULE if target else SOURCE_RULE,
                    "parent": parent["identity"],
                    "parent_pages": parent["pages"],
                    **({"actor_ids": list(ids)} if ids is not None else {}),
                },
            )
            changed += 1
        assert changed > 30
        marker["formatVersion"] = 4
        members["necropsy-snapshot.json"] = canonical_bytes(marker)
        converted = tmp_path / "constructed-v4.zip"
        with zipfile.ZipFile(converted, "w", compression=zipfile.ZIP_STORED) as out:
            for name, body in members.items():
                out.writestr(name, body)
        with VerifiedArchive(converted) as new:
            after = open_snapshot(new)
            assert after.descriptor().format == "necropsy-live-snapshot-v4"
            for ref in before.expected_streams():
                a, b = before.read_stream(ref), after.read_stream(ref)
                assert a.status == b.status and a.events == b.events
                assert a.boundary_ambiguities == b.boundary_ambiguities
            reports = {r["code"]: r for r in after.reports()}
            for proof in (*marker["streams"], *marker["encounter_streams"]):
                if proof.get("derivation", {}).get("rule") in {
                    SOURCE_RULE,
                    CRITICAL_RULE,
                    TARGET_RULE,
                }:
                    verify_projection(new, marker, proof, reports[proof["report"]])
