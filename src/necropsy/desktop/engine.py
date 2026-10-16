"""Allowlisted JSON-lines desktop bridge. Credentials never cross this boundary."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlparse
from uuid import uuid4

from necropsy import __version__
from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.report.offline import run_offline
from necropsy.report.package import build_outputs, package_name
from necropsy.report.render import render_playbook, render_report, view_of
from necropsy.tui.service import AnalysisService, RunLibrary, SavedRun, Stopped, categories
from necropsy.wcl.cache import is_link
from necropsy.wcl.context import CharacterContext
from necropsy.wcl.credentials import CredentialStoreError
from necropsy.wcl.urls import parse_character_url

Json = dict[str, Any]
Emit = Callable[[Json], None]
LONG_OPERATIONS = frozenset({"connect", "identify", "analyze", "resume", "demo", "snapshot"})


def describe_run(run: SavedRun) -> Json:
    return {
        "id": str(run.out),
        "title": run.title,
        "status": run.status,
        "detail": run.detail,
        "when": run.when,
        "updated": run.updated,
        "has_report": (run.out / "analysis.json").is_file(),
        "can_resume": not run.finished
        and (run.resumable or run.legacy or bool(run.options.get("url"))),
    }


def describe_character(context: CharacterContext) -> Json:
    name = CLASS_NAMES.get(context.class_id.value, "Unsupported class")
    return {
        "name": context.name.value,
        "server": context.server.value,
        "region": context.region.value,
        "class_name": name,
        "class_key": name.lower().replace(" ", "-"),
        "faction": getattr(context.faction.value, "value", "Unknown faction"),
        "ready": context.same_faction_ready,
        "partition": context.partition.id if context.partition else None,
        "partitions": [{"id": p.id, "name": p.name} for p in context.partitions],
        "ambiguity": context.ambiguity,
        "notes": list(context.notes),
        "categories": [
            {"label": label, "value": value} for label, value in categories(context.class_id.value)
        ],
    }


class DesktopEngine:
    def __init__(
        self,
        emit: Emit,
        library: RunLibrary | None = None,
        service: AnalysisService | None = None,
    ) -> None:
        self.emit = emit
        self.library = library or RunLibrary()
        self.service = service or AnalysisService()
        self.stop = threading.Event()
        self.worker: threading.Thread | None = None
        self.context: CharacterContext | None = None
        self.url = ""

    @property
    def busy(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    def notify(self, message: str) -> None:
        self.emit({"event": "progress", "data": message})

    def browser(self, url: str) -> None:
        # This is an authorize URL, never a callback or a credential record.
        self.emit({"event": "browser", "data": url})

    def find_run(self, run_id: str) -> SavedRun:
        for run in self.library.discover():
            if str(run.out) == run_id:
                return run
        raise ValueError("This saved analysis is no longer available. Refresh your library.")

    def handle(self, request: Json) -> None:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        if not isinstance(request_id, int) or not isinstance(params, dict):
            self.emit({"id": request_id, "error": "Invalid desktop request."})
            return
        if method in LONG_OPERATIONS:
            if self.busy:
                self.emit({"id": request_id, "error": "An operation is already running."})
                return
            self.stop.clear()
            self.emit({"event": "busy", "data": True})
            self.worker = threading.Thread(
                target=self._work, args=(request_id, str(method), params), daemon=False
            )
            self.worker.start()
        else:
            self._respond(request_id, str(method), params)

    def _respond(self, request_id: int, method: str, params: Json) -> None:
        try:
            result = self.dispatch(method, params)
            self.emit({"id": request_id, "result": result})
        except Stopped:
            self.emit({"id": request_id, "result": {"stopped": True}})
        except Exception as error:
            message = (
                "Unlock your computer's password vault and try again. Linux needs a running "
                "Secret Service or KWallet desktop session."
                if isinstance(error, CredentialStoreError)
                else str(error)
            )
            self.emit({"id": request_id, "error": message})

    def _work(self, request_id: int, method: str, params: Json) -> None:
        try:
            self._respond(request_id, method, params)
        finally:
            self.library.active_run = None
            self.emit({"event": "countdown", "data": 0})
            self.emit({"event": "busy", "data": False})

    def shutdown(self) -> None:
        self.stop.set()
        if self.worker is not None:
            self.worker.join()

    def dispatch(self, method: str, params: Json) -> Any:
        if method == "hello":
            return {"version": __version__, "runs": self.list_runs()}
        if method == "list":
            return self.list_runs()
        if method == "stop":
            self.stop.set()
            self.notify(
                "Saving your progress. An active request can take up to 30 seconds to stop."
            )
            return None
        if method == "connect":
            self.service.connect(self.stop, self.notify, self.browser)
            return {"connected": True}
        if method == "identify":
            self.context = None
            url = str(params["url"]).strip()
            parse_character_url(url)  # reject invalid links before opening the password vault
            partition = params.get("partition")
            context = self.service.identify(
                url,
                self.stop,
                self.notify,
                self.browser,
                int(partition) if partition is not None else None,
            )
            self.url, self.context = url, context
            return describe_character(context)
        if method == "analyze":
            if self.context is None or not self.context.same_faction_ready:
                raise ValueError("Find your character first so we can verify its raid and faction.")
            category = str(params["category"])
            if category not in {value for _, value in categories(self.context.class_id.value)}:
                raise ValueError("Choose one of the specs shown for your character.")
            return self.analyze(self.library.create(self.url, category, self.context))
        if method == "resume":
            run = self.find_run(str(params["id"]))
            if not describe_run(run)["can_resume"]:
                raise ValueError("This analysis is already complete. Open its Playbook instead.")
            if run.legacy:
                run = self.library.recover_legacy(run)
            return self.analyze(run)
        if method == "import":
            if self.busy:
                raise ValueError("Wait for the current operation before adding an analysis.")
            return describe_run(self.library.import_run(str(params["path"])))
        if method in ("demo", "snapshot"):
            return self.offline(method, params)
        if method == "report":
            run = self.find_run(str(params["id"]))
            analysis = run.out / "analysis.json"
            if is_link(analysis):
                raise ValueError("The saved analysis goes through a link.")
            view = view_of(analysis.read_bytes())
            page = str(params.get("view", "playbook"))
            if page not in ("playbook", "report"):
                raise ValueError("Choose Playbook or Report.")
            # Regenerate trusted templates; never execute an imported HTML file.
            return {
                "html": render_playbook(view) if page == "playbook" else render_report(view),
                "class_key": view.experience["class_key"],
                "title": run.title,
            }
        if method == "export":
            if self.busy:
                raise ValueError("Wait for the current operation before exporting a package.")
            run = self.find_run(str(params["id"]))
            analysis = run.out / "analysis.json"
            if is_link(analysis):
                raise ValueError("The saved analysis goes through a link.")
            data = analysis.read_bytes()
            view_of(data)  # validate before writing any output
            from necropsy.report.render import load_document

            document, _ = load_document(data)
            destination = Path(str(params["path"])).expanduser().absolute()
            if destination.suffix.lower() != ".zip":
                raise ValueError("Save the package with a .zip extension.")
            package = build_outputs(data)[package_name(document)]
            assert package is not None
            destination.write_bytes(package)
            return {"path": str(destination)}
        if method == "open_link":
            url = str(params["url"])
            parsed = urlparse(url)
            if (
                parsed.scheme != "https"
                or parsed.hostname
                not in (
                    "warcraftlogs.com",
                    "www.warcraftlogs.com",
                    "vanilla.warcraftlogs.com",
                    "classic.warcraftlogs.com",
                )
                or parsed.username
                or parsed.password
                or parsed.port not in (None, 443)
            ):
                raise ValueError("Only secure Warcraft Logs links can be opened here.")
            if not webbrowser.open(url):
                raise ValueError("Could not open your browser. Open Warcraft Logs manually.")
            return None
        raise ValueError("Unknown desktop operation.")

    def list_runs(self) -> list[Json]:
        return [describe_run(run) for run in self.library.discover()]

    def analyze(self, run: SavedRun) -> Json:
        self.library.active_run = run.out
        outcome = self.service.run(
            run,
            self.stop,
            self.notify,
            self.browser,
            lambda remaining: self.emit({"event": "countdown", "data": remaining}),
        )
        return {"run": describe_run(run), "partial": outcome.code != 0}

    def offline(self, method: str, params: Json) -> Json:
        if method == "demo":
            sample = resources.files("necropsy.desktop").joinpath("assets", "demo.zip")
            if sample.is_file():
                with resources.as_file(sample) as path:
                    return self.import_snapshot(path, example=True)
            # Source checkouts use the committed sample without duplicating it.
            path = Path(__file__).resolve().parents[3] / "tests/fixtures/haplina_naxx_subset.zip"
            if not path.is_file():
                raise ValueError("The example is missing. Reinstall the desktop application.")
        else:
            path = Path(str(params["path"])).expanduser().absolute()
        return self.import_snapshot(path, example=method == "demo")

    def import_snapshot(self, path: Path, *, example: bool) -> Json:
        self.service.check(self.stop)
        self.notify("Preparing the offline example…" if example else "Reading your saved snapshot…")
        out = self.library.runs / f"offline-{uuid4().hex[:12]}"
        # Offline publication is atomic at its established output boundary. Let it
        # finish before honoring stop so a close never discards the completed report.
        run_offline(path, out, package=True)
        run = self.library.load(out)
        if example:
            run.title = f"Example · {run.title}"
        run.store("Offline report", "Example data — a limited sample." if example else "")
        self.notify("Your offline Playbook is ready.")
        return {"run": describe_run(run), "partial": False}


def serve(source: TextIO, target: TextIO, root: Path | None = None) -> None:
    lock = threading.Lock()

    def emit(message: Json) -> None:
        with lock:
            target.write(json.dumps(message, ensure_ascii=False) + "\n")
            target.flush()

    engine = DesktopEngine(emit, RunLibrary(root))
    try:
        for line in source:
            try:
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError("Expected a JSON object.")
                engine.handle(request)
            except ValueError, TypeError:
                emit({"id": None, "error": "Invalid desktop request."})
    finally:
        # EOF means the shell closed its pipe: save cooperatively before exiting.
        engine.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Necropsy desktop JSON bridge")
    parser.add_argument("--version", action="version", version=f"necropsy {__version__}")
    parser.add_argument("--data-dir", type=Path, help="Use an isolated saved-analysis library")
    args = parser.parse_args()
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")
    # Library output belongs on stderr; stdout is exclusively the wire protocol.
    target = sys.stdout
    sys.stdout = sys.stderr
    serve(sys.stdin, target, args.data_dir)


if __name__ == "__main__":
    main()
