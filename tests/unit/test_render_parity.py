"""The receipt's content check binds each expected text, complete, to its own boss
section on each page; another boss's section or a shared prefix never counts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import render_parity as rp

TEXT_A = "Cleanse Impending Doom from the main tank first."
TEXT_B = "Stand at max range from Magmadar."


def site(
    tmp_path: Path, first: str, second: str, *, playbook: dict[str, object] | None = None
) -> Path:
    def boss(encounter: int, text: str) -> dict[str, object]:
        return {
            "encounter_id": encounter,
            "playbook": playbook
            or {"encounter_strategy": {"items": [{"text": text}]}, "class_notes": []},
        }

    analysis = {"bosses": [boss(1, TEXT_A), boss(2, TEXT_B)]}
    (tmp_path / "analysis.json").write_text(json.dumps(analysis), encoding="utf-8")
    sections = f'<section id="boss-1">{first}</section><section id="boss-2">{second}</section>'
    page = f"<main>{sections}</main>"
    for name in ("report.html", "playbook.html"):
        (tmp_path / name).write_text(page, encoding="utf-8")
    return tmp_path


def test_texts_in_their_own_sections_pass(tmp_path: Path) -> None:
    result = rp.content_check(site(tmp_path, f"<p>{TEXT_A}</p>", f"<p>{TEXT_B}</p>"))
    assert result["missing_texts"] == 0
    assert result["missing_sections"] == 0


def test_a_text_found_only_under_another_boss_is_missing(tmp_path: Path) -> None:
    result = rp.content_check(site(tmp_path, "", f"<p>{TEXT_A}</p><p>{TEXT_B}</p>"))
    assert result["missing_texts"] == 2  # boss 1's text, on both pages
    assert result["bosses"]["1"]["strategy"]["missing"]["report.html"] == [TEXT_A]


def test_a_shared_prefix_is_not_the_complete_text(tmp_path: Path) -> None:
    truncated = TEXT_A[: len(TEXT_A) - 10]
    result = rp.content_check(site(tmp_path, f"<p>{truncated}</p>", f"<p>{TEXT_B}</p>"))
    assert result["missing_texts"] == 2


def test_inline_markup_and_entities_read_as_the_reader_sees_them(tmp_path: Path) -> None:
    marked = "Cleanse <strong>Impending Doom</strong> from the main tank&nbsp;first."
    result = rp.content_check(site(tmp_path, f"<p>{marked}</p>", f"<p>{TEXT_B}</p>"))
    assert result["missing_texts"] == 0


def test_a_missing_section_and_an_unknown_layout_are_explicit(tmp_path: Path) -> None:
    (tmp_path / "x").mkdir()
    directory = site(tmp_path / "x", f"<p>{TEXT_A}</p>", f"<p>{TEXT_B}</p>")
    for name in ("report.html", "playbook.html"):
        (directory / name).write_text(f'<section id="boss-1"><p>{TEXT_A}</p></section>', "utf-8")
    result = rp.content_check(directory)
    assert result["missing_sections"] == 2
    assert result["bosses"]["2"]["sections_missing"] == ["playbook.html", "report.html"]
    (tmp_path / "y").mkdir()
    other = rp.content_check(site(tmp_path / "y", "", "", playbook={"something_else": 1}))
    assert other["unchecked_bosses"] == ["1", "2"]
    assert other["missing_texts"] == 0


def test_a_duplicate_section_id_is_refused(tmp_path: Path) -> None:
    directory = site(tmp_path, f"<p>{TEXT_A}</p>", f"<p>{TEXT_B}</p>")
    page = '<section id="boss-1"></section><section id="boss-1"></section>'
    (directory / "report.html").write_text(page, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate element id boss-1"):
        rp.content_check(directory)
