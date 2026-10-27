"""Staging for exported files: build privately, publish to the target in one step.

Why: Chromium's ``--print-to-pdf`` writes straight to the path it is given. With the
target still open in a viewer that write fails *silently*, the old PDF stays on disk,
and every later step (operator legends, running elements) worked on - or reported
success with - that stale file. Now every PDF is printed and post-processed in a
private temp folder; only `publish_export_file` touches the real target.

Publishing copies the finished file to a hidden sibling of the target (same folder, so
the final `os.replace` stays atomic and sync clients never see a half-written file)
and replaces the target. A lock that appeared *during* the build is handled with the
same `ExportTargetPolicy` as the pre-check in `validate_export_output_path`.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .blatt_kern_io_pdf import write_pdf_from_html
from .export_path_guardrails import (
    LOCK_POLICY_ALTERNATE,
    ExportTargetPolicy,
    LockedExportTargetError,
    alternate_target_names,
)

PUBLISH_ATTEMPTS = 4
PUBLISH_RETRY_DELAY_SECONDS = 0.25
"""Short, bounded retry for locks that sync clients hold only for a moment."""

_HIDDEN_PREFIX = ".~blattwerk-"
_LOCK_WINERRORS = {5, 32, 33}


@dataclass
class StagedExport:
    """Work file of one staged export; `published_path` is set after a successful exit."""

    work_path: Path
    target: Path
    published_path: Path | None = None


@contextmanager
def staged_export(target, target_policy: ExportTargetPolicy | None = None):
    """Yield a `StagedExport` whose ``work_path`` lives in a private temp folder.

    On normal exit the work file is published to ``target`` (see
    `publish_export_file`); on an exception nothing is published. The temp folder is
    always removed.

    Example:
        >>> with staged_export(Path("out.pdf")) as staged:  # doctest: +SKIP
        ...     render(staged.work_path)
        >>> staged.published_path  # doctest: +SKIP
    """
    target = Path(target)
    with tempfile.TemporaryDirectory(prefix="blattwerk-export-") as temp_dir:
        staged = StagedExport(work_path=Path(temp_dir) / f"export{target.suffix}", target=target)
        yield staged
        staged.published_path = publish_export_file(staged.work_path, target, target_policy)


def publish_export_file(work_path, target, target_policy: ExportTargetPolicy | None = None) -> Path:
    """Move the finished ``work_path`` onto ``target``; returns the path actually written.

    Raises:
        RuntimeError: The build produced no file.
        LockedExportTargetError: Target stays locked and the policy is "error" (or no
            alternate name is free).
    """
    work_path, target = Path(work_path), Path(target)
    if not work_path.exists():
        raise RuntimeError("Export-Datei wurde nicht erstellt.")
    target.parent.mkdir(parents=True, exist_ok=True)

    candidates = [target]
    if target_policy is not None and target_policy.lock_policy == LOCK_POLICY_ALTERNATE:
        candidates.extend(c for c in alternate_target_names(target) if c != target)
    for candidate in candidates:
        if _replace_into(work_path, candidate):
            return candidate
    raise LockedExportTargetError(target)


def write_document_output(html: str, target, target_policy: ExportTargetPolicy | None = None, render_pdf=None) -> Path:
    """Write ``html`` as HTML or (via staging) PDF, chosen by the target's suffix.

    The shared tail of every HTML->PDF exporter (Schild, Markdown, Erwartungshorizont).

    Args:
        html: Complete HTML document.
        target: Already validated target path (``.html`` or ``.pdf``).
        target_policy: Locked-target handling for the publish step.
        render_pdf: ``(html, pdf_path) -> path`` printer. Callers pass their own module's
            `write_pdf_from_html`, so tests can keep patching it there; ``None`` uses the
            Chromium printer (resolved at call time, not import time).
    """
    render_pdf = render_pdf or write_pdf_from_html
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix.lower() == ".html":
        target.write_text(html, encoding="utf-8")
        return target
    with staged_export(target, target_policy) as staged:
        render_pdf(html, staged.work_path)
    return staged.published_path


def _replace_into(work_path: Path, candidate: Path) -> bool:
    """Copy to a hidden sibling of ``candidate`` and replace it; False if it stays locked."""
    hidden = candidate.with_name(f"{_HIDDEN_PREFIX}{os.getpid()}-{candidate.name}")
    try:
        shutil.copyfile(work_path, hidden)
        for attempt in range(PUBLISH_ATTEMPTS):
            try:
                os.replace(hidden, candidate)
                return True
            except OSError as error:
                if not _is_lock_error(error):
                    raise
                if attempt + 1 < PUBLISH_ATTEMPTS:
                    time.sleep(PUBLISH_RETRY_DELAY_SECONDS)
        return False
    finally:
        hidden.unlink(missing_ok=True)


def _is_lock_error(error: OSError) -> bool:
    """True for "file is open elsewhere" errors (Windows sharing/access violations)."""
    return isinstance(error, PermissionError) or getattr(error, "winerror", None) in _LOCK_WINERRORS
