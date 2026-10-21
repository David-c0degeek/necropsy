"""Independent rejection cases precede local-model trials and content promotion."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest

from scripts import guidance_lint as gl
from scripts import guidance_work_order as wo


@pytest.fixture
def bundle(tmp_path: Path) -> tuple[wo.Order, dict[str, Any]]:
    source: dict[str, Any] = {
        "boss": "Sapphiron",
        "encounter_id": 51119,
        "url": "https://example.invalid/Sapphiron",
        "excerpts": {
            "resistance": "The encounter requires frost resistance.",
            "healers": "Healers should avoid excessive frost resistance gear.",
            "spread": "Keep spread during ground phase.",
            "conflicted": "Obsolete claim.",
        },
        "conflicts": [{"keys": ["conflicted"], "issue": "unresolved"}],
    }
    path = tmp_path / "source.json"
    path.write_text(
        json.dumps({"retrieval": {"date": "2026-10-21"}, "sources": [source]}), encoding="utf-8"
    )
    order = wo.Order(
        id="draft-one",
        kind="guidance-draft-v1",
        input=wo.InputPin(path="source.json", sha256=wo.sha(path)),
        encounter_id=51119,
        boss="Sapphiron",
        class_id=7,
        faction="Alliance",
        metric="hps",
        category="Holy",
        allowed_keys=["resistance", "healers", "spread"],
        wall_seconds=600,
        max_output_tokens=4096,
        max_prompt_bytes=20000,
    )
    items = []
    for key in ("resistance", "healers"):
        items.append(
            {
                "rule": f"sapphiron-priest-{key}-v1",
                "section": "strategy",
                "classes": [7],
                "metrics": ["hps"],
                "source": source["url"],
                "retrieved": "2026-10-21",
                "text": source["excerpts"][key],
                "support": [key],
                "quotes": {key: source["excerpts"][key]},
            }
        )
    categories = {
        c: {"status": "unknown", "rules": [], "reason": wo.UNKNOWN} for c in gl.CATEGORIES
    }
    categories["preparation"] = {"status": "draft", "rules": [items[0]["rule"]], "reason": ""}
    categories["loadout"] = {"status": "draft", "rules": [items[1]["rule"]], "reason": ""}
    return order, {
        "order_id": order.id,
        "encounter_id": 51119,
        "boss": "Sapphiron",
        "items": items,
        "categories": categories,
    }


def _bytes(draft: dict[str, Any]) -> bytes:
    return json.dumps(draft).encode()


def test_supported_draft_passes_without_claiming_content_approval(
    bundle: Any, tmp_path: Path
) -> None:
    order, draft = bundle
    assert wo.verify(order, _bytes(draft), tmp_path) == []
    prompt = wo.prompt_for(order, tmp_path)
    assert "conflicted" not in json.loads(prompt.split("\n", 1)[1])["excerpts"]
    assert "output_schema" in prompt


@pytest.mark.parametrize(
    "case",
    [
        "fabricated_quote",
        "empty_support",
        "invented_support",
        "wrong_class",
        "wrong_metric",
        "wrong_source",
        "unsupported_timer",
        "fake_removal",
        "missing_position_boundary",
        "missing_category",
        "duplicate_rule",
        "unknown_advice",
        "wrong_identity",
        "extra_command",
    ],
)
def test_planted_defects_cannot_pass(bundle: Any, tmp_path: Path, case: str) -> None:
    order, original = bundle
    draft = copy.deepcopy(original)
    item = draft["items"][0]
    if case == "fabricated_quote":
        item["quotes"]["resistance"] = "The guide never said this."
    elif case == "empty_support":
        item["support"] = []
    elif case == "invented_support":
        item["support"] = ["fabricated"]
        item["quotes"] = {"fabricated": "Made up."}
    elif case == "wrong_class":
        item["classes"] = [3]
    elif case == "wrong_metric":
        item["metrics"] = ["dps"]
    elif case == "wrong_source":
        item["source"] = "https://wrong.invalid"
    elif case == "unsupported_timer":
        item["text"] = "The air phase begins after 123 seconds."
    elif case == "fake_removal":
        item["text"] = "Priests can remove curses according to the cited source."
    elif case == "missing_position_boundary":
        item["text"] = "Stand away from blizzards."
    elif case == "missing_category":
        del draft["categories"]["utility"]
    elif case == "duplicate_rule":
        draft["items"][1]["rule"] = item["rule"]
    elif case == "unknown_advice":
        draft["categories"]["utility"]["reason"] = "Unknown, but Priests should cleanse."
    elif case == "wrong_identity":
        draft["encounter_id"] = 51118
    else:
        draft["command"] = "do something outside the draft folder"
    try:
        findings = wo.verify(order, _bytes(draft), tmp_path)
    except ValueError:
        return
    assert findings


def test_conflicts_and_input_drift_are_rejected_before_a_prompt(
    bundle: Any, tmp_path: Path
) -> None:
    order, _ = bundle
    bad = order.model_copy(update={"allowed_keys": ["conflicted"]})
    with pytest.raises(ValueError, match="conflicting"):
        wo.prompt_for(bad, tmp_path)
    (tmp_path / "source.json").write_bytes(b"changed")
    with pytest.raises(ValueError, match="pin"):
        wo.prompt_for(order, tmp_path)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.mark.parametrize("case", ["good", "schema", "timeout", "mutation"])
def test_runner_uses_native_ask_with_caps_and_detects_even_untracked_mutation(
    bundle: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    order, draft = bundle
    (tmp_path / ".gitignore").write_text("drafts/\n", encoding="utf-8")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "input")
    fake_binary = tmp_path / "fake-localpilot"
    fake_binary.write_bytes(b"test executable")
    monkeypatch.setattr(shutil, "which", lambda _: str(fake_binary))
    actual_run = subprocess.run

    def invoke(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if command[0] == "git":
            return actual_run(command, **kwargs)
        assert command[:4] == [str(fake_binary), "ask", "--provider", "bounded-local"]
        assert kwargs["timeout"] == 600
        cwd = Path(kwargs["cwd"])
        assert (cwd / "prompt.txt").read_bytes() == command[-1].encode("utf-8")
        config = tomllib.loads((cwd / ".localpilot.toml").read_text(encoding="utf-8"))
        assert config["providers"]["bounded-local"]["max_tokens"] == 4096
        assert config["research"]["web"]["enabled"] is False
        assert "127.0.0.1" in config["providers"]["bounded-local"]["base_url"]
        if case == "timeout":
            raise subprocess.TimeoutExpired(command, 600, output=b"partial", stderr=b"stall")
        if case == "mutation":
            (tmp_path / "outside.txt").write_text("unexpected", encoding="utf-8")
        return subprocess.CompletedProcess(
            command, 0, b"{}" if case == "schema" else _bytes(draft), b""
        )

    monkeypatch.setattr(subprocess, "run", invoke)
    receipt = wo.run(
        order, tmp_path / "drafts", "local-model", "http://127.0.0.1:11435/v1", tmp_path
    )
    assert receipt["mechanical_pass"] is (case == "good")
    assert receipt["content_review"] == "pending"
    assert receipt["input_tokens"] is None and receipt["output_tokens"] is None
    out = tmp_path / "drafts" / order.id
    assert (out / "packet.json").is_file() and (out / "run.json").is_file()
    if case == "timeout":
        assert (out / "draft.json").read_bytes() == b"partial"
    if case == "mutation":
        assert receipt["tree_mutation"]


def test_nonlocal_provider_is_rejected_before_any_process_or_write(
    bundle: Any, tmp_path: Path
) -> None:
    order, _ = bundle
    with pytest.raises(ValueError, match="loopback"):
        wo.run(order, tmp_path / "drafts", "model", "https://example.com/v1", tmp_path)
    assert not (tmp_path / "drafts").exists()
