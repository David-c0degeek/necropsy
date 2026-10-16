"""Saved runs and cooperative analysis supervision; no terminal dependencies."""

from __future__ import annotations

import json
import math
import os
import threading
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from platformdirs import user_data_path

from necropsy.analysis.class_catalog import WCL_CATEGORIES, category_label, talent_tree
from necropsy.report.render import load_document
from necropsy.wcl.analyze import AnalyzeError, Outcome, plain_dir, run_analyze
from necropsy.wcl.auth import (
    CLIENT_ID_ENV,
    PUBLIC_CLIENT_ID,
    Auth,
    AuthState,
    CallbackListener,
    PkceAttempt,
)
from necropsy.wcl.cache import CacheError, is_link, item_lock
from necropsy.wcl.checkpoint import DIRECTORY, save, saved_options
from necropsy.wcl.client import RateLimited, SystemClock, WclClient
from necropsy.wcl.context import CharacterContext, resolve
from necropsy.wcl.credentials import CredentialStore
from necropsy.wcl.sites import VANILLA, require_supported
from necropsy.wcl.urls import parse_character_url

Notify = Callable[[str], None]
SESSION = "necropsy-session.json"
COMPLETE_WITH_NOTES = "Complete — data notes"
DATA_NOTES = (
    "Analysis finished. Some results are limited by the available logs, such as missing "
    "fights or uncertain pet usage. No restart is required. See the coverage notes "
    "in your Playbook for details."
)


class Stopped(Exception):
    """The user requested a safe stop; saved requests remain usable."""


class StopClock(SystemClock):
    def __init__(self, stopped: threading.Event) -> None:
        self.stopped = stopped

    def sleep(self, seconds: float) -> None:
        if self.stopped.wait(seconds):
            raise Stopped


@dataclass
class SavedRun:
    out: Path
    options: dict[str, Any]
    title: str
    status: str = "Saved"
    updated: str = ""
    detail: str = ""
    legacy: bool = False

    @property
    def finished(self) -> bool:
        return self.status in (
            "Complete",
            COMPLETE_WITH_NOTES,
            "Partial — report ready",
            "Offline report",
        )

    @property
    def when(self) -> str:
        try:
            return datetime.fromisoformat(self.updated).astimezone().strftime("%d %b %H:%M")
        except ValueError:
            return "Earlier run"

    @property
    def resumable(self) -> bool:
        return (self.out / DIRECTORY / "run.json").is_file()

    @property
    def report(self) -> Path | None:
        for name in ("playbook.html", "report.html"):
            path = self.out / name
            if path.is_file() and not is_link(path):
                return path
        return None

    def store(self, status: str, detail: str = "") -> None:
        self.status, self.detail = status, detail
        self.updated = datetime.now(UTC).isoformat()
        save(
            self.out / SESSION,
            {
                "version": 1,
                "options": self.options,
                "title": self.title,
                "status": status,
                "updated": self.updated,
                "detail": detail,
            },
        )


