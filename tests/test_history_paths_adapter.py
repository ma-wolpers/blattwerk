from pathlib import Path

from app.storage.history_paths_adapter import (
    normalize_recent_entries,
    resolve_history_path,
    to_history_relative_path,
)


def test_resolve_history_path_keeps_absolute_paths():
    history_root = Path("a:/Code/blattwerk")
    absolute = Path("a:/Code/blattwerk/docs/ARCHITEKTUR.md")

    resolved = resolve_history_path(str(absolute), history_root)

    assert resolved == absolute


def test_to_history_relative_path_uses_root_relative_when_possible():
    history_root = Path("a:/Code/blattwerk")
    path = Path("a:/Code/blattwerk/docs/ARCHITEKTUR.md")

    relative = to_history_relative_path(path, history_root)

    assert relative == "docs/ARCHITEKTUR.md"


def test_normalize_recent_entries_deduplicates_and_caps():
    history_root = Path("a:/Code/blattwerk")
    entries = [
        "docs/ARCHITEKTUR.md",
        "docs/ARCHITEKTUR.md",
        "app/core/blatt_validator.py",
    ]

    normalized = normalize_recent_entries(entries, history_root, max_recent_files=2)

    assert normalized == ["docs/ARCHITEKTUR.md", "app/core/blatt_validator.py"]
