"""Rendert die optionalen Geometrie-Objekte (Achsen, Punkte, Strecken, Funktionsgraphen, Polygone) als SVG-Overlay.

Konsumiert die geparsten Einträge aus `answer_grid_entries.py`/
`answer_grid_shapes.py` sowie die Achsen-Rendering-Bausteine aus
`answer_grid_axis.py` und setzt sie zu einem einzigen SVG-Overlay zusammen,
das über dem Hintergrund-Raster (`answer_grid_svg_frame.py`) liegt.
"""

from __future__ import annotations

from html import escape

from .answer_grid_axis import (
    _clamp_axis_origin,
    _render_axis_arrowheads_and_names,
    _render_axis_ticks_and_labels,
    _resolve_axis_name,
    _resolve_axis_state,
    origin_to_canvas,
)
from .answer_grid_entries import (
    _GeometryCoordinateSystem,
    _inside_grid,
    _parse_functions,
    _parse_pairs,
    _parse_points,
    _parse_positive_float,
    _parse_sequence,
)
from .answer_grid_function_eval import _sample_function_points
from .answer_grid_shapes import _render_circles_section, _render_polygons_section
from .answer_grid_svg_frame import _svg_viewport_frame
from .answer_grid_svg_style import _svg_fill_style_attr, _svg_stroke_style_attr


def _render_points_section(raw_entries, coord_system, cols, rows, include_solutions):
    """Section-Renderer für `points`: liefert `(shapes, labels)` getrennt (siehe Z-Order-Regel)."""
    entries = _parse_points(raw_entries, coord_system, include_solutions)
    shapes, labels = [], []
    cross_half = 0.18
    for px, py, label, color, thickness, mode in entries:
        if not _inside_grid(px, py, cols, rows):
            continue
        stroke_style = _svg_stroke_style_attr(color, thickness)
        shapes.append(
            f"<line class='grid-point grid-mode-{mode}'{stroke_style} x1='{px - cross_half:.4f}' y1='{py - cross_half:.4f}' x2='{px + cross_half:.4f}' y2='{py + cross_half:.4f}' />"
        )
        shapes.append(
            f"<line class='grid-point grid-mode-{mode}'{stroke_style} x1='{px - cross_half:.4f}' y1='{py + cross_half:.4f}' x2='{px + cross_half:.4f}' y2='{py - cross_half:.4f}' />"
        )
        if label:
            labels.append(
                f"<text class='grid-point-label grid-mode-{mode}'{_svg_fill_style_attr(color)} x='{px + 0.24:.4f}' y='{py - 0.24:.4f}'>{escape(label)}</text>"
            )
    return shapes, labels


def _render_sequence_section(raw_entries, coord_system, cols, rows, include_solutions):
    """Section-Renderer für `sequence`: Verbindungs-Polylinie und Punkt-Kreuze sind beide "Shapes" dieser Sektion."""
    entries = _parse_sequence(raw_entries, coord_system, include_solutions)
    visible = [entry for entry in entries if _inside_grid(entry[0], entry[1], cols, rows)]

    shapes, labels = [], []
    if len(visible) >= 2:
        seq_color, seq_thickness, seq_mode = visible[0][3], visible[0][4], visible[0][5]
        points_attr = " ".join(
            f"{x:.4f},{y:.4f}"
            for x, y, _label, _color, _thickness, _mode in sorted(visible, key=lambda item: item[0])
        )
        stroke_style = _svg_stroke_style_attr(seq_color, seq_thickness)
        shapes.append(
            f"<polyline class='grid-sequence-line grid-mode-{seq_mode}'{stroke_style} points='{points_attr}' />"
        )

    cross_half = 0.18
    for px, py, label, color, thickness, mode in visible:
        stroke_style = _svg_stroke_style_attr(color, thickness)
        shapes.append(
            f"<line class='grid-point grid-mode-{mode}'{stroke_style} x1='{px - cross_half:.4f}' y1='{py - cross_half:.4f}' x2='{px + cross_half:.4f}' y2='{py + cross_half:.4f}' />"
        )
        shapes.append(
            f"<line class='grid-point grid-mode-{mode}'{stroke_style} x1='{px - cross_half:.4f}' y1='{py + cross_half:.4f}' x2='{px + cross_half:.4f}' y2='{py - cross_half:.4f}' />"
        )
        if label:
            labels.append(
                f"<text class='grid-point-label grid-mode-{mode}'{_svg_fill_style_attr(color)} x='{px + 0.24:.4f}' y='{py - 0.24:.4f}'>{escape(label)}</text>"
            )
    return shapes, labels


