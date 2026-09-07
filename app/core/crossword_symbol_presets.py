"""Kindgerechte Emoji-Themen für Crossword-Positionsstile (`numbering=symbols`).

Bewusst eine kleine, reine Daten-API: ein Theme liefert ausschließlich eine
geordnete Label-Sequenz, kein Layout-/Positionswissen. Die Zuordnung
Position -> Label bleibt Sache des Aufrufers (`answer_special_crossword.py`):
`theme.labels[index - 1]`, wobei `index` der bereits vorhandene 1-basierte
Wert aus der bestehenden Nummerierung (`crossword_numbering.py`) bzw. der
1-basierte Index in `CrosswordCodeSelection.letters` ist. Dieses Modul zählt
und traversiert nie selbst -- sonst entstünde eine zweite Quelle der
Wahrheit für "welche Position bekommt welches Label".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolTheme:
    """Ein benanntes, geordnetes Emoji-Set."""

    name: str
    labels: tuple[str, ...]


ALL_SYMBOL_THEMES: tuple[SymbolTheme, ...] = (
    SymbolTheme(
        "fruits",
        (
            "🍎", "🍌", "🍇", "🍊", "🍓", "🍉", "🍒", "🍑", "🍍", "🥝",
            "🥭", "🍐", "🍋", "🍈", "🫐", "🍏", "🥥", "🍅", "🥑", "🫒",
            "🍆", "🥕", "🌽", "🥒",
        ),
    ),
    SymbolTheme(
        "animals",
        (
            "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯",
            "🦁", "🐮", "🐷", "🐸", "🐵", "🐔", "🐧", "🐦", "🦆", "🦉",
            "🐺", "🐗", "🐴", "🦄",
        ),
    ),
    SymbolTheme(
        "plants",
        (
            "🌳", "🌵", "🌻", "🌹", "🌷", "🌼", "🌸", "🍀", "🌿", "🌱",
            "🍁", "🍄", "🌾", "🌴", "🎋", "🪴", "🌺", "🌰", "🍂", "🍃",
            "🌲", "🥀", "🪷", "🪻",
        ),
    ),
)

SYMBOL_THEME_NAMES: frozenset[str] = frozenset(theme.name for theme in ALL_SYMBOL_THEMES)


def symbol_theme_by_name(name: str) -> SymbolTheme | None:
    """Liefert das `SymbolTheme` mit gegebenem `name`, oder `None`."""
    for theme in ALL_SYMBOL_THEMES:
        if theme.name == name:
            return theme
    return None
