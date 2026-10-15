"""Reader for live snapshots Necropsy acquired itself ("snapshot v1").

Below the top level a v1 archive uses the v6 member layout, so the v6 reader
does the reading; only the top level differs. Instead of the export's
profile/manifest/selection files there is one `necropsy-snapshot.json`,
validated strictly: subject (from the resolved character), zone and partition,
the selected fights with their participants, every requested boss with its
acquisition coverage, and the page digests that the acquisition cache
certified for every stream. An archive with that file is always read as v1;
a malformed one is an error, never read as v6 instead.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from necropsy.analysis.evidence import Faction
from necropsy.analysis.roles import CLASS_NAMES, ranking_policy
from necropsy.rules import load_rules
from necropsy.snapshot.archive import VerifiedArchive
from necropsy.snapshot.model import (
    ActorRole,
    Character,
    Participant,
    SelectedFight,
    SnapshotDescriptor,
    SnapshotError,
    SnapshotScope,
    Zone,
)
from necropsy.snapshot.v0 import V0Snapshot, _StreamKey
from necropsy.wcl.acquire import faction_verdict, fight_pets, player_actor
from necropsy.wcl.cache import (
    CacheError,
    FightKey,
    StreamKey,
    canonical_bytes,
    check_identity,
    check_pages,
)
from necropsy.wcl.context import SUPPORTED_ZONE_ID
from necropsy.wcl.fetch import EVENTS_LIMIT, QUERY_VERSION
from necropsy.wcl.sites import VANILLA

GAME, ZONE = "classic_era", "naxxramas"
COHORT = "same-faction-deep"
_FACTIONS = {"Alliance": Faction.ALLIANCE, "Horde": Faction.HORDE}
MARKER = "necropsy-snapshot.json"
KIND = "necropsy.live-snapshot"
FORMAT_VERSION = 1
FORMAT = "necropsy-live-snapshot-v1"


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class LiveSubject(_Strict):
    id: int = Field(gt=0)
    canonical_id: int | None = None
    name: str = Field(min_length=1)
    class_id: int
    server: str = Field(min_length=1)
    region: str = Field(min_length=1)
    faction: Literal["Alliance", "Horde"]
    ranking_category: str | None = None
    ranking_metric: str | None = None


class LiveZone(_Strict):
    id: int
    name: str
    partition: int


class LiveParticipant(_Strict):
    kind: Literal["you", "top"]
    boss: str
    encounterID: int
    player: str = Field(min_length=1)
    server: str | None
    leaderboardPosition: int | None = Field(default=None, gt=0)
    total: float | None
    duration: int | None
    spec: str | None


class LiveFight(_Strict):
    reportID: str = Field(min_length=1)
    fightID: int = Field(gt=0)
    participants: tuple[LiveParticipant, ...] = Field(min_length=1)


class LiveStream(_Strict):
    report: str
    fight: int
    role: Literal["player", "pet"]
    actor_id: int = Field(gt=0)
    direction: Literal["source", "target"]
    pages: tuple[str, ...] = Field(min_length=1)
    """SHA-256 of every page member, in order, as the cache certified them."""
    identity: dict[str, Any]
    """The canonical request the cache marker certified (no credentials)."""
    meta: dict[str, Any]
    """Fetch provenance; points are account-wide readings, never an exact stream cost."""


class LiveReportSet(_Strict):
    report: str
    revision: int = Field(ge=0)
    fight_ids: tuple[int, ...] = Field(min_length=1)
    endpoint: Literal["client", "user"]
    sha256: str
    cache_sha256: str | None = None
    """Optional full digest of the exact cached generation (older v1 archives omit it)."""
    """SHA-256 of the canonical acquired report object wrapped in reports/<code>/bundle.json."""


class LiveSnapshotFile(_Strict):
    kind: Literal["necropsy.live-snapshot"]
    formatVersion: int = Field(ge=FORMAT_VERSION, le=FORMAT_VERSION)
    subject: LiveSubject
    zone: LiveZone
    cohort: str
    top_n: int = Field(gt=0)
    endpoint: Literal["client", "user"]
    cross_faction: bool
    comparison_order: tuple[int, ...] = ()
    metadata_order: tuple[int, ...] = ()
    stopped: str | None
    fights: tuple[LiveFight, ...]
    bosses: tuple[dict[str, Any], ...]
    streams: tuple[LiveStream, ...]
    report_sets: tuple[LiveReportSet, ...]
    limitations: tuple[str, ...]


class V1Snapshot(V0Snapshot):
    """`SnapshotReader` over a live snapshot archive."""

    _top_level = frozenset({MARKER})

    def __init__(self, archive: VerifiedArchive) -> None:
        self._live: LiveSnapshotFile | None = None
        super().__init__(archive)
        self._prove_actors()
        self._prove_streams()

    def _file(self) -> LiveSnapshotFile:
        if self._live is None:
            try:
                self._live = LiveSnapshotFile.model_validate_json(self._archive.read_bytes(MARKER))
            except ValidationError as error:
                raise SnapshotError(f"{MARKER} is not a valid live snapshot: {error}") from None
        return self._live

    def _canonical(self, live: LiveSnapshotFile) -> None:
        """The snapshot must describe the supported class and cohort it claims to be."""
        if live.subject.class_id not in CLASS_NAMES:
            raise SnapshotError("the live snapshot subject class is unsupported")
        if live.zone.id != SUPPORTED_ZONE_ID:
            raise SnapshotError(f"zone {live.zone.id} is not supported")
        if live.cohort != COHORT:
            raise SnapshotError(f"unknown live cohort {live.cohort!r}")
        if live.top_n != int(load_rules(GAME, "benchmarks")["live_cohort"]["deep"]):
            raise SnapshotError("top_n differs from the live cohort rule")
        names = {
            int(e["id"]): str(e["name"]) for e in load_rules(GAME, f"zones/{ZONE}")["encounters"]
        }
        for f in live.fights:
            for p in f.participants:
                if names.get(p.encounterID) != p.boss:
                    raise SnapshotError(f"{p.boss!r} is not encounter {p.encounterID}")
        for b in live.bosses:
            encounter = b.get("encounter_id")
            if not isinstance(encounter, int) or names.get(encounter) != b.get("boss"):
                raise SnapshotError(f"boss record {b.get('boss')!r} is not a supported encounter")
        if live.subject.class_id == 2 or live.subject.ranking_category is not None:
            self._check_selected_category(live)
        if live.metadata_order:
            expected_metadata = tuple(b["encounter_id"] for b in live.bosses)[
                : len(live.metadata_order)
            ]
            if (
                live.subject.class_id != 2 and live.subject.ranking_category is None
            ) or live.metadata_order != expected_metadata:
                raise SnapshotError("metadata order differs from requested spec encounter order")
            sources = {
                document["encounter"]["id"]
                for source, document in self.rankings()
                if source.startswith("leaderboards/")
                and any(p.get("page") == 1 for p in document.get("pages", []))
            }
            if not set(live.metadata_order) <= sources:
                raise SnapshotError("metadata prefetch provenance has no saved ranking rows")
        if live.comparison_order:
            order = {eid: i for i, eid in enumerate(names)}
            expected = tuple(
                b["encounter_id"]
                for b in sorted(
                    (b for b in live.bosses if b.get("attempted") is not False),
                    key=lambda b: (
                        (b.get("subject") or {}).get("status") == "complete",
                        order[b["encounter_id"]],
                    ),
                )
            )
            if (
                live.subject.class_id != 2 and live.subject.ranking_category is None
            ) or live.comparison_order != expected:
                raise SnapshotError(
                    "comparison order differs from the selected-spec acquisition policy"
                )

    def _check_selected_category(self, live: LiveSnapshotFile) -> None:
        category = live.subject.ranking_category
        if category is None:
            categories = {
                ((b.get("key") or {}).get("spec") or {}).get("value")
                for b in live.bosses
                if b.get("key")
            }
            if len(categories) == 1:
                category = categories.pop()
        metric = live.subject.ranking_metric
        if metric is None:
            metrics = {
                ((b.get("key") or {}).get("metric") or {}).get("value")
                for b in live.bosses
                if b.get("key") and "metric" in b["key"]
            }
            if len(metrics) == 1:
                metric = metrics.pop()
        try:
            policy = ranking_policy(live.subject.class_id, category, metric)
        except ValueError as error:
            raise SnapshotError(str(error)) from None
        expected = {
            "class_name": policy.class_name,
            "spec": policy.category,
            "role": policy.role,
            "metric": policy.metric,
        }
        for boss in live.bosses:
            key = boss.get("key")
            if key is None:
                continue
            for name, value in expected.items():
                if name == "metric" and name not in key:
                    # Early category snapshots encode metric through the verified category.
                    continue
                dimension = key.get(name) or {}
                if dimension.get("value") != value or dimension.get("status") != "enforced":
                    raise SnapshotError(f"selected-spec snapshot has incompatible {name} dimension")
        for fight in live.fights:
            if any(p.spec != policy.category for p in fight.participants):
                raise SnapshotError("participant category differs from snapshot selection")

    def _bundle(self, code: str) -> dict[str, Any]:
        member = f"reports/{code}/bundle.json"
        if member not in self._archive:
            raise SnapshotError(f"{member} is missing")
        report = (self._archive.read_json(member).get("reportData") or {}).get("report")
        if not isinstance(report, dict) or report.get("code") != code:
            raise SnapshotError(f"{member} has no report {code}")
        return report

    def _check_reports(self, live: LiveSnapshotFile) -> None:
        """Each fight and participant against the acquired combined report it came from."""
        sets = {s.report: s for s in live.report_sets}
        if len(sets) != len(live.report_sets):
            raise SnapshotError("a report set is listed twice")
        codes = {f.reportID for f in live.fights}
        if codes != set(sets):
            raise SnapshotError("report sets do not match the fights' reports")
        subject_faction = _FACTIONS[live.subject.faction]
        for code, rset in sets.items():
            report = self._bundle(code)
            if rset.endpoint != live.endpoint:
                raise SnapshotError(f"report {code} was acquired through another endpoint")
            if rset.cache_sha256 is not None:
                record = {
                    "endpoint": rset.endpoint,
                    "fight_ids": list(rset.fight_ids),
                    "report": report,
                }
                if hashlib.sha256(canonical_bytes(record)).hexdigest() != rset.cache_sha256:
                    raise SnapshotError(f"report {code} differs from its cached generation")
            if (
                canonical_bytes(report)
                and hashlib.sha256(canonical_bytes(report)).hexdigest() != rset.sha256
            ):
                raise SnapshotError(f"report {code} is not the acquired combined report")
            if report.get("revision") != rset.revision:
                raise SnapshotError(f"report {code} revision differs from its report set")
            fights = {f.get("id"): f for f in report.get("fights") or () if isinstance(f, dict)}
            listed = sorted(f.fightID for f in live.fights if f.reportID == code)
            if listed != list(rset.fight_ids) or set(fights) != set(listed):
                raise SnapshotError(f"report {code} fights differ from the selected fights")
            for f in (x for x in live.fights if x.reportID == code):
                for p in f.participants:
                    if fights[f.fightID].get("encounterID") != p.encounterID:
                        raise SnapshotError(f"{code} fight {f.fightID} is another encounter")
                    actor, why = player_actor(
                        report, p.player, p.server, CLASS_NAMES[live.subject.class_id]
                    )
                    if actor is None:
                        raise SnapshotError(f"{p.player} in {code} fight {f.fightID}: {why}")
                    verdict = faction_verdict(report, actor, CLASS_NAMES[live.subject.class_id])
                    if verdict.status != "observed" or verdict.faction is None:
                        raise SnapshotError(
                            f"{p.player}'s faction is not observed: {verdict.reason}"
                        )
                    same = verdict.faction is subject_faction
                    ceiling = live.cross_faction and p.kind == "top" and p.leaderboardPosition == 1
                    if not same and not ceiling:
                        raise SnapshotError(f"{p.player} is not the subject's faction")
                    if p.kind == "you" and (p.player != live.subject.name or not same):
                        raise SnapshotError(f"the subject entry in {code} is not the subject")

    def _build_descriptor(self) -> SnapshotDescriptor:
        live = self._file()
        self._canonical(live)
        self._check_reports(live)
        seen: set[tuple[str, int]] = set()
        fights = []
        for f in live.fights:
            key = (f.reportID, f.fightID)
            if key in seen:
                raise SnapshotError(f"fight {key} is listed twice")
            seen.add(key)
            people = {(p.kind, p.player, p.boss) for p in f.participants}
            if len(people) != len(f.participants):
                raise SnapshotError(f"fight {key} lists a participant twice")
            fights.append(
                SelectedFight(
                    report_code=f.reportID,
                    fight_id=f.fightID,
                    participants=tuple(
                        Participant(
                            kind=p.kind,
                            boss=p.boss,
                            encounter_id=p.encounterID,
                            player=p.player,
                            server=p.server,
                            leaderboard_position=p.leaderboardPosition,
                            total=p.total,
                            duration_ms=p.duration,
                            spec=p.spec,
                        )
                        for p in f.participants
                    ),
                )
            )
        assert self._archive.sha256 is not None
        subject = live.subject
        return SnapshotDescriptor(
            format=FORMAT,
            archive_sha256=self._archive.sha256,
            scope=SnapshotScope.FULL,
            subject=Character(
                id=subject.id,
                name=subject.name,
                class_id=subject.class_id,
                server=subject.server,
                region=subject.region,
            ),
            zone=Zone(id=live.zone.id, name=live.zone.name, partition=live.zone.partition),
            cohort=live.cohort,
            top_n=live.top_n,
            fights=tuple(sorted(fights, key=lambda f: (f.report_code, f.fight_id))),
            source_fight_count=len(fights),
            source_errors=(),
            mode="live",
            limitations=live.limitations,
            acquisition={
                "endpoint": live.endpoint,
                "cross_faction": live.cross_faction,
                "stopped": live.stopped,
                "subject_faction": subject.faction,
                "subject_canonical_id": subject.canonical_id,
                "bosses": [dict(b) for b in live.bosses],
                **(
                    {"comparison_order": list(live.comparison_order)}
                    if live.comparison_order
                    else {}
                ),
                **({"metadata_order": list(live.metadata_order)} if live.metadata_order else {}),
                **(
                    {
                        "selected_category": subject.ranking_category,
                        "selected_metric": subject.ranking_metric,
                    }
                    if subject.class_id == 2 or subject.ranking_category is not None
                    else {}
                ),
            },
        )

    def _ranking_scope(self) -> set[str]:
        """Every requested boss, including those with no acquired fight."""
        return {str(b.get("boss")) for b in self._file().bosses if b.get("boss")}

    def rankings(self) -> Iterator[tuple[str, dict[str, Any]]]:
        live = self._file()
        expected = {b["encounter_id"]: b["boss"] for b in live.bosses}
        for source, document in super().rankings():
            if source.startswith("leaderboards/"):
                encounter = document.get("encounter") or {}
                eid, partition = encounter.get("id"), document.get("partition")
                if (
                    type(eid) is not int
                    or expected.get(eid) != encounter.get("name")
                    or type(partition) is not int
                    or partition != live.zone.partition
                ):
                    raise SnapshotError(
                        f"{source}: leaderboard encounter/partition differs from snapshot"
                    )
                for page in document.get("pages") or []:
                    if type(page.get("page")) is not int or page["page"] < 1:
                        raise SnapshotError(f"{source}: leaderboard has an invalid page number")
                    ranking = page.get("characterRankings")
                    if isinstance(ranking, str):
                        try:
                            ranking = json.loads(ranking)
                        except ValueError:
                            raise SnapshotError(
                                f"{source}: leaderboard ranking JSON is malformed"
                            ) from None
                        page["characterRankings"] = ranking
                    if not isinstance(ranking, dict):
                        raise SnapshotError(f"{source}: leaderboard ranking page is not an object")
                    if "page" in ranking and (
                        type(ranking["page"]) is not int or ranking["page"] != page["page"]
                    ):
                        raise SnapshotError(f"{source}: leaderboard response is another page")
            yield source, document

    def _check_stream_identity(
        self, key: tuple[str, int, str, int, str], proof: LiveStream, names: list[str]
    ) -> None:
        """The certified request must be this report revision's exact fight and contract."""
        live = self._file()
        code, fight, role, actor, direction = key
        rset = next((s for s in live.report_sets if s.report == code), None)
        if rset is None:
            raise SnapshotError(f"stream {key} has no report set")
        try:
            fight_key = FightKey(VANILLA, code, rset.revision, fight)
            canon = check_identity(
                StreamKey(fight_key, role, actor, direction, live.endpoint), proof.identity
            )
        except CacheError as error:
            raise SnapshotError(f"stream {key} identity is invalid: {error}") from None
        bounds = self._fight(code, fight)
        if (canon["start_time"], canon["end_time"]) != bounds:
            raise SnapshotError(f"stream {key} bounds differ from its report fight")
        contract = {
            "data_type": "All",
            "limit": EVENTS_LIMIT,
            "include_resources": True,
            "translate": True,
            "query_version": QUERY_VERSION,
            "endpoint": live.endpoint,
        }
        if any(canon[k] != v for k, v in contract.items()):
            raise SnapshotError(f"stream {key} was not fetched with the supported request")
        try:
            pages = [json.loads(self._archive.read_bytes(n)) for n in names]
            check_pages(canon, pages)
        except (ValueError, CacheError) as error:
            raise SnapshotError(f"stream {key} pages are not a complete stream: {error}") from None

    def _fight(self, code: str, fight: int) -> tuple[float, float]:
        report = self._bundle(code)
        for f in report.get("fights") or ():
            if isinstance(f, dict) and f.get("id") == fight:
                start, end = f.get("startTime"), f.get("endTime")
                if (
                    isinstance(start, (int, float))
                    and isinstance(end, (int, float))
                    and not (isinstance(start, bool) or isinstance(end, bool))
                ):
                    return float(start), float(end)
        raise SnapshotError(f"report {code} has no bounded fight {fight}")

    def _prove_actors(self) -> None:
        """Each participant's actor dir is the report's actor; pet lists match ownership."""
        live = self._file()
        for f in live.fights:
            report = self._bundle(f.reportID)
            fight = next(
                x
                for x in report.get("fights") or ()
                if isinstance(x, dict) and x.get("id") == f.fightID
            )
            base = f"events/{f.reportID}/fight_{f.fightID}/"
            dirs = self._dirs_under(base)
            for p in f.participants:
                actor_id, why = player_actor(
                    report, p.player, p.server, CLASS_NAMES[live.subject.class_id]
                )
                if actor_id is None:
                    raise SnapshotError(f"{p.player}: {why}")
                mine = [d for d in dirs if d.startswith(f"player_{actor_id}_")]
                if len(mine) != 1:
                    raise SnapshotError(
                        f"{p.player} has {len(mine)} actor dirs for actor {actor_id}"
                    )
                folder = f"{base}{mine[0]}/"
                selection = self._archive.read_json(f"{folder}selection.json")
                master = {
                    a.get("id"): a
                    for a in (report.get("masterData") or {}).get("actors") or ()
                    if isinstance(a, dict)
                }
                if (
                    selection.get("actor") != master.get(actor_id)
                    or selection.get("player") != p.player
                ):
                    raise SnapshotError(f"{folder}selection.json is not {p.player}'s report actor")
                known, _why = fight_pets(report, fight, actor_id)
                listed = f"{folder}pets.json" in self._archive
                if known is None:
                    if listed:
                        raise SnapshotError(
                            f"{p.player}'s pets are unproven but a pet list is present"
                        )
                    continue
                if not listed:
                    raise SnapshotError(f"{p.player}'s proven pet list is missing")
                pets = self._archive.read_json(f"{folder}pets.json")
                if (
                    not isinstance(pets, list)
                    or [x.get("id") for x in pets] != known
                    or any(x != master.get(x.get("id")) for x in pets)
                ):
                    raise SnapshotError(
                        f"{p.player}'s pet list differs from the report's ownership"
                    )

    def _prove_streams(self) -> None:
        """Every participant has its actor; every stream's pages match certified digests."""
        live = self._file()
        proofs: dict[tuple[str, int, str, int, str], LiveStream] = {
            (s.report, s.fight, s.role, s.actor_id, s.direction): s for s in live.streams
        }
        if len(proofs) != len(live.streams):
            raise SnapshotError("a stream is listed twice in the provenance")
        used = set()
        for ref in self._expected:
            if ref.role is ActorRole.PET_DISCOVERY:
                continue
            if ref.actor_id is None:
                raise SnapshotError(
                    f"{ref.report_code} fight {ref.fight_id}: no single actor for {ref.actor_name}"
                )
            key = (ref.report_code, ref.fight_id, ref.role.value, ref.actor_id, ref.direction.value)
            proof = proofs.get(key)
            if proof is None:
                raise SnapshotError(f"no certified pages for stream {key}")
            used.add(key)
            prefix = self._prefixes.get(
                _StreamKey(ref.report_code, ref.fight_id, ref.role, ref.actor_id, ref.direction)
            )
            names = sorted(
                n
                for n in self._names
                if prefix is not None
                and n.startswith(prefix)
                and n[len(prefix) :].removesuffix(".json").isdigit()
            )
            digests = tuple(hashlib.sha256(self._archive.read_bytes(n)).hexdigest() for n in names)
            if digests != proof.pages:
                raise SnapshotError(f"pages of stream {key} differ from the certified digests")
            self._check_stream_identity(key, proof, names)
        if used != set(proofs):
            raise SnapshotError("the provenance lists streams that are not in the archive")


def open_snapshot(archive: VerifiedArchive) -> V0Snapshot:
    """The reader for this archive: live (v1) when the marker exists, else the v6 export."""
    if MARKER in archive:
        return V1Snapshot(archive)
    return V0Snapshot(archive)


__all__ = ["FORMAT", "KIND", "MARKER", "LiveSnapshotFile", "V1Snapshot", "open_snapshot"]
