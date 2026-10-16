"""Keyboard/mouse guided application. Work and credentials stay in the service."""

from __future__ import annotations

import threading
import webbrowser
from collections.abc import Callable
from typing import Any, ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    Collapsible,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from necropsy import __version__
from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.tui.service import AnalysisService, RunLibrary, SavedRun, Stopped, categories
from necropsy.wcl.analyze import AnalyzeError
from necropsy.wcl.cache import CacheError
from necropsy.wcl.context import CharacterContext


class NecropsyApp(App[None]):
    TITLE = "Necropsy"
    SUB_TITLE = "Raid insight. Next-pull clarity."
    ENABLE_COMMAND_PALETTE = False
    BINDINGS: ClassVar = [
        Binding("ctrl+q", "request_quit", "Quit"),
        Binding("ctrl+c", "stop", "Stop / quit"),
        Binding("f5", "refresh", "Refresh saved runs"),
    ]
    CSS = """
    Screen { background: #10151b; color: #e6e9ec; }
    Header { background: #1d2833; }
    #page { padding: 1 3; }
    #brand { text-style: bold; color: #ddb879; margin-bottom: 1; }
    .help { color: #a8b5c2; margin-bottom: 1; }
    Label { margin-top: 1; }
    Input, Select { margin-bottom: 1; }
    Button { margin: 0 1 1 0; }
    Horizontal { height: auto; }
    #identity { padding: 1; border-left: thick #ddb879; margin-bottom: 1; }
    #activity { color: #ddb879; margin-top: 1; }
    #spinner { height: 1; }
    #reset { color: #f3c77e; }
    #log { height: 8; border: round #354656; margin-bottom: 1; }
    #history-heading { text-style: bold; margin-top: 1; }
    #saved-detail { margin-bottom: 1; color: #a8b5c2; }
    Collapsible { padding: 0; margin: 0; }
    TabbedContent, ContentSwitcher, TabPane { height: auto; }
    TabPane { padding: 1 0; }
    """

    def __init__(
        self,
        library: RunLibrary | None = None,
        service: AnalysisService | None = None,
        opener: Callable[[str], Any] = webbrowser.open,
    ) -> None:
        super().__init__()
        self.library = library or RunLibrary()
        self.service = service or AnalysisService()
        self.opener = opener
        self.saved: list[SavedRun] = []
        self.context: CharacterContext | None = None
        self.character_url = ""
        self.busy = False
        self.stop_event = threading.Event()
        self.quit_after_stop = False
        self.browser_url: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(id="page"):
            yield Static(f"NECROPSY  {__version__}  ·  Classic Era / Naxxramas", id="brand")
            yield Static(
                "Paste your Warcraft Logs character link. We'll guide you from there.",
                classes="help",
            )
            with TabbedContent(initial="new-analysis", id="tabs"):
                with TabPane("New analysis", id="new-analysis"):
                    yield Label("Your character")
                    yield Input(
                        placeholder="https://vanilla.warcraftlogs.com/character/…",
                        id="character-url",
                    )
                    with Horizontal():
                        yield Button("Find my character", variant="primary", id="find")
                        yield Button("Connect Warcraft Logs", id="connect")
                    yield Static("", id="identity", markup=False)
                    yield Label("Choose a raid partition", id="partition-label")
                    yield Select[str](
                        [], prompt="Choose the raid history to analyze", id="partition"
                    )
                    yield Label("What do you play?", id="spec-label")
                    yield Select[str]([], prompt="Choose your spec", id="spec")
                    yield Button("Analyze my character", variant="success", id="analyze")
                with TabPane("Saved analyses", id="saved-analyses"):
                    yield Static("Your saved analyses", id="history-heading")
                    yield Static(
                        "Close the app and continue here later. Finished reports work offline.",
                        classes="help",
                    )
                    yield Select[str]([], prompt="No saved analyses yet", id="saved")
                    yield Static("", id="saved-detail", markup=False)
                    with Horizontal():
                        yield Button(
                            "Continue analysis", variant="primary", id="continue", disabled=True
                        )
                        yield Button("Open report", id="report", disabled=True)
                        yield Button("Refresh", id="refresh")
                    with Collapsible(title="Find an older analysis saved elsewhere"):
                        yield Input(
                            placeholder="Folder containing your saved analysis", id="import-path"
                        )
                        yield Button("Add to saved analyses", id="import")
            yield Static("Ready when you are.", id="activity", markup=False)
            yield LoadingIndicator(id="spinner")
            yield Static("", id="reset")
            with Horizontal():
                yield Button("Stop and save", variant="warning", id="stop", disabled=True)
                yield Button("Open sign-in page", id="browser")
            with Collapsible(title="Activity details"):
                yield RichLog(id="log", wrap=True, markup=False, max_lines=100)
            yield Static(
                "Sign-in stays in your password vault. Reports stay on this computer.",
                classes="help",
            )
        yield Footer()

    def on_mount(self) -> None:
        for widget_id in (
            "identity",
            "partition-label",
            "partition",
            "spec-label",
            "spec",
            "analyze",
            "browser",
            "spinner",
            "stop",
            "reset",
        ):
            self.query_one(f"#{widget_id}").display = False
        self.action_refresh()
        if self.saved:
            self.query_one("#tabs", TabbedContent).active = "saved-analyses"
            self.query_one("#saved", Select).focus()
        else:
            self.query_one("#character-url", Input).focus()

    def show_progress(self, message: str) -> None:
        self.query_one("#activity", Static).update(message)
        self.query_one("#log", RichLog).write(message)

    def show_browser(self, url: str) -> None:
        self.browser_url = url
        self.query_one("#browser").display = True

    def show_countdown(self, remaining: int) -> None:
        message = ""
        if remaining:
            minutes, seconds = divmod(remaining, 60)
            message = (
                f"Continuing in {minutes:02d}:{seconds:02d}. "
                "Warcraft Logs needs a rest. You can stop and return later."
            )
        self.query_one("#reset", Static).update(message)
        self.query_one("#reset").display = bool(remaining)
        if remaining and remaining % 30 == 0:
            self.action_refresh()

    def set_busy(self, value: bool) -> None:
        self.busy = value
        for widget_id in (
            "find",
            "connect",
            "analyze",
            "continue",
            "import",
            "refresh",
            "character-url",
            "spec",
            "partition",
        ):
            self.query_one(f"#{widget_id}").disabled = value
        self.query_one("#stop", Button).disabled = not value
        self.query_one("#stop").display = value
        self.query_one("#spinner").display = value
        if not value:
            finished_run = self.library.active_run
            self.library.active_run = None
            self.query_one("#browser").display = False
            self.show_countdown(0)
            self.action_refresh()
            if finished_run is not None:
                self.query_one("#tabs", TabbedContent).active = "saved-analyses"

    def start_operation(self, kind: str, run: SavedRun | None = None) -> None:
        if self.busy:
            return
        if kind == "identify":
            self.character_url = self.query_one("#character-url", Input).value.strip()
            self.context = None
            for widget_id in (
                "identity",
                "partition-label",
                "partition",
                "spec-label",
                "spec",
                "analyze",
            ):
                self.query_one(f"#{widget_id}").display = False
        self.stop_event = threading.Event()
        self.set_busy(True)
        if run is not None:
            self.library.active_run = run.out
            self.action_refresh(str(run.out))
        self.query_one("#stop", Button).focus()
        self.operation(kind, run)

    @work(thread=True, exit_on_error=False)
    def operation(self, kind: str, run: SavedRun | None) -> None:
        def notify(message: str) -> None:
            self.call_from_thread(self.show_progress, message)

        def browser(url: str) -> None:
            self.call_from_thread(self.show_browser, url)

        try:
            if kind == "connect":
                self.service.connect(self.stop_event, notify, browser)
            elif kind == "identify":
                context = self.service.identify(
                    self.character_url, self.stop_event, notify, browser
                )
                self.call_from_thread(self.show_character, context)
            elif kind == "partition":
                partition = self.call_from_thread(
                    lambda: self.query_one("#partition", Select).value
                )
                context = self.service.identify(
                    self.character_url, self.stop_event, notify, browser, int(partition)
                )
                self.call_from_thread(self.show_character, context)
            elif run is not None:
                if run.legacy:
                    run = self.library.recover_legacy(run)
                outcome = self.service.run(
                    run,
                    self.stop_event,
                    notify,
                    browser,
                    lambda remaining: self.call_from_thread(self.show_countdown, remaining),
                )
                self.call_from_thread(self.completed, run, outcome.code)
        except Stopped:
            notify("Stopped safely. Select your saved analysis below to continue later.")
        except Exception as error:
            notify(
                "Stopped safely. Your saved analyses are available below."
                if self.stop_event.is_set()
                else self.friendly_error(error)
            )
        finally:
            self.call_from_thread(self.set_busy, False)
            if self.quit_after_stop:
                self.call_from_thread(self.exit)

    @staticmethod
    def friendly_error(error: Exception) -> str:
        from necropsy.wcl.credentials import CredentialStoreError

        if isinstance(error, CredentialStoreError):
            return (
                "Your password vault is unavailable. Unlock Windows Credential Manager, "
                "macOS Keychain, or your Linux desktop's password wallet, then try Connect again. "
                "Linux needs a running Secret Service or KWallet desktop session."
            )
        return f"Needs attention: {error}"

    def show_character(self, context: CharacterContext) -> None:
        self.context = context
        name = CLASS_NAMES.get(context.class_id.value, "Unsupported class")
        faction = context.faction.value
        faction_name = getattr(faction, "value", "Faction unknown")
        self.query_one("#identity", Static).update(
            f"{context.name.value} · {name} · {faction_name}\n{context.server.value} · Naxxramas"
        )
        self.query_one("#identity").display = True
        if context.ambiguity:
            self.query_one("#partition", Select).set_options(
                [(p.name, str(p.id)) for p in context.partitions]
            )
            self.query_one("#partition").display = True
            self.query_one("#partition-label").display = True
            self.show_progress(
                "Choose which raid partition to use. We'll look it up automatically."
            )
            return
        if not context.same_faction_ready:
            self.show_progress(
                "Faction could not be verified. Try another Warcraft Logs character link."
            )
            return
        choices = categories(context.class_id.value)
        if not choices:
            self.show_progress("This character's class is not supported for Classic Era Naxxramas.")
            return
        selector = self.query_one("#spec", Select)
        selector.set_options(choices)
        selector.value = choices[0][1]
        for widget_id in ("spec", "spec-label"):
            self.query_one(f"#{widget_id}").display = len(choices) > 1
        self.query_one("#analyze").display = True
        self.query_one("#partition").display = False
        self.query_one("#partition-label").display = False
        self.show_progress(
            "Character found. Choose your spec, then Analyze my character."
            if len(choices) > 1
            else "Character found. Choose Analyze my character to begin."
        )

    def completed(self, run: SavedRun, code: int) -> None:
        self.show_progress("Your report is ready." if code == 0 else run.detail)
        self.action_refresh(str(run.out))
        if run.report is not None and not self.opener(run.report.as_uri()):
            self.show_progress(
                f"Your report is saved at {run.report}. Use Open report to try again."
            )

    def action_refresh(self, selected: str | None = None) -> None:
        try:
            self.saved = self.library.discover()
            selector = self.query_one("#saved", Select)
            old = selector.value
            selector.set_options(
                [(f"{run.title} · {run.when} · {run.status}", str(run.out)) for run in self.saved]
            )
            target = selected or (str(old) if old is not Select.BLANK else "")
            if self.saved:
                selector.value = (
                    target
                    if any(str(r.out) == target for r in self.saved)
                    else str(self.saved[0].out)
                )
            self.update_saved()
        except (OSError, ValueError, KeyError, TypeError, CacheError, AnalyzeError) as error:
            self.show_progress(f"Could not load the saved analyses: {error}")

    def selected_run(self) -> SavedRun | None:
        value = self.query_one("#saved", Select).value
        return next((run for run in self.saved if str(run.out) == value), None)

    def update_saved(self) -> None:
        run = self.selected_run()
        self.query_one("#continue", Button).disabled = self.busy or run is None or run.finished
        self.query_one("#report", Button).disabled = run is None or run.report is None
        self.query_one("#saved-detail", Static).update(
            "" if run is None else f"{run.title} · {run.when}\n{run.status}\n{run.detail}"
        )

    @on(Select.Changed, "#saved")
    def saved_changed(self) -> None:
        self.update_saved()

    @on(Select.Changed, "#partition")
    def partition_changed(self, event: Select.Changed) -> None:
        if event.value is not Select.BLANK and not self.busy:
            self.start_operation("partition")

    @on(Input.Submitted, "#character-url")
    def url_submitted(self) -> None:
        self.start_operation("identify")

    @on(Input.Changed, "#character-url")
    def url_changed(self, event: Input.Changed) -> None:
        if not self.busy and event.value.strip() != self.character_url:
            self.context = None
            for name in (
                "identity",
                "partition-label",
                "partition",
                "spec-label",
                "spec",
                "analyze",
            ):
                self.query_one(f"#{name}").display = False

    @on(Button.Pressed)
    def pressed(self, event: Button.Pressed) -> None:
        choice = event.button.id
        if choice in ("find", "connect"):
            self.start_operation("identify" if choice == "find" else "connect")
        elif choice == "analyze" and self.context is not None and not self.busy:
            value = self.query_one("#spec", Select).value
            if value is not Select.BLANK:
                try:
                    created = self.library.create(self.character_url, str(value), self.context)
                    self.start_operation("run", created)
                except (OSError, ValueError) as error:
                    self.show_progress(str(error))
        elif choice == "continue":
            run = self.selected_run()
            if run is not None:
                self.start_operation("run", run)
        elif choice == "report":
            run = self.selected_run()
            if run is not None and run.report is not None:
                self.opener(run.report.as_uri())
        elif choice == "browser" and self.browser_url is not None:
            self.opener(self.browser_url)
        elif choice == "stop":
            self.action_stop()
        elif choice == "refresh":
            self.action_refresh()
        elif choice == "import" and not self.busy:
            try:
                run = self.library.import_run(self.query_one("#import-path", Input).value.strip())
                self.action_refresh(str(run.out))
                self.show_progress("Saved analysis added. Select it above to open or continue.")
            except (OSError, ValueError, KeyError, TypeError, CacheError, AnalyzeError) as error:
                self.show_progress(f"Could not load that analysis: {error}")

    def action_stop(self) -> None:
        if self.busy:
            self.stop_event.set()
            self.show_progress(
                "Saving progress... An active request may take up to 30 seconds to stop."
            )
        else:
            self.exit()

    def action_request_quit(self) -> None:
        if self.busy:
            self.quit_after_stop = True
            self.action_stop()
        else:
            self.exit()


def launch() -> None:
    NecropsyApp().run()
