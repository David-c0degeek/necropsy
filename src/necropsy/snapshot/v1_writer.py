"""Write a finalized live acquisition as a verified archive (no network here).

Actor-only captures retain format v1. Encounter-context acquisitions use format
v2 with additional certified whole-fight and filtered-critical streams.

Input is a finalized acquisition (`wcl.acquire.finalize_reports` has recorded
one combined report per code) and the verified cache it was written to. Only
complete entries become fights. Event pages are copied byte for byte from the
cache after verification; their digests go into the provenance the reader
checks. A pet list is written only when pet ownership was proven; unknown pets
leave it out so the reader reports pet discovery as missing.

The archive, its entries manifest and a SHA-256 file are published as one set:
every target is checked first, each file appears whole without replacing
anything, and a failure removes the files this attempt published.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import os
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from necropsy.analysis.roles import CLASS_NAMES, ranking_policy
from necropsy.raids import RAIDS, raid_for_zone
from necropsy.rules import load_rules
from necropsy.snapshot.archive import (
    ArchiveError,
    EntryDigest,
    EntryOrigin,
    VerifiedArchive,
    format_entries_manifest,
    parse_entries_manifest,
)
from necropsy.snapshot.model import SnapshotError
from necropsy.snapshot.v1 import FORMAT_VERSION, KIND, MARKER, open_snapshot
from necropsy.wcl.acquire import (
    Acquisition,
    BossAcquisition,
    Entry,
    discover_pets,
    faction_verdict,
    fight_pets,
    player_actor,
)
from necropsy.wcl.cache import Cache, StreamKey, canonical_bytes, is_link, item_lock, publish

GAME = "classic_era"
COHORT = "same-faction-deep"
_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

LIVE_DESCRIPTION = (
    "Live snapshot: comparisons use up to five acquired same-faction fights per boss. "
    "Medians need three known values. Metadata-only ranking rows are retained as context, "
    "not complete event analyses. An overall #1 from the other faction is included only "
    "when requested and verified. Coverage records missing or unresolved data."
)


class WriteError(Exception):
    """The acquisition cannot be written as a snapshot; nothing was published."""


def safe_name(text: str) -> str:
    """ASCII-safe path part for a display name (letters, digits, '-', '_')."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", folded).strip("_")
    return cleaned[:40] or "x"


def _boss_names(zone: str | None = None) -> dict[int, str]:
    raids = RAIDS if zone is None else (next(r for r in RAIDS if r.slug == zone),)
    return {
        int(e["id"]): str(e["name"])
        for raid in raids
        for e in load_rules(GAME, f"zones/{raid.slug}")["encounters"]
    }


@dataclass(frozen=True)
class Written:
    archive: Path
    entries: Path
    sha256_file: Path
    sha256: str
    fights: int
    streams: int


def _participant(boss: BossAcquisition, e: Entry, name: str) -> dict[str, Any]:
    if e.kind == "subject":
        row = (boss.subject_pick.row if boss.subject_pick else None) or {}
        position = None
    else:
        row = e.candidate.raw if e.candidate is not None else {}
        position = e.candidate.position if e.candidate is not None else None
    amount = row.get("amount")
    duration = row.get("duration")
    if isinstance(amount, float) and not math.isfinite(amount):
        raise WriteError(f"{e.name}'s ranking amount is not finite")
    return {
        "kind": "you" if e.kind == "subject" else "top",
        "boss": name,
        "encounterID": boss.encounter_id,
        "player": e.name,
        "server": e.server,
        "leaderboardPosition": position,
        "total": float(amount)
        if isinstance(amount, (int, float)) and not isinstance(amount, bool)
        else None,
        "duration": duration
        if isinstance(duration, int) and not isinstance(duration, bool)
        else None,
        "spec": row.get("spec") if isinstance(row.get("spec"), str) else None,
    }