class RunLibrary:
    def __init__(self, root: Path | None = None) -> None:
        self.discover_legacy = root is None
        self.active_run: Path | None = None
        self.root = plain_dir(root or user_data_path("Necropsy", appauthor=False), "app data")
        self.runs = plain_dir(self.root / "runs", "saved analyses")
        old_cache = Path.home() / "necropsy" / "wcl-cache"
        self.cache = (
            old_cache
            if self.discover_legacy and old_cache.is_dir() and not is_link(old_cache)
            else self.root / "cache"
        )
        self.imports = self.root / "imported-runs.json"

    def create(
        self, url: str, category: str, context: CharacterContext, declared_tree: str | None = None
    ) -> SavedRun:
        if context.partition is None:
            raise ValueError("Choose a raid partition before starting.")
        declared_tree = talent_tree(context.class_id.value, declared_tree)
        if category not in {value for _, value in categories(context.class_id.value)}:
            raise ValueError("Choose a WCL comparison category for your class.")
        label = category_label(context.class_id.value, None if category == "all" else category)
        out = self.runs / (datetime.now(UTC).strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8])
        out.mkdir()
        run = SavedRun(
            out,
            {
                "url": url,
                "cache": str(self.cache),
                "endpoint": "user",
                "partition": context.partition.id,
                "category": category,
                "faction": context.faction.value.value,
                "package": True,
                "cross_faction": False,
                "metric": None,
                "name": None,
                **({"talent_tree": declared_tree} if declared_tree is not None else {}),
            },
            f"{context.name.value} · "
            + (f"{declared_tree} · " if declared_tree else "")
            + f"WCL {label} · Naxxramas",
        )
        run.store("Ready")
        return run

    def load(self, out: Path) -> SavedRun:
        out = plain_dir(out, "saved run")
        session = out / SESSION
        checkpoint = out / DIRECTORY / "run.json"
        if is_link(session) or is_link(checkpoint) or is_link(out / DIRECTORY):
            raise ValueError("Saved run goes through a link.")
        if session.is_file():
            data = json.loads(session.read_bytes())
            options = saved_options(out) if checkpoint.is_file() else data["options"]
            status = str(data["status"])
            detail = str(data.get("detail", ""))
            if status == "Partial — report ready":
                status, detail = COMPLETE_WITH_NOTES, DATA_NOTES
            if status in ("Running", "Waiting", "Connecting") and out != self.active_run:
                status = "Interrupted — ready to continue"
            return SavedRun(
                out,
                options,
                str(data["title"]),
                status,
                str(data.get("updated", "")),
                detail,
            )
        if checkpoint.is_file():
            options = saved_options(out)
            ref = parse_character_url(options["url"])
            character = ref.name or f"Character {ref.character_id}"
            analysis = out / "analysis.json"
            if analysis.is_file() and not is_link(analysis):
                document, _ = load_document(analysis.read_bytes())
                character = str(document["subject"]["name"])
            return SavedRun(
                out,
                options,
                f"{character} · {options['category'] or 'All specs'}",
                "Saved — ready to continue",
            )
        analysis = out / "analysis.json"
        if is_link(analysis):
            raise ValueError("Saved analysis is a link.")
        document, _ = load_document(analysis.read_bytes())
        subject = document["subject"]
        acquisition = document.get("acquisition") or {}
        category = acquisition.get("selected_category")
        metric = next(
            (
                (((b.get("key") or {}).get("metric") or {}).get("value"))
                for b in acquisition.get("bosses", [])
                if b.get("key")
            ),
            None,
        )
        options = {
            "url": f"https://vanilla.warcraftlogs.com/character/id/{subject['id']}",
            "cache": str(self.cache),
            "category": category,
            "metric": metric,
            "endpoint": acquisition.get("endpoint") or "user",
            "partition": document["zone"]["partition"],
            "faction": None,
            "cross_faction": document["options"]["cross_faction"],
            "package": True,
            "name": None,
        }
        return SavedRun(
            out,
            options,
            f"{subject['name']} · {category or 'Saved report'}",
            "Older run — recover cached data" if document["mode"] == "live" else "Offline report",
            legacy=True,
        )

    def discover(self) -> list[SavedRun]:
        paths = list(self.runs.iterdir())
        if self.imports.is_file() and not is_link(self.imports):
            paths.extend(Path(p) for p in json.loads(self.imports.read_bytes()))
        legacy = Path.home() / "necropsy"
        if self.discover_legacy and legacy.is_dir() and not is_link(legacy):
            paths.extend(legacy.iterdir())
        found: dict[Path, SavedRun] = {}
        for path in paths:
            if not path.is_dir() or is_link(path):
                continue
            if not any(
                (path / name).is_file()
                for name in (SESSION, "analysis.json", f"{DIRECTORY}/run.json")
            ):
                continue
            try:
                run = self.load(path)
            except OSError, ValueError, KeyError, TypeError, CacheError, AnalyzeError:
                continue
            found[run.out] = run
        return sorted(found.values(), key=lambda run: run.updated or run.out.name, reverse=True)

    def import_run(self, path: str) -> SavedRun:
        out = Path(path).expanduser().absolute()
        if not out.is_dir():
            raise ValueError("Choose the folder containing the saved analysis.")
        run = self.load(out)
        previous = json.loads(self.imports.read_bytes()) if self.imports.exists() else []
        save(self.imports, sorted({*previous, str(out)}))
        return run

    def recover_legacy(self, old: SavedRun) -> SavedRun:
        out = self.runs / f"recovered-{uuid4().hex[:12]}"
        out.mkdir()
        run = SavedRun(out, old.options.copy(), old.title, "Ready")
        run.store(
            "Ready", "Recovering cached data from an older analysis; original files are preserved."
        )
        return run


def categories(class_id: int) -> list[tuple[str, str]]:
    choices = [(label, slug) for slug, (_id, label) in WCL_CATEGORIES.get(class_id, {}).items()]
    if class_id == 3:
        choices.append(("All Hunter categories (legacy)", "all"))
    return choices


