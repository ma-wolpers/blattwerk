"""Grid-Antwort-Renderer: Schreibraster und Koordinatensysteme (öffentliche API).

Orchestriert die Renderer für `:::grid` (`render_grid_answer`) und
`:::geometry` (`render_geometry_answer`) sowie das einfache `:::dots`-Feld
(`render_dots_answer`). Die eigentliche Geometrie-/SVG-Detailarbeit lebt in
den Nachbarmodulen `answer_grid_svg_frame.py` (Viewport/Hintergrundraster),
`answer_grid_axis.py` (Achsen-Geometrie), `answer_grid_entries.py`
(Geometrie-Objekt-Parsing) und `answer_grid_primitives.py`
(Geometrie-Objekt-Rendering) — dieses Modul bleibt bewusst der schlanke
öffentliche Einstiegspunkt, den `blatt_kern_answer_table.py` importiert.
"""

from __future__ import annotations

import math
import re

from .answer_special_shared import _option_is_enabled, _safe_int
from .answer_yaml_payload import parse_yaml_answer_payload_with_solution
from .answer_grid_axis import _parse_origin, _resolve_axis_name
from .answer_grid_entries import _parse_positive_float
from .answer_grid_primitives import _render_grid_primitives_svg
from .answer_grid_svg_frame import _estimate_geometry_bleed_units, _render_grid_background_svg


_DEFAULT_GEOMETRY_COLS = 20
_DEFAULT_PRINTABLE_WIDTH_CM = 18.0


def _parse_grid_scale(raw_value):
    """Parst den Grid-Maßstab als sichere CSS-Länge."""
    if raw_value is None:
        return "0.5cm"

    text = str(raw_value).strip()
    if re.fullmatch(r"\d+(?:\.\d+)?(cm|mm|px|pt|em|rem|%)", text, flags=re.IGNORECASE):
        return text
    return "0.5cm"


def _grid_cell_size_to_cm(scale_value):
    """Konvertiert einen geparsten Grid-Zellwert nach cm für deterministisches Bleed-Padding.

    `em`/`rem`/`%` sind kontextabhängig und lassen sich ohne Layout-Engine
    nicht exakt in cm umrechnen; dafür ein stabiler Fallback (`0.5`) statt
    einer Fehlberechnung.
    """
    text = str(scale_value or "").strip().lower()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(cm|mm|px|pt|em|rem|%)", text)
    if not match:
        return 0.5

    value = float(match.group(1))
    unit = match.group(2)

    if unit == "cm":
        return value
    if unit == "mm":
        return value / 10.0
    if unit == "px":
        return value * (2.54 / 96.0)
    if unit == "pt":
        return value * (2.54 / 72.0)

    # em/rem/% are context-dependent; keep a stable fallback.
    return 0.5


def _resolve_runtime_printable_width_cm(options):
    """Löst die druckbare Breite aus dem vom Layout-Rendering übergebenen Laufzeitkontext auf."""
    raw_value = (options or {}).get("_printable_width_cm")
    parsed = _as_float(raw_value)
    if parsed is None or parsed <= 0:
        return _DEFAULT_PRINTABLE_WIDTH_CM
    return parsed


