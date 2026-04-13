from pathlib import Path

from app.storage.history_paths_adapter import (
    normalize_recent_path,
    normalize_recent_entries,
    resolve_recent_path,
)


def test_resolve_recent_path_keeps_absolute_paths():
    absolute = Path("a:/Code/blattwerk/docs/ARCHITEKTUR.md")

    resolved = resolve_recent_path(str(absolute))

    assert str(resolved).endswith("docs\\ARCHITEKTUR.md") or str(resolved).endswith("docs/ARCHITEKTUR.md")


def test_normalize_recent_path_returns_absolute_posix_text():
    path = Path("a:/Code/blattwerk/docs/ARCHITEKTUR.md")

    normalized = normalize_recent_path(path)

    assert normalized.endswith("/docs/ARCHITEKTUR.md")


def test_normalize_recent_entries_deduplicates_and_caps():
    entries = [
        "a:/Code/blattwerk/docs/ARCHITEKTUR.md",
        "a:/Code/blattwerk/docs/ARCHITEKTUR.md",
        "a:/Code/blattwerk/app/core/blatt_validator.py",
    ]

    normalized = normalize_recent_entries(entries, max_recent_files=2)

    assert normalized[0].endswith("/docs/ARCHITEKTUR.md")
    assert normalized[1].endswith("/app/core/blatt_validator.py")
