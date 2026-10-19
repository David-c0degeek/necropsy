"""Pin and verify the SHA-256 references nested inside cell closure records.

A closure record (tests/golden/raids/closures/*.json) pins its evidence files,
its source review and its archive to one commit. Every pin is the SHA-256 of
the raw Git blob at that commit (`git show COMMIT:PATH`), never of working-tree
bytes, which can differ (for example CRLF on Windows). An archive kept in Git
LFS is pinned by its pointer's oid, and a hydrated working copy must match both
the oid and the size.

    uv run python scripts/closure_pins.py verify [CLOSURE ...]
    uv run python scripts/closure_pins.py pin CLOSURE --commit REV [--replace]

`verify` checks every closure (default: all of them) against its recorded
commit, and checks that coverage.json references to closure files match the
files committed at HEAD. Files changed at HEAD since a closure commit are
reported, but are not a failure. `pin` fills `commit` and every pin of a new
closure from REV and refuses evidence whose working bytes differ from REV.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLOSURES = Path("tests/golden/raids/closures")
COVERAGE = Path("tests/golden/raids/coverage.json")
LFS_SIGNATURE = b"version https://git-lfs.github.com/spec/v1"
HEX64 = re.compile(r"[0-9a-f]{64}")
LFS_POINTER = re.compile(
    rb"version https://git-lfs\.github\.com/spec/v1\n"
    rb"oid sha256:([0-9a-f]{64})\nsize (0|[1-9][0-9]*)\n"
)


class PinError(ValueError):
    """A pin cannot be established from committed bytes."""


def git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)


def resolve(root: Path, rev: str) -> str:
    done = git(root, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    if done.returncode:
        raise PinError(f"{rev} is not a commit")
    return done.stdout.decode().strip()


def blob(root: Path, commit: str, path: str) -> bytes | None:
    done = git(root, "cat-file", "blob", f"{commit}:{path}")
    return done.stdout if done.returncode == 0 else None


def lfs_pointer(data: bytes) -> tuple[str, int] | None:
    """(oid, size) of a canonical LFS pointer, or None for ordinary bytes.

    Anything that starts with the pointer's version text, whatever follows it
    (CRLF, a truncated pointer), must be exactly canonical; it is never hashed
    as ordinary bytes."""
    if not data.startswith(LFS_SIGNATURE):
        return None
    match = LFS_POINTER.fullmatch(data)
    if match is None:
        raise PinError("a Git LFS pointer is malformed")
    return match.group(1).decode(), int(match.group(2))


def committed_pin(root: Path, commit: str, path: str) -> str:
    """The pin of PATH at COMMIT: the LFS oid for a pointer, else the blob's SHA-256."""
    data = blob(root, commit, path)
    if data is None:
        raise PinError(f"{path} does not exist at {commit[:12]}")
    pointer = lfs_pointer(data)
    return pointer[0] if pointer else hashlib.sha256(data).hexdigest()


def working_check(root: Path, commit: str, path: str) -> tuple[str | None, str | None]:
    """(problem, note) comparing the working copy of PATH with COMMIT.

    An identical unhydrated LFS pointer is accepted with a metadata-only note:
    its payload was not checked."""
    data = blob(root, commit, path)
    if data is None:
        return f"{path} does not exist at {commit[:12]}", None
    file = root / path
    if not file.is_file():
        return f"{path} is missing from the working tree", None
    working = file.read_bytes()
    pointer = lfs_pointer(data)
    if pointer is not None:
        if working == data:
            return None, f"{path}: unhydrated LFS pointer, metadata only (payload not checked)"
        oid, size = pointer
        if len(working) != size or hashlib.sha256(working).hexdigest() != oid:
            return f"{path}: the working file does not match its LFS oid and size", None
        return None, None
    if working != data:
        crlf = b"\r\n" in working and b"\r\n" not in data
        return f"{path}: working bytes differ from the commit" + (" (CRLF)" if crlf else ""), None
    return None, None


def pins(closure: Any, *, draft: bool = False) -> list[tuple[str, str, str]]:
    """Every nested pin as (locator, path, recorded SHA-256), one per occurrence.

    The record must have a commit string, a non-empty evidence_files_at_closure
    map and archive and source_review references, each with a path and a
    SHA-256. A draft passed to `pin` may leave the commit and hashes blank."""
    if not isinstance(closure, dict):
        raise PinError("a closure must be a JSON object")
    if not isinstance(closure.get("commit"), str) or not (draft or closure["commit"]):
        raise PinError("the closure has no commit")

    def digest(locator: str, value: Any) -> str:
        if not isinstance(value, str) or not (
            (draft and value == "") or HEX64.fullmatch(value) is not None
        ):
            raise PinError(f"{locator} is not a SHA-256")
        return value

    files = closure.get("evidence_files_at_closure")
    if not isinstance(files, dict) or not files:
        raise PinError("the closure has no evidence_files_at_closure")
    found = []
    for path, value in files.items():
        locator = f"evidence_files_at_closure[{path}]"
        found.append((locator, path, digest(locator, value)))
    for key in ("archive", "source_review"):
        ref = closure.get(key)
        if not isinstance(ref, dict) or not isinstance(ref.get("path"), str) or not ref["path"]:
            raise PinError(f"the closure has no {key} path")
        found.append((key, ref["path"], digest(f"{key}.sha256", ref.get("sha256"))))
    return found


