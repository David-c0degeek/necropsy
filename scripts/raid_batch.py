"""Write and verify layer-based raid completion batches (D036).

Usage: uv run python scripts/raid_batch.py write SPEC
       uv run python scripts/raid_batch.py digests CELL_ID [--rev REV]

A cell is COMPLETE when four layers are green, and a batch manifest
(tests/golden/raids/batches/<batch>.json) records them for many cells at once:

1. Engines: one digest per raid over every package file except the zone
   files, plus the raid's zone rules without the cell-scoped parts below. A
   change to any of them makes every cell of that raid stale until a new batch
   re-attests it.
2. Capture: one committed render_parity receipt per capture, rendered at
   `commit`, with source and installed pages identical, a clean wheel payload,
   every text of each cell's boss present and a recorded sampled picture.
3. Content: one digest per cell over that boss's strategy items for the cell's
   class and metric, the boss's encounter facts and the cell's ranking metric
   policy. A content edit makes only the affected boss and configuration stale.
4. Register: coverage.json references the manifest (path, bytes, cell), never
   the shared files themselves.

Every artifact is pinned by its SHA-256 (receipts, ranking oracles, archives,
entries); independent fact cases are pinned by a digest of the case alone, so a
new case in the same register is not a change. The verifier lives in
scripts/check_raid_coverage.py and recomputes all of it from the checkout.

A spec (JSON) names what the batch claims; everything else is derived:

    {"batch": "mc-healers-1",
     "captures": {ID: {"receipt": "workspace/.../receipt.json",
                       "visual_sample": {"picture": NAME, "by": WHO, "result": TEXT}}},
     "cells": {CELL_ID: {"coverage_note": TEXT, "matrix_note": TEXT}}}

`write` refuses a dirty package, a receipt that is not at HEAD or whose
engine or content digests differ from HEAD's, a cell whose registered actor
source is not that capture's, and a cell without its fact cases or ranking
oracle. It copies each receipt to tests/golden/raids/receipts/, writes the
manifest and sets the cells COMPLETE in coverage.json and the matrix. Review of
the batch (content diffs, receipt summaries, the register diff) stays a human
and navigator step; this script only makes the claim mechanical and checkable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # run as a script: make the sibling tools importable
    sys.path.insert(0, str(ROOT))

from scripts.close_unit import MATRIX, matrix_row, matrix_rows  # noqa: E402

PACKAGE = "src/necropsy"
ZONES = f"{PACKAGE}/rules/classic_era/zones"
BATCHES = "tests/golden/raids/batches"
RECEIPTS = "tests/golden/raids/receipts"
COVERAGE = "tests/golden/raids/coverage.json"
FACTS = "tests/golden/raids/facts.json"
HEALING_FACTS = "tests/golden/raids/healing-facts.json"
CLEAN_VISUAL = re.compile(r"^\d+ screens, 0 with findings$")

Reader = Callable[[str], bytes]


def _git(root: Path, *args: str, stdin: str | None = None) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, input=stdin, capture_output=True, text=True, check=True
    ).stdout


def canonical(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Tree:
    """Package blobs and file bytes of one revision, or of the working tree."""

    def __init__(self, root: Path, rev: str | None = None) -> None:
        self.root, self.rev = root, rev
        self._blobs: dict[str, str] | None = None

    def read(self, path: str) -> bytes:
        if self.rev is None:
            return (self.root / path).read_bytes()
        return subprocess.run(
            ["git", "show", f"{self.rev}:{path}"], cwd=self.root, capture_output=True, check=True
        ).stdout

    def blobs(self) -> dict[str, str]:
        """Git blob ids of package files: clean-filtered, so line endings never differ."""
        if self._blobs is None:
            if self.rev is not None:
                rows = _git(self.root, "ls-tree", "-r", self.rev, "--", PACKAGE).splitlines()
                self._blobs = {r.split("\t", 1)[1]: r.split()[2] for r in rows}
            else:
                paths = _git(
                    self.root,
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "--",
                    PACKAGE,
                ).splitlines()
                paths = sorted(p for p in set(paths) if (self.root / p).is_file())
                ids = _git(self.root, "hash-object", "--stdin-paths", stdin="\n".join(paths))
                self._blobs = dict(zip(paths, ids.split(), strict=True))
        return self._blobs

    def yaml(self, path: str) -> dict[str, Any]:
        data = yaml.safe_load(self.read(path).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path} is not a mapping")
        return data


def engine_digest(tree: Tree, raid: str) -> str:
    """Everything that renders a raid except the cell-scoped content layer."""
    package = {p: b for p, b in tree.blobs().items() if not p.startswith(f"{ZONES}/")}
    zone = tree.yaml(f"{ZONES}/{raid}.yaml")
    zone.pop("ranking_metric_policies", None)
    guidance = tree.yaml(f"{ZONES}/{raid}_guidance.yaml")
    guidance.pop("strategy", None)
    facts = tree.yaml(f"{ZONES}/{raid}_facts.yaml")
    facts.pop("encounters", None)
    return canonical({"package": package, "zone": zone, "guidance": guidance, "facts": facts})


def cell_scope(cell_id: str) -> tuple[str, int, int, str, str, str]:
    raid, encounter, class_id, category, metric, faction = cell_id.split("/")
    return raid, int(encounter), int(class_id), category, metric, faction


def ranking_policy(tree: Tree, cell_id: str) -> dict[str, Any] | None:
    raid, encounter, class_id, category, metric, faction = cell_scope(cell_id)
    want = {
        "encounter_id": encounter,
        "class_id": class_id,
        "category": category,
        "metric": metric,
        "faction": faction,
    }
    zone = tree.yaml(f"{ZONES}/{raid}.yaml")
    hits = [p for p in zone.get("ranking_metric_policies") or () if p.get("scope") == want]
    if len(hits) > 1:
        raise ValueError(f"{cell_id}: {len(hits)} ranking metric policies")
    return hits[0] if hits else None


def content_digest(tree: Tree, cell_id: str) -> str:
    """The boss, class and metric content one review covers, as data."""
    raid, encounter, class_id, _, metric, _ = cell_scope(cell_id)
    strategy = (tree.yaml(f"{ZONES}/{raid}_guidance.yaml").get("strategy") or {}).get(encounter)
    if strategy is not None:
        strategy = dict(strategy)
        strategy["items"] = [
            row
            for row in strategy.get("items") or ()
            if class_id in row.get("classes", (class_id,))
            and metric in row.get("metrics", (metric,))
        ]
    facts = [
        e for e in tree.yaml(f"{ZONES}/{raid}_facts.yaml")["encounters"] if e["id"] == encounter
    ]
    return canonical(
        {"strategy": strategy, "facts": facts, "policy": ranking_policy(tree, cell_id)}
    )


def fact_cases(root: Path, source: dict[str, Any], metric: str) -> list[dict[str, Any]]:
    """The independent actor (and, for HPS, recipient) cases of one actor source."""

    def same(case: dict[str, Any]) -> bool:
        return bool(
            case.get("report") == source["report"]
            and case.get("fight") == source["fight"]
            and case.get("actor") == source["actor"]
            and case.get("sha256") == source["archive"]["sha256"]
        )

    actor = [c for c in json.loads((root / FACTS).read_text(encoding="utf-8"))["cases"] if same(c)]
    if len(actor) != 1:
        raise ValueError(f"{len(actor)} actor fact cases for the actor source")
    cases = [{"path": FACTS, "locator": actor[0]["id"], "digest": canonical(actor[0])}]
    if metric == "hps":
        healing = [
            c
            for c in json.loads((root / HEALING_FACTS).read_text(encoding="utf-8"))["cases"]
            if same(c) and c.get("actor_case") == actor[0]["id"]
        ]
        if len(healing) != 1:
            raise ValueError(f"{len(healing)} recipient fact cases for the actor source")
        cases.append(
            {"path": HEALING_FACTS, "locator": healing[0]["id"], "digest": canonical(healing[0])}
        )
    return cases


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def receipt_problems(
    receipt: dict[str, Any], commit: str, cell_id: str, archive: dict[str, Any]
) -> list[str]:
    """What one receipt must show for one cell; paths are compared portably."""
    _, encounter, class_id, category, metric, faction = cell_scope(cell_id)
    problems = []
    if receipt.get("commit") != commit:
        problems.append("receipt was rendered at another commit")
    rec_archive = receipt.get("archive") or {}
    if (
        str(rec_archive.get("path", "")).replace("\\", "/") != archive["path"]
        or rec_archive.get("sha256") != archive["sha256"]
    ):
        problems.append("receipt renders another archive")
    unit = receipt.get("unit") or {}
    if (unit.get("class_id"), unit.get("category"), unit.get("metric"), unit.get("faction")) != (
        class_id,
        category,
        metric,
        faction,
    ):
        problems.append("receipt subject differs from cell")
    payload = (receipt.get("wheel") or {}).get("payload") or {}
    if (
        receipt.get("source_equals_installed") is not True
        or not payload.get("files")
        or any(payload.get(k) for k in ("mismatched", "not_in_git", "missing_from_wheel"))
    ):
        problems.append("receipt source and installed renders are not identical")
    boss = ((receipt.get("content") or {}).get("bosses") or {}).get(str(encounter))
    if (
        not boss
        or boss.get("outcome") != "checked"
        or boss.get("sections_missing")
        or any(
            missing
            for kind in ("strategy", "facts", "class_notes", "removals")
            for missing in ((boss.get(kind) or {}).get("missing") or {}).values()
        )
        or receipt.get("content_source_missing") != 0
    ):
        problems.append("receipt does not show every text of the cell's boss")
    visual = receipt.get("visual") or {}
    if set(visual) != {"report.html", "playbook.html"} or any(
        v.get("exit") != 0 or not CLEAN_VISUAL.match(str(v.get("summary", "")))
        for v in visual.values()
    ):
        problems.append("receipt visual checks are missing or have findings")
    return problems


def manifest_problems(
    root: Path,
    manifest: dict[str, Any],
    cell_id: str,
    source: dict[str, Any],
    tree: Tree | None = None,
) -> list[str]:
    """Every layer of one cell in one batch, recomputed from the checkout."""
    tree = tree or Tree(root)
    cell = (manifest.get("cells") or {}).get(cell_id)
    if cell is None:
        return ["batch manifest does not list the cell"]
    artifacts: dict[str, str] = manifest.get("artifacts") or {}
    problems = []
    for path, digest in sorted(artifacts.items()):
        file = root / path
        if not file.is_file() or sha256_bytes(file.read_bytes()) != digest:
            problems.append(f"missing or changed batch artifact: {path}")
    capture = (manifest.get("captures") or {}).get(cell.get("capture"))
    if capture is None:
        return [*problems, "batch cell names an unknown capture"]
    archive = {"path": source["archive"]["path"], "sha256": source["archive"]["sha256"]}
    if (
        capture.get("archive") != archive
        or capture.get("entries")
        != {
            "path": source["entries"]["path"],
            "sha256": source["entries"]["sha256"],
        }
        or (cell.get("report"), cell.get("fight"), cell.get("actor"))
        != (source["report"], source["fight"], source["actor"])
    ):
        problems.append("batch identity differs from the registered actor source")
    for key in ("archive", "entries", "receipt"):
        ref = capture.get(key) or {}
        if artifacts.get(str(ref.get("path"))) != ref.get("sha256"):
            problems.append(f"batch capture {key} is not a pinned artifact")
    if not capture.get("visual_sample", {}).get("picture"):
        problems.append("batch capture has no sampled picture")
    try:
        receipt = json.loads((root / capture["receipt"]["path"]).read_text(encoding="utf-8"))
        problems.extend(receipt_problems(receipt, manifest["commit"], cell_id, archive))
    except (OSError, KeyError, ValueError) as exc:
        problems.append(f"unreadable batch receipt: {exc}")
    raid, *_, metric, _ = cell_scope(cell_id)
    if (manifest.get("engine") or {}).get(raid) != engine_digest(tree, raid):
        problems.append("stale engine verification: re-attest the batch")
    if cell.get("content") != content_digest(tree, cell_id):
        problems.append("stale content verification: review this boss and configuration again")
    try:
        if cell.get("facts") != fact_cases(root, source, metric):
            problems.append("independent fact cases differ from the batch")
    except ValueError as exc:
        problems.append(f"independent facts: {exc}")
    policy = ranking_policy(tree, cell_id)
    ranking = cell.get("ranking")
    if policy is not None:
        if not ranking or ranking.get("path") != policy["evidence"]:
            problems.append("batch ranking oracle is not the cell policy's evidence")
        elif artifacts.get(ranking["path"]) != ranking.get("sha256"):
            problems.append("batch ranking oracle is not a pinned artifact")
        else:
            oracle = json.loads((root / ranking["path"]).read_text(encoding="utf-8"))
            if oracle.get("rule") != policy["rule"]:
                problems.append("batch ranking oracle belongs to another policy")
    elif ranking is not None:
        problems.append("batch ranking oracle without a cell-scoped policy")
    return problems


def _pin(root: Path, path: str) -> dict[str, str]:
    return {"path": path, "sha256": sha256_bytes((root / path).read_bytes())}


def write(spec: dict[str, Any], root: Path = ROOT) -> int:
    """Derive, check and write one batch; nothing changes unless every cell passes."""
    name = spec["batch"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise ValueError(f"batch name {name!r} must be lowercase words and hyphens")
    head = _git(root, "rev-parse", "HEAD").strip()
    if _git(root, "status", "--porcelain", "--", PACKAGE).strip():
        raise ValueError(f"{PACKAGE} differs from HEAD; commit before writing a batch")
    here = Tree(root)
    coverage = json.loads((root / COVERAGE).read_text(encoding="utf-8"))
    records = {r["cell_id"]: r for r in coverage["records"]}
    artifacts: dict[str, str] = {}
    captures: dict[str, Any] = {}
    receipts: dict[str, tuple[Path, dict[str, Any]]] = {}
    for capture_id, capture in spec["captures"].items():
        receipt_file = Path(capture["receipt"])
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        receipts[capture_id] = (receipt_file, receipt)
        rev = Tree(root, receipt["commit"])
        raid_ids = {cell_scope(c)[0] for c in spec["cells"]}
        for raid in raid_ids:
            if engine_digest(rev, raid) != engine_digest(here, raid):
                raise ValueError(f"{capture_id}: receipt engine differs from HEAD for {raid}")
        archive = receipt["archive"]
        archive_path = str(archive["path"]).replace("\\", "/")
        target = f"{RECEIPTS}/{name}-{capture_id}.json"
        captures[capture_id] = {
            "archive": {"path": archive_path, "sha256": archive["sha256"]},
            "entries": {
                "path": str(receipt["entries"]["path"]).replace("\\", "/"),
                "sha256": receipt["entries"]["sha256"],
            },
            "receipt": {"path": target, "sha256": sha256_bytes(receipt_file.read_bytes())},
            "receipt_commit": receipt["commit"],
            "visual_sample": capture["visual_sample"],
        }
        for key in ("archive", "entries", "receipt"):
            artifacts[captures[capture_id][key]["path"]] = captures[capture_id][key]["sha256"]
    cells: dict[str, Any] = {}
    for cell_id in spec["cells"]:
        record = records.get(cell_id)
        source = (record or {}).get("real_actor_source")
        if source is None:
            raise ValueError(f"{cell_id}: no registered real actor source")
        owner = [
            c for c, v in captures.items() if v["archive"]["sha256"] == source["archive"]["sha256"]
        ]
        if len(owner) != 1:
            raise ValueError(f"{cell_id}: {len(owner)} captures render its actor source")
        receipt = receipts[owner[0]][1]
        problems = receipt_problems(
            receipt, receipt["commit"], cell_id, captures[owner[0]]["archive"]
        )
        if problems:
            raise ValueError(f"{cell_id}: {'; '.join(problems)}")
        rev = Tree(root, receipt["commit"])
        if content_digest(rev, cell_id) != content_digest(here, cell_id):
            raise ValueError(f"{cell_id}: content changed since the receipt's commit")
        entry: dict[str, Any] = {
            "capture": owner[0],
            "report": source["report"],
            "fight": source["fight"],
            "actor": source["actor"],
            "content": content_digest(here, cell_id),
            "facts": fact_cases(root, source, cell_scope(cell_id)[4]),
        }
        policy = ranking_policy(here, cell_id)
        if policy is not None:
            entry["ranking"] = _pin(root, policy["evidence"])
            artifacts[policy["evidence"]] = entry["ranking"]["sha256"]
        cells[cell_id] = entry
    commits = {c["receipt_commit"] for c in captures.values()}
    if len(commits) != 1:
        raise ValueError(f"a batch renders at one commit, not {sorted(commits)}")
    manifest = {
        "version": 1,
        "batch": name,
        "commit": commits.pop(),
        "attested_at": head,
        "engine": {raid: engine_digest(here, raid) for raid in {cell_scope(c)[0] for c in cells}},
        "captures": captures,
        "cells": cells,
        "artifacts": dict(sorted(artifacts.items())),
    }
    # The receipts must exist before the manifest's own verification can run.
    for capture_id, (source_path, _) in receipts.items():
        target = root / captures[capture_id]["receipt"]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target)
    for cell_id in cells:
        problems = manifest_problems(
            root, manifest, cell_id, records[cell_id]["real_actor_source"], here
        )
        if problems:
            for capture in captures.values():
                (root / capture["receipt"]["path"]).unlink(missing_ok=True)
            raise ValueError(f"{cell_id}: {'; '.join(problems)}")
    path = f"{BATCHES}/{name}.json"
    data = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    (root / BATCHES).mkdir(parents=True, exist_ok=True)
    (root / path).write_bytes(data)
    rows, newline = matrix_rows(root)
    head_row = rows[0]
    for cell_id in cells:
        record = records[cell_id]
        record.update(
            status="COMPLETE",
            references={
                "batch": [{"path": path, "sha256": sha256_bytes(data), "locator": cell_id}]
            },
            note=spec["cells"][cell_id]["coverage_note"],
        )
        row = matrix_row(rows, cell_id)
        values = {d: f"{path}#{cell_id}" for d in head_row[10:17]}
        values["real_actor_source"] = f"{COVERAGE}#{cell_id}"
        values.update(status="COMPLETE", notes=spec["cells"][cell_id]["matrix_note"])
        for column, value in values.items():
            row[head_row.index(column)] = value
        print(f"{cell_id}: COMPLETE ({name})")
    (root / COVERAGE).write_bytes(
        (json.dumps(coverage, indent=2, ensure_ascii=False) + "\n").encode()
    )
    out = io.StringIO()
    csv.writer(out, lineterminator=newline).writerows(rows)
    (root / MATRIX).write_bytes(out.getvalue().encode("utf-8"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("write")
    w.add_argument("spec", type=Path)
    d = sub.add_parser("digests")
    d.add_argument("cell_id")
    d.add_argument("--rev")
    args = parser.parse_args(argv)
    if args.command == "write":
        return write(json.loads(args.spec.read_text(encoding="utf-8")))
    tree = Tree(ROOT, args.rev)
    raid = cell_scope(args.cell_id)[0]
    print(
        json.dumps(
            {
                "engine": engine_digest(tree, raid),
                "content": content_digest(tree, args.cell_id),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
