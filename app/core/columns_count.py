"""Spaltenzahl eines `:::columns`-Bereichs: Grenzen und das Lesen von `cols=`.

Renderer (`blatt_kern_layout_columns.py`), Validator
(`blatt_validator_columns.py`) und das Block-Einfügen im Editor brauchen
dieselbe Vorstellung davon, wie viele Spalten ein Bereich hat. Vorher stand
die Klemmung 2..6 an drei Stellen, das Lesen von `cols=` an zwei.
"""

from __future__ import annotations

COLUMNS_MIN = 2
"""Weniger als zwei Spalten sind kein Spaltenbereich."""

COLUMNS_MAX = 6
"""Mehr Spalten passen nicht sinnvoll auf eine Seite; der Renderer schneidet ab."""

COLUMNS_DEFAULT = 2
"""Spaltenzahl ohne (lesbares) `cols=`."""


def clamp_columns_count(count: int) -> int:
    """Begrenzt eine Spaltenzahl auf `COLUMNS_MIN`..`COLUMNS_MAX`."""
    return max(COLUMNS_MIN, min(int(count), COLUMNS_MAX))


def resolve_columns_count(options) -> int:
    """Spaltenzahl aus den Optionen eines `columns`-Kopfes (`cols=`), begrenzt.

    Fehlt `cols` oder ist der Wert keine ganze Zahl, gilt `COLUMNS_DEFAULT`.
    """
    try:
        raw = int((options or {}).get("cols", COLUMNS_DEFAULT))
    except (TypeError, ValueError):
        raw = COLUMNS_DEFAULT
    return clamp_columns_count(raw)
