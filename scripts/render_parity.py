"""Render one capture from a pinned commit, from source and from an isolated wheel.

Usage: uv run python scripts/render_parity.py ARCHIVE --entries ENTRIES --commit REV
           --out DIR [--browser msedge] [--skip-visual]

One receipt (DIR/receipt.json) replaces the hand-run render review of a capture
unit:

1. A worktree of REV (resolved to its full commit) builds the wheel. Every file in
   the wheel's package must equal its Git blob at REV, and every tracked package
   file must be in the wheel.
2. The wheel is installed with `--no-deps` into a new virtual environment next to
   the hashed runtime requirements in capture/requirements.txt.
3. `necropsy offline` renders the archive twice: from the REV worktree's own
   source (run inside the worktree, so the checkout's `src` is never imported)
   and from the installed wheel (run from an empty directory). analysis.json,
   report.html, playbook.html and the package must be byte-identical.
4. For every boss in the saved analysis, the texts the saved playbook says the
   pages show (strategy items, encounter fact timings, healer notes and removal
   labels) must appear on both pages. A boss without a personal playbook, or a
   playbook layout this check does not know, is recorded as such; nothing is
   skipped silently.
5. `visual_check` runs once per page with one anchor per boss section and per
   facts section, in dark and light at 1440 and 390 and in print CSS. A short
   list of pictures to look at by eye is recorded; a clean run is layout,
   network and console evidence only.

The receipt is evidence for review, never a cell closure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ("analysis.json", "report.html", "playbook.html")
REQUIREMENTS = "capture/requirements.txt"


def run(command: list[str], cwd: Path, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=True, **kwargs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=True
    ).stdout


def wheel_payload(wheel: Path, commit: str) -> dict[str, Any]:
    tracked = {
        line[len("src/") :]
        for line in run(
            ["git", "ls-tree", "-r", "--name-only", commit, "src/necropsy"], ROOT
        ).stdout.split()
    }
    with zipfile.ZipFile(wheel) as archive:
        names = {n for n in archive.namelist() if n.startswith("necropsy/") and not n.endswith("/")}
        mismatched = sorted(n for n in names if archive.read(n) != git_blob(commit, f"src/{n}"))
    return {
        "files": len(names),
        "mismatched": mismatched,
        "not_in_git": sorted(names - tracked),
        "missing_from_wheel": sorted(tracked - names),
    }


def _single(directory: Path, pattern: str) -> Path:
    found = sorted(directory.glob(pattern))
    if len(found) != 1:
        raise SystemExit(f"expected one {pattern} in {directory}, found {len(found)}")
    return found[0]


BLOCKS = frozenset(
    [
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "details",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "summary",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    ]
)
VOID = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "source",
        "track",
        "wbr",
    ]
)


class _Sections(HTMLParser):
    """The text of every element whose id is wanted, with inline markup joined
    without spaces and block boundaries as spaces, as a reader sees it."""

    def __init__(self, wanted: set[str]) -> None:
        super().__init__(convert_charrefs=True)
        self.wanted = wanted
        self.open: list[tuple[str, str, int]] = []  # (id, tag, depth at open)
        self.depth = 0
        self.text: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in BLOCKS:
            self._add(" ")
        if tag in VOID:
            return
        self.depth += 1
        element = dict(attrs).get("id")
        if element in self.wanted:
            if element in self.text:
                raise ValueError(f"duplicate element id {element}")
            self.text[element] = []
            self.open.append((element, tag, self.depth))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID:
            return
        if self.open and self.open[-1][1] == tag and self.open[-1][2] == self.depth:
            self.open.pop()
        self.depth -= 1
        if tag in BLOCKS:
            self._add(" ")

    def handle_data(self, data: str) -> None:
        self._add(data)

    def _add(self, data: str) -> None:
        for element, _, _ in self.open:
            self.text[element].append(data)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def section_texts(page: Path, ids: set[str]) -> dict[str, str]:
    parser = _Sections(ids)
    parser.feed(page.read_text(encoding="utf-8"))
    parser.close()
    return {element: normalize("".join(parts)) for element, parts in parser.text.items()}


def _texts(rows: Any, key: str) -> list[str]:
    return [str(r[key]) for r in rows or () if isinstance(r, dict) and r.get(key)]


def expected_texts(boss: dict[str, Any]) -> dict[str, Any]:
    playbook = boss.get("playbook")
    if not isinstance(playbook, dict):
        return {"outcome": "no personal playbook"}
    static = playbook.get("static") if isinstance(playbook.get("static"), dict) else {}
    facts = playbook.get("encounter_facts") or (static or {}).get("encounter")
    strategy = playbook.get("encounter_strategy") or (static or {}).get("guidance")
    known = any(k in playbook for k in ("encounter_strategy", "encounter_facts", "static"))
    if not known:
        return {"outcome": "playbook layout not checked"}
    return {
        "outcome": "checked",
        "strategy": _texts((strategy or {}).get("items"), "text"),
        "facts": _texts((facts or {}).get("timings"), "text"),
        "class_notes": _texts(playbook.get("class_notes"), "text"),
        "removals": _texts(playbook.get("mechanic_removals"), "label"),
    }


def content_check(directory: Path) -> dict[str, Any]:
    """Each boss's expected texts, complete and normalized, inside that boss's own
    section (id boss-<encounter>) on each page; a missing section is a finding."""
    analysis = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    ids = {f"boss-{b['encounter_id']}" for b in analysis["bosses"]}
    pages = {
        name: section_texts(directory / name, ids) for name in ("report.html", "playbook.html")
    }
    bosses = {}
    for boss in analysis["bosses"]:
        section = f"boss-{boss['encounter_id']}"
        expected = expected_texts(boss)
        result: dict[str, Any] = {"outcome": expected.pop("outcome")}
        result["sections_missing"] = sorted(n for n, found in pages.items() if section not in found)
        for kind, texts in expected.items():
            normalized = [normalize(t) for t in texts]
            result[kind] = {
                "expected": len(normalized),
                "missing": {
                    name: [t for t in normalized if t not in found.get(section, "")]
                    for name, found in pages.items()
                },
            }
        bosses[str(boss["encounter_id"])] = result
    missing = sum(
        len(v)
        for b in bosses.values()
        for kind in b.values()
        if isinstance(kind, dict)
        for v in kind["missing"].values()
    )
    sections = sum(len(b["sections_missing"]) for b in bosses.values())
    unchecked = sorted(k for k, b in bosses.items() if b["outcome"] != "checked")
    return {
        "bosses": bosses,
        "missing_texts": missing,
        "missing_sections": sections,
        "unchecked_bosses": unchecked,
    }


def visual(tool: Path, site: Path, out: Path, ids: list[int], browser: str) -> dict[str, Any]:
    anchors = {
        "report.html": [a for i in ids for a in (f"boss-{i}", f"boss-{i}-plan")],
        "playbook.html": [a for i in ids for a in (f"boss-{i}", f"boss-{i}-during")],
    }
    runs = {}
    for page, ids_ in anchors.items():
        target = out / page.removesuffix(".html")
        command = [
            sys.executable,
            str(tool),
            str(site),
            "--page",
            page,
            "--out",
            str(target),
            "--browser",
            browser,
            "--print",
            "--theme-storage",
            "necropsy:theme",
        ]
        for anchor in ids_:
            command += ["--anchor", anchor]
        done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        findings = target / "findings.json"
        runs[page] = {
            "exit": done.returncode,
            "summary": (done.stdout.strip().splitlines() or [""])[-1],
            "findings_sha256": sha256(findings) if findings.is_file() else None,
            "anchors": len(ids_),
        }
    return runs


def sample(ids: list[int], content: dict[str, Any]) -> list[str]:
    """The pictures to look at by eye: the fullest and the sparsest boss."""

    def size(i: int) -> int:
        boss = content["bosses"][str(i)]
        return sum(k["expected"] for k in boss.values() if isinstance(k, dict))

    picks = sorted({max(ids, key=size), min(ids, key=size)})
    names = []
    for i in picks:
        names += [
            f"report/report.html-1440-dark-at-boss-{i}-plan.png",
            f"report/report.html-390-light-at-boss-{i}-plan.png",
            f"playbook/playbook.html-1440-light-at-boss-{i}-during.png",
            f"playbook/playbook.html-390-dark-at-boss-{i}-during.png",
            f"playbook/playbook.html-1440-light-print-at-boss-{i}-during.png",
        ]
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("archive", type=Path)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", default="msedge", choices=("msedge", "chromium"))
    parser.add_argument("--skip-visual", action="store_true")
    args = parser.parse_args(argv)
    archive, entries, out = args.archive.resolve(), args.entries.resolve(), args.out.resolve()
    if out.exists():
        raise SystemExit(f"{out} exists; use a new directory for every receipt")
    commit = run(["git", "rev-parse", "--verify", f"{args.commit}^{{commit}}"], ROOT).stdout.strip()
    archive_sha = sha256(archive)
    out.mkdir(parents=True)
    tree = out / "worktree"
    run(["git", "worktree", "add", "--detach", "-q", str(tree), commit], ROOT)
    try:
        run(["uv", "build", "--wheel", "-q", "-o", str(out / "dist")], tree)
        wheel = _single(out / "dist", "necropsy-*.whl")
        payload = wheel_payload(wheel, commit)
        venv = out / "venv"
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run(["uv", "venv", "-q", "--python", "3.14", str(venv)], ROOT)
        run(
            [
                "uv",
                "pip",
                "install",
                "-q",
                "--python",
                str(python),
                "--require-hashes",
                "--no-deps",
                "-r",
                str(tree / REQUIREMENTS),
            ],
            ROOT,
        )
        run(["uv", "pip", "install", "-q", "--python", str(python), "--no-deps", str(wheel)], ROOT)
        offline = ["offline", str(archive), "--sha256", archive_sha, "--entries", str(entries)]
        run(["uv", "run", "--frozen", "necropsy", *offline, "--out", str(out / "source")], tree)
        with tempfile.TemporaryDirectory() as empty:
            run(
                [str(python), "-I", "-m", "necropsy", *offline, "--out", str(out / "installed")],
                Path(empty),
            )
            origin = run(
                [str(python), "-I", "-c", "import necropsy; print(necropsy.__file__)"], Path(empty)
            ).stdout.strip()
        packages = {
            side: _single(out / side, "necropsy-*.zip").name for side in ("source", "installed")
        }
        hashes = {}
        for name in (*OUTPUTS, packages["source"]):
            hashes[name] = {
                side: sha256(out / side / (packages[side] if name.endswith(".zip") else name))
                for side in ("source", "installed")
            }
        identical = all(len(set(v.values())) == 1 for v in hashes.values())
        content = {side: content_check(out / side) for side in ("source", "installed")}
        analysis = json.loads((out / "source/analysis.json").read_text(encoding="utf-8"))
        ids = [int(b["encounter_id"]) for b in analysis["bosses"]]
        tool = tree / "scripts/visual_check.py"
        visuals = (
            None
            if args.skip_visual
            else visual(tool, out / "installed", out / "visual", ids, args.browser)
        )
        # The configuration is the capture's own, from its archive marker.
        with zipfile.ZipFile(archive) as raw:
            marker = json.loads(raw.read("necropsy-snapshot.json"))
        subject = marker.get("subject") or {}
        unit = {
            "zone": (marker.get("zone") or {}).get("id"),
            "partition": (marker.get("zone") or {}).get("partition"),
            "class_id": subject.get("class_id"),
            "category": subject.get("ranking_category"),
            "metric": subject.get("ranking_metric"),
            "faction": subject.get("faction"),
        }
        tools = {
            "python": sys.version.split()[0],
            "uv": run(["uv", "--version"], ROOT).stdout.strip(),
            "render_parity_sha256": sha256(Path(__file__)),
            "visual_check_sha256": sha256(tool),
            "requirements_sha256": sha256(tree / REQUIREMENTS),
            "uv_lock_sha256": sha256(tree / "uv.lock"),
        }
    finally:
        run(["git", "worktree", "remove", "--force", str(tree)], ROOT)
    receipt = {
        "commit": commit,
        "unit": unit,
        "archive": {"path": str(args.archive), "sha256": archive_sha},
        "entries": {"path": str(args.entries), "sha256": sha256(entries)},
        "wheel": {"name": wheel.name, "sha256": sha256(wheel), "payload": payload},
        "installed_from": origin,
        "outputs": hashes,
        "source_equals_installed": identical,
        "content": content["installed"],
        "content_source_missing": content["source"]["missing_texts"],
        "visual": visuals,
        "sample_by_eye": sample(ids, content["installed"]) if visuals else [],
        "tools": tools,
        "note": "Evidence for review only; not a closure and not visual or domain approval.",
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(out / "venv", ignore_errors=True)
    clean = (
        identical
        and not any(payload[k] for k in ("mismatched", "not_in_git", "missing_from_wheel"))
        and all(
            content[side][key] == 0
            for side in ("source", "installed")
            for key in ("missing_texts", "missing_sections")
        )
        and (visuals is None or all(v["exit"] == 0 for v in visuals.values()))
    )
    print(f"{out / 'receipt.json'}: {'clean' if clean else 'PROBLEMS'}")
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
