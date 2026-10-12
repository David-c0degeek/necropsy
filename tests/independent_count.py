"""An implementation of the event count that shares no code with ingest.

Used to check the ingested event total: per fight, an event's count is its
largest multiplicity in any single stream, with identity by key-sorted JSON.
"""

from __future__ import annotations

import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

_STREAM_PAGE = re.compile(r"^events/([^/]+)/(fight_\d+)/([^/]+)/(source|target)_\d{3}\.json$")


def merged_event_count(archive: Path, exclude_actor_dirs: frozenset[str] = frozenset()) -> int:
    """`exclude_actor_dirs` holds `<code>/<fight_n>/<actor dir>` paths to leave out."""
    streams: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            m = _STREAM_PAGE.match(name)
            if m and f"{m.group(1)}/{m.group(2)}/{m.group(3)}" not in exclude_actor_dirs:
                streams[(m.group(1), m.group(2), m.group(3), m.group(4))].append(name)
        per_fight: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
        for (code, fight, _actor, _direction), pages in streams.items():
            counter: Counter[str] = Counter()
            for page in sorted(pages):
                for event in (json.loads(zf.read(page)) or {}).get("data") or []:
                    counter[json.dumps(event, sort_keys=True)] += 1
            merged = per_fight[(code, fight)]
            for key, n in counter.items():
                merged[key] = max(merged[key], n)
    return sum(sum(c.values()) for c in per_fight.values())
