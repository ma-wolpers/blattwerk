"""Persistenz-Helfer für die Liste zuletzt geöffneter Dateien."""

from __future__ import annotations

import json


def load_recent_files(store_path, max_recent_files):
    """Lädt die letzten Dateien aus JSON oder liefert leere Liste."""
    if not store_path.exists():
        return []

    try:
        data = json.loads(store_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    loaded = data.get("recent_files", []) if isinstance(data, dict) else []
    return [str(item) for item in loaded if str(item).strip()][:max_recent_files]


def save_recent_files(store_path, recent_files, max_recent_files):
    """Speichert die letzten Dateien als JSON."""
    payload = {"recent_files": recent_files[:max_recent_files]}
    store_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_recent_file(recent_files, path_text, max_recent_files):
    """Fügt einen Eintrag hinzu, entfernt Duplikate und begrenzt Länge."""
    cleaned = [item for item in recent_files if item != path_text]
    cleaned.insert(0, path_text)
    return cleaned[:max_recent_files]


def remove_recent_file(recent_files, path_text):
    """Entfernt einen Verlaufseintrag."""
    return [item for item in recent_files if item != path_text]
