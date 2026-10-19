"""The pre-review gate sees every change against its base, checks bytes without
touching deleted or binary files, never reports PASS for a check that did not
run, selects closures by what changed, and fails when a check rewrites a file."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts import pre_review as pr

CLOSURE = pr.CLOSURES + "cell.json"
PILOT = pr.CLOSURES + "pilot.json"


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)
    return done.stdout.decode().strip()


def write(root: Path, path: str, data: bytes | str) -> None:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_bytes(data.encode() if isinstance(data, str) else data)


def commit(root: Path, message: str = "c") -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def closure(commit_id: str, review_sha: str) -> str:
    return json.dumps(
        {
            "commit": commit_id,
            "archive": {"path": "raw.bin", "sha256": sha(b"archive\n")},
            "evidence_files_at_closure": {"rule.yaml": sha(b"rule\n")},
            "source_review": {"path": "review.json", "sha256": review_sha},
        }
    )


def coverage(*refs: tuple[str, str]) -> str:
    references = [{"path": path, "sha256": digest} for path, digest in refs]
    return json.dumps({"records": [{"cell_id": "c", "references": {"x": references}}]})


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.invalid")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "config", "core.autocrlf", "false")
    write(tmp_path, "keep.txt", "keep\n")
    write(tmp_path, "gone.txt", "gone\n")
    write(tmp_path, "rule.yaml", "rule\n")
    write(tmp_path, "raw.bin", "archive\n")
    write(tmp_path, ".gitattributes", "*.dat -text\n")
    first = commit(tmp_path, "evidence")
    # The pilot pins a review that is only committed afterwards: a real failure.
    write(tmp_path, PILOT, closure(first, sha(b"{}\n")))
    write(tmp_path, "review.json", "{}\n")
    write(tmp_path, pr.COVERAGE, coverage())
    commit(tmp_path, "pilot")
    return tmp_path


def quiet(command: Sequence[str], root: Path) -> subprocess.CompletedProcess[str]:
    """Every tool passes; pytest reports one passed test."""
    out = "1 passed in 0.1s\n" if "pytest" in command else ""
    return subprocess.CompletedProcess(list(command), 0, out, "")


def statuses(results: list[pr.Result]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for r in results:
        found.setdefault(r.name, []).append(r.status)
    return found


def test_the_changed_set_covers_commits_edits_untracked_and_deletions(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "keep.txt", "keep more\n")
    commit(repo, "edit")
    write(repo, "staged.txt", "staged\n")
    git(repo, "add", "staged.txt")
    write(repo, "new.txt", "new\n")
    (repo / "gone.txt").unlink()
    found = pr.changes(repo, base)
    assert found.present == ["keep.txt", "new.txt", "staged.txt"]
    assert found.deleted == ["gone.txt"]
    assert found.base == base


def test_a_base_that_is_not_an_ancestor_is_refused(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "side")
    write(repo, "side.txt", "x\n")
    side = commit(repo, "side")
    git(repo, "checkout", "-q", "main")
    with pytest.raises(pr.GateError, match="not an ancestor"):
        pr.changes(repo, side)
    with pytest.raises(pr.GateError, match="not a commit"):
        pr.changes(repo, "no-such-ref")


def test_byte_checks_flag_text_and_skip_binary_and_deleted_files(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "crlf.txt", b"a\r\nb\r\n")
    write(repo, "open.txt", b"no newline")
    write(repo, "space.txt", b"trailing  \n")
    write(repo, "blob.dat", b"\x00\x01 binary  ")
    (repo / "gone.txt").unlink()
    found = pr.changes(repo, base)
    assert "blob.dat" in found.binary
    checks = {r.name: r for r in pr.byte_checks(repo, found)}
    assert (checks["CRLF"].status, checks["CRLF"].detail) == (pr.FAIL, "crlf.txt")
    assert (checks["final newline"].status, checks["final newline"].detail) == (
        pr.FAIL,
        "open.txt",
    )
    assert checks["trailing whitespace"].detail == "space.txt"


def test_old_trailing_whitespace_in_a_tracked_file_is_not_this_change(repo: Path) -> None:
    write(repo, "old.txt", "old  \n")
    base = commit(repo, "old whitespace")
    write(repo, "old.txt", "old  \nnew line\n")
    checks = {r.name: r for r in pr.byte_checks(repo, pr.changes(repo, base))}
    assert checks["trailing whitespace"].status == pr.PASS


def test_a_check_that_cannot_run_or_finds_no_tests_is_never_a_pass(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_tests(command: Sequence[str], root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(command), 5, "no tests ran in 0.1s\n", "")

    def skipped(command: Sequence[str], root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(command), 0, "3 skipped in 0.1s\n", "")

    assert pr.pytest_result(no_tests, repo, "t", [], "s").status == pr.SKIP
    assert pr.pytest_result(skipped, repo, "t", [], "s").status == pr.SKIP
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert pr.tool(quiet, repo, "ruff", ["uv", "run", "ruff"], "s").status == pr.SKIP
    assert pr.pytest_result(quiet, repo, "t", [], "s").status == pr.SKIP


def test_an_unrelated_coverage_change_does_not_revalidate_the_pilot(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    write(repo, pr.COVERAGE, coverage() + "\n")
    _, _, results = pr.gate(repo, base, False, quiet)
    assert statuses(results)["coverage closure references"] == [pr.PASS]
    assert "closure pins" not in statuses(results)


def test_a_new_reference_to_the_pilot_exposes_its_failure(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    pilot = sha((repo / PILOT).read_bytes())
    write(repo, pr.COVERAGE, coverage((PILOT, pilot)))
    _, _, results = pr.gate(repo, base, False, quiet)
    pins = [r for r in results if r.name == "closure pins"]
    assert [(r.status, r.scope) for r in pins] == [(pr.FAIL, PILOT)]
    assert "review.json does not exist at" in pins[0].detail


def test_a_changed_pilot_fails_and_a_good_closure_passes(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    write(repo, PILOT, (repo / PILOT).read_text(encoding="utf-8") + "\n")
    write(repo, CLOSURE, closure(base, sha(b"{}\n")))
    _, _, results = pr.gate(repo, base, False, quiet)
    pins = {r.scope: r.status for r in results if r.name == "closure pins"}
    assert pins == {PILOT: pr.FAIL, CLOSURE: pr.PASS}


def test_a_check_that_rewrites_a_file_fails_the_gate(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "tool.py", "x = 1\n")

    def formatter(command: Sequence[str], root: Path) -> subprocess.CompletedProcess[str]:
        if "format" in command:
            write(root, "tool.py", "x = 2\n")
        return quiet(command, root)

    _, prints, results = pr.gate(repo, base, False, formatter)
    last = results[-1]
    assert (last.name, last.status, last.detail) == (
        "nothing changed during the checks",
        pr.FAIL,
        "tool.py",
    )
    assert prints["tool.py"] == sha(b"x = 1\n")


def test_the_header_lists_raw_fingerprints_deletions_and_every_check(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "keep.txt", "keep more\n")
    (repo / "gone.txt").unlink()
    found, prints, results = pr.gate(repo, base, False, quiet)
    text = pr.header(found, prints, results, "# Checklist\n- [ ] item")
    assert f"base {base[:12]}" in text
    assert f"- keep.txt {sha(b'keep more\n')[:12]}" in text
    assert "- gone.txt (deleted)" in text
    assert "raw working bytes" in text and "not canonical Git pins" in text
    assert "Result: every selected check passed (mechanical evidence only)" in text
    skipped = [*results[:-1], pr.Result("mypy", pr.SKIP, "configured files", "uv missing")]
    assert "Result: INCOMPLETE, not run: mypy (uv missing)" in pr.header(found, prints, skipped, "")
    failing = [*results, pr.Result("ruff", pr.FAIL, "x")]
    assert "Result: FAIL (ruff)" in pr.header(found, prints, failing, "")
    assert "- PASS CRLF - 1 text file(s)" in text
    assert text.rstrip().endswith("- [ ] item")
    assert text.isascii()


def test_related_tests_follow_changed_modules_and_test_files(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "scripts/thing.py", "x = 1\n")
    write(repo, "tests/unit/test_thing.py", "def test_x() -> None: ...\n")
    write(repo, "tests/unit/test_other.py", "def test_y() -> None: ...\n")
    commit(repo, "tests")
    write(repo, "scripts/thing.py", "x = 2\n")
    write(repo, "tests/unit/test_other.py", "def test_y() -> None: assert True\n")
    found = pr.changes(repo, base)
    assert pr.related_tests(repo, found) == [
        "tests/unit/test_other.py",
        "tests/unit/test_thing.py",
    ]


def test_main_exits_1_on_a_failure_and_2_on_a_bad_base(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "crlf.txt", b"a\r\n")
    assert pr.main(["--base", base], root=repo, run=quiet) == 1
    assert "FAIL CRLF" in capsys.readouterr().out
    assert pr.main(["--base", "nope"], root=repo, run=quiet) == 2


@pytest.mark.parametrize(
    ("path", "data"),
    [("unreviewed.txt", "new\n"), ("keep.txt", "edited by a check\n")],
    ids=["new-file", "unchanged-tracked-file"],
)
def test_a_check_that_adds_or_edits_another_file_fails_the_gate(
    repo: Path, path: str, data: str
) -> None:
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "x.py", "x = 1\n")

    def sneaky(command: Sequence[str], root: Path) -> subprocess.CompletedProcess[str]:
        if "mypy" in command:
            write(root, path, data)
        return quiet(command, root)

    _, _, results = pr.gate(repo, base, False, sneaky)
    assert (results[-1].status, results[-1].detail) == (pr.FAIL, path)


def test_a_staged_change_undone_in_the_working_tree_is_seen_and_fails(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "keep.txt", "staged change\n")
    git(repo, "add", "keep.txt")
    write(repo, "keep.txt", "keep\n")  # working bytes back to the base, index still changed
    found = pr.changes(repo, base)
    assert found.present == ["keep.txt"]
    assert found.index_differs == ["keep.txt"]
    _, _, results = pr.gate(repo, base, False, quiet)
    first = results[0]
    assert (first.name, first.status, first.detail) == (
        "index matches working bytes",
        pr.FAIL,
        "keep.txt",
    )


def test_copying_a_legacy_pilot_reference_into_another_cell_exposes_the_pilot(
    repo: Path,
) -> None:
    pilot = sha((repo / PILOT).read_bytes())
    old = {"cell_id": "old", "references": {"x": [{"path": PILOT, "sha256": pilot}]}}
    legacy = json.dumps({"records": [old]})
    write(repo, pr.COVERAGE, legacy)
    base = commit(repo, "legacy reference")
    new = {"cell_id": "new", "references": {"x": [{"path": PILOT, "sha256": pilot}]}}
    write(repo, pr.COVERAGE, json.dumps({"records": [old, new]}))
    _, _, results = pr.gate(repo, base, False, quiet)
    pins = [(r.status, r.scope) for r in results if r.name == "closure pins"]
    assert pins == [(pr.FAIL, PILOT)]
    # The unchanged legacy occurrence alone does not revalidate the pilot.
    write(repo, pr.COVERAGE, legacy + "\n")
    _, _, results = pr.gate(repo, base, False, quiet)
    assert "closure pins" not in statuses(results)
