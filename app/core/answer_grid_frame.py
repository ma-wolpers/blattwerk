"""Rahmen eines `:::geometry`-Blocks: Maße, Randbereich, Bleed und Koordinatensystem -- eine Quelle für Renderer und Validator.

Ausgelagert aus `answer_grid_plot.render_geometry_answer`, damit Validator
(`blatt_validator_geometry_labels` für AN019, `blatt_validator_answers_math`
für AN040) und Layout-Schätzung mit exakt denselben Maßen rechnen wie der
Renderer.

Flächenmodell (Mathe-Rasterkoordinaten, `(0, 0)` = links unten):

- **Hauptfläche** `[0, width] × [0, height]` -- trägt Ticks und Tick-Zahlen;
  nur sie zählt als „die Fläche“ (`AN040`).
- **Randbereich** (`margin=`, Standard ½ Zelle je Seite) -- ein Saum um die
  Hauptfläche, in dem Hintergrund, Achsen und Objekte weiterlaufen. Hauptfläche
  plus Saum bilden die **Box** (das `.answer.grid`-Element, mit `frame=true`
  umrandet).
- **Bleed** -- Platz außerhalb der Box für Achsennamen und Beschriftungen. Er
  wird vor dem Label-Layout geschätzt und ist dafür eine feste Zone
  (Bleed-Variante 2: Labels werden auf Box plus Bleed begrenzt, die
  Seitengeometrie ändert sich nie).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .answer_grid_axis import _resolve_axis_name, _resolve_axis_state
from .answer_grid_coords import _GeometryCoordinateSystem, _inside_grid
from .answer_grid_entries import _parse_positive_float
from .answer_grid_svg_frame import _estimate_geometry_bleed_units, _svg_viewport_frame
from .answer_special_shared import _safe_int, frame_requested
from .blatt_validator_constants import GEOMETRY_MARGIN_DEFAULT, GEOMETRY_MARGIN_LIMIT

DEFAULT_GEOMETRY_COLS = 20


@dataclass(frozen=True)
class GeometryFrame:
    """Maße eines Geometry-Blocks in Rastereinheiten.

    Attributes:
        width_units: Breite der Hauptfläche.
        height_units: Höhe der Hauptfläche.
        margin_units: Breite des Randbereichs je Seite (`0 <= m < 1`).
        bleed_units: Platz `(oben, rechts, unten, links)` außerhalb der Box.
        framed: `True`, wenn die Box einen sichtbaren Rahmen bekommt (`frame=true`).
    """

    width_units: int
    height_units: int
    margin_units: float
    bleed_units: tuple[float, float, float, float]
    framed: bool

    @property
    def box_units(self) -> tuple[float, float]:
        """Breite und Höhe der Box (Hauptfläche plus Randbereich auf beiden Seiten)."""
        return float(self.width_units) + 2 * self.margin_units, float(self.height_units) + 2 * self.margin_units

    @property
    def visible_extent(self) -> tuple[float, float, float, float]:
        """Sichtbarer Bereich `(links, unten, rechts, oben)` in Mathe-Rasterkoordinaten -- das Ende von Achsen und Linien."""
        margin = self.margin_units
        return 0.0 - margin, 0.0 - margin, float(self.width_units) + margin, float(self.height_units) + margin

    @property
    def zone_units(self) -> tuple[float, float, float, float]:
        """Ausdehnung der Label-Zone über die Hauptfläche hinaus je Seite `(oben, rechts, unten, links)`: Randbereich plus Bleed."""
        return tuple(bleed + self.margin_units for bleed in self.bleed_units)

    def is_visible(self, x: float, y: float) -> bool:
        """Liegt die Mathe-Rasterkoordinate in Hauptfläche oder Randbereich (wird also gezeichnet)?"""
        return _inside_grid(x, y, self.width_units, self.height_units, self.margin_units)

    def is_in_main_area(self, x: float, y: float) -> bool:
        """Liegt die Mathe-Rasterkoordinate in der Hauptfläche (Grenze für `AN040`)?"""
        return _inside_grid(x, y, self.width_units, self.height_units)

    def viewport(self) -> tuple[str, str]:
        """`(viewBox, style)` für jedes SVG-Overlay dieses Blocks (Hintergrund und Objekte teilen ihn)."""
        return _svg_viewport_frame(self.width_units, self.height_units, self.bleed_units, self.margin_units)


def parse_geometry_margin(raw) -> float | None:
    """Liest `margin=` (Rasterzellen je Seite); `None` heißt ungültig.

    Fehlt der Wert oder ist er leer, gilt `GEOMETRY_MARGIN_DEFAULT`. Gültig ist
    jede endliche Zahl mit `0 <= m < GEOMETRY_MARGIN_LIMIT`. Der Renderer fällt
    bei `None` auf den Standard zurück, der Validator meldet den Wert (`OP002`)
    -- beide über diese eine Funktion.
    """
    if raw is None or str(raw).strip() == "":
        return GEOMETRY_MARGIN_DEFAULT
    try:
        value = float(str(raw).strip())
    except ValueError:
        return None
    if not math.isfinite(value) or not 0.0 <= value < GEOMETRY_MARGIN_LIMIT:
        return None
    return value


def resolve_geometry_frame(options) -> GeometryFrame:
    """Liest `width`/`height`/`margin`/`frame` und schätzt den Bleed für Achsenlabels/-namen.

    `width` fehlt oder ist leer → `DEFAULT_GEOMETRY_COLS`; `height` → 5; ein
    ungültiges `margin` → `GEOMETRY_MARGIN_DEFAULT`. Der Ursprung zählt die
    Zeile von unten (0,0 = links unten).
    """
    height_units = max(1, _safe_int(options.get("height", 5), 5))
    width_option = options.get("width")
    has_explicit_width = width_option is not None and str(width_option).strip() != ""
    width_units = (
        max(1, _safe_int(width_option, DEFAULT_GEOMETRY_COLS)) if has_explicit_width else DEFAULT_GEOMETRY_COLS
    )
    margin = parse_geometry_margin(options.get("margin"))
    if margin is None:
        margin = GEOMETRY_MARGIN_DEFAULT
    axis_state, logical_origin = _resolve_axis_state(options)
    bleed = _estimate_geometry_bleed_units(
        logical_origin,
        width_units,
        height_units,
        _parse_positive_float(options.get("step_x"), 1.0),
        _parse_positive_float(options.get("step_y"), 1.0),
        axis_state == "active",
        _resolve_axis_name(options, "axis_label_x", aliases=("x_label", "axis_x_label"), default="x"),
        _resolve_axis_name(options, "axis_label_y", aliases=("y_label", "axis_y_label"), default="y"),
        margin=margin,
    )
    return GeometryFrame(width_units, height_units, margin, tuple(bleed), frame_requested(options))


def resolve_coordinate_system(options) -> _GeometryCoordinateSystem | None:
    """Koordinatensystem der Objekte aus `axis`/`origin`/`step_x`/`step_y`; ``None`` im Achsenzustand `"broken"`.

    Eine Stelle für Renderer (`build_geometry_scene`) und Validator (`AN040`):
    Im Zustand `"broken"` (`axis=true` ohne gültiges `origin`) gibt es bewusst
    kein Koordinatensystem -- kein stiller Rückfall auf Rasterkoordinaten, der
    Validator meldet `OP005`.
    """
    axis_state, origin = _resolve_axis_state(options)
    if axis_state == "broken":
        return None
    return _GeometryCoordinateSystem(
        axis_active=(axis_state == "active"),
        origin=origin,
        step_x=_parse_positive_float(options.get("step_x"), 1.0),
        step_y=_parse_positive_float(options.get("step_y"), 1.0),
    )