def _render_pairs_section(raw_entries, coord_system, cols, rows, include_solutions):
    """Section-Renderer für `pairs`."""
    entries = _parse_pairs(raw_entries, coord_system, include_solutions)
    shapes, labels = [], []
    for gx1, gy1, gx2, gy2, label, color, thickness, mode, line_style in entries:
        stroke_style = _svg_stroke_style_attr(color, thickness)
        shapes.append(
            f"<line class='grid-segment grid-segment-{line_style} grid-mode-{mode}'{stroke_style} x1='{gx1:.4f}' y1='{gy1:.4f}' x2='{gx2:.4f}' y2='{gy2:.4f}' />"
        )
        if label:
            mid_x, mid_y = (gx1 + gx2) / 2, (gy1 + gy2) / 2
            labels.append(
                f"<text class='grid-segment-label grid-mode-{mode}'{_svg_fill_style_attr(color)} x='{mid_x + 0.16:.4f}' y='{mid_y - 0.16:.4f}'>{escape(label)}</text>"
            )
    return shapes, labels


def _render_functions_section(raw_entries, coord_system, cols, rows, include_solutions):
    """Section-Renderer für `functions`."""
    entries = _parse_functions(raw_entries, coord_system.axis_active, include_solutions)
    shapes, labels = [], []
    for expr, x_min, x_max, label, color, thickness, mode in entries:
        poly_points = _sample_function_points(expr, x_min, x_max, coord_system, cols, rows)
        if len(poly_points) < 2:
            continue
        points_attr = " ".join(f"{x:.4f},{y:.4f}" for x, y in poly_points)
        stroke_style = _svg_stroke_style_attr(color, thickness)
        shapes.append(
            f"<polyline class='grid-function-line grid-mode-{mode}'{stroke_style} points='{points_attr}' />"
        )
        if label:
            end_x, end_y = poly_points[-1]
            labels.append(
                f"<text class='grid-function-label grid-mode-{mode}'{_svg_fill_style_attr(color)} x='{end_x + 0.16:.4f}' y='{end_y - 0.16:.4f}'>{escape(label)}</text>"
            )
    return shapes, labels


_SECTION_RENDERERS = {
    "points": _render_points_section,
    "sequence": _render_sequence_section,
    "pairs": _render_pairs_section,
    "polygons": _render_polygons_section,
    "circles": _render_circles_section,
    "functions": _render_functions_section,
}
"""Dispatch-Tabelle Sektionsname -> `(raw_entries, coord_system, cols, rows, include_solutions) -> (shapes, labels)`.

`_render_grid_primitives_svg` iteriert `payload.items()` in
YAML-Dokumentreihenfolge und schlägt hier nach, statt die Sektionen in
einer im Code fest verdrahteten Reihenfolge zu rendern -- die Zeichen-
Reihenfolge im Ergebnis-SVG folgt dadurch der Reihenfolge, in der die
Sektionen im `:::geometry`-Payload tatsächlich stehen.
"""


