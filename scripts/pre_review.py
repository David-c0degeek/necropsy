"""Run the mechanical checks before a review request and print its header.

    uv run python scripts/pre_review.py [--base REV] [--full]

The changed set is everything that differs from BASE (default origin/main): the
committed diff, staged and unstaged edits, and untracked files that are not
ignored. Deleted files are listed but never hashed or run. BASE is resolved to
a commit once and must be an ancestor of HEAD; nothing is fetched.

Checks, each reported PASS, FAIL or SKIP with its command and scope:
CRLF, missing final newline and whitespace errors in changed text files;
ruff and ruff format on changed Python; mypy; check_docs when Markdown changed;
capture_queue verify when the queue changed, or verify --snapshot when only its
pinned research changed;
closure_pins for changed closures, and for closures newly referenced from a
changed coverage.json; fact_freeze check for changed files written by it;
golden replays: the whole golden file when it changed (or only `--golden-k EXPR`,
labelled as targeted), else a changed zone rules file's raid seed replays; and
pytest on changed test files plus tests/unit/test_<name>.py for a changed module
<name>.py (a heuristic, never a claim of complete impact coverage). `--full`
runs the CI fast suite as well. A check that cannot run, or tests that are all
skipped or absent, are SKIP, never PASS.

The header lists the changed files with the SHA-256 of their raw working bytes,
which are not canonical Git pins. A rename shows as a deletion plus an addition.
The fingerprints are taken before the checks and again after them: a check that
rewrites a file fails the gate. Exit 1 on any FAIL.

A passing gate is necessary mechanical evidence. It is never domain, visual or
review approval; the checklist printed after the header still needs a person.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # run as a script: make the sibling tools importable
    sys.path.insert(0, str(ROOT))

from scripts import closure_pins, fact_freeze  # noqa: E402

CHECKLIST = Path("tasks/raid-completion/review-checklist.md")
COVERAGE = "tests/golden/raids/coverage.json"
CLOSURES = "tests/golden/raids/closures/"
QUEUE_INPUTS = (
    "tasks/raid-completion/capture-queue.json",
    "tasks/raid-completion/research/capture-",
)
TRAILING = re.compile(rb"[ \t]+\r?\n")
CI_MARKERS = "not golden and not live and not acceptance"
GOLDEN = "tests/golden/test_raid_evidence.py"
# Zone rule files whose changes reach only that raid's saved analyses.
ZONE_RULES = re.compile(r"^src/necropsy/rules/classic_era/zones/(mc|bwl|aq40)(_[a-z]+)?\.yaml$")
PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


def run_command(command: Sequence[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command), cwd=root, capture_output=True, text=True, encoding="utf-8", check=False
    )


@dataclass
class Result:
    name: str
    status: str
    scope: str
    detail: str = ""


@dataclass
class Changes:
    base: str
    head: str
    present: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    binary: set[str] = field(default_factory=set)
    index_differs: list[str] = field(default_factory=list)
    """Paths whose staged version differs from the fingerprinted working bytes."""


class GateError(ValueError):
    """The gate cannot establish what changed."""


def git(root: Path, *args: str) -> bytes:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if done.returncode:
        raise GateError(f"git {' '.join(args)} failed: {done.stderr.decode(errors='replace')}")
    return done.stdout


def changes(root: Path, base: str) -> Changes:
    """Every path that differs from BASE, from the working tree's point of view."""
    try:
        resolved = git(root, "rev-parse", "--verify", f"{base}^{{commit}}").decode().strip()
    except GateError:
        raise GateError(f"{base} is not a commit") from None
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", resolved, "HEAD"], cwd=root, check=False
    ).returncode:
        raise GateError(f"{base} is not an ancestor of HEAD")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    found = Changes(resolved, head)
    committed = _names(root, "diff", "-z", "--no-renames", "--name-only", resolved, "HEAD")
    staged = _names(root, "diff", "-z", "--no-renames", "--name-only", "--cached")
    unstaged = _names(root, "diff", "-z", "--no-renames", "--name-only")
    untracked = _names(root, "ls-files", "-z", "--others", "--exclude-standard")
    # The union, not the net diff: a staged change undone in the working tree
    # still ships with a commit, so it must be seen.
    for name in sorted(committed | staged | unstaged | untracked):
        (found.present if (root / name).is_file() else found.deleted).append(name)
    found.index_differs = sorted(staged & unstaged)
    for line in git(root, "diff", "-z", "--no-renames", "--numstat", resolved).split(b"\0"):
        parts = line.split(b"\t")
        if len(parts) == 3 and parts[0] == b"-":
            found.binary.add(parts[2].decode())
    for name in found.present:
        attributes = git(root, "check-attr", "text", "--", name).decode()
        if attributes.rstrip().endswith(": unset") or b"\0" in (root / name).read_bytes()[:8000]:
            found.binary.add(name)
    return found


