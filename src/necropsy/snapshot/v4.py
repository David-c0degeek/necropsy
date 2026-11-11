"""Exact, versioned source/critical projections from one certified encounter-All stream."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Literal, Self

from pydantic import Field, ValidationError, model_validator

from necropsy.raids import DERIVED_TARGET_ZONES, DERIVED_VIEW_ZONES
from necropsy.snapshot.model import SnapshotDescriptor, SnapshotError
from necropsy.snapshot.v1 import MARKER, LiveSnapshotFile, LiveStream, _Strict
from necropsy.snapshot.v2 import EncounterStream, V2Snapshot
from necropsy.snapshot.v3 import LiveSnapshotFileV3, LiveStreamV3, V3Snapshot
from necropsy.wcl.acquire import fight_pets
from necropsy.wcl.cache import canonical_bytes
from necropsy.wcl.derive import (
    CRITICAL_RULE,
    SOURCE_RULE,
    TARGET_RULE,
    DerivationUnsupported,
    project_pages,
    source_actor_ids,
)

FORMAT = "necropsy-live-snapshot-v4"


class DerivationV4(_Strict):
    rule: Literal[
        "target-equals-encounter-all-v1",
        "source-owned-encounter-all-v1",
        "critical-hit-type-encounter-all-v1",
    ]
    parent: dict[str, Any]
    parent_pages: tuple[str, ...] = Field(min_length=1)
    actor_ids: tuple[int, ...] | None = None

    @model_validator(mode="after")
    def _actors(self) -> Self:
        if self.rule == SOURCE_RULE:
            if (
                not self.actor_ids
                or tuple(sorted(set(self.actor_ids))) != self.actor_ids
                or any(i <= 0 for i in self.actor_ids)
            ):
                raise ValueError("source derivation requires canonical owned actor ids")
        elif self.actor_ids is not None:
            raise ValueError("actor ids apply only to source projections")
        return self


class LiveStreamV4(LiveStreamV3):
    derivation: DerivationV4 | None = None  # type: ignore[assignment]

    @model_validator(mode="after")
    def _one_provenance(self) -> Self:
        if (self.identity is None) == (self.derivation is None):
            raise ValueError("a stream has exactly one request or derivation provenance")
        if self.derivation is not None:
            expected = TARGET_RULE if self.direction == "target" else SOURCE_RULE
            if self.derivation.rule != expected or self.meta:
                raise ValueError("actor derivation has the wrong direction or claims request costs")
        return self


class EncounterStreamV4(EncounterStream):
    identity: dict[str, Any] | None  # type: ignore[assignment]
    derivation: DerivationV4 | None = None

    @model_validator(mode="after")
    def _one_provenance(self) -> Self:
        if (self.identity is None) == (self.derivation is None):
            raise ValueError("an encounter stream has exactly one request or derivation provenance")
        if self.derivation is not None and (
            self.role != "critical" or self.derivation.rule != CRITICAL_RULE or self.meta
        ):
            raise ValueError("only cost-free critical projections may derive from encounter-All")
        return self


class LiveSnapshotFileV4(LiveSnapshotFileV3):
    formatVersion: int = Field(ge=4, le=4)
    streams: tuple[LiveStreamV4, ...]
    encounter_streams: tuple[EncounterStreamV4, ...]


class V4Snapshot(V3Snapshot):
    def _file(self) -> LiveSnapshotFileV4:
        if self._live is None:
            try:
                self._live = LiveSnapshotFileV4.model_validate_json(
                    self._archive.read_bytes(MARKER)
                )
            except ValidationError as error:
                raise SnapshotError(f"{MARKER} is not a valid live snapshot v4: {error}") from None
        assert isinstance(self._live, LiveSnapshotFileV4)
        return self._live

    def _canonical(self, live: LiveSnapshotFile) -> None:
        V2Snapshot._canonical(self, live)
        if live.zone.id not in DERIVED_VIEW_ZONES:
            raise SnapshotError("derived projections are not supported for this raid")
        actor_derived = any(
            p.derivation and p.derivation.rule == SOURCE_RULE for p in self._file().streams
        )
        critical_derived = any(
            p.derivation and p.derivation.rule == CRITICAL_RULE
            for p in self._file().encounter_streams
        )
        target_derived = live.zone.id not in DERIVED_TARGET_ZONES and any(
            p.derivation for p in self._file().streams
        )
        if not (actor_derived or critical_derived or target_derived):
            raise SnapshotError("a v4 snapshot needs a source or critical projection")

    def _build_descriptor(self) -> SnapshotDescriptor:
        return super()._build_descriptor().model_copy(update={"format": FORMAT})

    def _check_stream_proof(
        self,
        key: tuple[str, int, str, int, str],
        proof: LiveStream,
        names: list[str],
    ) -> None:
        assert isinstance(proof, LiveStreamV4)
        if proof.derivation is None or proof.derivation.rule == TARGET_RULE:
            super()._check_stream_proof(key, proof, names)
        else:
            self._check_projection(key, proof, names)

    def _check_encounter_proof(self, proof: EncounterStream, names: list[str]) -> None:
        assert isinstance(proof, EncounterStreamV4)
        if proof.derivation is None:
            assert proof.identity is not None
            self._check_stream_identity(
                (proof.report, proof.fight, proof.role, None, "all"), proof.identity, names
            )
        else:
            self._check_projection(
                (proof.report, proof.fight, proof.role, None, "all"), proof, names
            )

    def _check_projection(
        self,
        key: tuple[str, int, str, int | None, str],
        proof: LiveStreamV4 | EncounterStreamV4,
        names: list[str],
    ) -> None:
        code, fight, role, actor, direction = key
        derivation = proof.derivation
        assert derivation is not None
        parents = [
            p
            for p in self._file().encounter_streams
            if (p.report, p.fight, p.role) == (code, fight, "encounter")
        ]
        if len(parents) != 1 or parents[0].identity is None or parents[0].derivation is not None:
            raise SnapshotError("projection needs one requested encounter-All parent")
        parent = parents[0]
        if derivation.parent != parent.identity or derivation.parent_pages != parent.pages:
            raise SnapshotError("projection parent request or digests differ")
        parent_names = self._names_for(parent)
        if any(name not in self._archive for name in parent_names):
            raise SnapshotError("projection parent pages are missing")
        parent_bytes = [self._archive.read_bytes(n) for n in parent_names]
        if tuple(hashlib.sha256(p).hexdigest() for p in parent_bytes) != parent.pages:
            raise SnapshotError("projection parent bytes differ from certified digests")
        assert parent.identity is not None
        self._check_stream_identity(
            (code, fight, "encounter", None, "all"), parent.identity, parent_names
        )
        parent_pages = [json.loads(p) for p in parent_bytes]
        floor, end = self._fight(code, fight)
        for page in parent_pages:
            if any(
                type(e.get("timestamp")) not in (int, float)
                or not math.isfinite(e["timestamp"])
                or not floor <= e["timestamp"] <= end
                for e in page["data"]
            ):
                raise SnapshotError("projection parent has out-of-scope event timestamps")
            if page["nextPageTimestamp"] is not None:
                floor = page["nextPageTimestamp"]
        ids = None
        try:
            if role != "critical":
                if actor is None or direction != "source" or derivation.rule != SOURCE_RULE:
                    raise DerivationUnsupported("wrong source derivation scope")
                # scoped_reports verifies the original acquisition's full digest and identity.
                if not hasattr(self, "_projection_reports"):
                    self._projection_reports = {
                        (r["code"], r["fights"][0]["id"]): r
                        for name, r in self.scoped_reports()
                        if name == f"reports/{r['code']}/fight_{r['fights'][0]['id']}.json"
                    }
                report = self._projection_reports[(code, fight)]
                ids = source_actor_ids(report, fight, actor)
                if ids != derivation.actor_ids:
                    raise DerivationUnsupported("source ownership differs from acquired report")
                actors = {a["id"]: a for a in report["masterData"]["actors"]}
                f = next(f for f in report["fights"] if f["id"] == fight)
                owners = {a["id"]: a.get("petOwner") for a in actors.values()}
                owners.update(
                    {p["id"]: p["petOwner"] for p in f["friendlyPets"] if p.get("petOwner")}
                )
                root = actor
                while owners[root] is not None:
                    root = owners[root]
                if actors[root].get("type") != "Player" or fight_pets(report, f, root)[0] is None:
                    raise DerivationUnsupported("source ownership completeness is unknown")
            elif derivation.rule != CRITICAL_RULE:
                raise DerivationUnsupported("wrong critical derivation rule")
            projected = project_pages(parent_pages, derivation.rule, actor_ids=ids)
        except (DerivationUnsupported, KeyError, StopIteration) as error:
            raise SnapshotError(f"unsupported projection: {error}") from None
        if len(names) != len(projected) or any(
            self._archive.read_bytes(name) != canonical_bytes(page)
            for name, page in zip(names, projected, strict=True)
        ):
            raise SnapshotError("derived bytes differ from the exact ordered parent projection")
