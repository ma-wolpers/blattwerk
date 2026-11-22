"""Ein Durchlauf über den sichtbaren Text eines fertigen HTML-Dokuments.

Einzige Stelle, die weiß, welche Teile einer fertigen Seite Text sind, den ein Nachlauf
verändern darf. Genutzt von `emoji_markup.mark_emoji_glyphs` (Emoji-Klasse) und
`print_hyphenation.hyphenate_html` (Trennstellen); beide geben nur noch an, was mit einem
Stück reinem Text passieren soll.

Unverändert bleiben immer:

- alles vor ``<body>`` (Titel, Styles, Skripte); ein Fragment ohne ``<body>`` gilt ganz
  als Inhalt,
- Tags samt Attributen und Kommentare,
- Inhalte der übersprungenen Elemente (`DEFAULT_SKIPPED_ELEMENTS`, je Nachlauf erweiterbar;
  ein ``<span>`` in SVG-Text wäre z. B. ungültig),
- Bereiche, die ein Nachlauf zusätzlich schützt (etwa seine eigene Markierung, damit er
  idempotent bleibt),
- Formeln (``$…$``/``$$…$$``, erkannt über `find_math_span_ranges`), damit MathJax die
  LaTeX-Quelle unverändert sieht.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from functools import lru_cache

from .math_span_protection import find_math_span_ranges

DEFAULT_SKIPPED_ELEMENTS = ("script", "style", "svg", "textarea", "title")
"""Elemente, deren Inhalt kein Fließtext ist."""

_BODY_START_RE = re.compile(r"<body\b[^>]*>", re.IGNORECASE)


@lru_cache(maxsize=None)
def _protected_re(skipped_elements: tuple[str, ...], protected_pattern: str) -> re.Pattern:
    """Muster aller Bereiche, die der Durchlauf überspringt (zwischengespeichert je Nachlauf).

    Reihenfolge: Kommentare, übersprungene Elemente samt Inhalt, die eigene Schutzregel des
    Nachlaufs, zuletzt jeder einzelne Tag.
    """
    names = "|".join(re.escape(name) for name in skipped_elements)
    own = f"|{protected_pattern}" if protected_pattern else ""
    return re.compile(rf"<!--.*?-->|<({names})\b.*?</\1\s*>{own}|<[^>]*>", re.DOTALL | re.IGNORECASE)


def _map_segment(text: str, transform: Callable[[str], str]) -> str:
    """Wendet `transform` auf ein Textstück zwischen Tags an, Formeln ausgenommen."""
    if not text:
        return text
    parts: list[str] = []
    position = 0
    for start, end in find_math_span_ranges(text):
        parts.append(transform(text[position:start]))
        parts.append(text[start:end])
        position = end
    parts.append(transform(text[position:]))
    return "".join(parts)


def map_body_text(
    html: str,
    transform: Callable[[str], str],
    *,
    skipped_elements: tuple[str, ...] = DEFAULT_SKIPPED_ELEMENTS,
    protected_pattern: str = "",
) -> str:
    """Ersetzt jedes Stück sichtbaren Text im Body durch ``transform(stück)``.

    Args:
        html: Vollständiges Dokument oder Fragment.
        transform: Bekommt reinen Text (noch HTML-escaped, ohne Tags und Formeln) und
            liefert seinen Ersatz; darf eigene Tags einfügen.
        skipped_elements: Elemente, deren ganzer Inhalt unverändert bleibt.
        protected_pattern: Zusätzlicher Regex (ohne Gruppen-Rückbezüge) für Bereiche, die
            unverändert bleiben, z. B. die schon gesetzte eigene Markierung.

    Returns:
        Das Dokument mit ersetzten Textstücken; alles andere zeichengenau unverändert.

    Example:
        >>> map_body_text("<p title='a'>a $a$</p>", str.upper)
        "<p title='a'>A $a$</p>"
    """
    if not html:
        return html
    protected = _protected_re(tuple(skipped_elements), protected_pattern)
    body = _BODY_START_RE.search(html)
    head_end = body.end() if body else 0
    parts: list[str] = [html[:head_end]]
    position = head_end
    for match in protected.finditer(html, head_end):
        parts.append(_map_segment(html[position : match.start()], transform))
        parts.append(match.group(0))
        position = match.end()
    parts.append(_map_segment(html[position:], transform))
    return "".join(parts)
