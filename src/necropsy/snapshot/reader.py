"""Interface every snapshot format implements, so ingest never depends on a layout."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol

from necropsy.snapshot.model import SnapshotDescriptor, StreamRead, StreamRef


class SnapshotReader(Protocol):
    def descriptor(self) -> SnapshotDescriptor:
        """Subject, cohort and selected fights. For a subset, only the subset's fights."""
        ...

    def reports(self) -> Iterator[dict[str, Any]]:
        """WCL `report` objects (fights, masterData, playerDetails, rankings) in scope."""
        ...

    def rankings(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """(source, document) for leaderboard pages and the subject's own rankings in scope."""
        ...

    def expected_streams(self) -> list[StreamRef]:
        """Every stream the snapshot should contain for the selected fights."""
        ...

    def read_stream(self, ref: StreamRef) -> StreamRead:
        """All events of one stream, or why the stream is missing or incomplete."""
        ...

    def issues(self) -> list[str]:
        """Content the reader did not recognise or could not place."""
        ...
