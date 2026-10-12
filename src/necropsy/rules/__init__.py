"""Versioned game rules shipped as package data.

Rules are stable game facts (spell IDs, buffs, faction codes) kept out of code
so they can be reviewed and versioned on their own. Each file records where its
values came from.
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from typing import Any

import yaml


class RuleError(Exception):
    """A rule file is missing or malformed."""


@cache
def load_rules(game: str, name: str) -> dict[str, Any]:
    resource = files("necropsy.rules").joinpath(game, f"{name}.yaml")
    try:
        text = resource.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuleError(f"no rule file {game}/{name}.yaml") from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise RuleError(f"{game}/{name}.yaml must be a mapping")
    return data