def _coverage_entry(e: Entry | None) -> dict[str, Any] | None:
    if e is None:
        return None
    return {
        "kind": e.kind,
        "player": e.name,
        "report": e.report_code,
        "fight": e.fight_id,
        "status": e.status,
        "reason": e.reason,
        "pets": e.pets,
        "confirmed_pets": e.pet_ids,
        "combatant_context_reason": e.combatant_context_reason,
        "combatant_context_sha256": None
        if e.combatant_context is None
        else hashlib.sha256(canonical_bytes(e.combatant_context)).hexdigest(),
        "pets_reason": e.pets_reason,
        "generations": e.generations,
        "bundle_generation": None
        if e.bundle_key is None or e.bundle_sha256 is None
        else {
            "sha256": e.bundle_sha256,
            "report": e.bundle_key.code,
            "fight": e.bundle_key.fight,
            "revision": e.bundle_key.revision,
        },
        "verdict": None
        if e.verdict is None
        else {
            "status": e.verdict.status,
            "faction": None if e.verdict.faction is None else e.verdict.faction.value,
            "reason": e.verdict.reason,
        },
    }


def _check_binding(acquisition: Acquisition, boss: BossAcquisition, e: Entry) -> None:
    """Boss key, context, entry and bundle must all describe the same request."""
    context = acquisition.context
    key, bundle = boss.key, e.bundle_key
    assert context is not None and key is not None and bundle is not None
    assert context.partition is not None and context.faction.value is not None
    if key.encounter.value != boss.encounter_id:
        raise WriteError(f"boss {boss.encounter_id} has another encounter's key")
    if key.partition.value != context.partition.id or key.zone.value != context.zone_id:
        raise WriteError(f"boss {boss.encounter_id} key is not the character's zone/partition")
    if key.faction.value != context.faction.value.value or key.site.value != bundle.site.host:
        raise WriteError(f"boss {boss.encounter_id} key is not the character's faction/site")
    if (bundle.code, bundle.fight) != (e.report_code, e.fight_id):
        raise WriteError(f"entry {e.name} bundle is another report or fight")
    need = {("player", e.actor_id, d) for d in ("source", "target")}
    need |= {("pet", pid, d) for pid in e.pet_ids for d in ("source", "target")}
    have = [(s.role, s.actor_id, s.direction) for s in e.streams]
    if sorted(have) != sorted(need) or len(have) != len(set(have)):
        raise WriteError(f"entry {e.name} does not have exactly its player and pet streams")
    wanted_context = (
        {(role, None, "all") for role in ("encounter", "critical")}
        if acquisition.encounter_context
        else set()
    )
    found_context = [(s.role, s.actor_id, s.direction) for s in e.encounter_streams]
    if set(found_context) != wanted_context or len(found_context) != len(wanted_context):
        raise WriteError(f"entry {e.name} does not have its declared encounter scopes")
    rset = acquisition.reports.get(e.report_code)
    fight = None
    if rset is not None:
        fight = next(
            (
                f
                for f in rset.report.get("fights") or ()
                if isinstance(f, dict) and f.get("id") == e.fight_id
            ),
            None,
        )
    if fight is None:
        raise WriteError(f"entry {e.name} fight is not in its combined report")
    bounds = (fight.get("startTime"), fight.get("endTime"))
    for s in (*e.streams, *e.encounter_streams):
        if (s.identity.get("start_time"), s.identity.get("end_time")) != bounds:
            raise WriteError(f"a stream of {e.name} has other fight bounds than its report")
    for s in (*e.streams, *e.encounter_streams):
        ident = s.identity
        if (
            ident.get("code"),
            ident.get("revision"),
            ident.get("fight"),
            ident.get("endpoint"),
        ) != (bundle.code, bundle.revision, bundle.fight, acquisition.endpoint):
            raise WriteError(f"a stream of {e.name} belongs to another request")


