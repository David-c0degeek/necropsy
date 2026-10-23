"""Synthetic draft layout specimens: no acquisition, real player or rule activation."""

import argparse
import dataclasses
import hashlib
import json
import sys
from html import escape
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path.cwd()))

from necropsy import __version__
from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.analysis.encounters import strategy
from necropsy.raids.scope import coverage_cells
from necropsy.report.analysis_json import AnalysisDocument
from necropsy.report.render import build_view, render_playbook, render_report
from necropsy.report.render.playbook_view import with_strategy
from scripts.check_guidance_proposal import check

root = Path.cwd().resolve()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, required=True, help="fresh directory under workspace/")
work = parser.parse_args().out.resolve()
if not work.is_relative_to(root / "workspace"):
    raise SystemExit("preview output must be under workspace/")
work.mkdir(parents=True, exist_ok=False)
bundle = root / "tasks/naxx-completion/research/coordinator-guidance-drafts.json"
verified = check(bundle)
general_path = root / "tasks/naxx-completion/research/naxx-strategy-proposal.yaml"
tank_path = root / "tasks/naxx-completion/research/naxx-category-strategy-proposal.yaml"
general = yaml.safe_load(general_path.read_bytes())
tanks = yaml.safe_load(tank_path.read_bytes())
for encounter, entry in tanks["strategy"].items():
    general["strategy"][encounter]["items"].extend(entry["items"])
real_loader = strategy.load_rules


def draft_rules(game, name):
    return general if name == "zones/naxxramas_guidance" else real_loader(game, name)


warning = (
    "DRAFT LAYOUT PREVIEW. Synthetic missing-data specimen; no player, capture, "
    "observed duty, approved guidance or content acceptance."
)
manifest = {
    "kind": warning,
    "version": __version__,
    "verified_general_proposal": verified,
    "inputs": {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [bundle, general_path, tank_path]
    },
    "specimens": [],
    "recipe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "scope": (
        "Render-only view-model overlay; source proposal/content review "
        "and real capture acceptance remain open."
    ),
}
manifest["render_sources_sha256"] = {
    p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted((root / "src/necropsy/report/render").rglob("*"))
    if p.is_file() and p.suffix in {".py", ".css", ".js", ".j2"}
}
configs = [
    c.configuration for c in coverage_cells() if c.raid == "naxxramas" and c.encounter_id == 51118
]
for config in configs:
    key = f"{config.class_id}-{config.category.lower()}-{config.metric}-{config.faction.lower()}"
    out = work / key
    out.mkdir()
    doc = {
        "schema_id": "necropsy.analysis",
        "schema_version": 1,
        "necropsy_version": __version__,
        "mode": "historical",
        "options": {"cross_faction": False},
        "snapshot": {
            "archive_sha256": "0" * 64,
            "scope": "subset",
            "format": "synthetic-draft-layout-preview",
            "source_fight_count": 0,
            "selected_fights": 0,
            "database_schema_version": 1,
        },
        "subject": {
            "id": 0,
            "name": f"DRAFT PREVIEW {config.category} {config.metric}",
            "server": "Synthetic",
            "region": "Preview",
            "class_id": config.class_id,
        },
        "zone": {"id": 2006, "name": "Naxxramas", "partition": 1},
        "cohort": {"kind": "synthetic-draft-layout", "top_n": 0, "limitations": [warning]},
        "coverage": {
            "streams": 0,
            "streams_not_complete": 0,
            "event_anomalies": 0,
            "snapshot_issues": 1,
        },
        "acquisition": {
            "selected_category": config.category,
            "subject_faction": config.faction,
            "bosses": [],
        },
        "bosses": [],
    }
    # A changed proposal must not inherit review marks from an older draft.
    doc["acquisition"]["preview_source_sha256"] = manifest["inputs"]
    selections = {}
    for encounter, entry in general["strategy"].items():
        with patch.object(strategy, "load_rules", draft_rules):
            selected = strategy.encounter_strategy(
                "naxxramas", encounter, 1, config.class_id, config.metric, category=config.category
            )
        assert selected is not None
        selections[encounter] = dataclasses.asdict(selected)
        selections[encounter]["limitation"] = warning + " " + selections[encounter]["limitation"]
        doc["acquisition"]["bosses"].append(
            {"boss": entry["boss"], "attempted": False, "coverage": {"reasons": [warning]}}
        )
        doc["bosses"].append(
            {
                "encounter_id": encounter,
                "boss": entry["boss"],
                "rules": {
                    "ranking_exclusions": [],
                    "native_targets": None,
                    "ranking_exclusion_rule": {
                        "rule": "synthetic-preview-unvalidated",
                        "basis": "unvalidated",
                        "validation": None,
                    },
                },
                "subject": None,
                "cohort": [],
                "overall_cohort": [],
                "recommendations": [],
                "benchmarks": {
                    "baseline": None if config.class_id == 3 else {"note": warning, "entries": 0},
                    "ceiling": None,
                    "raid_speed": None,
                    "cross_faction": None,
                    "excluded": {"other_faction": 0, "unknown_faction": 0},
                },
                "encounter": {
                    "target_integrity": None,
                    "raid_utility": None,
                    "cohort_target_integrity": [],
                },
                "playbook": None
                if config.class_id == 3
                else {
                    "selected_category": config.category,
                    "selected_metric": config.metric,
                    "selected_faction": config.faction,
                    "limitations": [warning],
                },
            }
        )
    # A schema-valid missing-data document produces the ordinary view. Draft text
    # enters only a copied view model, never the analysis or production rule data.
    AnalysisDocument.model_validate(doc)
    raw = json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    (out / "synthetic-analysis.json").write_bytes(raw)
    view = build_view(doc, hashlib.sha256(raw).hexdigest())
    if config.class_id == 3:
        view = dataclasses.replace(
            view,
            bosses=tuple(
                dataclasses.replace(
                    b,
                    reference=with_strategy(
                        dict(b.reference), {"encounter_strategy": selections[b.encounter_id]}
                    ),
                )
                for b in view.bosses
            ),
        )
    else:
        view = dataclasses.replace(
            view,
            class_views={
                eid: with_strategy(dict(v), {"encounter_strategy": selections[eid]})
                for eid, v in view.class_views.items()
            },
        )
    for name, render in [("report", render_report), ("playbook", render_playbook)]:
        html = render(view)
        assert "DRAFT PREVIEW" in html and warning in html
        (out / f"{name}.html").write_text(html, encoding="utf-8", newline="\n")
    manifest["specimens"].append(
        {
            "key": key,
            "configuration": dataclasses.asdict(config),
            "selected_strategy": selections,
            "analysis_sha256": hashlib.sha256(raw).hexdigest(),
            "pages": {
                name: hashlib.sha256((out / f"{name}.html").read_bytes()).hexdigest()
                for name in ["report", "playbook"]
            },
        }
    )
