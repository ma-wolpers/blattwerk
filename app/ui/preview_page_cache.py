"""Cache der gerasterten Vorschauseiten über alle Tabs und Ansichten.

Ein Eintrag je Schlüssel statt eines Platzes pro Tab: Beim Wechsel zwischen Aufgabe und
Lösung oder A4 und A5 bleibt der vorige Stand erhalten, und der Wechsel zurück braucht
keinen Druck. Die Speichergrenze gilt daher für die ganze App.

Der Schlüssel (`_build_preview_cache_key`) kennt den Inhalt und die Optionen, aber nicht die
eingebundenen Bilder, denn die stehen erst im fertigen HTML. Deshalb merkt sich jeder Eintrag
die Dateien, die der Druck gemeldet hat, und gilt nur, solange sie unverändert sind.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from ..core.render_job import RenderObserver

DEFAULT_BUDGET_BYTES = 400 * 1024 * 1024
_BYTES_PER_PIXEL = 4
"""Pillow legt auch RGB-Bilder mit 4 Byte je Pixel ab."""


def _file_state(path: Path) -> tuple[int, int] | None:
    """Änderungszeit und Größe einer Datei; None, wenn sie fehlt."""
    try:
        stats = path.stat()
    except OSError:
        return None
    return stats.st_mtime_ns, stats.st_size


class FileDependencyCollector(RenderObserver):
    """Sammelt während eines Laufs den Zustand aller gemeldeten lokalen Dateien."""

    def __init__(self) -> None:
        self.dependencies: dict[Path, tuple[int, int] | None] = {}

    def file_dependency(self, path: Path) -> None:
        """Merkt sich den Zustand der Datei; eine fehlende Datei zählt auch (Auftauchen)."""
        self.dependencies[path] = _file_state(path)


@dataclass(frozen=True)
class CachedPreview:
    """Ein gespeichertes Vorschau-Ergebnis.

    Attributes:
        images: Die gerasterten Seiten.
        diagnostics: Compile-Warnungen des Laufs, damit sie auch bei Treffern gelten.
        dependencies: Zustand der eingebundenen Dateien zum Zeitpunkt des Drucks.
        path: Quelldatei, für `PreviewPageCache.drop`.
    """

    images: tuple
    diagnostics: tuple
    dependencies: dict
    path: str

    @property
    def size_bytes(self) -> int:
        """Geschätzter Speicherbedarf der Seiten."""
        return sum(image.width * image.height * _BYTES_PER_PIXEL for image in self.images)

    def is_current(self) -> bool:
        """True, solange keine eingebundene Datei sich geändert hat oder neu aufgetaucht ist."""
        return all(_file_state(path) == state for path, state in self.dependencies.items())


class PreviewPageCache:
    """LRU-Cache mit Speichergrenze; der zuletzt gespeicherte Eintrag bleibt immer erhalten."""

    def __init__(self, budget_bytes: int = DEFAULT_BUDGET_BYTES) -> None:
        self._budget = budget_bytes
        self._entries: OrderedDict[object, CachedPreview] = OrderedDict()

    def get(self, key) -> CachedPreview | None:
        """Liefert den gültigen Eintrag und markiert ihn als zuletzt genutzt.

        Ein Eintrag mit geänderten Dateien wird entfernt, damit er keinen Speicher belegt.
        """
        entry = self._entries.get(key)
        if entry is None:
            return None
        if not entry.is_current():
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return entry

    def put(self, key, entry: CachedPreview) -> None:
        """Speichert einen Eintrag und verdrängt die ältesten, bis die Grenze passt.

        Ein Eintrag, der allein über der Grenze liegt, wird nicht gespeichert. Angezeigt wird
        er trotzdem, nur der nächste Wechsel druckt dann neu.
        """
        self._entries.pop(key, None)
        if entry.size_bytes > self._budget:
            return
        self._entries[key] = entry
        while sum(item.size_bytes for item in self._entries.values()) > self._budget:
            self._entries.popitem(last=False)

    def drop(self, path: str) -> None:
        """Entfernt alle Einträge einer Quelldatei, etwa beim Schließen ihres Tabs."""
        for key in [key for key, entry in self._entries.items() if entry.path == path]:
            del self._entries[key]
