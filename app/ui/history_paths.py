"""Hilfsfunktionen für Verlaufspfade und UI-Storage-Dateien."""

from __future__ import annotations

import os
from pathlib import Path

from ..storage.local_config_store import (
    DEFAULT_HISTORY_ROOT_NAME,
    DEFAULT_MAX_RECENT_FILES,
    LEGACY_RECENT_FILES_PATH,
    LEGACY_UI_SETTINGS_PATH,
    LOCAL_CONFIG_PATH,
    STORAGE_STATE_DIR,
)

MAX_RECENT_FILES = DEFAULT_MAX_RECENT_FILES
HISTORY_ROOT_NAME = DEFAULT_HISTORY_ROOT_NAME


def find_history_root(anchor_name: str):
    """Sucht den übergeordneten Projektordner für relative Verlaufspfade."""
    file_path = Path(__file__).resolve()
    for parent in file_path.parents:
        if parent.name.lower() == anchor_name.lower():
            return parent
    return file_path.parents[2]


def clean_path_text(path_text):
    """Bereinigt Pfadtexte um Leerzeichen und umschließende Anführungszeichen."""
    return (path_text or "").strip().strip('"').strip("'")


def to_history_relative_path(path: Path, history_root: Path):
    """Konvertiert absolute Dateipfade in Verlaufspfade relativ zu `history_root`."""
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
    """Löst Verlaufseinträge (relativ/absolut) in absolute Dateipfade auf."""
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
    """Normalisiert Verlaufseinträge auf relative Pfade und entfernt Duplikate."""
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
