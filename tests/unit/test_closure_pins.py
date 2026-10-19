"""Closure pins come from committed blobs only: CRLF or edited working bytes are
refused, LFS archives match their pointer's oid and size, and a pin that is
missing at the recorded commit is a failure, not a warning."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import closure_pins as cp

CLOSURE = "tests/golden/raids/closures/cell.json"
ARCHIVE_BYTES = b"PK\x03\x04 pretend archive bytes"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pointer(data: bytes, size: int | None = None) -> bytes:
    return (
        b"version https://git-lfs.github.com/spec/v1\n"
        + f"oid sha256:{sha(data)}\nsize {len(data) if size is None else size}\n".encode()
    )


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)
    return done.stdout.decode().strip()


def write(root: Path, path: str, data: bytes) -> None:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_bytes(data)


def closure(**pins: Any) -> dict[str, Any]:
    return {
        "version": 1,
        "cell_id": "mc/1/1/A/dps/Horde",
        "commit": pins.get("commit", ""),
        "archive": {"path": "raw/a.zip", "sha256": pins.get("archive", "")},
        "evidence_files_at_closure": {"src/rule.yaml": pins.get("rule", "")},
        "source_review": {"path": "review.json", "sha256": pins.get("review", "")},
        "fields": {"note": "narrative stays untouched"},
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.invalid")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "config", "core.autocrlf", "false")
    write(tmp_path, "src/rule.yaml", b"rule: 1\n")
    write(tmp_path, "review.json", b"{}\n")
    write(tmp_path, "raw/a.zip", pointer(ARCHIVE_BYTES))
    write(tmp_path, str(cp.COVERAGE), json.dumps({"records": []}).encode())
    write(tmp_path, CLOSURE, json.dumps(closure()).encode())
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "evidence")
    write(tmp_path, "raw/a.zip", ARCHIVE_BYTES)  # hydrated, as git-lfs checks it out
    return tmp_path


def head(root: Path) -> str:
    return git(root, "rev-parse", "HEAD")


def pinned(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = json.loads((root / CLOSURE).read_bytes())
    return result


RULE = "evidence_files_at_closure[src/rule.yaml]"


def test_pin_takes_every_hash_from_the_commit_and_keeps_the_narrative(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cp.main(["pin", CLOSURE, "--commit", "HEAD"], root=repo) == 0
    result = pinned(repo)
    assert result["commit"] == head(repo)
    assert result["evidence_files_at_closure"] == {"src/rule.yaml": sha(b"rule: 1\n")}
    assert result["source_review"]["sha256"] == sha(b"{}\n")
    assert result["archive"]["sha256"] == sha(ARCHIVE_BYTES)  # the LFS oid
    assert result["fields"] == {"note": "narrative stays untouched"}
    out = capsys.readouterr().out
    assert f"note: commit: (blank) -> {head(repo)[:12]}" in out
    assert f"note: {RULE}: (blank) -> {sha(b'rule: 1\n')[:12]}" in out
    assert "metadata only" not in out  # the archive was hydrated and checked
    git(repo, "add", CLOSURE)
    git(repo, "commit", "-q", "-m", "closure")
    assert cp.main(["verify"], root=repo) == 0


def test_pin_refuses_crlf_or_edited_working_bytes(repo: Path) -> None:
    write(repo, "src/rule.yaml", b"rule: 1\r\n")
    assert cp.main(["pin", CLOSURE, "--commit", "HEAD"], root=repo) == 2
    assert pinned(repo)["commit"] == ""
    with pytest.raises(cp.PinError, match=r"\(CRLF\)"):
        cp.pin_closure(repo, Path(CLOSURE), "HEAD")
    write(repo, "src/rule.yaml", b"rule: 2\n")
    with pytest.raises(cp.PinError, match="working bytes differ"):
        cp.pin_closure(repo, Path(CLOSURE), "HEAD")


def test_pin_refuses_a_hydrated_archive_that_does_not_match_its_pointer(repo: Path) -> None:
    write(repo, "raw/a.zip", ARCHIVE_BYTES + b"x")
    with pytest.raises(cp.PinError, match="LFS oid and size"):
        cp.pin_closure(repo, Path(CLOSURE), "HEAD")


def test_pin_refuses_a_pointer_whose_size_disagrees(repo: Path) -> None:
    write(repo, "raw/a.zip", pointer(ARCHIVE_BYTES, size=len(ARCHIVE_BYTES) + 1))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "wrong size")
    write(repo, "raw/a.zip", ARCHIVE_BYTES)
    with pytest.raises(cp.PinError, match="LFS oid and size"):
        cp.pin_closure(repo, Path(CLOSURE), "HEAD")


def test_an_unhydrated_pointer_identical_to_the_blob_is_reported_as_metadata_only(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "raw/a.zip", pointer(ARCHIVE_BYTES))
    result, notes = cp.pin_closure(repo, Path(CLOSURE), "HEAD")
    assert result["archive"]["sha256"] == sha(ARCHIVE_BYTES)
    assert "raw/a.zip: unhydrated LFS pointer, metadata only (payload not checked)" in notes
    assert cp.main(["pin", CLOSURE, "--commit", "HEAD"], root=repo) == 0
    assert "note: raw/a.zip: unhydrated LFS pointer, metadata only" in capsys.readouterr().out


@pytest.mark.parametrize(
    "data",
    [
        b"version https://git-lfs.github.com/spec/v1\noid md5:abc\n",
        b"version https://git-lfs.github.com/spec/v1\r\noid sha256:"
        + b"a" * 64
        + b"\r\nsize 3\r\n",
        b"version https://git-lfs.github.com/spec/v1",
        pointer(ARCHIVE_BYTES).rstrip(b"\n"),
    ],
    ids=["bad-oid", "crlf", "truncated-version", "no-final-newline"],
)
def test_a_malformed_pointer_is_refused_not_hashed(repo: Path, data: bytes) -> None:
    write(repo, "raw/a.zip", data)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "broken pointer")
    with pytest.raises(cp.PinError, match="malformed"):
        cp.committed_pin(repo, head(repo), "raw/a.zip")
    with pytest.raises(cp.PinError, match="malformed"):
        cp.pin_closure(repo, Path(CLOSURE), "HEAD")


def test_pin_refuses_an_existing_pin_and_a_commit_outside_head(repo: Path) -> None:
    base = head(repo)
    git(repo, "checkout", "-q", "-b", "side")
    write(repo, "side.txt", b"x\n")
    git(repo, "add", "side.txt")
    git(repo, "commit", "-q", "-m", "side")
    side = head(repo)
    git(repo, "checkout", "-q", "main")
    with pytest.raises(cp.PinError, match="not an ancestor"):
        cp.pin_closure(repo, Path(CLOSURE), side)
    write(repo, CLOSURE, json.dumps(closure(commit=base)).encode())
    assert cp.main(["pin", CLOSURE, "--commit", "HEAD"], root=repo) == 2


def _committed_closure(repo: Path, record: dict[str, Any] | None = None, **pins: Any) -> None:
    write(repo, CLOSURE, json.dumps(record if record is not None else closure(**pins)).encode())
    git(repo, "add", CLOSURE)
    git(repo, "commit", "-q", "-m", "closure")


def _good(repo: Path) -> dict[str, Any]:
    return {
        "commit": head(repo),
        "archive": sha(ARCHIVE_BYTES),
        "rule": sha(b"rule: 1\n"),
        "review": sha(b"{}\n"),
    }


def test_verify_fails_a_pin_missing_at_its_commit_and_a_wrong_hash(repo: Path) -> None:
    good = _good(repo)
    base = good["commit"]
    _committed_closure(repo, **good)
    assert cp.verify_closure(repo, Path(CLOSURE)) == ([], [])
    _committed_closure(repo, **{**good, "rule": "0" * 64})
    failures, _ = cp.verify_closure(repo, Path(CLOSURE))
    assert failures == [
        f"{CLOSURE}: {RULE}: src/rule.yaml is {sha(b'rule: 1\n')[:12]} at {base[:12]}, "
        "pinned 000000000000"
    ]
    git(repo, "rm", "-q", "review.json")
    git(repo, "commit", "-q", "-m", "drop review")
    later = head(repo)
    write(repo, "review.json", b"{}\n")
    git(repo, "add", "review.json")
    git(repo, "commit", "-q", "-m", "review again")
    _committed_closure(repo, **{**good, "commit": later})
    failures, _ = cp.verify_closure(repo, Path(CLOSURE))
    assert failures == [f"{CLOSURE}: source_review: review.json does not exist at {later[:12]}"]


def test_every_occurrence_of_a_path_is_checked_separately(repo: Path) -> None:
    good = _good(repo)
    record = closure(**good)
    record["evidence_files_at_closure"]["review.json"] = "0" * 64  # wrong, same path as the review
    _committed_closure(repo, record)
    failures, _ = cp.verify_closure(repo, Path(CLOSURE))
    assert failures == [
        f"{CLOSURE}: evidence_files_at_closure[review.json]: review.json is "
        f"{sha(b'{}\n')[:12]} at {good['commit'][:12]}, pinned 000000000000"
    ]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda r: {"commit": r["commit"]}, "no evidence_files_at_closure"),
        (lambda r: {**r, "evidence_files_at_closure": {}}, "no evidence_files_at_closure"),
        (lambda r: {k: v for k, v in r.items() if k != "archive"}, "no archive path"),
        (
            lambda r: {**r, "source_review": {"sha256": r["source_review"]["sha256"]}},
            "no source_review",
        ),
        (lambda r: {**r, "archive": {**r["archive"], "sha256": "ABC"}}, r"archive\.sha256 is not"),
        (lambda r: {**r, "commit": ""}, "no commit"),
        (lambda r: {**r, "evidence_files_at_closure": {"src/rule.yaml": 5}}, "is not a SHA-256"),
    ],
    ids=[
        "commit-only",
        "empty-evidence",
        "no-archive",
        "no-review-path",
        "bad-hash",
        "blank-commit",
        "non-string",
    ],
)
def test_a_closure_missing_or_malforming_its_pin_groups_fails(
    repo: Path, change: Any, message: str
) -> None:
    _committed_closure(repo, change(closure(**_good(repo))))
    failures, _ = cp.verify_closure(repo, Path(CLOSURE))
    assert len(failures) == 1 and re.search(message, failures[0]), failures


def test_a_draft_still_needs_every_pin_group(repo: Path) -> None:
    write(repo, CLOSURE, json.dumps({"commit": ""}).encode())
    with pytest.raises(cp.PinError, match="no evidence_files_at_closure"):
        cp.pin_closure(repo, Path(CLOSURE), "HEAD")


def test_verify_notes_later_changes_without_failing(repo: Path) -> None:
    good = _good(repo)
    _committed_closure(repo, **good)
    write(repo, "src/rule.yaml", b"rule: 2\n")
    git(repo, "add", "src/rule.yaml")
    git(repo, "commit", "-q", "-m", "change")
    assert cp.verify_closure(repo, Path(CLOSURE)) == (
        [],
        [f"{CLOSURE}: {RULE}: src/rule.yaml changed at HEAD since {good['commit'][:12]}"],
    )


def test_verify_checks_coverage_references_to_closure_files(repo: Path) -> None:
    _committed_closure(repo, **_good(repo))
    committed = sha((repo / CLOSURE).read_bytes())
    for digest, failing in ((committed, False), ("1" * 64, True)):
        record = {
            "cell_id": "mc/1/1/A/dps/Horde",
            "references": {"implementation": [{"path": CLOSURE, "sha256": digest}]},
        }
        write(repo, str(cp.COVERAGE), json.dumps({"records": [record]}).encode())
        git(repo, "add", str(cp.COVERAGE))
        git(repo, "commit", "-q", "-m", "register")
        assert bool(cp.verify_coverage(repo)) is failing


def test_the_pilot_closure_reports_its_one_mixed_commit_pin() -> None:
    """The legacy pilot pins its source review, which was committed after the
    recorded closure commit. The finding stays a real failure."""
    root = cp.ROOT
    recorded = json.loads((root / cp.CLOSURES / "mc-50668-6-holy-hps-alliance.json").read_bytes())
    if cp.git(root, "cat-file", "-e", f"{recorded['commit']}^{{commit}}").returncode:
        pytest.skip("shallow checkout without the pilot's closure commit")
    failures, _ = cp.verify_closure(root, cp.CLOSURES / "mc-50668-6-holy-hps-alliance.json")
    assert failures == [
        "tests/golden/raids/closures/mc-50668-6-holy-hps-alliance.json: source_review: "
        "tests/golden/raids/geddon-source-review.json does not exist at 5bf85e676e89"
    ]
