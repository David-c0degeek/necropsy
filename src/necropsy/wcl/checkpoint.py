"""Run-local request journal. Stores API data, never headers or tokens."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from necropsy.wcl.cache import CacheCorrupt, canonical_bytes, is_link, publish

DIRECTORY = ".necropsy-run"


def saved_options(out: Path) -> dict[str, Any]:
    root = out / DIRECTORY
    if is_link(root):
        raise CacheCorrupt(f"checkpoint path is a link: {root}")
    path = root / "run.json"
    if not os.path.lexists(path):
        raise CacheCorrupt(
            "no saved run checkpoint in this output directory. For a pre-0.1.1 run, "
            "reuse the same --cache with a fresh --out directory once; "
            "subsequent attempts can use --resume"
        )
    digest(path)
    try:
        state = json.loads(path.read_bytes())
        options = state["options"]
        required = {
            "url",
            "cache",
            "partition",
            "endpoint",
            "cross_faction",
            "name",
            "package",
            "category",
            "metric",
            "faction",
        }
        if (
            state["version"] != 1
            or not isinstance(options, dict)
            or not required <= set(options)
            or set(options) - required - {"talent_tree"}
        ):
            raise ValueError("unsupported checkpoint format")
        if "talent_tree" in options and not isinstance(options["talent_tree"], str):
            raise ValueError("talent_tree must be a declaration string")
    except (ValueError, KeyError, TypeError) as error:
        raise CacheCorrupt(f"invalid run checkpoint: {error}") from error
    return options


def digest(path: Path) -> str:
    if is_link(path) or not path.is_file():
        raise CacheCorrupt(f"checkpoint file is missing or not a plain file: {path}")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path: Path, value: Any) -> None:
    """Replace run metadata atomically under the caller's output lock."""
    if is_link(path):
        raise CacheCorrupt(f"checkpoint path is a link: {path}")
    temporary = path.with_name(f".{path.name}.{os.urandom(8).hex()}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(canonical_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class Journal:
    """Successful requests are immutable and bound to their exact query and scope."""

    def __init__(self, root: Path) -> None:
        self.root = root
        if is_link(root):
            raise CacheCorrupt(f"checkpoint path is a link: {root}")
        root.mkdir(exist_ok=True)
        self.scope = "acquisition"
        self.reused = 0
        self.captured_at: str | None = None

    def identity(
        self, site: str, endpoint: str, query: str, variables: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        return dict(
            site=site,
            endpoint=endpoint,
            query=query,
            variables=dict(variables or {}),
            scope=self.scope,
        )

    def _path(self, identity: dict[str, Any]) -> Path:
        key = hashlib.sha256(canonical_bytes(identity)).hexdigest()
        return self.root / f"{key}.json"

    def read(self, identity: dict[str, Any]) -> dict[str, Any] | None:
        path = self._path(identity)
        if not os.path.lexists(path):
            return None
        digest(path)
        try:
            record = json.loads(path.read_bytes())
            data = record["data"]
            if (
                record["identity"] != identity
                or not isinstance(data, dict)
                or record["sha256"] != hashlib.sha256(canonical_bytes(data)).hexdigest()
            ):
                raise ValueError("request identity or digest differs")
        except (ValueError, KeyError, TypeError) as error:
            raise CacheCorrupt(f"invalid request checkpoint {path}: {error}") from error
        self.reused += 1
        self.captured_at = record.get("captured_at")
        return data

    def write(
        self, identity: dict[str, Any], data: Mapping[str, Any], captured_at: str | None = None
    ) -> None:
        publish(
            self._path(identity),
            canonical_bytes(
                {
                    "identity": identity,
                    "data": data,
                    "captured_at": captured_at,
                    "sha256": hashlib.sha256(canonical_bytes(data)).hexdigest(),
                }
            ),
        )

    def forget_report(self, code: str) -> None:
        """Discard this report's request journal when its revision changes."""
        for path in self.root.glob("*.json"):
            digest(path)
            record = json.loads(path.read_bytes())
            if record["identity"]["variables"].get("code") == code:
                path.unlink()


class Checkpoint:
    """Options, context and files owned by this analysis, under its output lock."""

    def __init__(self, out: Path, options: dict[str, Any], resume: bool) -> None:
        self.out = out
        self.root = out / DIRECTORY
        if is_link(self.root):
            raise CacheCorrupt(f"checkpoint path is a link: {self.root}")
        self.path = self.root / "run.json"
        self.state: dict[str, Any]
        if resume:
            digest(self.path)
            try:
                self.state = json.loads(self.path.read_bytes())
                outputs = self.state["outputs"]
                if not isinstance(outputs, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in outputs.items()
                ):
                    raise ValueError("outputs must map paths to digests")
            except (ValueError, KeyError, TypeError) as error:
                raise CacheCorrupt(f"invalid run checkpoint: {error}") from error
            if self.state.get("version") != 1 or self.state.get("options") != options:
                raise CacheCorrupt(
                    "resume options differ from the saved run; use the original command"
                )
            for relative, expected in self.state["outputs"].items():
                path = Path(relative)
                if path.drive or path.is_absolute() or ".." in path.parts:
                    raise CacheCorrupt("unsafe output path in checkpoint")
                for parent in path.parents:
                    if is_link(out / parent):
                        raise CacheCorrupt("output path goes through a link")
                if digest(out / path) != expected:
                    raise CacheCorrupt(
                        f"saved output changed: {relative}; refusing to overwrite it"
                    )
        else:
            if os.path.lexists(self.path):
                raise CacheCorrupt("this directory has a saved run; continue with --resume")
            self.root.mkdir(exist_ok=True)
            self.state = {"version": 1, "options": options, "outputs": {}}
            self.flush()

    def flush(self) -> None:
        save(self.path, self.state)

    def record(self, paths: list[Path]) -> None:
        for path in paths:
            self.state["outputs"][path.relative_to(self.out).as_posix()] = digest(path)
        self.flush()

    def bind(self, context: dict[str, Any]) -> None:
        previous = self.state.get("context")
        if previous is not None and previous != context:
            raise CacheCorrupt(
                "resolved character, class, faction or partition changed since this run"
            )
        self.state["context"] = context
        self.flush()

    @property
    def allowed(self) -> set[str]:
        return set(self.state["outputs"])