def _render_grid_primitives_svg(options, payload, rows, cols, include_solutions, bleed_units=(0.0, 0.0, 0.0, 0.0)):
    """Rendert optionale geometrische Primitive innerhalb des Rasters als SVG.

    Z-Reihenfolge: (1) Achse ganz unten (nur im Achsenzustand `"active"`,
    siehe `_resolve_axis_state`), (2) alle übrigen Geometry-Objekte in
    exakt der Reihenfolge ihres Auftretens im YAML-Payload, (3) alle Labels
    (inkl. Achsennamen und Tick-Zahlenwerte) ganz oben, sektionsübergreifend
    zusammengefasst. Gibt einen leeren String zurück, wenn nach allen
    Schritten kein einziges sichtbares Element übrig bleibt, damit
    Aufrufer kein leeres `<svg>`-Element in die Ausgabe schreiben.

    Im Achsenzustand `"broken"` (`axis=true` mit ungültigem/fehlendem
    `origin`) wird **sofort** `""` zurückgegeben, bevor irgendein
    `_parse_*`/Section-Dispatch läuft -- kein Achsenkreuz, keine Shapes,
    keine Labels, in keinem Koordinatenmodus. Kein stiller Rückfall auf
    Rasterkoordinaten; der Validator meldet diesen Zustand separat (`OP005`).
    """
    axis_state, origin = _resolve_axis_state(options)
    if axis_state == "broken":
        return ""
    # `origin` zählt die Zeile von unten (0,0 = links unten); ab hier SVG-Rasterkoordinate.
    origin = origin_to_canvas(origin, rows)

    step_x = _parse_positive_float(options.get("step_x"), 1.0)
    step_y = _parse_positive_float(options.get("step_y"), 1.0)
    coord_system = _GeometryCoordinateSystem(
        axis_active=(axis_state == "active"),
        origin=origin,
        step_x=step_x,
        step_y=step_y,
        canvas_height=float(rows),
    )

    bottom_layer = []
    axis_label_layer = []
    if axis_state == "active":
        axis_origin = _clamp_axis_origin(origin[0], origin[1], cols, rows)
        logical_ox, logical_oy = origin
        axis_ox, axis_oy = axis_origin
        axis_label_x = _resolve_axis_name(
            options, "axis_label_x", aliases=("x_label", "axis_x_label"), default="x"
        )
        axis_label_y = _resolve_axis_name(
            options, "axis_label_y", aliases=("y_label", "axis_y_label"), default="y"
        )
        bottom_layer.append(
            f"<line class='grid-axis' x1='0' y1='{axis_oy:.4f}' x2='{cols:.4f}' y2='{axis_oy:.4f}' />"
        )
        bottom_layer.append(
            f"<line class='grid-axis' x1='{axis_ox:.4f}' y1='0' x2='{axis_ox:.4f}' y2='{rows:.4f}' />"
        )
        arrow_shapes, arrow_labels = _render_axis_arrowheads_and_names(
            axis_ox, axis_oy, cols, rows, axis_label_x, axis_label_y
        )
        bottom_layer.extend(arrow_shapes)
        axis_label_layer.extend(arrow_labels)
        tick_shapes, tick_labels = _render_axis_ticks_and_labels(
            logical_ox, logical_oy, axis_ox, axis_oy, cols, rows, step_x, step_y
        )
        bottom_layer.extend(tick_shapes)
        axis_label_layer.extend(tick_labels)

    shape_layer, label_layer = [], list(axis_label_layer)
    if isinstance(payload, dict):
        for section, raw_entries in payload.items():
            renderer = _SECTION_RENDERERS.get(section)
            if renderer is None:
                continue
            section_shapes, section_labels = renderer(raw_entries, coord_system, cols, rows, include_solutions)
            shape_layer.extend(section_shapes)
            label_layer.extend(section_labels)

    all_markup = bottom_layer + shape_layer + label_layer
    if not all_markup:
        return ""

    view_box, frame_style = _svg_viewport_frame(cols, rows, bleed_units)

    return (
        f"<svg class='grid-overlay' viewBox='{view_box}' preserveAspectRatio='none' aria-hidden='true' style='{frame_style}'>"
        f"{''.join(all_markup)}"
        "</svg>"
    )
