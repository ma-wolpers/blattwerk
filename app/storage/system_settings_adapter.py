"""Normalization helpers for persisted system settings."""

from __future__ import annotations

from .local_config_store import (
    DEFAULT_MAX_RECENT_FILES,
    MAX_MAX_RECENT_FILES,
    MIN_MAX_RECENT_FILES,
)


def normalize_system_settings_payload(system_settings):
    """Normalize recent-files limit from persisted settings."""

    max_recent_raw = (system_settings or {}).get(
        "max_recent_files", DEFAULT_MAX_RECENT_FILES
    )
    try:
        max_recent_files = int(max_recent_raw)
    except Exception:
        max_recent_files = DEFAULT_MAX_RECENT_FILES

    if max_recent_files < MIN_MAX_RECENT_FILES:
        max_recent_files = MIN_MAX_RECENT_FILES
    if max_recent_files > MAX_MAX_RECENT_FILES:
        max_recent_files = MAX_MAX_RECENT_FILES

    return {
        "max_recent_files": max_recent_files,
    }
