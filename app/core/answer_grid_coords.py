"""Die Koordinaten der Geometry: Objekt- → Mathe-Raster- → SVG-Koordinaten.

Die Geometry rechnet intern durchgehend in **Mathe-Rasterkoordinaten**: `(0, 0)`
ist die linke untere Ecke des Rasters, 1 Einheit = 1 Zelle, `y` wächst nach oben.
Das gilt für Ursprung, Achsen-Klemmung, Ticks, Randschätzung, Objektkoordinaten,
Funktionsproben, Kreiskonturen und Flächenschwerpunkte.

SVG zählt `y` nach unten. `to_svg` ist die einzige Stelle, die diese Umkehr
kennt; sie läuft direkt vor der Ausgabe und vor dem Label-Layout. Das Layout
selbst bleibt im SVG-Raum, weil es Textboxen und feste Bildschirmversätze
(„Label rechts oberhalb des Kreuzes“) behandelt, also Darstellung und keine
Mathematik.

Davor bildet `_GeometryCoordinateSystem` die Objekt-Koordinaten aus dem YAML
(mit oder ohne Achse) auf Mathe-Rasterkoordinaten ab; `_inside_grid` prüft, ob
eine solche Koordinate in Hauptfläche bzw. Randbereich liegt.
"""

from __future__ import annotations

from dataclasses import dataclass


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


def _inside_grid(x_value, y_value, cols, rows, margin=0.0):
    """Prüft, ob eine Mathe-Rasterkoordinate in `[-margin, cols+margin] × [-margin, rows+margin]` liegt.

    Ohne `margin` ist das die Hauptfläche; `GeometryFrame.is_visible` und
    `.is_in_main_area` (`answer_grid_frame.py`) sind die beiden Aufrufer.
    """
    low = 0.0 - margin
    return low <= x_value <= float(cols) + margin and low <= y_value <= float(rows) + margin


@dataclass(frozen=True)
class _GeometryCoordinateSystem:
    """Bündelt die Umrechnung Objekt-Koordinaten -> Mathe-Rasterkoordinaten an EINER Stelle.

    Ersetzt das frühere Muster, `axis_enabled`/`origin`/`step_x`/`step_y`
    als lose Parameter durch jede `_parse_*`-Funktion einzeln
    durchzureichen -- die Umrechnungsformel existiert dadurch nur noch
    einmal (hier), statt in `_parse_points`/`_parse_sequence`/`_parse_pairs`
    und `_sample_function_points` (`answer_grid_function_eval.py`) separat
    dupliziert zu werden.

    `axis_active` ist nur im Tri-State `"active"` `True` (siehe
    `_resolve_axis_state`, `answer_grid_axis.py`) -- der Zustand `"broken"`
    erreicht das Parsing gar nicht erst, `_render_grid_primitives_svg`
    bricht dafür schon vorher ab.

    Eine einzige Konvention für alle Sektionen: `(0, 0)` ist die **linke
    untere** Ecke, `y` wächst nach oben -- ohne Achse direkt in Rastereinheiten,
    mit Achse relativ zu `origin` (dessen Zeile ebenfalls von unten zählt). Auch
    das Ergebnis zählt von unten; die Umkehr fürs SVG macht allein
    `answer_grid_coords.to_svg`. (Bis 2026-10-06 zählten `points[].col`/`row`
    und die `origin`-Zeile von oben; Bestandsdokumente wurden migriert.)
    """

    axis_active: bool
    origin: tuple[float, float] | None
    step_x: float
    step_y: float

    def point(self, x, y):
        """Bildet eine Objekt-Koordinate `(x, y)` auf eine Mathe-Rasterkoordinate ab."""
        if self.axis_active:
            return self.origin[0] + (x / self.step_x), self.origin[1] + (y / self.step_y)
        return x, y

    def radius(self, r):
        """Bildet einen skalaren Radius `r` auf `(rx, ry)` in Rastereinheiten ab.

        Im Achsenmodus ggf. anisotrop (unterschiedliche `step_x`/`step_y`
        ergeben eine Ellipse); ohne Achse ist die Rasterzelle immer
        quadratisch, daher `(r, r)`.
        """
        if self.axis_active:
            return r / self.step_x, r / self.step_y
        return r, r
