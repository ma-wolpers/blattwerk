"""Inhaltliche Prüfungen für `table`, `numberline` und `geometry`: Maße, Bereiche, Formeln.

Alle Größen kommen aus den Funktionen der Renderer (`resolve_table_layout`,
`_build_number_line_config`, `_resolve_axis_state`), damit Warnung und Darstellung
übereinstimmen.
"""

from __future__ import annotations

import yaml

from .answer_grid_axis import _resolve_axis_state
from .answer_grid_function_eval import _eval_function_expr
from .answer_numberline_parse import _build_number_line_config, _parse_number_line_payload
from .answer_numberline_values import _as_numberline_float
from .answer_table_content import parse_table_content_payload
from .answer_table_layout import parse_positional_option_list
from .answer_special_shared import _safe_int

_DEFAULT_TABLE_ROWS = 4
_SAMPLE_POINTS = 21
_DEFAULT_DOMAIN = (-10.0, 10.0)


def check_table(collect, options, content) -> None:
    """Prüft Tabellenmaße gegen Zellen und Kopfzeilen (`AN032`, `AN033`, `AN049`).

    Der Renderer lässt das Größte gewinnen. Ein ausdrückliches `rows=`/`cols=`, das nicht
    passt, ist also fast immer ein Versehen.
    """
    cells, _extra = parse_table_content_payload(content)
    widest = max((len(row) for row in cells), default=0)
    if "cols" in options and widest > _safe_int(options.get("cols"), widest):
        collect.add("AN032", f"`cols={options['cols']}`, aber eine Zeile in `cells:` hat {widest} Zellen.")
    if "rows" in options and len(cells) > _safe_int(options.get("rows"), len(cells)):
        collect.add("AN032", f"`rows={options['rows']}`, aber `cells:` hat {len(cells)} Zeilen.", anchor="AN032:rows")
    column_headers = parse_positional_option_list(options.get("column_headers"))
    data_cols = max(_safe_int(options.get("cols"), 0), widest)
    if column_headers and data_cols and len(column_headers) != data_cols:
        collect.add("AN049", f"`column_headers` hat {len(column_headers)} Einträge bei {data_cols} Spalten.", anchor="AN049:column_headers")
    row_headers = parse_positional_option_list(options.get("row_headers"))
    data_rows = max(_safe_int(options.get("rows"), 0), len(cells))
    if row_headers and data_rows and len(row_headers) != data_rows:
        collect.add("AN049", f"`row_headers` hat {len(row_headers)} Einträge bei {data_rows} Zeilen.", anchor="AN049:row_headers")
    if cells and "rows" not in options and len(cells) < _DEFAULT_TABLE_ROWS and len(row_headers) < _DEFAULT_TABLE_ROWS:
        collect.add("AN033", f"`cells:` hat {len(cells)} Zeilen, ohne `rows=` wird auf {_DEFAULT_TABLE_ROWS} aufgefüllt.")


def check_numberline(collect, options, content) -> None:
    """Prüft Bereich und Werte der Zahlengerade (`AN037`-`AN039`)."""
    low = _as_numberline_float(options.get("min") or options.get("minimum"))
    high = _as_numberline_float(options.get("max") or options.get("maximum"))
    if low is not None and high is not None and high <= low:
        collect.add("AN038", f"`min={low:g}` muss kleiner sein als `max={high:g}`.", severity="error")
        return
    step = _as_numberline_float(options.get("tick_step"))
    if step is not None and step <= 0:
        collect.add("AN039", "`tick_step` muss größer als 0 sein.", severity="error")
        return
    config = _build_number_line_config(options)
    number_min, number_max = config["min"], config["max"]
    payload, _solution = _parse_number_line_payload(content)
    for section in ("labels", "answers", "values"):
        for entry in payload.get(section) or [] if isinstance(payload, dict) else []:
            value = _as_numberline_float(entry.get("value") if isinstance(entry, dict) else entry)
            if value is not None and not number_min <= value <= number_max:
                collect.add("AN037", f"`{value:g}` in `{section}` liegt außerhalb von {number_min:g} bis {number_max:g}.", anchor=f"AN037:{section}:{value:g}")


def _visible_range(options):
    """Sichtbarer Bereich `(x_min, x_max, y_min, y_max)`, `None` ohne brauchbare Maße.

    Ohne Achse sind es die Rasterzellen, mit Achse mathematische Koordinaten.
    """
    width, height = _safe_int(options.get("width"), 0), _safe_int(options.get("height"), 0)
    if width <= 0 or height <= 0:
        return None
    state = _resolve_axis_state(options)
    mode, origin = state
    if mode != "active":
        return 0.0, float(width), 0.0, float(height)
    origin_x, origin_y = origin
    step_x = _as_numberline_float(options.get("step_x")) or 1.0
    step_y = _as_numberline_float(options.get("step_y")) or 1.0
    return (
        -origin_x * step_x,
        (width - 1 - origin_x) * step_x,
        -origin_y * step_y,
        (height - 1 - origin_y) * step_y,
    )


def _check_points(collect, payload, visible) -> None:
    """Punkte außerhalb der Fläche wären unsichtbar oder abgeschnitten (`AN040`)."""
    x_min, x_max, y_min, y_max = visible
    for section in ("points", "sequence"):
        for number, entry in enumerate(payload.get(section) or [], start=1):
            if not isinstance(entry, dict):
                continue
            x = _as_numberline_float(entry.get("x", entry.get("col")))
            y = _as_numberline_float(entry.get("y", entry.get("row")))
            if x is None or y is None:
                continue
            if not (x_min <= x <= x_max and y_min <= y <= y_max):
                collect.add("AN040", f"Punkt {number} in `{section}` ({x:g}|{y:g}) liegt außerhalb der Fläche.", anchor=f"AN040:{section}:{number}")


def _check_functions(collect, payload) -> None:
    """Funktionsterme müssen sich auswerten lassen (`AN041`)."""
    for number, entry in enumerate(payload.get("functions") or [], start=1):
        expr = entry.get("expr") if isinstance(entry, dict) else None
        if not expr:
            continue
        low, high = _DEFAULT_DOMAIN
        samples = [_eval_function_expr(expr, low + (high - low) * i / (_SAMPLE_POINTS - 1)) for i in range(_SAMPLE_POINTS)]
        if all(value is None for value in samples):
            collect.add("AN041", f"Der Term `{expr}` in `functions[{number}]` lässt sich nicht auswerten.", severity="error", anchor=f"AN041:{number}")


def check_geometry(collect, options, content) -> None:
    """Prüft Punkte gegen die Fläche und Funktionsterme."""
    try:
        payload = yaml.safe_load(content or "")
    except yaml.YAMLError:
        return
    if not isinstance(payload, dict):
        return
    visible = _visible_range(options)
    if visible is not None:
        _check_points(collect, payload, visible)
    _check_functions(collect, payload)
