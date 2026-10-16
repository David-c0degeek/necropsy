from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from necropsy.cli import app
from necropsy.desktop import launcher


def test_no_arguments_and_gui_command_open_desktop_without_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[str] = []
    monkeypatch.setattr(launcher, "launch", lambda: opened.append("gui"))
    for args in ([], ["gui"]):
        result = CliRunner().invoke(app, args)
        assert result.exit_code == 0, result.output
    assert opened == ["gui", "gui"]
    result = CliRunner().invoke(app, ["tui"])
    assert result.exit_code == 1
    assert "interactive terminal" in result.output
    assert opened == ["gui", "gui"]


def test_missing_gui_explains_recovery_without_silent_tui_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NECROPSY_GUI_PATH", str(tmp_path / "missing app"))
    result = CliRunner().invoke(app, [])
    assert result.exit_code == 1
    assert "one-line installer" in result.output


def test_configured_native_path_is_passed_without_a_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "app & spaces" / "gui"
    target.parent.mkdir()
    target.touch()
    monkeypatch.setenv("NECROPSY_GUI_PATH", str(target))
    calls: list[tuple[list[str], dict[str, object]]] = []

    def spawn(args: list[str], **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr("necropsy.desktop.launcher.subprocess.Popen", spawn)
    launcher.launch()
    assert calls[0][0] == [str(target)]
    assert not calls[0][1].get("shell")
