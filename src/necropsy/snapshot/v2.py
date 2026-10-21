"""Versioned live snapshots with separately certified whole-encounter event scopes."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any, Literal

from pydantic import Field, ValidationError

from necropsy.raids import ENCOUNTER_CONTEXT_PARTITIONS, ENCOUNTER_CONTEXT_ZONES
from necropsy.snapshot.archive import VerifiedArchive
from necropsy.snapshot.canonical import canonical_json
from necropsy.snapshot.model import (
    ActorRole,
    Direction,
    SnapshotDescriptor,
    SnapshotError,
    StreamRead,
    StreamRef,
    StreamStatus,
)
from necropsy.snapshot.v1 import MARKER, LiveSnapshotFile, V1Snapshot, _Strict

FORMAT = "necropsy-live-snapshot-v2"


class EncounterStream(_Strict):
    report: str
    fight: int = Field(gt=0)
    role: Literal["encounter", "critical"]
    actor_id: None
    direction: Literal["all"]
    pages: tuple[str, ...] = Field(min_length=1)
    identity: dict[str, Any]
    meta: dict[str, Any]


class LiveSnapshotFileV2(LiveSnapshotFile):
    formatVersion: int = Field(ge=2, le=2)
    encounter_streams: tuple[EncounterStream, ...]


class V2Snapshot(V1Snapshot):
    """Reuse actor/report proofs and page decoding; add explicit encounter-scope proofs."""

    _known = (
        *V1Snapshot._known,
        re.compile(r"^events/[^/]+/fight_\d+/encounter/(all|critical)_\d{3}\.json$"),
    )

    def __init__(self, archive: VerifiedArchive) -> None:
        super().__init__(archive)
        self._prove_encounter_streams()

    def _file(self) -> LiveSnapshotFileV2:
        if self._live is None:
            try:
                self._live = LiveSnapshotFileV2.model_validate_json(
                    self._archive.read_bytes(MARKER)
                )
            except ValidationError as error:
                raise SnapshotError(f"{MARKER} is not a valid live snapshot v2: {error}") from None
        assert isinstance(self._live, LiveSnapshotFileV2)
        return self._live

    def _canonical(self, live: LiveSnapshotFile) -> None:
        super()._canonical(live)
        if (
            live.zone.id not in ENCOUNTER_CONTEXT_ZONES
            or live.zone.partition not in ENCOUNTER_CONTEXT_PARTITIONS
        ):
            raise SnapshotError("encounter context requires a supported new Era raid partition")

    def _build_descriptor(self) -> SnapshotDescriptor:
        return super()._build_descriptor().model_copy(update={"format": FORMAT})

    @staticmethod
    def _names_for(proof: EncounterStream) -> list[str]:
        prefix = "all" if proof.role == "encounter" else "critical"
        return [
            f"events/{proof.report}/fight_{proof.fight}/encounter/{prefix}_{n:03d}.json"
            for n in range(1, len(proof.pages) + 1)
        ]

    def expected_streams(self) -> list[StreamRef]:
        return [
            *super().expected_streams(),
            *(
                StreamRef(
                    report_code=p.report,
                    fight_id=p.fight,
                    actor_id=None,
                    actor_name="Encounter" if p.role == "encounter" else "Critical damage",
                    role=ActorRole(p.role),
                    direction=Direction.ALL,
                )
                for p in self._file().encounter_streams
            ),
        ]

    def read_stream(self, ref: StreamRef) -> StreamRead:
        if ref.role not in {ActorRole.ENCOUNTER, ActorRole.CRITICAL}:
            return super().read_stream(ref)
        proof = next(
            (
                p
                for p in self._file().encounter_streams
                if (p.report, p.fight, p.role, p.actor_id, p.direction)
                == (
                    ref.report_code,
                    ref.fight_id,
                    ref.role.value,
                    ref.actor_id,
                    ref.direction.value,
                )
            ),
            None,
        )
        if proof is None:
            return StreamRead(ref, StreamStatus.MISSING, 0, [], 0, "no certified encounter stream")
        return self._read_pages(ref, self._names_for(proof))

    def _prove_encounter_streams(self) -> None:
        proofs = self._file().encounter_streams
        keys = {(p.report, p.fight, p.role) for p in proofs}
        wanted = {
            (f.reportID, f.fightID, role)
            for f in self._file().fights
            for role in ("encounter", "critical")
        }
        if len(keys) != len(proofs) or keys != wanted:
            raise SnapshotError(
                "encounter provenance must certify both scopes once per selected fight"
            )
        listed = set()
        for proof in proofs:
            names = self._names_for(proof)
            listed.update(names)
            if any(n not in self._archive for n in names):
                raise SnapshotError("certified encounter pages are missing")
            digests = tuple(hashlib.sha256(self._archive.read_bytes(n)).hexdigest() for n in names)
            if digests != proof.pages:
                raise SnapshotError("encounter pages differ from certified digests")
            self._check_stream_identity(
                (proof.report, proof.fight, proof.role, None, "all"), proof.identity, names
            )
        actual = {n for n in self._names if "/encounter/" in n and n.startswith("events/")}
        if actual != listed:
            raise SnapshotError("encounter members differ from certified page scope")
        refs = self.expected_streams()
        for fight in self._file().fights:
            scoped = [
                r for r in refs if (r.report_code, r.fight_id) == (fight.reportID, fight.fightID)
            ]
            all_ref = next(r for r in scoped if r.role is ActorRole.ENCOUNTER)
            all_events = self.read_stream(all_ref).events
            complete = Counter(canonical_json(e) for e in all_events)
            for ref in scoped:
                if ref.role in {ActorRole.ENCOUNTER, ActorRole.PET_DISCOVERY}:
                    continue
                subset = Counter(canonical_json(e) for e in self.read_stream(ref).events)
                if subset - complete:
                    raise SnapshotError(
                        "actor or critical events are not a subset of encounter data"
                    )
                if ref.role in {ActorRole.PLAYER, ActorRole.PET}:
                    field = "sourceID" if ref.direction is Direction.SOURCE else "targetID"
                    owned = Counter(
                        canonical_json(e) for e in all_events if e.get(field) == ref.actor_id
                    )
                    if owned - subset:
                        raise SnapshotError(
                            "owned encounter events are missing from their actor direction stream"
                        )
