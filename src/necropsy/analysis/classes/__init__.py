"""Class plugins: class-specific forensics on top of the generic analyzers.

A plugin is registered for one game and one WCL class ID. Only the Classic Era
Hunter exists so far; other classes are added as plugins, not as branches in
shared code.
"""

from __future__ import annotations

from typing import Any, Protocol

import duckdb

from necropsy.analysis.context import ParticipantFight
from necropsy.analysis.generic.environment import EnvironmentProfile


class ClassPlugin(Protocol):
    game: str
    class_id: int
    name: str

    def analyze(
        self, con: duckdb.DuckDBPyConnection, pf: ParticipantFight, profile: EnvironmentProfile
    ) -> Any: ...


_REGISTRY: dict[tuple[str, int], ClassPlugin] = {}


def register(plugin: ClassPlugin) -> ClassPlugin:
    key = (plugin.game, plugin.class_id)
    if key in _REGISTRY:
        raise ValueError(f"a plugin is already registered for {key}")
    _REGISTRY[key] = plugin
    return plugin


def plugin_for(game: str, class_id: int) -> ClassPlugin | None:
    _load_builtin()
    return _REGISTRY.get((game, class_id))


def _load_builtin() -> None:
    # Imported for its registration side effect.
    from necropsy.analysis.classes.classic_era import hunter  # noqa: F401
