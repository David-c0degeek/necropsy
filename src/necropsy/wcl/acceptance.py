"""Checks and a receipt for a manual live acceptance run of `necropsy analyze`.

Everything here works on files a run already wrote (no credentials, no network):
the snapshot set, analysis.json, the pages and the shareable package. The
comparison with a historical analysis is explicit: without a matching historical
document it is reported as not performed, never as empty historical samples.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

from necropsy.analysis.context import realm_key
from necropsy.report.analysis_json import AnalysisDocument
from necropsy.report.package import ANALYSIS_FILE, PLAYBOOK_FILE, REPORT_FILE, package_name
from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest
from necropsy.snapshot.v1 import V1Snapshot
from necropsy.wcl.context import SUPPORTED_ZONE_ID

CREDENTIAL_FIELDS = frozenset(
    {"access_token", "refresh_token", "client_secret", "authorization", "secret", "password"}
)
EXPECTED_DIFFERENCES = (
    "Live comparisons use acquired same-faction fights; the historical export holds the "
    "recorded overall top five, so cohort players are expected to differ.",
    "Rankings move over time; the subject's best fight and the leaderboard can change "
    "between the historical export and the live run.",
)


class AcceptanceFailure(AssertionError):
    """A written run does not meet the acceptance checks."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def credential_fields(value: Any, path: str = "") -> list[str]:
    """JSON paths whose key names a credential field (structure check, no secret values)."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            where = f"{path}.{key}" if path else str(key)
            if str(key).casefold() in CREDENTIAL_FIELDS:
                found.append(where)
            found += credential_fields(item, where)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            found += credential_fields(item, f"{path}[{i}]")
    return found


def check_package(path: Path) -> list[str]:
    """Every packaged member must match the package's own checksum manifest."""
    problems: list[str] = []
    with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as archive:
        all_names = archive.namelist()
        names = set(all_names)
        if len(names) != len(all_names):
            return ["the package holds a member name twice"]
        if "manifest.json" not in names:
            return ["the package has no manifest.json"]
        try:
            manifest = json.loads(archive.read("manifest.json"))
        except ValueError:
            return ["the package manifest is not valid JSON"]
        files = manifest.get("files") if isinstance(manifest, dict) else None
        if not isinstance(files, list):
            return ["the package manifest has no file list"]
        listed: dict[str, dict[str, Any]] = {}
        for f in files:
            if (
                not isinstance(f, dict)
                or not isinstance(f.get("path"), str)
                or not isinstance(f.get("sha256"), str)
                or not isinstance(f.get("bytes"), int)
                or isinstance(f.get("bytes"), bool)
            ):
                return ["the package manifest has a malformed file record"]
            if f["path"] in listed:
                return [f"the package manifest lists {f['path']} twice"]
            listed[f["path"]] = f
        for name in sorted(names - {"manifest.json"}):
            entry = listed.get(name)
            data = archive.read(name)
            if entry is None:
                problems.append(f"{name} is not in the package manifest")
            elif entry.get("sha256") != hashlib.sha256(data).hexdigest() or entry.get(
                "bytes"
            ) != len(data):
                problems.append(f"{name} differs from the package manifest")
        for name in sorted(set(listed) - names):
            problems.append(f"{name} is listed but missing from the package")
    return problems


