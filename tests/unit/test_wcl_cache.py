"""Immutable acquisition cache: whole-file no-clobber publication, verified reads,
OS-released locks, contained paths. Data written here is synthetic."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from necropsy.wcl.cache import (
    Cache,
    CacheBusy,
    CacheConflict,
    CacheCorrupt,
    CacheError,
    CacheUnsupported,
    FightKey,
    StreamKey,
    UnsafeKey,
    item_lock,
    publish,
)
from necropsy.wcl.sites import SITES, VANILLA, Site

IDENTITY: dict[str, Any] = {
    "site": VANILLA.host,
    "code": "AbC123",
    "revision": 4,
    "fight": 7,
    "actor_id": 3,
    "role": "player",
    "direction": "source",
    "start_time": 0.0,
    "end_time": 100.0,
    "data_type": "All",
    "limit": 10000,
    "include_resources": True,
    "translate": True,
    "query_version": 1,
    "endpoint": "client",
}


def _key(**over: Any) -> StreamKey:
    fight = FightKey(VANILLA, "AbC123", 4, 7)
    base: dict[str, Any] = {"fight": fight, "role": "player", "actor_id": 3, "direction": "source"}
    base.update(over)
    return StreamKey(**base)


def _page(n: int, cursor: Any = None) -> dict[str, Any]:
    return {"data": [{"timestamp": n, "type": "cast"}] * n, "nextPageTimestamp": cursor}


@pytest.mark.parametrize(
    "code",
    ["../x", "a/b", "C:", "a\\b", "", "x" * 33, "abc\0", "ab cd", "ÃƒÂ¤", 5, "AbC123\n", "Ab\tC"],
)
def test_hostile_report_codes_are_refused(code: Any) -> None:
    with pytest.raises(UnsafeKey):
        FightKey(VANILLA, code, 1, 1)


@pytest.mark.parametrize(
    ("revision", "fight"), [(-1, 1), (True, 1), (1.0, 1), (None, 1), (1, 0), (1, -3), (1, True)]
)
def test_revision_and_fight_must_be_genuine_integers(revision: Any, fight: Any) -> None:
    with pytest.raises(UnsafeKey):
        FightKey(VANILLA, "AbC", revision, fight)


def test_only_the_canonical_supported_site_is_accepted() -> None:
    with pytest.raises(UnsafeKey):
        FightKey(SITES["fresh.warcraftlogs.com"], "AbC", 1, 1)
    with pytest.raises(UnsafeKey):
        FightKey(Site("vanilla", "evil.example", supported=True), "AbC", 1, 1)
    with pytest.raises(UnsafeKey):
        _key(role="boss")
    with pytest.raises(UnsafeKey):
        _key(direction="both")
    with pytest.raises(UnsafeKey):
        _key(actor_id=0)


def test_publish_never_replaces_and_reuses_identical_bytes(tmp_path: Path) -> None:
    target = tmp_path / "f.json"
    assert publish(target, b"one") == "published"
    assert publish(target, b"one") == "reused"
    with pytest.raises(CacheConflict):
        publish(target, b"two")
    assert target.read_bytes() == b"one"
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


def test_publish_without_hard_links_refuses_rather_than_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_links(src: Any, dst: Any) -> None:
        raise OSError(1, "Operation not permitted")

    monkeypatch.setattr(os, "link", no_links)
    with pytest.raises(CacheUnsupported):
        publish(tmp_path / "f.json", b"x")
    assert not (tmp_path / "f.json").exists()


def test_streams_round_trip_and_verify_identity(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    written = store.write_stream(_key(), IDENTITY, [_page(2, 10.0), _page(1)])
    assert [len(p["data"]) for p in written.pages] == [2, 1]
    again = store.read_stream(_key(), IDENTITY)
    assert again is not None and again.pages == written.pages
    with pytest.raises(CacheConflict):
        store.read_stream(_key(), {**IDENTITY, "end_time": 200.0})
    # A completed stream is reused, never rewritten, even when asked again.
    store.write_stream(_key(), IDENTITY, [_page(9)])
    assert store.read_stream(_key(), IDENTITY).pages == written.pages  # type: ignore[union-attr]


def test_a_failing_fetch_leaves_no_marker_and_a_retry_completes(tmp_path: Path) -> None:
    store = Cache(tmp_path)

    def broken() -> Any:
        yield _page(1, 5.0)
        raise RuntimeError("connection dropped")

    with pytest.raises(RuntimeError):
        store.write_stream(_key(), IDENTITY, broken())
    assert store.read_stream(_key(), IDENTITY) is None
    done = store.write_stream(_key(), IDENTITY, [_page(3)])
    assert [len(p["data"]) for p in done.pages] == [3]
    folder = tmp_path / "vanilla" / "AbC123" / "r4" / "fight_7" / "client_player_3_source"
    assert sorted(p.name for p in folder.iterdir()) == ["page_001.json", "stream.json"]


def test_a_crash_before_the_marker_link_publishes_nothing_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Cache(tmp_path)
    real = os.link

    def die_on_marker(src: Any, dst: Any) -> None:
        if str(dst).endswith("stream.json"):
            raise KeyboardInterrupt
        real(src, dst)

    monkeypatch.setattr(os, "link", die_on_marker)
    with pytest.raises(KeyboardInterrupt):
        store.write_stream(_key(), IDENTITY, [_page(1)])
    monkeypatch.setattr(os, "link", real)
    assert store.read_stream(_key(), IDENTITY) is None
    assert store.write_stream(_key(), IDENTITY, [_page(1)]).pages[0]["data"]


def test_tampered_pages_are_detected_on_read(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    store.write_stream(_key(), IDENTITY, [_page(2)])
    page = (
        tmp_path
        / "vanilla"
        / "AbC123"
        / "r4"
        / "fight_7"
        / "client_player_3_source"
        / "page_001.json"
    )
    page.write_bytes(page.read_bytes().replace(b"cast", b"heal"))
    with pytest.raises(CacheCorrupt):
        store.read_stream(_key(), IDENTITY)


def test_a_malformed_marker_is_never_complete(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    store.write_stream(_key(), IDENTITY, [_page(1)])
    folder = tmp_path / "vanilla" / "AbC123" / "r4" / "fight_7" / "client_player_3_source"
    marker = folder / "stream.json"
    record = json.loads(marker.read_bytes())
    marker.unlink()
    marker.write_bytes(b"{")
    with pytest.raises(CacheCorrupt):
        store.read_stream(_key(), IDENTITY)
    marker.unlink()
    marker.write_bytes(json.dumps({**record, "terminal": False}).encode())
    with pytest.raises(CacheCorrupt):
        store.read_stream(_key(), IDENTITY)


def _bundle_record(revision: int = 4, **over: Any) -> dict[str, Any]:
    return {
        "endpoint": "client",
        "report": {"code": "AbC123", "revision": revision, "fights": [{"id": 7}], **over},
    }


def test_report_generations_change_without_replacing_prior_bytes(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    key = FightKey(VANILLA, "AbC123", 4, 7)
    first = store.put_bundle(key, _bundle_record())
    assert store.put_bundle(key, _bundle_record()) == first
    second = store.put_bundle(key, _bundle_record(title="changed"))
    assert first != second
    newer = FightKey(VANILLA, "AbC123", 5, 7)
    store.put_bundle(newer, _bundle_record(5))
    assert store.get_bundle(key, "client", first) == _bundle_record()
    assert store.get_bundle(key, "client", second) == _bundle_record(title="changed")


def test_endpoint_namespaces_coexist_and_are_bound_to_identities(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    client_key, user_key = _key(), _key(endpoint="user")
    store.write_stream(client_key, IDENTITY, [_page(1)])
    user_identity = {**IDENTITY, "endpoint": "user"}
    store.write_stream(user_key, user_identity, [_page(2)])
    assert len(store.read_stream(client_key, IDENTITY).pages[0]["data"]) == 1  # type: ignore[union-attr]
    assert len(store.read_stream(user_key, user_identity).pages[0]["data"]) == 2  # type: ignore[union-attr]
    with pytest.raises(UnsafeKey):
        store.read_stream(user_key, IDENTITY)
    with pytest.raises(UnsafeKey):
        _key(endpoint="../user")
    first = store.put_bundle(client_key.fight, _bundle_record())
    user_record = {**_bundle_record(), "endpoint": "user"}
    second = store.put_bundle(user_key.fight, user_record)
    assert store.get_bundle(client_key.fight, "client", first) == _bundle_record()
    assert store.get_bundle(user_key.fight, "user", second) == user_record


def test_old_cache_format_is_refused_without_modifying_it(tmp_path: Path) -> None:
    marker = tmp_path / "cache-format.json"
    marker.write_text('{"cache_format":1}', encoding="utf-8")
    data = tmp_path / "old-data.json"
    data.write_bytes(b"retained")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(CacheError, match="use a new cache directory"):
        Cache(tmp_path)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_report_set_reads_require_the_exact_generation(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    key = _key().fight
    report = _bundle_record()["report"]
    first = store.put_report_set(key, (7,), "client", report)
    second = store.put_report_set(key, (7,), "client", {**report, "title": "new"})
    assert first != second
    assert store.get_report_set(key, (7,), "client", first)["report"] == report  # type: ignore[index]
    assert store.get_report_set(key, (7,), "user", first) is None
    path = next(tmp_path.rglob(f"report_set_client_{first}.json"))
    path.unlink()
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(CacheCorrupt, match="generation digest"):
        store.get_report_set(key, (7,), "client", first)
    assert store.get_report_set(key, (7,), "client", second) is not None


def test_cache_files_hold_no_credentials(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    store.write_stream(_key(), IDENTITY, [_page(1)])
    store.put_bundle(FightKey(VANILLA, "AbC123", 4, 7), _bundle_record())
    blob = b"".join(p.read_bytes() for p in tmp_path.rglob("*") if p.is_file())
    for sentinel in (b"Bearer", b"Authorization", b"access_token", b"client_secret"):
        assert sentinel not in blob


def _junction(link: Path, target: Path) -> bool:
    if sys.platform == "win32":
        import _winapi

        _winapi.CreateJunction(str(target), str(link))
        return True
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        return False
    return True


def test_links_inside_the_cache_are_refused(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    store = Cache(root)
    if not _junction(root / "vanilla", outside):
        pytest.skip("cannot create a directory link here")
    with pytest.raises(UnsafeKey):
        store.write_stream(_key(), IDENTITY, [_page(1)])
    assert list(outside.iterdir()) == []


_HOLDER = """
import sys, time
from pathlib import Path
from necropsy.wcl.cache import item_lock
with item_lock(Path(sys.argv[1])):
    print("locked", flush=True)
    time.sleep(120)
