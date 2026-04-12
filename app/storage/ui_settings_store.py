"""Persistenz-Helfer für UI-Einstellungen (z. B. Theme)."""

from __future__ import annotations

import json


def load_ui_settings(store_path):
    """Lädt UI-Einstellungen aus JSON oder liefert Defaults."""
    if not store_path.exists():
        return {}

    try:
        data = json.loads(store_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def save_ui_settings(store_path, settings):
    """Speichert UI-Einstellungen als JSON."""
    payload = settings if isinstance(settings, dict) else {}
    store_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