def build_members(acquisition: Acquisition, store: Cache) -> dict[str, tuple[bytes, EntryOrigin]]:
    """Every archive member and its origin, deterministically, from verified data."""
    context = acquisition.context
    if context is None:
        raise WriteError("the acquisition has no resolved character context")
    if context.class_id.value not in CLASS_NAMES or context.zone_id not in {
        r.zone_id for r in RAIDS
    }:
        raise WriteError("the acquisition is not for a supported class and zone")
    if context.partition is None or context.faction.level != "observed":
        raise WriteError("the acquisition context has no partition or observed faction")
    requested = list(acquisition.requested)
    if not requested or len(set(requested)) != len(requested):
        raise WriteError("the acquisition has no valid requested boss list")
    if acquisition.requested and [b.encounter_id for b in acquisition.bosses] != list(
        acquisition.requested[: len(acquisition.bosses)]
    ):
        raise WriteError("the acquired bosses do not follow the requested order")
    names = _boss_names(raid_for_zone(context.zone_id).slug)
    members: dict[str, tuple[bytes, EntryOrigin]] = {}
    fights: dict[tuple[str, int], dict[str, Any]] = {}
    actor_dirs: dict[tuple[str, int, int], dict[str, Any]] = {}
    streams: list[dict[str, Any]] = []
    complete = acquisition.complete_entries()
    codes = {e.report_code for _, e in complete}
    if codes != set(acquisition.reports):
        raise WriteError("combined reports are missing; finalize the acquisition first")
    for code, rset in sorted(acquisition.reports.items()):
        cached = store.get_report_set(rset.key, rset.fight_ids, rset.endpoint, rset.sha256)
        if cached is None or cached["report"] != rset.report:
            raise WriteError(f"the combined report {code} is not the cached one")
        members[f"reports/{code}/bundle.json"] = (
            canonical_bytes({"reportData": {"report": rset.report}}),
            EntryOrigin.GENERATED,
        )
    for boss, e in complete:
        if (
            boss.key is None
            or e.bundle_key is None
            or e.bundle_sha256 is None
            or e.actor_id is None
        ):
            raise WriteError(f"entry {e.name} has no key")
        original = store.get_bundle(e.bundle_key, acquisition.endpoint, e.bundle_sha256)
        if original is None:
            raise WriteError(f"entry {e.name}'s exact report generation is missing")
        # Refuse a generation reference that no longer describes this verified entry.
        source_report = original["report"]
        if (
            player_actor(source_report, e.name, e.server, CLASS_NAMES[context.class_id.value])[0]
            != e.actor_id
        ):
            raise WriteError(f"entry {e.name}'s report generation has another actor")
        source_fight = next(
            (f for f in source_report.get("fights") or [] if f.get("id") == e.fight_id), None
        )
        if (
            source_report.get("revision") != e.bundle_key.revision
            or source_fight is None
            or source_fight.get("encounterID") != boss.encounter_id
            or fight_pets(source_report, source_fight, e.actor_id)[0] != e.pets
            or list(discover_pets(source_report, source_fight, e.actor_id).confirmed) != e.pet_ids
            or faction_verdict(source_report, e.actor_id, CLASS_NAMES[context.class_id.value])
            != e.verdict
        ):
            raise WriteError(f"entry {e.name}'s report generation differs from its evidence")
        members[f"reports/{e.report_code}/fight_{e.fight_id}.json"] = (
            canonical_bytes(original),
            EntryOrigin.ACQUIRED,
        )
        _check_binding(acquisition, boss, e)
        rset = acquisition.reports[e.report_code]
        if e.bundle_key.revision != rset.key.revision or e.fight_id not in rset.fight_ids:
            raise WriteError(f"entry {e.name} is not covered by the combined report")
        name = names.get(boss.encounter_id, f"encounter {boss.encounter_id}")
        fight = fights.setdefault(
            (e.report_code, e.fight_id),
            {"reportID": e.report_code, "fightID": e.fight_id, "participants": []},
        )
        reason = _participant(boss, e, name)
        fight["participants"].append(reason)
        actors = (rset.report.get("masterData") or {}).get("actors") or []
        by_id = {a.get("id"): a for a in actors if isinstance(a, dict)}
        player = by_id.get(e.actor_id)
        if player is None:
            raise WriteError(f"actor {e.actor_id} of {e.name} is not in the combined report")
        base = f"events/{e.report_code}/fight_{e.fight_id}/"
        key = (e.report_code, e.fight_id, e.actor_id)
        folder = f"{base}player_{e.actor_id}_{safe_name(e.name)}/"
        if e.combatant_context is not None:
            members[f"{folder}combatant_context.json"] = (
                canonical_bytes(e.combatant_context),
                EntryOrigin.GENERATED,
            )
        entry_dir = actor_dirs.setdefault(
            key,
            {
                "actor": player,
                "player": e.name,
                "reasons": [],
                "folder": folder,
                "pets": e.pets,
                "confirmed_pets": e.pet_ids,
            },
        )
        if entry_dir["pets"] != e.pets or entry_dir["confirmed_pets"] != e.pet_ids:
            raise WriteError(f"{e.name} in {e.report_code} fight {e.fight_id} has two pet lists")
        entry_dir["reasons"].append(reason)
        for record in (*e.streams, *e.encounter_streams):
            if record.role == "player":
                prefix = folder
            elif record.role in {"encounter", "critical"}:
                prefix = f"{base}encounter/"
            else:
                pet = by_id.get(record.actor_id) or {}
                prefix = f"{base}pet_{record.actor_id}_{safe_name(str(pet.get('name') or 'pet'))}/"
            stream_key = (e.report_code, e.fight_id, record.role, record.actor_id, record.direction)
            earlier = next((s for s in streams if s["key"] == stream_key), None)
            if earlier is not None:
                if earlier["identity"] != record.identity:
                    raise WriteError(f"stream {stream_key} has two different identities")
                continue
            pages = store.page_bytes(
                StreamKey(
                    e.bundle_key,
                    record.role,
                    record.actor_id,
                    record.direction,
                    acquisition.endpoint,
                ),
                record.identity,
            )
            digests = []
            page_kind = "critical" if record.role == "critical" else record.direction
            for n, data in enumerate(pages, 1):
                members[f"{prefix}{page_kind}_{n:03d}.json"] = (data, EntryOrigin.ACQUIRED)
                digests.append(hashlib.sha256(data).hexdigest())
            streams.append(
                {
                    "key": stream_key,
                    "pages": digests,
                    "identity": record.identity,
                    "meta": record.meta,
                }
            )
    for (code, fight_id, _actor), info in actor_dirs.items():
        folder = info["folder"]
        members[f"{folder}selection.json"] = (
            canonical_bytes(
                {"actor": info["actor"], "player": info["player"], "reasons": info["reasons"]}
            ),
            EntryOrigin.GENERATED,
        )
        if info["pets"] is not None or info["confirmed_pets"]:
            actors = (acquisition.reports[code].report.get("masterData") or {}).get("actors") or []
            pets = sorted(
                [
                    a
                    for a in actors
                    if isinstance(a, dict) and a.get("id") in info["confirmed_pets"]
                ],
                key=lambda a: a["id"],
            )
            filename = "pets.json" if info["pets"] is not None else "confirmed_pets.json"
            members[f"{folder}{filename}"] = (canonical_bytes(pets), EntryOrigin.GENERATED)
        _ = fight_id
    bosses = []
    for boss in acquisition.bosses:
        name = names.get(boss.encounter_id, f"encounter {boss.encounter_id}")
        if boss.selection is not None and boss.key is not None:
            doc = {
                "encounter": {"id": boss.encounter_id, "name": name},
                "partition": boss.key.partition.value,
                "pages": boss.selection.raw_pages,
            }
            members[f"leaderboards/{boss.encounter_id}_{safe_name(name)}.json"] = (
                canonical_bytes(doc),
                EntryOrigin.GENERATED,
            )
        if boss.subject_pick is not None and boss.key is not None:
            raw = boss.subject_raw
            decoded = raw
            if isinstance(raw, str):
                try:
                    decoded = json.loads(raw)
                except ValueError:
                    decoded = None
            doc = {
                "encounter": {"id": boss.encounter_id, "name": name},
                "partition": boss.key.partition.value,
                "character": context.name.value,
                "encounterRankings": decoded if isinstance(decoded, dict) else None,
            }
            if isinstance(raw, str):
                doc["encounterRankingsAsReturned"] = raw
            members[f"user_rankings/{boss.encounter_id}_{safe_name(name)}.json"] = (
                canonical_bytes(doc),
                EntryOrigin.GENERATED,
            )
        bosses.append(_boss_record(boss, name))
    attempted = {b.encounter_id for b in acquisition.bosses}
    for encounter in acquisition.requested:
        if encounter not in attempted:
            bosses.append(
                {
                    "encounter_id": encounter,
                    "boss": names.get(encounter, f"encounter {encounter}"),
                    "attempted": False,
                    "coverage": {
                        "complete": False,
                        "reasons": [f"not attempted: run stopped ({acquisition.stopped})"],
                    },
                }
            )
    limitations = [LIVE_DESCRIPTION]
    for b in bosses:
        for reason in b["coverage"]["reasons"]:
            limitations.append(f"{b['boss']}: {reason}")
    if acquisition.stopped:
        limitations.append(f"Acquisition stopped early: {acquisition.stopped}")
    assert context.partition is not None and context.faction.value is not None
    marker = {
        "kind": KIND,
        "formatVersion": 2 if acquisition.encounter_context else FORMAT_VERSION,
        "subject": {
            "id": context.character_id.value,
            "canonical_id": context.canonical_id.value,
            "name": context.name.value,
            "class_id": context.class_id.value,
            "server": context.server.value,
            "region": context.region.value,
            "faction": context.faction.value.value,
            **({"talent_tree": context.talent_tree} if context.talent_tree is not None else {}),
            **(
                {
                    "ranking_category": context.ranking_category,
                    "ranking_metric": ranking_policy(
                        context.class_id.value, context.ranking_category, context.ranking_metric
                    ).metric,
                }
                if context.class_id.value == 2 or context.ranking_category is not None
                else {}
            ),
        },
        "zone": {
            "id": context.zone_id,
            "name": context.zone_name.value or "",
            "partition": context.partition.id,
        },
        "cohort": COHORT,
        "top_n": int(load_rules(GAME, "benchmarks")["live_cohort"]["deep"]),
        "endpoint": acquisition.endpoint,
        "cross_faction": acquisition.cross_faction,
        **(
            {"metadata_order": list(acquisition.metadata_order)}
            if acquisition.metadata_order
            else {}
        ),
        **(
            {"comparison_order": list(acquisition.comparison_order)}
            if acquisition.comparison_order
            else {}
        ),
        "stopped": acquisition.stopped,
        "fights": [fights[k] for k in sorted(fights)],
        "bosses": bosses,
        "streams": [
            {
                "report": s["key"][0],
                "fight": s["key"][1],
                "role": s["key"][2],
                "actor_id": s["key"][3],
                "direction": s["key"][4],
                "pages": s["pages"],
                "identity": s["identity"],
                "meta": s["meta"],
            }
            for s in sorted(streams, key=lambda s: s["key"])
            if s["key"][2] in {"player", "pet"}
        ],
        **(
            {
                "encounter_streams": [
                    {
                        "report": s["key"][0],
                        "fight": s["key"][1],
                        "role": s["key"][2],
                        "actor_id": None,
                        "direction": "all",
                        "pages": s["pages"],
                        "identity": s["identity"],
                        "meta": s["meta"],
                    }
                    for s in sorted(streams, key=lambda s: s["key"])
                    if s["key"][2] in {"encounter", "critical"}
                ]
            }
            if acquisition.encounter_context
            else {}
        ),
        "report_sets": [
            {
                "report": code,
                "revision": rset.key.revision,
                "fight_ids": list(rset.fight_ids),
                "endpoint": rset.endpoint,
                "sha256": hashlib.sha256(canonical_bytes(rset.report)).hexdigest(),
                "cache_sha256": rset.sha256,
            }
            for code, rset in sorted(acquisition.reports.items())
        ],
        "limitations": limitations,
    }
    members[MARKER] = (canonical_bytes(marker), EntryOrigin.GENERATED)
    return members