def _names(root: Path, *args: str) -> set[str]:
    return {p.decode() for p in git(root, *args).split(b"\0") if p}


def state(root: Path, found: Changes) -> tuple[Any, ...]:
    """What the header describes: HEAD, the index, and every changed path's bytes."""
    index = hashlib.sha256(git(root, "diff", "--cached", "--raw", "-z", "--no-renames")).hexdigest()
    return (
        git(root, "rev-parse", "HEAD").decode().strip(),
        index,
        tuple(found.present),
        tuple(found.deleted),
        tuple(sorted(fingerprints(root, found.present).items())),
    )


def fingerprints(root: Path, paths: list[str]) -> dict[str, str]:
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}


def byte_checks(root: Path, found: Changes) -> list[Result]:
    text = [p for p in found.present if p not in found.binary]
    crlf = [p for p in text if b"\r\n" in (root / p).read_bytes()]
    unterminated = [
        p for p in text if (data := (root / p).read_bytes()) and not data.endswith(b"\n")
    ]
    spaces = [p for p in text if _new_whitespace(root, found.base, p)]
    scope = f"{len(text)} text file(s)"
    return [
        Result("CRLF", FAIL if crlf else PASS, scope, ", ".join(crlf)),
        Result("final newline", FAIL if unterminated else PASS, scope, ", ".join(unterminated)),
        Result("trailing whitespace", FAIL if spaces else PASS, scope, ", ".join(spaces)),
    ]


def _new_whitespace(root: Path, base: str, path: str) -> bool:
    """Trailing whitespace this change adds (pre-existing lines are not flagged)."""
    if git(root, "ls-files", "--", path):
        check = ["git", "diff", "--check", base, "--", path]
        return subprocess.run(check, cwd=root, capture_output=True, check=False).returncode != 0
    return TRAILING.search((root / path).read_bytes()) is not None


def tool(run: Runner, root: Path, name: str, command: Sequence[str], scope: str) -> Result:
    if shutil.which(command[0]) is None:
        return Result(name, SKIP, scope, f"{command[0]} is not available")
    done = run(command, root)
    detail = (done.stdout + done.stderr).strip().splitlines()[-1:] if done.returncode else []
    return Result(
        name,
        PASS if done.returncode == 0 else FAIL,
        f"{scope}: {' '.join(command)}",
        detail[0] if detail else "",
    )


def pytest_result(run: Runner, root: Path, name: str, args: Sequence[str], scope: str) -> Result:
    command = ["uv", "run", "pytest", "-q", *args]
    if shutil.which("uv") is None:
        return Result(name, SKIP, scope, "uv is not available")
    done = run(command, root)
    lines = (done.stdout + done.stderr).splitlines()
    # The summary is the last line naming a count; progress dots or a crash
    # traceback can follow it or replace it.
    counted = [line for line in lines if re.search(r"\d+ (passed|failed|error|skipped)", line)]
    summary = counted[-1].strip("= ") if counted else "no pytest summary"
    # Only pytest's own "no tests collected" exit (5) is a skip; any other
    # failing exit stays a failure whatever its output says.
    if done.returncode == 5:
        return Result(name, SKIP, scope, "no tests ran")
    passed = re.search(r"(\d+) passed", summary)
    if done.returncode == 0 and not passed:
        return Result(name, SKIP, scope, f"nothing passed: {summary}")
    if done.returncode != 0:
        failing = [line.split(" - ")[0] for line in lines if line.startswith(("FAILED ", "ERROR "))]
        tail = lines[-1].strip() if lines else ""
        summary = "; ".join([summary, *failing[:5]] + ([] if counted else [tail]))
    return Result(name, PASS if done.returncode == 0 else FAIL, scope, summary)