class AnalysisService:
    def __init__(self) -> None:
        self._auth: Auth | None = None
        self.client: WclClient | None = None

    @property
    def auth(self) -> Auth:
        if self._auth is None:
            self._auth = Auth(VANILLA, CredentialStore.open())
        return self._auth

    @staticmethod
    def check(stop: threading.Event) -> None:
        if stop.is_set():
            raise Stopped

    def connect(self, stop: threading.Event, notify: Notify, browser: Notify) -> None:
        self.check(stop)
        client_id = os.environ.get(CLIENT_ID_ENV) or PUBLIC_CLIENT_ID
        if not client_id:
            raise ValueError("This installation has no registered Warcraft Logs application ID.")
        attempt = PkceAttempt(client_id)
        url = self.auth.authorize_url(attempt.client_id, attempt.state, challenge=attempt.challenge)
        with CallbackListener(attempt.state) as listener:
            notify("Sign in to Warcraft Logs in your browser, then return here.")
            browser(url)
            webbrowser.open(url)
            code = listener.wait(cancelled=stop.is_set)
        self.check(stop)
        self.auth.complete_public_sign_in(attempt, code)
        notify("Warcraft Logs connected.")

    def ensure_connected(self, stop: threading.Event, notify: Notify, browser: Notify) -> None:
        if self.auth.state() is AuthState.LOGIN_NEEDED:
            self.connect(stop, notify, browser)

    def factory(self, stop: threading.Event) -> Callable[..., WclClient]:
        def make(site: Any, tokens: Any) -> WclClient:
            def provider(endpoint: str) -> str:
                self.check(stop)
                return str(tokens(endpoint))

            self.client = WclClient(site, provider, clock=StopClock(stop))
            return self.client

        return make

    def identify(
        self,
        url: str,
        stop: threading.Event,
        notify: Notify,
        browser: Notify,
        partition: int | None = None,
    ) -> CharacterContext:
        ref = parse_character_url(url)
        require_supported(ref.site)
        self.ensure_connected(stop, notify, browser)
        notify("Finding your character and raid history…")
        client = self.factory(stop)(ref.site, self.auth.token_for)
        try:
            return resolve(client, ref, endpoint="user", partition=partition)
        finally:
            client.close()

    def attempt(self, run: SavedRun, stop: threading.Event, notify: Notify) -> Outcome:
        options = dict(run.options)
        url = str(options.pop("url"))
        options["cache"] = Path(options["cache"])
        return run_analyze(
            url,
            out=run.out,
            **options,
            resume=run.resumable,
            tokens=lambda: self.auth.token_for,
            client_factory=self.factory(stop),
            progress=notify,
        )

    def reset_delay(self) -> int:
        client = self.client
        if client is not None and client.last_rate is not None and client.last_rate_at is not None:
            age = max(0.0, client.clock.monotonic() - client.last_rate_at)
            remaining = client.last_rate.reset_in_s - age
            if remaining > 0:
                return min(3601, math.ceil(remaining) + 1)
        return 60  # no reliable countdown: bounded recheck, never a busy retry loop

    def run(
        self,
        run: SavedRun,
        stop: threading.Event,
        notify: Notify,
        browser: Notify,
        countdown: Callable[[int], None],
    ) -> Outcome:
        with item_lock(run.out / ".necropsy-tui.lock"):
            return self._supervise(run, stop, notify, browser, countdown)

    def _supervise(
        self,
        run: SavedRun,
        stop: threading.Event,
        notify: Notify,
        browser: Notify,
        countdown: Callable[[int], None],
    ) -> Outcome:
        def progress(message: str) -> None:
            self.check(stop)
            notify(message)

        try:
            self.ensure_connected(stop, progress, browser)
            while True:
                self.check(stop)
                run.store("Running")
                try:
                    outcome = self.attempt(run, stop, progress)
                    self.check(stop)
                    quota = bool(outcome.acquisition and outcome.acquisition.stopped)
                except AnalyzeError as error:
                    if error.code != 3 or not any(
                        word in str(error) for word in ("BudgetExceeded", "RateLimited")
                    ):
                        raise
                    outcome, quota = None, True
                except RateLimited:
                    outcome, quota = None, True
                if not quota and outcome is not None:
                    status = "Complete" if outcome.code == 0 else COMPLETE_WITH_NOTES
                    run.store(status, "" if outcome.code == 0 else DATA_NOTES)
                    return outcome
                delay = self.reset_delay()
                run.store(
                    "Waiting",
                    "Warcraft Logs hourly allowance reached. Will continue automatically.",
                )
                progress(
                    "Hourly allowance reached. Progress saved; waiting to continue automatically."
                )
                deadline = time.monotonic() + delay
                while (remaining := math.ceil(deadline - time.monotonic())) > 0:
                    self.check(stop)
                    countdown(remaining)
                    if stop.wait(min(1.0, max(0.0, deadline - time.monotonic()))):
                        raise Stopped
                countdown(0)
                progress("Allowance reset time reached. Continuing your saved analysis…")
        except Exception:
            if stop.is_set():
                run.store("Stopped — ready to continue")
                raise Stopped from None
            run.store(
                "Needs attention", "Open this run and retry after addressing the displayed error."
            )
            raise