def _boss_record(boss: BossAcquisition, name: str) -> dict[str, Any]:
    sel = boss.selection
    return {
        "encounter_id": boss.encounter_id,
        "boss": name,
        "attempted": True,
        "key": None
        if boss.key is None
        else {
            k: {"value": getattr(boss.key, k).value, "status": getattr(boss.key, k).status}
            for k in (
                *boss.key.__dataclass_fields__,
                *(("metric",) if boss.key.class_name.value == "Druid" else ()),
            )
        },
        "subject_pick": None
        if boss.subject_pick is None
        else {
            "report": boss.subject_pick.report_code,
            "fight": boss.subject_pick.fight_id,
            "rule": boss.subject_pick.rule,
            "notes": list(boss.subject_pick.notes),
        },
        "subject": _coverage_entry(boss.subject),
        "cohort": [_coverage_entry(e) for e in boss.cohort],
        "dropped": [
            {"player": d.candidate.name, "position": d.candidate.position, "reason": d.reason}
            for d in boss.dropped
        ],
        "metadata": [
            {
                "player": c.name,
                "position": c.position,
                "report": c.report_code,
                "fight": c.fight_id,
                "faction": c.faction.value,
                "faction_level": c.faction.level,
                "faction_source": c.faction.source,
                "faction_rule": c.faction.rule,
                "faction_note": c.faction.note,
            }
            for c in boss.metadata
        ],
        "selection": None
        if sel is None
        else {
            "leaderboard_captured_at": next(
                (p.get("captured_at") for p in sel.raw_pages if p.get("page") == 1), None
            ),
            "stop": sel.stop,
            "pages": [{"page": p.page, "rows": p.rows} for p in sel.pages],
            "other_faction": sel.other_faction,
            "duplicates": sel.duplicates,
            "unresolved": [c.name for c in sel.unresolved],
            "inaccessible": [c.name for c in sel.inaccessible],
            "contradicted": [c.name for c in sel.contradicted],
            "displaced": [c.name for c in sel.displaced],
            "verdicts": [
                {
                    "position": pos,
                    "status": v.status,
                    "faction": None if v.faction is None else v.faction.value,
                    "reason": v.reason,
                }
                for pos, v in sorted(sel.verdicts.items())
            ],
        },
        "cross_faction": _coverage_entry(boss.cross_faction),
        "cross_faction_applicable": boss.cross_faction_applicable,
        "cross_faction_reason": boss.cross_faction_reason,
        "coverage": boss.coverage,
    }