def related_tests(root: Path, found: Changes) -> list[str]:
    """Changed test files, plus tests/unit/test_<name>.py for a changed <name>.py."""
    tests = {p for p in found.present if re.search(r"(^|/)test_[^/]*\.py$", p)}
    for path in found.present:
        if path.endswith(".py") and (path.startswith(("scripts/", "src/"))):
            candidate = f"tests/unit/test_{Path(path).stem}.py"
            if (root / candidate).is_file():
                tests.add(candidate)
    return sorted(tests)


def closure_results(root: Path, found: Changes) -> list[Result]:
    """Closures that changed, and closures newly referenced from a changed coverage.json."""
    cp = closure_pins
    targets = {p for p in found.present if p.startswith(CLOSURES) and p.endswith(".json")}
    results = []
    if COVERAGE in found.present:
        results.append(
            Result(
                "coverage closure references",
                FAIL if (problems := cp.verify_coverage(root)) else PASS,
                COVERAGE,
                "; ".join(problems),
            )
        )
        targets |= _newly_referenced(root, found.base)
    for path in sorted(targets):
        failures, _ = cp.verify_closure(root, Path(path))
        results.append(
            Result("closure pins", FAIL if failures else PASS, path, "; ".join(failures))
        )
    return results


def _closure_refs(data: Any) -> Counter[tuple[str, str, str, str]]:
    """Every reference to a closure, as (cell, field, path, sha), with multiplicity."""
    refs: Counter[tuple[str, str, str, str]] = Counter()
    for record in data.get("records", []):
        for name, group in (record.get("references") or {}).items():
            for ref in group:
                if str(ref.get("path", "")).startswith(CLOSURES):
                    key = (str(record.get("cell_id")), name, ref["path"], ref.get("sha256", ""))
                    refs[key] += 1
    return refs


def _newly_referenced(root: Path, base: str) -> set[str]:
    current = _closure_refs(json.loads((root / COVERAGE).read_bytes()))
    try:
        before = _closure_refs(json.loads(git(root, "show", f"{base}:{COVERAGE}")))
    except GateError:
        before = Counter()
    return {path for _, _, path, _ in current - before}


def fact_results(root: Path, found: Changes) -> list[Result]:
    ff = fact_freeze
    results = []
    for path in found.present:
        if not path.endswith(".json") or path in found.binary:
            continue
        try:
            data = json.loads((root / path).read_bytes())
        except ValueError:
            continue
        written_by = data.get("tool") if isinstance(data, dict) else None
        if isinstance(written_by, dict) and written_by.get("name") == "scripts/fact_freeze.py":
            code = ff.main(["check", str(root / path)])
            results.append(Result("fact freeze", PASS if code == 0 else FAIL, path))
    return results


def golden_run(found: Changes, tests: list[str], golden_k: str | None) -> tuple[str, str] | None:
    """The golden replay selection: a targeted -k run is labelled as such.

    A changed golden test file runs the whole file unless an explicit expression is
    given; changed zone rules alone run that raid's seed replays, which the
    file-name heuristic would otherwise skip entirely.
    """
    if GOLDEN in tests:
        if golden_k:
            return golden_k, f"targeted -k {golden_k!r}, NOT the full golden file"
        return "", "full golden file"
    raids = sorted({m[1] for p in found.present if (m := ZONE_RULES.match(p))})
    if not raids:
        return None
    expression = "seed_capture and (" + " or ".join(f"{r}-" for r in raids) + ")"
    return expression, f"zone rules changed: {', '.join(raids)} seed replays"


