"""Reader for the v6 Hunter deep-export layout ("snapshot v0").

Layout (all paths inside one zip):

    profile.json, manifest.json, selection.json      full-export originals
    subset.json                                      only in a fixture subset; defines its scope
    leaderboards/<encounterID>_<boss>.json           cohort ranking pages
    user_rankings/<encounterID>_<boss>.json          the subject's own rankings
    reports/<code>/bundle.json                       report, fights, masterData, playerDetails
    reports/<code>/selection_reasons.json
    events/<code>/fight_<n>/player_<id>_<name>/      selection.json, pets.json,
                                                     source_NNN.json, target_NNN.json
    events/<code>/fight_<n>/pet_<id>_<name>/         source_NNN.json, target_NNN.json

In a subset, `selection.json` and `manifest.json` still describe the full
export; `subset.json` alone defines which fights are in scope.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from necropsy.snapshot.archive import VerifiedArchive
from necropsy.snapshot.canonical import canonical_json
from necropsy.snapshot.model import (
    ActorRole,
    Character,
    Direction,
    Participant,
    SelectedFight,
    SnapshotDescriptor,
    SnapshotError,
    SnapshotScope,
    StreamRead,
    StreamRef,
    StreamStatus,
    Zone,
)

FORMAT = "wcl-hunter-deep-export-v6"
SUBSET_KIND = "necropsy.fixture-subset"
SUBSET_FORMAT_VERSION = 1

_TOP_LEVEL = {"profile.json", "manifest.json", "selection.json", "subset.json"}
_KNOWN = (
    re.compile(r"^(leaderboards|user_rankings)/[^/]+\.json$"),
    re.compile(r"^reports/[^/]+/(bundle|selection_reasons|fight_\d+)\.json$"),
    re.compile(
        r"^events/[^/]+/fight_\d+/player_\d+_[^/]+/(selection|pets|confirmed_pets|combatant_context)\.json$"
    ),
    re.compile(r"^events/[^/]+/fight_\d+/(player|pet)_\d+_[^/]+/(source|target)_\d{3}\.json$"),
)
_PAGE = re.compile(r"^(source|target)_(\d{3})\.json$")


@dataclass(frozen=True)
class _StreamKey:
    report_code: str
    fight_id: int
    role: ActorRole
    actor_id: int
    direction: Direction


def _server_name(value: Any) -> str | None:
    if isinstance(value, dict):
        name = value.get("name")
        return str(name) if name is not None else None
    return str(value) if value is not None else None


def _participant(raw: dict[str, Any]) -> Participant:
    return Participant(
        kind=raw["kind"],
        boss=raw["boss"],
        encounter_id=int(raw["encounterID"]),
        player=raw["player"],
        server=_server_name(raw.get("server")),
        leaderboard_position=raw.get("leaderboardPosition"),
        total=raw.get("total"),
        duration_ms=raw.get("duration"),
        spec=raw.get("spec"),
    )


def _boundary_overlap(previous: list[dict[str, Any]], current: list[dict[str, Any]]) -> bool:
    """Whether a page starts with events also ending the previous page at the same timestamp.

    Only flags the boundary; both copies are always kept, because identical
    events can genuinely occur at the same timestamp.
    """
    if not current:
        return False
    timestamp = current[0].get("timestamp")
    tail: Counter[str] = Counter()
    for event in reversed(previous):
        if event.get("timestamp") != timestamp:
            break
        tail[canonical_json(event)] += 1
    if not tail:
        return False
    head: Counter[str] = Counter()
    for event in current:
        if event.get("timestamp") != timestamp:
            break
        head[canonical_json(event)] += 1
    return bool(tail & head)


def _fight_dir(report_code: str, fight_id: int) -> str:
    return f"events/{report_code}/fight_{fight_id}/"


class V0Snapshot:
    """`SnapshotReader` over an open `VerifiedArchive` in the v6 export layout.

    Subclasses for other top-level formats override `_top_level`,
    `_build_descriptor` and `_ranking_scope`; everything below the top level is
    read the same way.
    """

    _top_level: frozenset[str] = frozenset(_TOP_LEVEL)

    def __init__(self, archive: VerifiedArchive) -> None:
        self._archive = archive
        self._names = archive.names()
        self._issues: list[str] = []
        self._descriptor = self._build_descriptor()
        self._prefixes: dict[_StreamKey, str] = {}
        self._expected = self._build_expected_streams()
        self._check_members()

    # -- descriptor ------------------------------------------------------------

    def descriptor(self) -> SnapshotDescriptor:
        return self._descriptor

    def _build_descriptor(self) -> SnapshotDescriptor:
        manifest = self._archive.read_json("manifest.json")
        profile = self._archive.read_json("profile.json")
        selection = self._archive.read_json("selection.json")
        character = profile["characterData"]["character"]
        zone = profile["worldData"]["zone"]
        full_fights = {
            (f["reportID"], int(f["fightID"])): f for f in selection if isinstance(f, dict)
        }
        if "subset.json" in self._archive:
            scope = SnapshotScope.SUBSET
            fights = self._subset_fights(self._archive.read_json("subset.json"), full_fights)
        else:
            scope = SnapshotScope.FULL
            fights = tuple(
                SelectedFight(
                    report_code=code,
                    fight_id=fight_id,
                    participants=tuple(_participant(p) for p in raw["participants"]),
                )
                for (code, fight_id), raw in sorted(full_fights.items())
            )
        assert self._archive.sha256 is not None
        return SnapshotDescriptor(
            format=FORMAT,
            archive_sha256=self._archive.sha256,
            scope=scope,
            subject=Character(
                id=int(character["id"]),
                name=character["name"],
                class_id=int(character["classID"]),
                server=character["server"]["name"],
                region=character["server"]["region"]["slug"],
            ),
            zone=Zone(id=int(zone["id"]), name=zone["name"], partition=int(manifest["partition"])),
            cohort="overall-top-n-plus-subject",
            top_n=int(manifest["topNPerBoss"]),
            fights=fights,
            source_fight_count=len(full_fights),
            source_errors=tuple(manifest.get("errors") or ()),
        )

    @staticmethod
    def _subset_fights(
        descriptor: dict[str, Any], full_fights: dict[tuple[str, int], dict[str, Any]]
    ) -> tuple[SelectedFight, ...]:
        if descriptor.get("kind") != SUBSET_KIND:
            raise SnapshotError(f"subset.json has unexpected kind {descriptor.get('kind')!r}")
        if descriptor.get("formatVersion") != SUBSET_FORMAT_VERSION:
            raise SnapshotError(
                f"unsupported subset.json formatVersion {descriptor.get('formatVersion')!r}"
            )
        fights: list[SelectedFight] = []
        for entry in descriptor["fights"]:
            key = (entry["reportID"], int(entry["fightID"]))
            original = full_fights.get(key)
            if original is None:
                raise SnapshotError(f"subset fight {key} is not in the original selection")
            participants: list[Participant] = []
            for wanted in entry["participants"]:
                matches = [
                    p
                    for p in original["participants"]
                    if p["kind"] == wanted["kind"]
                    and p["player"] == wanted["player"]
                    and p["boss"] == wanted["boss"]
                ]
                if len(matches) != 1:
                    raise SnapshotError(
                        f"subset participant {wanted['player']!r} ({wanted['kind']}, "
                        f"{wanted['boss']}) in {key} matches {len(matches)} original entries"
                    )
                participants.append(_participant(matches[0]))
            fights.append(
                SelectedFight(report_code=key[0], fight_id=key[1], participants=tuple(participants))
            )
        return tuple(sorted(fights, key=lambda f: (f.report_code, f.fight_id)))

    # -- reports and rankings --------------------------------------------------

    def _report_codes(self) -> list[str]:
        return sorted({f.report_code for f in self._descriptor.fights})

    def reports(self) -> Iterator[dict[str, Any]]:
        for code in self._report_codes():
            member = f"reports/{code}/bundle.json"
            if member not in self._archive:
                self._issues.append(f"report bundle missing: {member}")
                continue
            report = (self._archive.read_json(member).get("reportData") or {}).get("report")
            if not isinstance(report, dict):
                self._issues.append(f"report bundle without a report object: {member}")
                continue
            yield report

    def _ranking_scope(self) -> set[str]:
        """Boss names whose ranking documents are in scope."""
        return {p.boss for f in self._descriptor.fights for p in f.participants}

    def rankings(self) -> Iterator[tuple[str, dict[str, Any]]]:
        bosses = self._ranking_scope()
        for name in self._names:
            if not name.startswith(("leaderboards/", "user_rankings/")):
                continue
            document = self._archive.read_json(name)
            if (document.get("encounter") or {}).get("name") in bosses:
                yield name, document

    # -- streams ---------------------------------------------------------------

    def expected_streams(self) -> list[StreamRef]:
        return list(self._expected)

    def scoped_reports(self) -> Iterator[tuple[str, dict[str, Any]]]:
        for report in self.reports():
            if len(report.get("fights") or []) == 1:
                yield f"reports/{report['code']}/bundle.json", report

    def combatant_contexts(self) -> Iterator[tuple[str, dict[str, Any]]]:
        return iter(())

    def _dirs_under(self, prefix: str) -> list[str]:
        dirs = {n[len(prefix) :].split("/", 1)[0] for n in self._names if n.startswith(prefix)}
        return sorted(d for d in dirs if d and "/" not in d and not d.endswith(".json"))

    def _build_expected_streams(self) -> list[StreamRef]:
        refs: dict[tuple[Any, ...], StreamRef] = {}
        for fight in self._descriptor.fights:
            base = _fight_dir(fight.report_code, fight.fight_id)
            dirs = self._dirs_under(base)
            player_dirs = {
                d: self._archive.read_json(f"{base}{d}/selection.json")
                for d in dirs
                if d.startswith("player_") and f"{base}{d}/selection.json" in self._archive
            }
            matched: set[str] = set()
            for participant in fight.participants:
                found = [
                    d
                    for d, sel in player_dirs.items()
                    if any(
                        r.get("kind") == participant.kind
                        and r.get("player") == participant.player
                        and r.get("boss") == participant.boss
                        for r in sel.get("reasons", [])
                    )
                ]
                if len(found) != 1:
                    for direction in (Direction.SOURCE, Direction.TARGET):
                        ref = StreamRef(
                            report_code=fight.report_code,
                            fight_id=fight.fight_id,
                            actor_id=None,
                            actor_name=participant.player,
                            role=ActorRole.PLAYER,
                            direction=direction,
                        )
                        refs[
                            (
                                fight.report_code,
                                fight.fight_id,
                                "missing",
                                participant.player,
                                direction,
                            )
                        ] = ref
                    if len(found) > 1:
                        self._issues.append(
                            f"{base}: {participant.player} matches {len(found)} player dirs"
                        )
                    continue
                player_dir = found[0]
                matched.add(player_dir)
                self._add_actor_streams(refs, fight, base, player_dirs[player_dir], player_dir)
            for unmatched in sorted(set(player_dirs) - matched):
                self._issues.append(f"{base}{unmatched}: no selected participant")
        return list(refs.values())

    def _add_actor_streams(
        self,
        refs: dict[tuple[Any, ...], StreamRef],
        fight: SelectedFight,
        base: str,
        selection: dict[str, Any],
        player_dir: str,
    ) -> None:
        actor = selection["actor"]
        actor_id = int(actor["id"])
        for direction in (Direction.SOURCE, Direction.TARGET):
            key = _StreamKey(
                fight.report_code, fight.fight_id, ActorRole.PLAYER, actor_id, direction
            )
            self._prefixes[key] = f"{base}{player_dir}/{direction.value}_"
            refs[(key,)] = StreamRef(
                report_code=fight.report_code,
                fight_id=fight.fight_id,
                actor_id=actor_id,
                actor_name=actor["name"],
                role=ActorRole.PLAYER,
                direction=direction,
            )
        pets_member = f"{base}{player_dir}/pets.json"
        if pets_member not in self._archive:
            refs[(fight.report_code, fight.fight_id, "pets", actor_id)] = StreamRef(
                report_code=fight.report_code,
                fight_id=fight.fight_id,
                actor_id=None,
                actor_name=f"pets of {actor['name']}",
                role=ActorRole.PET_DISCOVERY,
                direction=Direction.LISTING,
                owner_actor_id=actor_id,
            )
            pets_member = f"{base}{player_dir}/confirmed_pets.json"
            if pets_member not in self._archive:
                return
        pet_dirs = self._dirs_under(base)
        for pet in self._archive.read_json(pets_member):
            pet_id = int(pet["id"])
            dirs = [d for d in pet_dirs if d.startswith(f"pet_{pet_id}_")]
            for direction in (Direction.SOURCE, Direction.TARGET):
                key = _StreamKey(
                    fight.report_code, fight.fight_id, ActorRole.PET, pet_id, direction
                )
                if len(dirs) == 1:
                    self._prefixes[key] = f"{base}{dirs[0]}/{direction.value}_"
                refs[(key,)] = StreamRef(
                    report_code=fight.report_code,
                    fight_id=fight.fight_id,
                    actor_id=pet_id,
                    actor_name=pet.get("name") or "",
                    role=ActorRole.PET,
                    direction=direction,
                    owner_actor_id=actor_id,
                )

    def read_stream(self, ref: StreamRef) -> StreamRead:
        if ref.actor_id is None:
            return StreamRead(ref, StreamStatus.MISSING, 0, [], 0, "actor not present in export")
        error = self._source_error(ref)
        key = _StreamKey(ref.report_code, ref.fight_id, ref.role, ref.actor_id, ref.direction)
        prefix = self._prefixes.get(key)
        pages = sorted(
            n
            for n in self._names
            if prefix and n.startswith(prefix) and _PAGE.match(n.rsplit("/", 1)[-1])
        )
        if not pages:
            status = StreamStatus.ERROR if error else StreamStatus.MISSING
            return StreamRead(ref, status, 0, [], 0, error or "no pages")
        numbers = [int(_PAGE.match(p.rsplit("/", 1)[-1]).group(2)) for p in pages]  # type: ignore[union-attr]
        if numbers != list(range(1, len(pages) + 1)):
            return StreamRead(
                ref, StreamStatus.MALFORMED, len(pages), [], 0, f"non-contiguous pages {numbers}"
            )
        events: list[dict[str, Any]] = []
        ambiguities = 0
        previous: list[dict[str, Any]] = []
        status = StreamStatus.COMPLETE
        detail = error
        for index, member in enumerate(pages):
            page = self._archive.read_json(member)
            if (
                not isinstance(page, dict)
                or not isinstance(page.get("data"), list)
                or "nextPageTimestamp" not in page
            ):
                return StreamRead(
                    ref, StreamStatus.MALFORMED, len(pages), [], 0, f"malformed page {member}"
                )
            data: list[dict[str, Any]] = page["data"]
            if previous and _boundary_overlap(previous, data):
                ambiguities += 1
            if data:
                previous = data
            events.extend(data)
            is_last = index == len(pages) - 1
            cursor = page["nextPageTimestamp"]
            if is_last and cursor is not None:
                status = StreamStatus.INCOMPLETE
                detail = detail or f"last page {member} has a next-page cursor"
            if not is_last and cursor is None:
                return StreamRead(
                    ref,
                    StreamStatus.MALFORMED,
                    len(pages),
                    [],
                    0,
                    f"page {member} ends the stream but more pages follow",
                )
        if error:
            status = StreamStatus.ERROR
        return StreamRead(ref, status, len(pages), events, ambiguities, detail)

    def _source_error(self, ref: StreamRef) -> str | None:
        for err in self._descriptor.source_errors:
            if err.get("report") != ref.report_code:
                continue
            fights = err.get("fightIDs") or [err.get("fightID")]
            if ref.fight_id not in fights:
                continue
            stage = err.get("stage")
            if (
                stage == "report"
                or (
                    stage == "player_events"
                    and ref.role is ActorRole.PLAYER
                    and err.get("player") == ref.actor_name
                )
                or (
                    stage == "pet_events"
                    and ref.role is ActorRole.PET
                    and err.get("pet") == ref.actor_name
                )
            ):
                return f"{stage}: {err.get('error')}"
        return None

    # -- issues ----------------------------------------------------------------

    def _check_members(self) -> None:
        in_scope = {_fight_dir(f.report_code, f.fight_id) for f in self._descriptor.fights}
        listed = {p.rsplit("/", 1)[0] + "/" for p in self._prefixes.values()}
        for name in self._names:
            if name in self._top_level:
                continue
            if not any(p.match(name) for p in _KNOWN):
                self._issues.append(f"unrecognised member: {name}")
                continue
            if name.startswith("events/"):
                fight_dir = "/".join(name.split("/")[:3]) + "/"
                actor_dir = "/".join(name.split("/")[:4]) + "/"
                if fight_dir not in in_scope:
                    self._issues.append(f"event member outside the selected fights: {name}")
                elif name.split("/")[3].startswith("pet_") and actor_dir not in listed:
                    self._issues.append(f"pet stream not listed in any pets.json: {name}")

    def issues(self) -> list[str]:
        return list(dict.fromkeys(self._issues))