def check_run(
    out: Path,
    snapshot: Path,
    entries: Path,
    sha256: str,
    *,
    requested: tuple[int, ...] | None = None,
    sha256_file: Path | None = None,
    package: bool = True,
) -> dict[str, Any]:
    """Verify what a run wrote; raises AcceptanceFailure on the first broken guarantee.

    The analysis must come from exactly this snapshot (archive digest), list exactly
    the snapshot's requested bosses (and `requested`, when given), and the package
    must hold exactly the current analysis and pages.
    """
    if sha256_file is not None:
        expected = f"{sha256}  {snapshot.name}"
        if sha256_file.read_text(encoding="utf-8").strip() != expected:
            raise AcceptanceFailure(f"{sha256_file.name} does not name {snapshot.name}'s digest")
    with VerifiedArchive(
        snapshot, expected_sha256=sha256, entries=load_entries_manifest(entries)
    ) as archive:
        reader = V1Snapshot(archive)
        snapshot_bosses = [
            b.get("encounter_id")
            for b in (reader.descriptor().acquisition or {}).get("bosses") or []
        ]
    document = json.loads((out / ANALYSIS_FILE).read_text(encoding="utf-8"))
    AnalysisDocument.model_validate(document)
    if document.get("mode") != "live":
        raise AcceptanceFailure("analysis.json is not a live analysis")
    if document["snapshot"]["archive_sha256"] != sha256:
        raise AcceptanceFailure("analysis.json was not built from this snapshot")
    acquisition = document.get("acquisition") or {}
    bosses = [b.get("encounter_id") for b in acquisition.get("bosses") or []]
    if not bosses or len(set(bosses)) != len(bosses):
        raise AcceptanceFailure("analysis.json does not list each requested boss once")
    if bosses != snapshot_bosses or (requested is not None and sorted(bosses) != sorted(requested)):
        raise AcceptanceFailure("analysis.json does not cover exactly the requested bosses")
    for page in (REPORT_FILE, PLAYBOOK_FILE):
        if not (out / page).is_file() or (out / page).stat().st_size == 0:
            raise AcceptanceFailure(f"{page} is missing or empty")
    package_sha = None
    if package:
        pkg = out / package_name(document)
        if not pkg.is_file():
            raise AcceptanceFailure(f"{pkg.name} is missing")
        problems = check_package(pkg)
        with zipfile.ZipFile(pkg) as archive:
            for name in (ANALYSIS_FILE, REPORT_FILE, PLAYBOOK_FILE):
                if (
                    name not in archive.namelist()
                    or archive.read(name) != (out / name).read_bytes()
                ):
                    problems.append(f"the package's {name} is not the current {name}")
            manifest = (
                json.loads(archive.read("manifest.json"))
                if "manifest.json" in archive.namelist()
                else {}
            )
        if manifest.get("analysis_sha256") != _sha256(out / ANALYSIS_FILE):
            problems.append("the package manifest names another analysis")
        if problems:
            raise AcceptanceFailure("; ".join(problems))
        package_sha = _sha256(pkg)
    leaked = credential_fields(document)
    if leaked:
        raise AcceptanceFailure(f"analysis.json has credential fields: {leaked}")
    return {"document": document, "package_sha256": package_sha}


SCAN_LIMIT = (
    "Pattern-based scan of the written output; finding nothing does not prove that no "
    "secret is present."
)


def secret_scan(out: Path) -> dict[str, str]:
    """`gitleaks dir <out> --redact`: passed, findings, unavailable or failed (never guessed).

    gitleaks exits 0 when it finds nothing and 1 when it finds something; any other
    outcome is a failed scan, not a clean one. Its output is not kept.
    """
    tool = shutil.which("gitleaks")
    if tool is None:
        return {"status": "unavailable", "note": "gitleaks not found on PATH", "limit": SCAN_LIMIT}
    try:
        run = subprocess.run(  # noqa: S603 - fixed tool path from PATH, list argv, no shell
            [tool, "dir", str(out), "--redact", "--no-banner", "--exit-code", "1"],
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "failed", "note": type(error).__name__, "limit": SCAN_LIMIT}
    status = {0: "passed", 1: "findings"}.get(run.returncode, "failed")
    note = "" if status != "failed" else f"gitleaks exit code {run.returncode}"
    return {"status": status, "note": note, "limit": SCAN_LIMIT}