def archive_bytes(members: dict[str, tuple[bytes, EntryOrigin]]) -> bytes:
    """A deterministic ZIP: sorted names, fixed timestamps, one compression level."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, members[name][0], compresslevel=9)
    return buffer.getvalue()


def _validate(out_dir: Path, stem: str, data: bytes, entries: str) -> None:
    """Open the finished archive with the live reader; any refusal publishes nothing."""
    check = out_dir / f".{stem}.{os.getpid()}.{os.urandom(4).hex()}.check.zip"
    try:
        with check.open("xb") as handle:
            handle.write(data)
        with VerifiedArchive(check, entries=parse_entries_manifest(entries)) as archive:
            open_snapshot(archive)
    except (SnapshotError, ArchiveError) as error:
        raise WriteError(f"the snapshot would not read back: {error}") from None
    finally:
        with contextlib.suppress(FileNotFoundError):
            check.unlink()


def write_snapshot(acquisition: Acquisition, store: Cache, out_dir: Path, stem: str) -> Written:
    """Publish `<stem>.zip`, `<stem>.entries` and `<stem>.sha256` in `out_dir`, or nothing."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", stem) or stem.startswith("."):
        raise WriteError(f"unsafe snapshot name {stem!r}")
    if not out_dir.is_dir() or is_link(out_dir):
        raise WriteError(f"{out_dir} must be an existing, real directory (not a link)")
    with item_lock(out_dir / f".{stem}.lock"):
        return _write_locked(acquisition, store, out_dir, stem)


