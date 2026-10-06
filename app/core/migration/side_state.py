"""Begleitzustand der Migration: delta-basiert und mit kanonischem Pfadvergleich.

Pro migriertem Item wird nur ein Delta `alt → neu` angewendet (Recent-Files
und Keys quittierter Warnungen); Undo wendet das inverse Delta nur für
tatsächlich zurückgenommene Items an. Es werden nie Config-Snapshots
zurückgeschrieben (R6-1).

Vergleiche laufen über `canonical_path_key` (R7-2): absolut, `/` statt `\\`,
unter Windows ohne Rücksicht auf Groß/Klein, ohne abschließende Trenner. Der
**geschriebene** Wert behält die Schreibweise des neuen Pfads.
"""

from __future__ import annotations

import ntpath
import os
import sys
from pathlib import Path


def canonical_path_key(path: str | Path, *, windows: bool | None = None) -> str:
    """Vergleichsform eines Pfads (nur zum Vergleichen, nie zum Speichern)."""
    use_windows = (sys.platform == "win32") if windows is None else windows
    text = str(path).strip()
    if use_windows:
        normalized = ntpath.normpath(ntpath.abspath(text) if sys.platform == "win32" else text)
        normalized = ntpath.normcase(normalized).replace("\\", "/")
    else:
        normalized = os.path.normpath(os.path.abspath(text))
    return normalized.rstrip("/") or "/"


def rename_entries(entries: list[str], old: str, new: str, *, to_storage) -> tuple[list[str], bool]:
    """Ersetzt in `entries` jeden Eintrag, der kanonisch `old` entspricht, durch `to_storage(new)`.

    Returns:
        ``(neue_liste, geändert)``; andere Einträge bleiben unverändert.
    """
    old_key = canonical_path_key(old)
    changed = False
    result = []
    for entry in entries:
        if canonical_path_key(entry) == old_key:
            result.append(to_storage(new))
            changed = True
        else:
            result.append(entry)
    return result, changed


class InMemorySideStateStore:
    """Test- und Referenzimplementierung des `SideStateStore`-Ports."""

    def __init__(self, recent_files=None, acknowledged=None) -> None:
        self.recent_files = list(recent_files or [])
        self.acknowledged = dict(acknowledged or {})

    def apply_rename(self, old: str, new: str) -> None:
        self.recent_files, _ = rename_entries(self.recent_files, old, new, to_storage=lambda p: Path(p).as_posix())
        old_key = canonical_path_key(old)
        for key in list(self.acknowledged):
            if canonical_path_key(key) == old_key:
                self.acknowledged[Path(new).as_posix()] = self.acknowledged.pop(key)
