"""Render the offline HTML report and playbook from analysis.json alone.

Templates are package data and every page is self-contained: CSS and JavaScript
are inlined, nothing is fetched, and all document text is escaped by Jinja's
autoescaping. Rendering the same analysis.json bytes twice gives identical pages.
"""

from __future__ import annotations

import hashlib
import json
from functools import cache
from importlib import resources
from typing import Any

from jinja2 import Environment, FunctionLoader, StrictUndefined
from markupsafe import Markup

from necropsy import __version__
from necropsy.report.analysis_json import AnalysisDocument
from necropsy.report.render.view import DocumentView, document_view

_PACKAGE = "necropsy.report.render"


class RenderError(ValueError):
    """analysis.json passed the envelope schema but lacks data the pages need."""


def build_view(document: dict[str, Any], analysis_sha: str) -> DocumentView:
    """The view model, with missing nested data reported as a RenderError."""
    try:
        return document_view(document, analysis_sha)
    except KeyError as exc:
        raise RenderError(
            f"analysis.json lacks data the report needs: {exc.args[0] if exc.args else exc}"
        ) from exc


def _read(kind: str, name: str) -> str:
    return resources.files(_PACKAGE).joinpath(kind, name).read_text(encoding="utf-8")


@cache
def _environment() -> Environment:
    env = Environment(
        loader=FunctionLoader(lambda name: _read("templates", name)),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    return env


def _assets() -> dict[str, Markup]:
    # The assets are our own files, not document data: safe to inline verbatim.
    return {
        "css": Markup(_read("assets", "report.css")),  # noqa: S704
        "js": Markup(_read("assets", "report.js")),  # noqa: S704
    }


def load_document(analysis: bytes) -> tuple[dict[str, Any], str]:
    """Parse and validate analysis.json bytes; returns (document, sha256 of the bytes)."""
    document = json.loads(analysis.decode("utf-8"))
    AnalysisDocument.model_validate(document)
    return document, hashlib.sha256(analysis).hexdigest()


def view_of(analysis: bytes) -> DocumentView:
    document, sha = load_document(analysis)
    return build_view(document, sha)


def _render(template: str, view: DocumentView, page: str) -> str:
    html = (
        _environment()
        .get_template(template)
        .render(doc=view, page=page, renderer_version=__version__, **_assets())
    )
    return html.replace("\r\n", "\n")


def render_report(view: DocumentView) -> str:
    template = "class-report.html.j2" if view.class_document else "report.html.j2"
    return _render(template, view, "report")


def render_playbook(view: DocumentView) -> str:
    template = "class-report.html.j2" if view.class_document else "playbook.html.j2"
    return _render(template, view, "playbook")


__all__ = [
    "RenderError",
    "build_view",
    "load_document",
    "render_playbook",
    "render_report",
    "view_of",
]
