"""Classify raw death flags without confusing Feign Death with a real death."""

from __future__ import annotations

import json


def real_death(raw: object) -> bool | None:
    """True for a genuine death, False for a literal feign, None if unresolved.

    Raw WCL JSON uses ``feign``; the scripting API's ``isFeign`` is a different
    interface. An absent raw flag retains ordinary death semantics.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return None
    if not isinstance(raw, dict):
        return None
    flag = raw.get("feign", False)
    return not flag if type(flag) is bool else None
