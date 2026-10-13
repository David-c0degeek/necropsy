"""Build the offline output set: report, playbook and the export package.

Everything comes from the analysis.json bytes alone and is deterministic: the
same bytes give the same pages and the same ZIP, byte for byte (sorted members,
fixed timestamps and permissions, fixed compression).

The package holds derived analysis of real players' logs. It is not anonymised;
share it only where the underlying logs may be shared.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from necropsy.report.publish import publish
from necropsy.report.render import build_view, load_document, render_playbook, render_report
from necropsy.report.render.view import resolve

ANALYSIS_FILE = "analysis.json"
REPORT_FILE = "report.html"
PLAYBOOK_FILE = "playbook.html"
MANIFEST_SCHEMA = "necropsy.package"
MANIFEST_VERSION = 1
_EPOCH = (1980, 1, 1, 0, 0, 0)
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def package_name(document: Mapping[str, Any]) -> str:
    """Derived from numeric IDs only, never from player or boss names."""
    return f"necropsy-{int(document['subject']['id'])}-{int(document['zone']['id'])}.zip"


def _cell(value: Any) -> Any:
    # Spreadsheet programs run cells starting like a formula; log text is untrusted.
    if isinstance(value, str) and value.startswith(_FORMULA_START):
        return "'" + value
    return value


def _csv(header: Sequence[str], rows: Iterable[Sequence[Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([_cell("" if v is None else v) for v in row])
    return buffer.getvalue().encode("utf-8")


def _value(ev: Any) -> Any:
    return ev.get("value") if isinstance(ev, dict) else None


def tables(document: Mapping[str, Any]) -> dict[str, bytes]:
    recs, cohort, shares, execution = [], [], [], []
    for boss in document["bosses"]:
        name = boss["boss"]
        eid = boss["encounter_id"]
        for r in boss["recommendations"]:
            recs.append(
                [
                    eid,
                    name,
                    r["rule"],
                    r["severity"],
                    r["confidence"],
                    r["controllability"],
                    r["finding"],
                    r["recommendation"],
                ]
            )
        for e in boss["cohort"]:
            cohort.append(
                [
                    eid,
                    name,
                    e["player"],
                    e["leaderboard_position"],
                    _value(e["environment"]["faction"]),
                    e["kill_duration_s"],
                    e["ranking"].get("ranked_dps"),
                    _value(e["environment"]["talents"]),
                ]
            )
        raw = boss["encounter"].get("ranked_target_shares")
        for s in (raw or {}).get("counted", []):
            shares.append(
                [
                    eid,
                    name,
                    s.get("name"),
                    s["kind"],
                    s.get("game_id"),
                    _value(s["median_share_pct"]),
                    s["n_known"],
                    s["n_unknown"],
                    _value(s["subject_share_pct"]),
                ]
            )
        subject = boss.get("subject")
        baseline = boss["benchmarks"].get("baseline")
        if subject is not None:
            for shot in ("auto", "aimed", "multi"):
                med = (baseline or {}).get("medians", {}).get(f"{shot}_per_min")
                execution.append(
                    [
                        eid,
                        name,
                        f"{shot}_shot",
                        _value(subject["hunter"]["shots"][f"{shot}_shot"]["per_minute"]),
                        None if med is None else _value(med["value"]),
                        None if med is None else med["n_known"],
                    ]
                )
    return {
        "tables/recommendations.csv": _csv(
            [
                "encounter_id",
                "boss",
                "rule",
                "severity",
                "confidence",
                "controllability",
                "finding",
                "recommendation",
            ],
            recs,
        ),
        "tables/cohort.csv": _csv(
            [
                "encounter_id",
                "boss",
                "player",
                "leaderboard_position",
                "faction",
                "kill_s",
                "ranked_dps",
                "talents",
            ],
            cohort,
        ),
        "tables/target_shares.csv": _csv(
            [
                "encounter_id",
                "boss",
                "target",
                "kind",
                "game_id",
                "median_share_pct",
                "n_known",
                "n_unknown",
                "your_share_pct",
            ],
            shares,
        ),
        "tables/execution.csv": _csv(
            ["encounter_id", "boss", "shot", "per_minute", "same_faction_median", "n_known"],
            execution,
        ),
    }


def evidence_files(document: Mapping[str, Any]) -> dict[str, bytes]:
    """Per boss: each recommendation with the evidence its paths resolve to."""
    out = {}
    for boss in document["bosses"]:
        items = [
            {
                "rule": r["rule"],
                "finding": r["finding"],
                "evidence": {p: resolve(boss, p) for p in r["evidence"]},
            }
            for r in boss["recommendations"]
        ]
        body = {
            "encounter_id": boss["encounter_id"],
            "boss": boss["boss"],
            "recommendations": items,
        }
        text = json.dumps(body, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        out[f"evidence/{int(boss['encounter_id'])}.json"] = text.encode("utf-8")
    return out


def _zip(members: Mapping[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 3
            zf.writestr(info, members[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def build_outputs(analysis: bytes, *, include_package: bool = True) -> dict[str, bytes | None]:
    """Every output file for one analysis, by file name; None marks a stale package to remove."""
    document, sha = load_document(analysis)
    view = build_view(document, sha)
    report = render_report(view).encode("utf-8")
    playbook = render_playbook(view).encode("utf-8")
    outputs: dict[str, bytes | None] = {
        ANALYSIS_FILE: analysis,
        REPORT_FILE: report,
        PLAYBOOK_FILE: playbook,
    }
    name = package_name(document)
    if not include_package:
        outputs[name] = None
        return outputs
    members: dict[str, bytes] = {
        ANALYSIS_FILE: analysis,
        REPORT_FILE: report,
        PLAYBOOK_FILE: playbook,
        **tables(document),
        **evidence_files(document),
    }
    manifest = {
        "schema_id": MANIFEST_SCHEMA,
        "schema_version": MANIFEST_VERSION,
        "necropsy_version": document["necropsy_version"],
        "analysis_schema_version": document["schema_version"],
        "analysis_sha256": sha,
        "archive_sha256": document["snapshot"]["archive_sha256"],
        "subject": {"id": document["subject"]["id"], "name": document["subject"]["name"]},
        "zone": document["zone"],
        "options": document["options"],
        "notice": "Derived analysis of real players' logs. Not anonymised.",
        "files": [
            {"path": p, "bytes": len(members[p]), "sha256": hashlib.sha256(members[p]).hexdigest()}
            for p in sorted(members)
        ],
    }
    members["manifest.json"] = (
        json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    outputs[name] = _zip(members)
    return outputs


def write_outputs(analysis: bytes, out_dir: Path, *, include_package: bool = True) -> list[Path]:
    """Render everything from analysis.json bytes and publish it into `out_dir` together."""
    outputs = build_outputs(analysis, include_package=include_package)
    publish(out_dir, outputs)
    return [out_dir / name for name, data in sorted(outputs.items()) if data is not None]


__all__ = [
    "ANALYSIS_FILE",
    "PLAYBOOK_FILE",
    "REPORT_FILE",
    "build_outputs",
    "evidence_files",
    "package_name",
    "tables",
    "write_outputs",
]