def verify_closure(root: Path, path: Path) -> tuple[list[str], list[str]]:
    """(failures, notes) for one closure record."""
    name = path.as_posix()
    failures: list[str] = []
    notes: list[str] = []
    try:
        closure = json.loads((root / path).read_bytes())
        entries = pins(closure)
        commit = resolve(root, closure["commit"])
    except (PinError, ValueError) as error:
        return [f"{name}: {error}"], notes
    if git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode:
        failures.append(f"{name}: commit {commit[:12]} is not an ancestor of HEAD")
    head = resolve(root, "HEAD")
    for locator, pinned, recorded in entries:
        try:
            actual = committed_pin(root, commit, pinned)
        except PinError as error:
            failures.append(f"{name}: {locator}: {error}")
            continue
        if actual != recorded:
            failures.append(
                f"{name}: {locator}: {pinned} is {actual[:12]} at {commit[:12]}, "
                f"pinned {recorded[:12]}"
            )
            continue
        try:
            now = committed_pin(root, head, pinned)
        except PinError:
            notes.append(f"{name}: {locator}: {pinned} no longer exists at HEAD")
            continue
        if now != recorded:
            notes.append(f"{name}: {locator}: {pinned} changed at HEAD since {commit[:12]}")
    return failures, notes


def verify_coverage(root: Path) -> list[str]:
    """coverage.json references to closure records must match their HEAD blobs."""
    register = json.loads((root / COVERAGE).read_bytes())
    head = resolve(root, "HEAD")
    failures = []
    for record in register.get("records", []):
        for refs in (record.get("references") or {}).values():
            for ref in refs:
                if not str(ref.get("path", "")).startswith(CLOSURES.as_posix() + "/"):
                    continue
                try:
                    actual = committed_pin(root, head, ref["path"])
                except PinError as error:
                    failures.append(f"{COVERAGE.as_posix()}: {record['cell_id']}: {error}")
                    continue
                if actual != ref["sha256"]:
                    failures.append(
                        f"{COVERAGE.as_posix()}: {record['cell_id']}: {ref['path']} is "
                        f"{actual[:12]} at HEAD, referenced {ref['sha256'][:12]}"
                    )
    return failures


def pin_closure(root: Path, path: Path, rev: str) -> tuple[dict[str, Any], list[str]]:
    """The closure with `commit` and every pin taken from REV's committed blobs,
    and notes: metadata-only LFS acceptance, then every changed value."""
    closure: dict[str, Any] = json.loads((root / path).read_bytes())
    entries = pins(closure, draft=True)
    commit = resolve(root, rev)
    if git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode:
        raise PinError(f"{rev} is not an ancestor of HEAD")
    problems: list[str] = []
    notes: list[str] = []
    for _, pinned, _ in entries:
        problem, note = working_check(root, commit, pinned)
        if problem:
            problems.append(problem)
        if note and note not in notes:
            notes.append(note)
    if problems:
        raise PinError("; ".join(problems))
    if closure["commit"] != commit:
        notes.append(f"commit: {closure['commit'][:12] or '(blank)'} -> {commit[:12]}")
    closure["commit"] = commit
    for locator, pinned, recorded in entries:
        value = committed_pin(root, commit, pinned)
        if value != recorded:
            notes.append(f"{locator}: {recorded[:12] or '(blank)'} -> {value[:12]}")
        if locator.startswith("evidence_files_at_closure["):
            closure["evidence_files_at_closure"][pinned] = value
        else:
            closure[locator]["sha256"] = value
    return closure, notes


def _write(target: Path, data: bytes) -> None:
    """Write next to the target and rename, so a failure keeps the previous bytes."""
    with tempfile.NamedTemporaryFile(
        dir=target.parent, prefix=f".{target.name}.", delete=False
    ) as handle:
        handle.write(data)
    try:
        Path(handle.name).replace(target)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("verify", help="check closures and their coverage references")
    check.add_argument("closures", nargs="*", type=Path)
    pin = sub.add_parser("pin", help="pin a new closure to a commit")
    pin.add_argument("closure", type=Path)
    pin.add_argument("--commit", required=True)
    pin.add_argument("--replace", action="store_true", help="rewrite pins that are already set")
    args = parser.parse_args(argv)
    if args.command == "pin":
        try:
            existing = json.loads((root / args.closure).read_bytes())
            if existing.get("commit") and not args.replace:
                print(f"refused: {args.closure} is already pinned; pass --replace")
                return 2
            pinned, notes = pin_closure(root, args.closure, args.commit)
        except (PinError, OSError, ValueError, KeyError) as error:
            print(f"closure pin refused: {error}", file=sys.stderr)
            return 2
        _write(
            root / args.closure, (json.dumps(pinned, indent=2, ensure_ascii=False) + "\n").encode()
        )
        for note in notes:
            print(f"note: {note}")
        print(f"pinned {args.closure.as_posix()} to {pinned['commit'][:12]}")
        return 0
    paths = args.closures or sorted((root / CLOSURES).glob("*.json"))
    failures: list[str] = []
    for path in paths:
        relative = (
            Path(path).resolve().relative_to(root.resolve())
            if Path(path).is_absolute()
            else Path(path)
        )
        problems, notes = verify_closure(root, relative)
        failures += problems
        for note in notes:
            print(f"note: {note}")
    failures += verify_coverage(root)
    for failure in failures:
        print(f"FAIL: {failure}")
    print(f"{len(paths)} closure(s), {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