def _as_float(value):
    """Konvertiert einen Wert nach `float`, liefert `None` statt einer Exception.

    Lokale Kopie statt Import aus `answer_grid_entries`, da dort nur
    private (`_`-präfixierte) Helper für die Geometry-Entry-Domäne liegen
    sollen und dieses Modul eine unabhängige, sehr kleine Konvertierung
    benötigt (kein Grund für eine Modul-übergreifende Abhängigkeit nur für
    eine Ein-Zeilen-Funktion).
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _estimate_grid_auto_cols(scale_value, printable_width_cm):
    """Schätzt die Standard-Spaltenzahl aus druckbarer Breite und Zellgröße zur Laufzeit."""
    cell_size_cm = max(0.01, _grid_cell_size_to_cm(scale_value))
    return max(1, int(math.floor(printable_width_cm / cell_size_cm)))


def render_dots_answer(options, content, include_solutions, render_solution_text):
    """Rendert ein Punktraster-Antwortfeld mit optionalem eingebetteten Lösungstext-Overlay."""
    height = options.get("height", "4cm")
    solution_text_html = render_solution_text(content, include_solutions)
    if solution_text_html:
        return (
            f"<div class='answer dots answer-overlay-container' style='height:{height}'>"
            f"<div class='answer-overlay-text'>{solution_text_html}</div>"
            "</div>"
        )
    return f"<div class='answer dots' style='height:{height}'></div>"


def render_grid_answer(options, content, include_solutions, render_solution_text):
    """Rendert ein Schreibraster mit optionalem Marker-basiertem Overlay-Text."""
    rows = max(1, _safe_int(options.get("rows", 5), 5))
    scale = _parse_grid_scale(options.get("scale"))
    printable_width_cm = _resolve_runtime_printable_width_cm(options)
    cols_option = options.get("cols")
    has_explicit_cols = cols_option is not None and str(cols_option).strip() != ""
    cols = (
        max(1, _safe_int(cols_option, _DEFAULT_GEOMETRY_COLS))
        if has_explicit_cols
        else _estimate_grid_auto_cols(scale, printable_width_cm)
    )

    grid_classes = ["answer", "grid"]
    style_parts = [f"--rows:{rows}", f"--cell-size:{scale}", f"--cols:{cols}"]

    solution_text_html = render_solution_text(content, include_solutions)
    grid_svg = _render_grid_background_svg(cols, rows)

    overlay_parts = [grid_svg]
    if solution_text_html:
        overlay_parts.append(
            f"<div class='answer-overlay-text'>{solution_text_html}</div>"
        )

    classes_html = " ".join(grid_classes)
    style_html = "; ".join(style_parts)
    if overlay_parts:
        classes_html = f"{classes_html} answer-overlay-container"
        return f"<div class='{classes_html}' style='{style_html}'>{''.join(overlay_parts)}</div>"

    return f"<div class='{classes_html}' style='{style_html}'></div>"


def render_geometry_answer(options, content, include_solutions, render_solution_text):
    """Rendert ein Koordinaten-/Raster-System mit optionalen YAML-definierten Overlays."""
    rows = max(1, _safe_int(options.get("rows", 5), 5))
    scale = _parse_grid_scale(options.get("scale"))
    cell_size_cm = _grid_cell_size_to_cm(scale)
    cols_option = options.get("cols")
    has_explicit_cols = cols_option is not None and str(cols_option).strip() != ""
    cols = max(1, _safe_int(cols_option, _DEFAULT_GEOMETRY_COLS)) if has_explicit_cols else _DEFAULT_GEOMETRY_COLS

    axis_enabled = _option_is_enabled(options.get("axis"), default=False)
    logical_origin = _parse_origin(options.get("origin"), cols, rows) if axis_enabled else None
    if axis_enabled and logical_origin is None:
        axis_enabled = False
    step_x = _parse_positive_float(options.get("step_x"), 1.0)
    step_y = _parse_positive_float(options.get("step_y"), 1.0)
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

    bleed_top_units, bleed_right_units, bleed_bottom_units, bleed_left_units = _estimate_geometry_bleed_units(
        logical_origin,
        cols,
        rows,
        step_x,
        step_y,
        axis_enabled,
        axis_label_x,
        axis_label_y,
    )

    payload, fallback_solution_text = _parse_grid_payload(content)
    grid_background_svg = _render_grid_background_svg(
        cols,
        rows,
        bleed_units=(
            bleed_top_units,
            bleed_right_units,
            bleed_bottom_units,
            bleed_left_units,
        ),
    )
    primitives_svg = _render_grid_primitives_svg(
        options,
        payload,
        rows,
        cols,
        include_solutions,
        bleed_units=(
            bleed_top_units,
            bleed_right_units,
            bleed_bottom_units,
            bleed_left_units,
        ),
    )

    grid_classes = ["answer", "grid"]
    style_parts = [f"--rows:{rows}", f"--cell-size:{scale}", f"--cols:{cols}"]

    solution_text_html = ""
    if include_solutions and fallback_solution_text.strip():
        solution_text_html = render_solution_text(fallback_solution_text)

    overlay_parts = [grid_background_svg]
    if primitives_svg:
        overlay_parts.append(primitives_svg)
    if solution_text_html:
        overlay_parts.append(
            f"<div class='answer-overlay-text'>{solution_text_html}</div>"
        )

    classes_html = " ".join(grid_classes)
    style_html = "; ".join(style_parts)
    if overlay_parts:
        classes_html = f"{classes_html} answer-overlay-container"
        grid_html = (
            f"<div class='{classes_html}' style='{style_html}'>{''.join(overlay_parts)}</div>"
        )
        if primitives_svg:
            bleed_top_cm = bleed_top_units * cell_size_cm
            bleed_right_cm = bleed_right_units * cell_size_cm
            bleed_bottom_cm = bleed_bottom_units * cell_size_cm
            bleed_left_cm = bleed_left_units * cell_size_cm
            bleed_style = (
                f"--grid-bleed-top:{bleed_top_cm:.4f}cm;"
                f"--grid-bleed-right:{bleed_right_cm:.4f}cm;"
                f"--grid-bleed-bottom:{bleed_bottom_cm:.4f}cm;"
                f"--grid-bleed-left:{bleed_left_cm:.4f}cm"
            )
            return f"<div class='grid-system-bleed' style='{bleed_style}'>{grid_html}</div>"
        return grid_html

    return f"<div class='{classes_html}' style='{style_html}'></div>"


def _parse_grid_payload(content):
    """Parst den YAML-Payload für Grid-Overlays und liefert `(payload, fallback_solution_text)`."""
    return parse_yaml_answer_payload_with_solution(content)
