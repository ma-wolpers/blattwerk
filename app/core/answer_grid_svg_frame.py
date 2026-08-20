"""SVG-Viewport-Rahmen und Rasterlinien-Hintergrund für Grid/Geometry-Antwortfelder.

Getrennt von `answer_grid_primitives.py` (Geometrie-*Objekte* wie Punkte/
Strecken/Funktionen), da Viewport-Berechnung und Rasterlinien-Rendering
unabhängig von den eigentlichen Nutzinhalten sind und von sowohl
`render_grid_answer` als auch `render_geometry_answer` benötigt werden.
"""

from __future__ import annotations

from .answer_grid_axis import (
    _choose_axis_label_stride,
    _clamp_axis_origin,
    _format_axis_label,
    _iter_axis_tick_positions,
    _should_render_axis_label,
)


def _svg_viewport_frame(cols, rows, bleed_units=(0.0, 0.0, 0.0, 0.0)):
    """Baut die gemeinsame SVG-Viewport-Geometrie für Hintergrund und Overlay.

    `bleed_units` erweitert den sichtbaren Bereich über die reinen
    `cols`/`rows` hinaus (z. B. für Achsenbeschriftungen, die außerhalb des
    Rasters liegen) — Hintergrund-Raster und Objekt-Overlay teilen sich
    exakt dieselbe `viewBox`/Positionierung, damit sie pixelgenau
    übereinanderliegen.
    """
    bleed_top, bleed_right, bleed_bottom, bleed_left = bleed_units
    view_x = -bleed_left
    view_y = -bleed_top
    view_w = float(cols) + bleed_left + bleed_right
    view_h = float(rows) + bleed_top + bleed_bottom

    left_pct = -(bleed_left / float(cols)) * 100.0 if cols else 0.0
    top_pct = -(bleed_top / float(rows)) * 100.0 if rows else 0.0
    width_pct = (view_w / float(cols)) * 100.0 if cols else 100.0
    height_pct = (view_h / float(rows)) * 100.0 if rows else 100.0

    style = (
        f"left:{left_pct:.4f}%; top:{top_pct:.4f}%; "
        f"width:{width_pct:.4f}%; height:{height_pct:.4f}%"
    )
    view_box = f"{view_x:.4f} {view_y:.4f} {view_w:.4f} {view_h:.4f}"
    return view_box, style


def _render_grid_background_svg(cols, rows, bleed_units=(0.0, 0.0, 0.0, 0.0)):
    """Rendert das Karo-Raster als SVG im selben Koordinatensystem wie die Overlays."""
    view_box, frame_style = _svg_viewport_frame(cols, rows, bleed_units)
    grid_lines = []

    for x in range(0, int(cols) + 1):
        grid_lines.append(
            f"<line class='grid-background-line' x1='{x:.4f}' y1='0' x2='{x:.4f}' y2='{rows:.4f}' />"
        )
    for y in range(0, int(rows) + 1):
        grid_lines.append(
            f"<line class='grid-background-line' x1='0' y1='{y:.4f}' x2='{cols:.4f}' y2='{y:.4f}' />"
        )

    return (
        f"<svg class='grid-overlay-bg' viewBox='{view_box}' preserveAspectRatio='none' aria-hidden='true' style='{frame_style}'>"
        f"{''.join(grid_lines)}"
        "</svg>"
    )


def _estimate_geometry_bleed_units(
    logical_origin,
    cols,
    rows,
    step_x,
    step_y,
    axis_enabled,
    axis_label_x,
    axis_label_y,
):
    """Schätzt den Bleed-Rand je Seite (in Grid-Einheiten) für Achsenlabels/-namen.

    Ohne diesen Zuschlag würden lange Achsenbeschriftungen (z. B.
    mehrstellige Zahlen oder ein langer `axis_label_y`-Text) über den Rand
    des Antwortfelds hinausragen und abgeschnitten werden. Die Schätzung
    basiert auf approximierten Zeichenbreiten (`char_w`) statt exakter
    Font-Metrik, da zum Zeitpunkt des Renderns keine echte Textmessung zur
    Verfügung steht (reines SVG-String-Building, kein Layout-Engine-Zugriff).
    """
    base_top = 0.55
    base_right = 0.55
    base_bottom = 0.55
    base_left = 0.55

    if not axis_enabled or logical_origin is None:
        return base_top, base_right, base_bottom, base_left

    axis_origin_x, axis_origin_y = _clamp_axis_origin(logical_origin[0], logical_origin[1], cols, rows)

    x_ticks = _iter_axis_tick_positions(logical_origin[0], cols, step_x)
    y_ticks = _iter_axis_tick_positions(logical_origin[1], rows, step_y)

    x_stride = _choose_axis_label_stride(len(x_ticks))
    y_stride = _choose_axis_label_stride(len(y_ticks))

    x_labels = [
        _format_axis_label(logical_x)
        for _gx, logical_x in x_ticks
        if _should_render_axis_label(logical_x, x_stride)
    ]
    y_labels = [
        _format_axis_label(-logical_y)
        for _gy, logical_y in y_ticks
        if _should_render_axis_label(logical_y, y_stride)
    ]

    max_x_chars = max((len(text) for text in x_labels), default=1)
    max_y_chars = max((len(text) for text in y_labels), default=1)

    # Approximate text box metrics in grid units.
    char_w = 0.26
    text_h = 0.78

    y_tick_left_overhang = 0.28 + (char_w * max_y_chars) + 0.14
    y_name_left_overhang = 0.12 + (char_w * max(1, len(axis_label_y or ""))) + 0.12
    x_label_bottom_overhang = max(0.0, (axis_origin_y + 0.58) - float(rows)) + text_h
    x_name_right_overhang = max(0.0, (float(cols) + 0.34 + 0.16 + (char_w * max(1, len(axis_label_x or "")))) - float(cols)) + 0.12
    y_arrow_top_overhang = 0.34 + 0.08
    y_name_top_overhang = 0.42 + text_h
    x_name_top_overhang = max(0.0, 0.28 - axis_origin_y) + text_h

    safety = 0.18
    top = max(base_top, y_arrow_top_overhang, y_name_top_overhang, x_name_top_overhang) + safety
    right = max(base_right, x_name_right_overhang) + safety
    bottom = max(base_bottom, x_label_bottom_overhang, 0.56 + (0.02 * max_x_chars)) + safety
    left = max(base_left, y_tick_left_overhang, y_name_left_overhang) + safety

    return top, right, bottom, left
