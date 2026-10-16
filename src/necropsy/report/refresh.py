"""Refresh derived report files while retaining saved-run ownership and source data."""

from __future__ import annotations

from pathlib import Path

from necropsy.report.package import ANALYSIS_FILE, build_outputs
from necropsy.report.publish import publish
from necropsy.wcl.analyze import LOCK, plain_dir
from necropsy.wcl.cache import is_link, item_lock
from necropsy.wcl.checkpoint import DIRECTORY, Checkpoint, saved_options


def refresh_saved_reports(out: Path) -> tuple[Path, ...]:
    """Re-render one existing analysis, without acquisition or analytical changes.

    Checkpoint finalization shares the publisher's ordinary-failure rollback.
    Like other report publication, this is not a crash-proof multi-file transaction;
    interrupted publication retains backups for the established recovery workflow.
    """
    if not out.is_dir():
        raise ValueError("The saved analysis folder is no longer available.")
    out = plain_dir(out, "saved analysis")
    with item_lock(out / LOCK):
        analysis = out / ANALYSIS_FILE
        if is_link(analysis) or not analysis.is_file():
            raise ValueError("The saved analysis must contain a plain analysis.json file.")
        checkpoint = None
        checkpoint_path = out / DIRECTORY / "run.json"
        if checkpoint_path.exists() or is_link(checkpoint_path) or is_link(out / DIRECTORY):
            options = saved_options(out)
            checkpoint = Checkpoint(out, options, resume=True)
        include_package = checkpoint is None or bool(checkpoint.state["options"]["package"])
        files = build_outputs(analysis.read_bytes(), include_package=include_package)
        # The analytical source and its timestamps remain untouched.
        files.pop(ANALYSIS_FILE)
        paths = [out / name for name, data in files.items() if data is not None]

        def finalize() -> None:
            if checkpoint is not None:
                for name, data in files.items():
                    if data is None:
                        checkpoint.state["outputs"].pop(name, None)
                checkpoint.record(paths)

        publish(out, files, finalize=finalize)
        return tuple(paths)
