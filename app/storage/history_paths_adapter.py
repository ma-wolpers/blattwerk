"""Recent-file path helpers without root-anchor indirection."""

from __future__ import annotations

from pathlib import Path

from .local_config_store import DEFAULT_MAX_RECENT_FILES

MAX_RECENT_FILES = DEFAULT_MAX_RECENT_FILES


def clean_path_text(path_text):
    """Normalize textual path entries from persisted values or user input."""

    return (path_text or "").strip().strip('"').strip("'")


def normalize_recent_path(path: Path):
    """Normalize recent-file path to absolute POSIX string."""

    try:
        resolved = path.expanduser().resolve()
    except Exception:
        resolved = Path(path)

    return resolved.as_posix()


def resolve_recent_path(path_text: str):
    """Resolve a persisted recent-file entry into an absolute path."""

    cleaned = clean_path_text(path_text)
    if not cleaned:
        return Path(cleaned)

    candidate = Path(cleaned)
    try:
        return candidate.expanduser().resolve()
    except Exception:
        return candidate


def normalize_recent_entries(entries: list[str], max_recent_files: int):
    """Normalize, deduplicate and cap recent-file history entries."""

    normalized = []
    seen = set()

    for entry in entries:
        resolved = resolve_recent_path(entry)
        normalized_entry = normalize_recent_path(resolved)
        if normalized_entry in seen:
            continue
        seen.add(normalized_entry)
        normalized.append(normalized_entry)

    return normalized[:max_recent_files]