def load_history(path: Path, character_id: int | None, partition: int | None) -> dict[str, Any]:
    """A historical analysis to compare with, validated before any live request is made."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        AnalysisDocument.model_validate(document)
    except (OSError, ValueError) as error:
        raise AcceptanceFailure(f"the historical analysis {path} is not usable: {error}") from None
    if document.get("mode") != "historical":
        raise AcceptanceFailure(f"{path} is not a historical analysis")
    if character_id is not None and document["subject"]["id"] != character_id:
        raise AcceptanceFailure(f"{path} is another character's analysis")
    if document["zone"]["id"] != SUPPORTED_ZONE_ID:
        raise AcceptanceFailure(f"{path} is not a Naxxramas analysis")
    if partition is not None and document["zone"]["partition"] != partition:
        raise AcceptanceFailure(f"{path} is for another partition")
    return dict(document)


def history_matches_context(history: dict[str, Any], context: Any) -> None:
    """The baseline must be the resolved character, zone and partition (before acquisition)."""
    partition = context.partition.id if context.partition is not None else None
    if history["subject"]["id"] != context.character_id.value:
        raise AcceptanceFailure("the historical analysis is another character's")
    if history["zone"]["id"] != context.zone_id or history["zone"]["partition"] != partition:
        raise AcceptanceFailure("the historical analysis is for another zone or partition")


def _historical(
    history: dict[str, Any] | None, live: dict[str, Any]
) -> tuple[dict[str, Any] | None, str]:
    if history is None:
        return None, "historical comparison not performed: no historical analysis given"
    AnalysisDocument.model_validate(history)
    if history.get("mode") != "historical":
        return None, "historical comparison not performed: the given analysis is not historical"
    same = (
        history["subject"]["id"] == live["subject"]["id"]
        and history["zone"]["id"] == live["zone"]["id"]
        and history["zone"]["partition"] == live["zone"]["partition"]
    )
    if not same:
        return None, "historical comparison not performed: another character, zone or partition"
    return history, "compared with the given historical analysis"


def _faction(entry: dict[str, Any] | None) -> Any:
    faction = ((entry or {}).get("environment") or {}).get("faction") or {}
    return faction.get("value")


def _identity(entry: dict[str, Any]) -> str:
    """`player-realm`, realm normalised the way the analysis matches realms."""
    return f"{entry.get('player')}-{realm_key(entry.get('server')) or '?'}"


def _players(section: dict[str, Any] | None, faction: Any) -> list[str] | None:
    """The section's cohort players of `faction`; None when there is no faction basis.

    Rows whose own faction is unknown are left out (they are not proven same-faction).
    """
    if faction is None:
        return None
    if section is None:
        return []
    return [_identity(e) for e in section.get("cohort") or [] if _faction(e) == faction]


def compare_with_history(live: dict[str, Any], history: dict[str, Any] | None) -> dict[str, Any]:
    """Per requested boss: live coverage and, when a matching history exists, differences."""
    base, status = _historical(history, live)
    # The comparison faction is the live subject's recorded faction; without it no
    # cohort can be called same-faction and overlaps stay unknown.
    basis = (live.get("acquisition") or {}).get("subject_faction")
    live_bosses = {b["encounter_id"]: b for b in live.get("bosses") or []}
    past = {b["encounter_id"]: b for b in (base or {}).get("bosses") or []}
    rows = []
    for record in (live.get("acquisition") or {}).get("bosses") or []:
        encounter = record.get("encounter_id")
        section = live_bosses.get(encounter)
        subject = record.get("subject") or {}
        row: dict[str, Any] = {
            "encounter_id": encounter,
            "boss": record.get("boss"),
            "attempted": record.get("attempted", True),
            "coverage": record.get("coverage"),
            "live_subject_fight": None
            if not subject
            else {"report": subject.get("report"), "fight": subject.get("fight")},
            "live_deep_players": _players(section, basis),
            "unknown_pets": [
                e.get("player")
                for e in [
                    record.get("subject"),
                    *(record.get("cohort") or []),
                    record.get("cross_faction"),
                ]
                if e and e.get("status") == "complete" and e.get("pets") is None
            ],
            "overall_first_acquired": bool(
                section and (section.get("benchmarks") or {}).get("overall_top")
            ),
        }
        if base is None:
            row["historical"] = "unknown (not compared)"
        elif encounter not in past:
            row["historical"] = "unavailable (boss not in the historical analysis)"
        else:
            old = past[encounter]
            old_subject = old.get("subject") or {}
            live_players = _players(section, basis)
            old_players = _players(old, basis)
            live_fight = row["live_subject_fight"]
            old_fight = (old_subject.get("report_code"), old_subject.get("fight_id"))
            same: bool | None
            if live_fight is None or live_fight.get("report") is None or None in old_fight:
                same = None  # unknown, not false
            else:
                same = old_fight == (live_fight["report"], live_fight["fight"])
            row["historical"] = {
                "subject_fight": {"report": old_fight[0], "fight": old_fight[1]},
                "same_subject_fight": same,
                **(
                    {"cohort_overlap": "unknown (no recorded subject faction)"}
                    if live_players is None or old_players is None
                    else {
                        "cohort_players": sorted(set(old_players)),
                        "both": sorted(set(live_players) & set(old_players)),
                        "only_live": sorted(set(live_players) - set(old_players)),
                        "only_historical": sorted(set(old_players) - set(live_players)),
                    }
                ),
            }
        rows.append(row)
    return {
        "historical_comparison": status,
        "expected_differences": list(EXPECTED_DIFFERENCES),
        "bosses": rows,
    }


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    """Publish the receipt without ever replacing an existing one."""
    from necropsy.wcl.cache import CacheConflict, canonical_bytes, publish

    leaked = credential_fields(receipt)
    if leaked:
        raise AcceptanceFailure(f"the receipt would hold credential fields: {leaked}")
    if os.path.lexists(path):
        raise AcceptanceFailure(f"{path} already exists; receipts are never replaced")
    try:
        published = publish(path, canonical_bytes(receipt))
    except CacheConflict:
        published = "conflict"
    if published != "published":
        raise AcceptanceFailure(f"{path} already exists; receipts are never replaced")


__all__ = [
    "EXPECTED_DIFFERENCES",
    "AcceptanceFailure",
    "check_package",
    "check_run",
    "compare_with_history",
    "credential_fields",
    "history_matches_context",
    "load_history",
    "secret_scan",
    "write_receipt",
]