def _write_locked(acquisition: Acquisition, store: Cache, out_dir: Path, stem: str) -> Written:
    targets = [out_dir / f"{stem}.zip", out_dir / f"{stem}.entries", out_dir / f"{stem}.sha256"]
    for target in targets:
        if os.path.lexists(target):
            raise WriteError(f"{target} already exists; snapshots are never replaced")
    members = build_members(acquisition, store)
    data = archive_bytes(members)
    digest = hashlib.sha256(data).hexdigest()
    entries = format_entries_manifest(
        EntryDigest(name, len(body), hashlib.sha256(body).hexdigest(), origin)
        for name, (body, origin) in members.items()
    )
    _validate(out_dir, stem, data, entries)
    contents = [data, entries.encode("utf-8"), f"{digest}  {stem}.zip\n".encode()]
    published: list[tuple[Path, int, int, bytes]] = []
    try:
        for target, body in zip(targets, contents, strict=True):
            if publish(target, body) != "published":
                raise WriteError(f"{target} appeared while writing")
            info = target.lstat()
            published.append((target, info.st_ino, info.st_dev, body))
    except BaseException:
        # Remove only files this attempt published that still are those files: same
        # inode and device (an inode number alone can be reused by a replacement on
        # some filesystems) and the same bytes.
        for path, ino, dev, body in published:
            with contextlib.suppress(FileNotFoundError):
                now = path.lstat()
                if (
                    (now.st_ino, now.st_dev) == (ino, dev)
                    and not is_link(path)
                    and path.read_bytes() == body
                ):
                    path.unlink()
        raise
    marker = json.loads(members[MARKER][0])
    return Written(
        targets[0],
        targets[1],
        targets[2],
        digest,
        len(marker["fights"]),
        len(marker["streams"]) + len(marker.get("encounter_streams", ())),
    )


__all__ = [
    "LIVE_DESCRIPTION",
    "WriteError",
    "Written",
    "archive_bytes",
    "build_members",
    "safe_name",
    "write_snapshot",
]