"""


def test_a_killed_writer_releases_its_lock(tmp_path: Path) -> None:
    lock = tmp_path / "item.lock"
    child = subprocess.Popen(
        [sys.executable, "-c", _HOLDER, str(lock)], stdout=subprocess.PIPE, text=True
    )
    try:
        assert child.stdout is not None and child.stdout.readline().strip() == "locked"
        with pytest.raises(CacheBusy), item_lock(lock):
            pass
    finally:
        child.kill()  # TerminateProcess / SIGKILL: no finally runs in the child
        child.wait(timeout=30)
    deadline = time.monotonic() + 10
    while True:
        try:
            with item_lock(lock):
                break
        except CacheBusy:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.1)
    assert lock.exists()


def test_page_hashes_cover_exact_published_bytes(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    store.write_stream(_key(), IDENTITY, [_page(1)])
    folder = tmp_path / "vanilla" / "AbC123" / "r4" / "fight_7" / "client_player_3_source"
    record = json.loads((folder / "stream.json").read_bytes())
    data = (folder / "page_001.json").read_bytes()
    assert record["pages"][0]["sha256"] == hashlib.sha256(data).hexdigest()
    assert record["identity"] == IDENTITY


@pytest.mark.parametrize(
    ("pages", "reason"),
    [
        ([], "at least one page"),
        ([_page(1, 10.0)], "terminal"),
        ([{"data": None, "nextPageTimestamp": None}], "list of events"),
        ([{"data": [1], "nextPageTimestamp": None}], "list of events"),
        ([{"data": []}], "events page"),
        ([_page(1, 10.0), _page(1, 10.0), _page(1)], "forward"),
        ([_page(1, 0.0), _page(1)], "forward"),
        ([_page(1, 101.0), _page(1)], "forward"),
        ([_page(1, True), _page(1)], "forward"),
        ([_page(1), _page(1)], "follows the terminal"),
    ],
)
def test_the_cache_itself_refuses_incomplete_pagination(
    tmp_path: Path, pages: list[Any], reason: str
) -> None:
    store = Cache(tmp_path)
    with pytest.raises(CacheCorrupt, match=reason):
        store.write_stream(_key(), IDENTITY, pages)
    assert store.read_stream(_key(), IDENTITY) is None


def test_an_empty_terminal_page_is_a_complete_stream(tmp_path: Path) -> None:
    done = Cache(tmp_path).write_stream(_key(), IDENTITY, [{"data": [], "nextPageTimestamp": None}])
    assert done.pages[0]["data"] == [] and not done.reused


@pytest.mark.parametrize(
    "change",
    [
        {"code": "DIFFERENT"},
        {"actor_id": 999},
        {"role": "pet"},
        {"direction": "target"},
        {"revision": 5},
        {"site": "fresh.warcraftlogs.com"},
        {"revision": True},
        {"fight": 7.0},
        {"translate": 1},
        {"start_time": float("nan")},
        {"start_time": 50.0, "end_time": 50.0},
        {"data_type": "Casts"},
        {"endpoint": "admin"},
        {"limit": 0},
    ],
)
def test_identity_must_be_the_keys_complete_request(tmp_path: Path, change: dict[str, Any]) -> None:
    store = Cache(tmp_path)
    with pytest.raises(UnsafeKey):
        store.write_stream(_key(), {**IDENTITY, **change}, [_page(1)])
    assert not (tmp_path / "vanilla").exists()


def test_identity_needs_every_field_and_no_extras(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    partial = {k: v for k, v in IDENTITY.items() if k != "endpoint"}
    with pytest.raises(UnsafeKey):
        store.write_stream(_key(), partial, [_page(1)])
    with pytest.raises(UnsafeKey):
        store.read_stream(_key(), {**IDENTITY, "fetched_at": "now"})


def test_a_reread_marker_is_compared_type_sensitively(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    store.write_stream(_key(), IDENTITY, [_page(1)])
    folder = tmp_path / "vanilla" / "AbC123" / "r4" / "fight_7" / "client_player_3_source"
    marker = folder / "stream.json"
    record = json.loads(marker.read_bytes())
    record["identity"]["start_time"] = 0  # int where the request has 0.0
    marker.unlink()
    marker.write_bytes(json.dumps(record).encode())
    with pytest.raises(CacheConflict):
        store.read_stream(_key(), IDENTITY)


def test_cleanup_removes_only_its_own_files(tmp_path: Path) -> None:
    store = Cache(tmp_path)
    folder = tmp_path / "vanilla" / "AbC123" / "r4" / "fight_7" / "client_player_3_source"
    folder.mkdir(parents=True)
    keep = ["page_notes.txt", "notes.tmp", ".stream.json.tmp", "page_1.json"]
    for name in keep:
        (folder / name).write_text("x")
    (folder / "foreign").mkdir()
    (folder / "page_007.json").write_text("stale")
    (folder / ".page_001.json.123.deadbeef.tmp").write_text("stale")
    store.write_stream(_key(), IDENTITY, [_page(1)])
    names = sorted(p.name for p in folder.iterdir())
    assert names == sorted([*keep, "foreign", "page_001.json", "stream.json"])


def _file_link(link: Path, target: Path) -> bool:
    try:
        link.symlink_to(target)
    except OSError:
        return False
    return True


@pytest.mark.parametrize("which", ["bundle", "stream"])
def test_lock_files_that_are_links_are_refused(tmp_path: Path, which: str) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.lock"
    store = Cache(root)
    fight = root / "vanilla" / "AbC123" / "r4" / "fight_7"
    fight.mkdir(parents=True)
    lock = fight / (".report.lock" if which == "bundle" else ".client_player_3_source.lock")
    if not _file_link(lock, outside):
        pytest.skip("cannot create a file symlink here")
    with pytest.raises(UnsafeKey):
        if which == "bundle":
            store.put_bundle(FightKey(VANILLA, "AbC123", 4, 7), _bundle_record())
        else:
            store.write_stream(_key(), IDENTITY, [_page(1)])
    assert not outside.exists()


def test_published_names_that_are_links_are_refused(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    target = tmp_path / "final.json"
    if not _file_link(target, outside):
        pytest.skip("cannot create a file symlink here")
    with pytest.raises(UnsafeKey):
        publish(target, b"x")
    assert not outside.exists()
