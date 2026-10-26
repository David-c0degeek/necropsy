"""Live snapshots whose actor target streams may be derived from the encounter-All scope.

A derived stream was never requested. It carries no request identity; instead it
names its parent, the same fight's encounter-All request, and the parent's page
digests. It is accepted only when the parent passes the unchanged strict request
contract over the derived pages themselves and the derived pages are the parent's
pages byte for byte.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from necropsy.raids import DERIVED_TARGET_ZONES
from necropsy.snapshot.model import SnapshotDescriptor, SnapshotError
from necropsy.snapshot.v1 import MARKER, LiveSnapshotFile, LiveStream, _Strict
from necropsy.snapshot.v2 import FORMAT as V2_FORMAT
from necropsy.snapshot.v2 import LiveSnapshotFileV2, V2Snapshot
from necropsy.wcl.acquire import DERIVATION_RULE

FORMAT = "necropsy-live-snapshot-v3"
ENCOUNTER_FORMATS = frozenset({V2_FORMAT, FORMAT})
"""Snapshot formats that carry certified whole-encounter scopes."""


class Derivation(_Strict):
    rule: Literal["target-equals-encounter-all-v1"]
    parent: dict[str, Any]
    """The exact canonical request of the same fight's encounter-All stream."""
    parent_pages: tuple[str, ...] = Field(min_length=1)


class LiveStreamV3(LiveStream):
    identity: dict[str, Any] | None  # type: ignore[assignment]
    derivation: Derivation | None = None

    @model_validator(mode="after")
    def _one_provenance(self) -> LiveStreamV3:
        if (self.identity is None) == (self.derivation is None):
            raise ValueError("a stream is either requested (identity) or derived, never both")
        if self.derivation is not None and self.direction != "target":
            raise ValueError("only target streams may be derived")
        return self


class LiveSnapshotFileV3(LiveSnapshotFileV2):
    formatVersion: int = Field(ge=3, le=3)
    streams: tuple[LiveStreamV3, ...]


class V3Snapshot(V2Snapshot):
    """V2 proofs, plus target streams derived from their fight's encounter-All pages."""

    def _file(self) -> LiveSnapshotFileV3:
        if self._live is None:
            try:
                self._live = LiveSnapshotFileV3.model_validate_json(
                    self._archive.read_bytes(MARKER)
                )
            except ValidationError as error:
                raise SnapshotError(f"{MARKER} is not a valid live snapshot v3: {error}") from None
        assert isinstance(self._live, LiveSnapshotFileV3)
        return self._live

    def _canonical(self, live: LiveSnapshotFile) -> None:
        super()._canonical(live)
        if live.zone.id not in DERIVED_TARGET_ZONES:
            raise SnapshotError("derived target streams are defined only for their supported raids")
        if not any(isinstance(s, LiveStreamV3) and s.derivation for s in live.streams):
            raise SnapshotError("a v3 snapshot must contain a derived stream; otherwise it is v2")

    def _build_descriptor(self) -> SnapshotDescriptor:
        return super()._build_descriptor().model_copy(update={"format": FORMAT})

    def _check_stream_proof(
        self, key: tuple[str, int, str, int, str], proof: LiveStream, names: list[str]
    ) -> None:
        assert isinstance(proof, LiveStreamV3)
        if proof.derivation is None:
            assert proof.identity is not None
            self._check_stream_identity(key, proof.identity, names)
            return
        code, fight, _role, _actor, direction = key
        derivation = proof.derivation
        if direction != "target":
            raise SnapshotError(f"stream {key}: only target streams may be derived")
        parents = [
            p
            for p in self._file().encounter_streams
            if (p.report, p.fight, p.role) == (code, fight, "encounter")
        ]
        if len(parents) != 1:
            raise SnapshotError(f"stream {key}: no single certified encounter-All parent")
        parent = parents[0]
        if derivation.parent != parent.identity or derivation.parent_pages != parent.pages:
            raise SnapshotError(f"stream {key}: derivation names another request than its parent")
        if proof.pages != parent.pages:
            raise SnapshotError(f"stream {key}: derived pages differ from the parent's pages")
        # The parent's own request contract, checked over the derived pages themselves.
        self._check_stream_identity((code, fight, "encounter", None, "all"), parent.identity, names)
        if any(
            self._archive.read_bytes(mine) != self._archive.read_bytes(theirs)
            for mine, theirs in zip(names, self._names_for(parent), strict=True)
        ):
            raise SnapshotError(f"stream {key}: derived pages are not the parent's bytes")


__all__ = ["DERIVATION_RULE", "ENCOUNTER_FORMATS", "FORMAT", "V3Snapshot"]
