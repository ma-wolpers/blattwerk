"""Rahmen eines `:::geometry`-Blocks: Rastergröße und Bleed-Rand, eine Quelle für Renderer und Validator.

Ausgelagert aus `answer_grid_plot.render_geometry_answer`, damit der
Label-Validator (`blatt_validator_geometry_labels`, AN019) das Layout mit
exakt denselben Maßen nachrechnet wie der Renderer. Der Bleed-Rand wird vor
dem Label-Layout aus Achsen und Achsennamen geschätzt und ist für das Layout
eine feste Zone (Bleed-Variante 2: Labels werden auf Zeichenfläche plus
bestehenden Rand begrenzt, die Seitengeometrie ändert sich nie).
"""

from __future__ import annotations

from dataclasses import dataclass

from .answer_grid_axis import _resolve_axis_name, _resolve_axis_state, origin_to_canvas
from .answer_grid_entries import _parse_positive_float
from .answer_grid_svg_frame import _estimate_geometry_bleed_units
from .answer_special_shared import _safe_int

DEFAULT_GEOMETRY_COLS = 20


@dataclass(frozen=True)
class GeometryFrame:
    """Rastergröße (Einheiten) und Bleed `(oben, rechts, unten, links)` eines Geometry-Blocks."""

    width_units: int
    height_units: int
    bleed_units: tuple[float, float, float, float]


def resolve_geometry_frame(options) -> GeometryFrame:
    """Liest `width`/`height` (Rastereinheiten) und schätzt den Bleed-Rand für Achsenlabels/-namen.

    `width` fehlt oder ist leer → `DEFAULT_GEOMETRY_COLS`; `height` → 5. Der
    Ursprung zählt die Zeile von unten (0,0 = links unten) und wird hier in
    die SVG-Rasterkoordinate umgerechnet.
    """
    height_units = max(1, _safe_int(options.get("height", 5), 5))
    width_option = options.get("width")
    has_explicit_width = width_option is not None and str(width_option).strip() != ""
    width_units = (
        max(1, _safe_int(width_option, DEFAULT_GEOMETRY_COLS)) if has_explicit_width else DEFAULT_GEOMETRY_COLS
    )
    axis_state, logical_origin = _resolve_axis_state(options)
    logical_origin = origin_to_canvas(logical_origin, height_units)
    bleed = _estimate_geometry_bleed_units(
        logical_origin,
        width_units,
        height_units,
        _parse_positive_float(options.get("step_x"), 1.0),
        _parse_positive_float(options.get("step_y"), 1.0),
        axis_state == "active",
        _resolve_axis_name(options, "axis_label_x", aliases=("x_label", "axis_x_label"), default="x"),
        _resolve_axis_name(options, "axis_label_y", aliases=("y_label", "axis_y_label"), default="y"),
    )
    return GeometryFrame(width_units, height_units, tuple(bleed))
