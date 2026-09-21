"""Kleine SVG-`style`-Attribut-Helfer für Geometry-Objekt-Rendering.

Ausgelagert aus `answer_grid_primitives.py`, damit `answer_grid_shapes.py`
(Polygon-/Kreis-Rendering) sie importieren kann, ohne einen Zirkelimport zu
erzeugen: `answer_grid_primitives.py` importiert umgekehrt die
Section-Renderer für `polygons`/`circles` aus `answer_grid_shapes.py`.
"""

from __future__ import annotations


def _svg_stroke_style_attr(color, thickness):
    """Baut ein optionales `style='stroke:...;stroke-width:...'`-Attribut für Linien-Elemente.

    `color`/`thickness` sind bereits über `parse_svg_color`/
    `parse_svg_thickness` sanitized (siehe `answer_grid_entries.py`) — hier
    wird nur noch zu einem CSS-`style`-Attribut zusammengesetzt, keine
    erneute Validierung von Rohtext. Liefert einen leeren String, wenn
    weder Farbe noch Dicke gesetzt sind, damit das Element auf die
    bestehende, mode-abhängige CSS-Klasse zurückfällt.
    """
    parts = []
    if color:
        parts.append(f"stroke:{color}")
    if thickness is not None:
        parts.append(f"stroke-width:{thickness:.4f}")
    return f" style='{';'.join(parts)}'" if parts else ""


def _svg_fill_style_attr(color):
    """Baut ein optionales `style='fill:...'`-Attribut für Label-`<text>`-Elemente."""
    return f" style='fill:{color}'" if color else ""


def _svg_shape_style_attr(color, thickness, fill):
    """Baut ein optionales `style='stroke:...;stroke-width:...;fill:...'`-Attribut für Polygon/Kreis/Bogen.

    Eigenständig neben `_svg_stroke_style_attr`, statt dessen Signatur um
    ein drittes `fill`-Argument zu erweitern: Punkte/Strecken/Funktionsgraphen
    kennen kein `fill`-Konzept (ihr CSS-Default `fill: none` genügt), ein
    dort stets leeres drittes Argument wäre unnötiger Ballast an jedem
    bestehenden Aufrufer.
    """
    parts = []
    if color:
        parts.append(f"stroke:{color}")
    if thickness is not None:
        parts.append(f"stroke-width:{thickness:.4f}")
    if fill:
        parts.append(f"fill:{fill}")
    return f" style='{';'.join(parts)}'" if parts else ""
