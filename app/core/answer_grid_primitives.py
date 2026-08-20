"""Rendert die optionalen Geometrie-Objekte (Achsen, Punkte, Strecken, Funktionsgraphen) als SVG-Overlay.

Konsumiert die geparsten Einträge aus `answer_grid_entries.py` sowie die
Achsen-Rendering-Bausteine aus `answer_grid_axis.py` und setzt sie zu einem
einzigen SVG-Overlay zusammen, das über dem Hintergrund-Raster
(`answer_grid_svg_frame.py`) liegt.
"""

from __future__ import annotations

from html import escape

from .answer_special_shared import _option_is_enabled
from .answer_grid_axis import (
    _clamp_axis_origin,
    _parse_origin,
    _render_axis_arrowheads_and_names,
    _render_axis_ticks_and_labels,
    _resolve_axis_name,
)
from .answer_grid_entries import (
    _inside_grid,
    _parse_functions,
    _parse_pairs,
    _parse_points,
    _parse_positive_float,
    _parse_sequence,
)
from .answer_grid_function_eval import _sample_function_points
from .answer_grid_svg_frame import _svg_viewport_frame


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


def _render_grid_primitives_svg(options, payload, rows, cols, include_solutions, bleed_units=(0.0, 0.0, 0.0, 0.0)):
    """Rendert optionale geometrische Primitive innerhalb des Rasters als SVG.

    Baut in dieser Reihenfolge auf: Achsenkreuz (falls `axis=true`) → Punkte/
    Sequenz-Kreuzmarkierungen → Sequenz-Polylinie → Strecken (`pairs`) →
    Funktionsgraphen. Gibt einen leeren String zurück, wenn nach allen
    Schritten kein einziges sichtbares Element übrig bleibt, damit
    Aufrufer kein leeres `<svg>`-Element in die Ausgabe schreiben.
    """
    axis_enabled = _option_is_enabled(options.get("axis"), default=False)
    origin = _parse_origin(options.get("origin"), cols, rows) if axis_enabled else None
    axis_origin = (
        _clamp_axis_origin(origin[0], origin[1], cols, rows)
        if axis_enabled and origin is not None
        else None
    )
    if axis_enabled and origin is None:
        axis_enabled = False

    step_x = _parse_positive_float(options.get("step_x"), 1.0)
    step_y = _parse_positive_float(options.get("step_y"), 1.0)

    lines = []
    if axis_enabled and origin is not None and axis_origin is not None:
        logical_ox, logical_oy = origin
        axis_ox, axis_oy = axis_origin
        axis_label_x = _resolve_axis_name(
            options,
            "axis_label_x",
            aliases=("x_label", "axis_x_label"),
            default="x",
        )
        axis_label_y = _resolve_axis_name(
            options,
            "axis_label_y",
            aliases=("y_label", "axis_y_label"),
            default="y",
        )
        lines.append(
            f"<line class='grid-axis' x1='0' y1='{axis_oy:.4f}' x2='{cols:.4f}' y2='{axis_oy:.4f}' />"
        )
        lines.append(
            f"<line class='grid-axis' x1='{axis_ox:.4f}' y1='0' x2='{axis_ox:.4f}' y2='{rows:.4f}' />"
        )
        lines.extend(
            _render_axis_arrowheads_and_names(
                axis_ox, axis_oy, cols, rows, axis_label_x, axis_label_y
            )
        )
        lines.extend(
            _render_axis_ticks_and_labels(
                logical_ox,
                logical_oy,
                axis_ox,
                axis_oy,
                cols,
                rows,
                step_x,
                step_y,
            )
        )

    point_entries = _parse_points(
        payload.get("points"), axis_enabled, origin, step_x, step_y, include_solutions
    )
    sequence_entries = _parse_sequence(
        payload.get("sequence"), axis_enabled, origin, step_x, step_y, include_solutions
    )
    segment_entries = _parse_pairs(
        payload.get("pairs"), axis_enabled, origin, step_x, step_y, include_solutions
    )
    fn_entries = _parse_functions(
        payload.get("functions"), axis_enabled, include_solutions
    )

    point_markup = []
    for px, py, label, color, thickness, mode in point_entries + sequence_entries:
        if not _inside_grid(px, py, cols, rows):
            continue
        cross_half = 0.18
        stroke_style = _svg_stroke_style_attr(color, thickness)
        point_markup.append(
            f"<line class='grid-point grid-mode-{mode}'{stroke_style} x1='{px - cross_half:.4f}' y1='{py - cross_half:.4f}' x2='{px + cross_half:.4f}' y2='{py + cross_half:.4f}' />"
        )
        point_markup.append(
            f"<line class='grid-point grid-mode-{mode}'{stroke_style} x1='{px - cross_half:.4f}' y1='{py + cross_half:.4f}' x2='{px + cross_half:.4f}' y2='{py - cross_half:.4f}' />"
        )
        if label:
            point_markup.append(
                f"<text class='grid-point-label grid-mode-{mode}'{_svg_fill_style_attr(color)} x='{px + 0.24:.4f}' y='{py - 0.24:.4f}'>{escape(label)}</text>"
            )

    if sequence_entries:
        filtered = [
            (x, y, color, thickness, mode)
            for x, y, _label, color, thickness, mode in sequence_entries
            if _inside_grid(x, y, cols, rows)
        ]
        if len(filtered) >= 2:
            seq_color, seq_thickness, seq_mode = filtered[0][2], filtered[0][3], filtered[0][4]
            points_attr = " ".join(
                f"{x:.4f},{y:.4f}"
                for x, y, _color, _thickness, _mode in sorted(filtered, key=lambda item: item[0])
            )
            stroke_style = _svg_stroke_style_attr(seq_color, seq_thickness)
            lines.append(
                f"<polyline class='grid-sequence-line grid-mode-{seq_mode}'{stroke_style} points='{points_attr}' />"
            )

    for gx1, gy1, gx2, gy2, label, color, thickness, mode, line_style in segment_entries:
        stroke_style = _svg_stroke_style_attr(color, thickness)
        lines.append(
            f"<line class='grid-segment grid-segment-{line_style} grid-mode-{mode}'{stroke_style} x1='{gx1:.4f}' y1='{gy1:.4f}' x2='{gx2:.4f}' y2='{gy2:.4f}' />"
        )
        if label:
            mid_x, mid_y = (gx1 + gx2) / 2, (gy1 + gy2) / 2
            lines.append(
                f"<text class='grid-segment-label grid-mode-{mode}'{_svg_fill_style_attr(color)} x='{mid_x + 0.16:.4f}' y='{mid_y - 0.16:.4f}'>{escape(label)}</text>"
            )

    for expr, x_min, x_max, label, color, thickness, mode in fn_entries:
        poly_points = _sample_function_points(
            expr, x_min, x_max, origin, step_x, step_y, cols, rows
        )
        if len(poly_points) < 2:
            continue
        points_attr = " ".join(f"{x:.4f},{y:.4f}" for x, y in poly_points)
        stroke_style = _svg_stroke_style_attr(color, thickness)
        lines.append(
            f"<polyline class='grid-function-line grid-mode-{mode}'{stroke_style} points='{points_attr}' />"
        )
        if label:
            end_x, end_y = poly_points[-1]
            lines.append(
                f"<text class='grid-function-label grid-mode-{mode}'{_svg_fill_style_attr(color)} x='{end_x + 0.16:.4f}' y='{end_y - 0.16:.4f}'>{escape(label)}</text>"
            )

    all_markup = lines + point_markup
    if not all_markup:
        return ""

    view_box, frame_style = _svg_viewport_frame(cols, rows, bleed_units)

    return (
        f"<svg class='grid-overlay' viewBox='{view_box}' preserveAspectRatio='none' aria-hidden='true' style='{frame_style}'>"
        f"{''.join(all_markup)}"
        "</svg>"
    )