def gate(
    root: Path,
    base: str,
    full: bool,
    run: Runner = run_command,
    golden_k: str | None = None,
) -> tuple[Changes, dict[str, str], list[Result]]:
    found = changes(root, base)
    before = fingerprints(root, found.present)
    start = state(root, found)
    results = [
        Result(
            "index matches working bytes",
            FAIL if found.index_differs else PASS,
            "staged changes",
            ", ".join(found.index_differs),
        ),
        *byte_checks(root, found),
    ]
    python = [p for p in found.present if p.endswith(".py")]
    uv = ["uv", "run"]
    if python:
        scope = f"{len(python)} file(s)"
        results.append(tool(run, root, "ruff", [*uv, "ruff", "check", *python], scope))
        format_check = [*uv, "ruff", "format", "--check", *python]
        results.append(tool(run, root, "ruff format", format_check, scope))
        results.append(tool(run, root, "mypy", [*uv, "mypy"], "configured files"))
    if any(p.endswith(".md") for p in found.present):
        docs = [*uv, "python", "scripts/check_docs.py"]
        results.append(tool(run, root, "docs", docs, "Markdown"))
    if any(p.startswith(QUEUE_INPUTS) for p in found.present + found.deleted):
        # A re-emitted queue must pin current inputs; otherwise the queue a runner
        # may be executing must be intact, and later input changes are its age.
        if QUEUE_INPUTS[0] in found.present + found.deleted:
            queue = [*uv, "python", "scripts/capture_queue.py", "verify"]
            results.append(tool(run, root, "capture queue pins", queue, "re-emitted queue"))
        else:
            queue = [*uv, "python", "scripts/capture_queue.py", "verify", "--snapshot"]
            results.append(tool(run, root, "capture queue snapshot", queue, "emitted queue"))
    results += closure_results(root, found)
    results += fact_results(root, found)
    tests = related_tests(root, found)
    golden = golden_run(found, tests, golden_k)
    tests = [t for t in tests if t != GOLDEN] if golden else tests
    if tests:
        scope = f"{len(tests)} file(s) (heuristic)"
        results.append(pytest_result(run, root, "related tests", ["-m", "not live", *tests], scope))
    if golden:
        expression, scope = golden
        args = ["-m", "not live", GOLDEN, *(["-k", expression] if expression else [])]
        results.append(pytest_result(run, root, "golden replays", args, scope))
    if full:
        results.append(pytest_result(run, root, "CI fast suite", ["-m", CI_MARKERS], CI_MARKERS))
    # Recompute everything: a check that edits, adds or deletes a file, or moves
    # HEAD or the index, makes the header describe something else.
    now = changes(root, base)
    moved = sorted(
        set(found.present) ^ set(now.present)
        | set(found.deleted) ^ set(now.deleted)
        | {p for p, d in fingerprints(root, now.present).items() if before.get(p) not in (None, d)}
    )
    if state(root, now)[:2] != start[:2]:
        moved.append("HEAD or index")
    status = FAIL if moved else PASS
    results.append(
        Result("nothing changed during the checks", status, "repository", ", ".join(moved))
    )
    return found, before, results


def header(found: Changes, prints: dict[str, str], results: list[Result], checklist: str) -> str:
    lines = [
        "## Review header",
        f"base {found.base[:12]}, HEAD {found.head[:12]}",
        "",
        "Changed files: SHA-256 of the raw working bytes, first 12. These are not canonical "
        "Git pins (line endings, clean filters and LFS can differ); pin with closure_pins or "
        "`git show REV:PATH`. A rename shows as a deletion plus an addition.",
    ]
    lines += [f"- {path} {digest[:12]}" for path, digest in prints.items()]
    lines += [f"- {path} (deleted)" for path in found.deleted]
    lines += ["", "Checks:"]
    for r in results:
        lines.append(f"- {r.status} {r.name} - {r.scope}" + (f" - {r.detail}" if r.detail else ""))
    failed = [r.name for r in results if r.status == FAIL]
    skipped = [f"{r.name} ({r.detail or r.scope})" for r in results if r.status == SKIP]
    if failed:
        verdict = f"Result: FAIL ({', '.join(failed)})"
    elif skipped:
        verdict = f"Result: INCOMPLETE, not run: {'; '.join(skipped)}"
    else:
        verdict = "Result: every selected check passed (mechanical evidence only)"
    lines += ["", verdict, "", checklist.strip()]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, root: Path = ROOT, run: Runner = run_command) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--full", action="store_true", help="also run the CI fast suite")
    parser.add_argument(
        "--golden-k",
        metavar="EXPR",
        help="run only these golden replays when the golden test file changed (labelled targeted)",
    )
    args = parser.parse_args(argv)
    try:
        found, prints, results = gate(root, args.base, args.full, run, args.golden_k)
    except GateError as error:
        print(f"pre-review gate refused: {error}", file=sys.stderr)
        return 2
    path = root / CHECKLIST
    checklist = path.read_text(encoding="utf-8") if path.is_file() else ""
    print(header(found, prints, results, checklist), end="")
    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
