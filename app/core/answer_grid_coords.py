"""Die eine Umrechnung der Geometry von Mathe- in SVG-Koordinaten.

Die Geometry rechnet intern durchgehend in **Mathe-Rasterkoordinaten**: `(0, 0)`
ist die linke untere Ecke des Rasters, 1 Einheit = 1 Zelle, `y` wächst nach oben.
Das gilt für Ursprung, Achsen-Klemmung, Ticks, Randschätzung, Objektkoordinaten,
Funktionsproben, Kreiskonturen und Flächenschwerpunkte.

SVG zählt `y` nach unten. `to_svg` ist die einzige Stelle, die diese Umkehr
kennt; sie läuft direkt vor der Ausgabe und vor dem Label-Layout. Das Layout
selbst bleibt im SVG-Raum, weil es Textboxen und feste Bildschirmversätze
(„Label rechts oberhalb des Kreuzes“) behandelt, also Darstellung und keine
Mathematik.
"""

from __future__ import annotations


def to_svg(x: float, y: float, rows: float) -> tuple[float, float]:
    """Rechnet einen Punkt aus Mathe-Rasterkoordinaten in SVG-Koordinaten um.

    Args:
        x: Spalte (unverändert).
        y: Zeile von unten.
        rows: Höhe des Rasters in Rastereinheiten.

    Returns:
        `(x, rows - y)`.
    """
    return x, float(rows) - y
