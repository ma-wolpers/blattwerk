"""History-path helpers used by UI persistence and recent-files handling."""

from __future__ import annotations

import os
from pathlib import Path

from .local_config_store import DEFAULT_HISTORY_ROOT_NAME, DEFAULT_MAX_RECENT_FILES

MAX_RECENT_FILES = DEFAULT_MAX_RECENT_FILES
HISTORY_ROOT_NAME = DEFAULT_HISTORY_ROOT_NAME


def find_history_root(anchor_name: str):
    """Find the top-level anchor folder used for relative history paths."""

    file_path = Path(__file__).resolve()
    for parent in file_path.parents:
        if parent.name.lower() == anchor_name.lower():
            return parent
    return file_path.parents[2]


def clean_path_text(path_text):
    """Normalize textual path entries from persisted values or user input."""

    return (path_text or "").strip().strip('"').strip("'")


def to_history_relative_path(path: Path, history_root: Path):
    """Convert absolute paths into history-root-relative paths when possible."""

    try:
        resolved = path.expanduser().resolve()
    except Exception:
        resolved = Path(path)

    try:
        relative_path = resolved.relative_to(history_root)
        return relative_path.as_posix()
    except ValueError:
        try:
            relative_path = os.path.relpath(str(resolved), str(history_root))
            return Path(relative_path).as_posix()
        except ValueError:
            return resolved.as_posix()


def resolve_history_path(path_text: str, history_root: Path):
    """Resolve a relative/absolute history entry into an absolute path."""

    cleaned = clean_path_text(path_text)
    if not cleaned:
        return Path(cleaned)

    candidate = Path(cleaned)
    if candidate.is_absolute():
        return candidate

    return (history_root / candidate).resolve()


def normalize_recent_entries(
    entries: list[str], history_root: Path, max_recent_files: int
):
    """Normalize, deduplicate and cap recent-file history entries."""

    normalized = []
    seen = set()

    for entry in entries:
        resolved = resolve_history_path(entry, history_root)
        relative_entry = to_history_relative_path(resolved, history_root)
        if relative_entry in seen:
            continue
        seen.add(relative_entry)
        normalized.append(relative_entry)

    return normalized[:max_recent_files]
