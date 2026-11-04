"""Formgrößen der ER-Diagramme: Rechtecke, Rauten und Ovale passend zum umbrochenen Text.

Einzige Quelle für alle Maße, die Anordnung (`diagram_er_layout`), Kantenführung
(`diagram_er_route`) und Zeichnung (`diagram_er`) gemeinsam brauchen.
"""

from __future__ import annotations

from .diagram_svg import LINE_HEIGHT, balanced_lines, text_width

ENTITY_HEIGHT = 32.0
DIAMOND_HEIGHT = 42.0
OVAL_HEIGHT = 28.0
"""Höhe einzeiliger Formen; jede weitere Namenszeile macht sie höher."""
RING_GAP = 15.0
"""Abstand des Attributrings von seiner Form."""
RECURSIVE_DROP = 34.0
"""Abstand einer rekursiven Raute von ihrer Entität."""
_WRAP_ENTITY = 120.0
_WRAP_OVAL = 150.0
"""Textbreite, ab der der Name einer Entität bzw. ein Attribut umbricht (Rauten: `title_box`)."""


def _box(lines: list[str]) -> tuple[float, int]:
    """Breite der breitesten Zeile und Zeilenzahl."""
    return max(text_width(line) for line in lines), len(lines)


def _diamond_size(text_width_: float, lines: int) -> tuple[float, float]:
    """Raute, in deren Seiten die Ecken des Textblocks gerade noch liegen.

    Bedingung `(b/2) / B + (h/2) / H <= 1` für Textbreite `b`, Texthöhe `h` und die
    Rautenhalbachsen `B`, `H`; jede weitere Zeile macht die Raute etwas höher.
    """
    height = DIAMOND_HEIGHT + (lines - 1) * LINE_HEIGHT * 1.5
    return text_width_ / (1 - lines * LINE_HEIGHT / height) + 12, height


def title_box(node) -> tuple[float, int]:
    """Breite der breitesten Zeile und Zeilenzahl des Namens einer Entität oder Raute.

    Entitäten brechen ab `_WRAP_ENTITY` um. Rauten nehmen ein oder zwei Zeilen, je
    nachdem, was die kleinere Raute ergibt: Eine zweizeilige Raute braucht etwa die
    doppelte Zeilenbreite, lohnt sich also nur, wenn sich der Name gut halbieren lässt.
    """
    if not node.diamond:
        return _box(balanced_lines(node.title.text, _WRAP_ENTITY))
    options = [_box(balanced_lines(node.title.text, 0.0, count)) for count in (1, 2)]
    return min(options, key=lambda box: sum(_diamond_size(*box)))


def attribute_box(cell) -> tuple[float, int]:
    """Breite der breitesten Zeile und Zeilenzahl eines Attributs (ohne `__`)."""
    return _box(balanced_lines(cell.text.replace("__", ""), _WRAP_OVAL))


def shape_size(node) -> tuple[float, float]:
    """Größe von Rechteck oder Raute ohne die Attribute, passend zum umbrochenen Namen."""
    width, lines = title_box(node)
    if node.diamond:
        return _diamond_size(width, lines)
    return max(width + 22, 64.0), ENTITY_HEIGHT + (lines - 1) * LINE_HEIGHT


def oval_size(cell) -> tuple[float, float]:
    """Größe eines Attribut-Ovals; mehrzeilig breiter, damit die Textecken im Oval bleiben."""
    width, lines = attribute_box(cell)
    if lines == 1:
        return width + 22, OVAL_HEIGHT
    return width * 1.3 + 22, OVAL_HEIGHT + (lines - 1) * LINE_HEIGHT * 1.2


def attribute_ring(node) -> tuple[float, float]:
    """Platz der Attribute neben und über/unter ihrer Form: `(seitlich zusammen, je oben/unten)`.

    Seitlich das breiteste Oval auf der einen und das zweitbreiteste auf der anderen Seite,
    oben und unten je eine Ovalhöhe, jeweils mit `RING_GAP` Abstand; ohne Attribute `(0, 0)`.
    Reicht das im Einzelfall nicht, weicht die Attributplatzierung nach außen aus, und der
    Rand wächst mit.
    """
    ovals = [oval_size(cell) for cell in node.attributes]
    if not ovals:
        return 0.0, 0.0
    widths = sorted((width for width, _height in ovals), reverse=True)
    sides = widths[0] + (widths[1] if len(widths) > 1 else widths[0]) + 2 * RING_GAP
    return sides, max(height for _width, height in ovals) + RING_GAP
