"""Canonical JSON for raw WCL events: the basis of event identity."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Key-sorted, whitespace-free JSON; equal events always serialize identically."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def event_uid(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