(work / "manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
)
rows = []
for specimen in manifest["specimens"]:
    config = specimen["configuration"]
    label = escape(
        f"{CLASS_NAMES[config['class_id']]} / {config['category']} / "
        f"{config['metric']} / {config['faction']}"
    )
    key = specimen["key"]
    rows.append(
        f'<tr><th scope="row">{label}</th>'
        f'<td><a href="{key}/report.html">Report</a></td>'
        f'<td><a href="{key}/playbook.html">Playbook</a></td></tr>'
    )
(work / "index.html").write_text(
    '<!doctype html><html lang="en"><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    "<title>Draft guidance layout previews</title><style>"
    "body{font:16px system-ui;margin:2rem;max-width:70rem}"
    "table{border-collapse:collapse}th,td{padding:.7rem;border-bottom:1px solid #aaa;"
    "text-align:left}a{margin-right:1rem}</style><h1>Draft guidance layout previews</h1>"
    "<p>Synthetic missing-data specimens for all 34 legal configurations and 15 bosses. "
    "No player assessment, capture validation, approved content or product acceptance.</p>"
    "<p>Draft advice is overlaid onto copied view models. Production rules are unchanged. "
    "The manifest binds source proposals, recipe, renderer and generated files.</p><table>"
    "<thead><tr><th>Configuration</th><th>Report</th><th>Playbook</th></tr></thead><tbody>"
    + "".join(rows)
    + "</tbody></table></html>\n",
    encoding="utf-8",
    newline="\n",
)
print(
    json.dumps(
        {"configurations": len(configs), "pages": 2 * len(configs), "production_rule_changes": 0}
    )
)
