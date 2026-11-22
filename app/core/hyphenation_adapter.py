"""Pyphen-Adapter: Silbentrennung eines einzelnen Worts nach Wörterbuch.

Einzige Stelle, die Pyphen-APIs benennt (`language_fallback`, `Pyphen(lang=...)`,
`Pyphen.inserted`). `print_hyphenation.py` kennt nur `hyphenator_for`; ändert sich das
Verhalten einer Pyphen-Version, ist nur diese Datei betroffen.

Verifizierte Pyphen-Eigenheiten (0.18.1), auf denen die Funktionen hier aufbauen:

- ``language_fallback("pt_BR")`` liefert ``"pt_BR"``, ``language_fallback("de")`` ``"de"``
  und für unbekannte Sprachen ``None`` (kein Fehler). Bindestrich-Codes wie ``pt-BR``
  versteht es nicht; deshalb wird ``-`` vorher zu ``_``.
- ``Pyphen(lang=..., left=2, right=2)`` lädt das LibreOffice-Wörterbuch; ``left``/``right``
  sind die Mindestzahl Buchstaben vor bzw. nach einer Trennstelle.
- ``inserted(word, hyphen=...)`` gibt das Wort mit eingefügtem Trennzeichen an jeder
  erlaubten Stelle zurück und lässt Wörter ohne Trennstelle unverändert.

Fehlt Pyphen (unvollständige Installation), liefert `hyphenator_for` immer ``None``:
Der Druck läuft dann wie vor der Silbentrennung weiter, statt abzubrechen.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

try:
    import pyphen
except ImportError:
    pyphen = None

PYPHEN_AVAILABLE = pyphen is not None
SOFT_HYPHEN = "­"
"""Weicher Trennstrich: unsichtbar, außer der Browser bricht genau dort um."""

MIN_FRAGMENT = 2
"""Mindestens so viele Buchstaben bleiben vor und nach einer Trennstelle stehen."""


@lru_cache(maxsize=None)
def _dictionary_name(language: str) -> str | None:
    """Pyphen-Wörterbuchname zu einem `<html lang>`-Wert oder ``None``.

    Example:
        >>> _dictionary_name("pt-BR") if PYPHEN_AVAILABLE else "pt_BR"
        'pt_BR'
    """
    if pyphen is None or not language:
        return None
    return pyphen.language_fallback(language.strip().replace("-", "_"))


@lru_cache(maxsize=None)
def hyphenator_for(language: str) -> Callable[[str], str] | None:
    """Liefert eine Funktion, die ein Wort mit weichen Trennstrichen versieht.

    Args:
        language: Wert des `<html lang>`-Attributs, z. B. ``de`` oder ``pt-BR``.

    Returns:
        ``wort -> wort mit U+00AD`` oder ``None``, wenn es für die Sprache kein
        Wörterbuch gibt (oder Pyphen fehlt). Ergebnisse je Wort werden zwischengespeichert,
        weil dieselben Wörter in einem Dokument oft vorkommen.

    Example:
        >>> hyphenate = hyphenator_for("de")
        >>> hyphenate("Stellenwerttafel").count(SOFT_HYPHEN) if hyphenate else 4
        4
    """
    name = _dictionary_name(language)
    if name is None:
        return None
    dictionary = pyphen.Pyphen(lang=name, left=MIN_FRAGMENT, right=MIN_FRAGMENT)

    @lru_cache(maxsize=4096)
    def hyphenate(word: str) -> str:
        """Setzt weiche Trennstriche an alle laut Wörterbuch erlaubten Stellen."""
        return dictionary.inserted(word, hyphen=SOFT_HYPHEN)

    return hyphenate
