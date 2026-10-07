"""Achsen-Geometrie für Grid-Koordinatensysteme: Ursprung, Ticks, Achsenbeschriftung.

Enthält alles, was mit der Umrechnung zwischen logischen Koordinaten
(mathematisches x/y) und Grid-Koordinaten (Spalte/Zeile im Raster) sowie der
visuellen Darstellung der Achsen selbst zu tun hat. Bewusst getrennt von
`answer_grid_entries.py` (Geometrie-Objekte wie Punkte/Strecken/Funktionen),
da Achsen-Rendering und Objekt-Parsing unabhängig veränderbar sein sollen.
"""

from __future__ import annotations

import math

from .answer_grid_label_model import TIER_AXIS, LabelSpec, Obstacle, stroke_pad
from .answer_special_shared import _option_is_enabled


def _parse_origin(raw_origin):
    """Parst den Ursprung im Format `spalte,zeile` ohne Clamping auf die Rastergrenzen.

    Konvention (wie in der Schulmathematik): `(0, 0)` ist die **linke untere**
    Ecke, die Zeile zählt von unten nach oben. Die Umrechnung in die
    SVG-Rasterkoordinate (Zeile von oben) macht ausschließlich
    `origin_to_canvas`.

    Kein `cols`/`rows`-Parameter: das Klemmen auf die *sichtbare*
    Achsenposition übernimmt separat `_clamp_axis_origin`, das reine Parsen
    des Formats braucht die Rastergröße nicht.
    """
    if not raw_origin:
        return None

    text = str(raw_origin).strip().replace(";", ",").replace(" ", "")
    parts = [part for part in text.split(",") if part]
    if len(parts) != 2:
        return None

    try:
        col = float(parts[0])
        row = float(parts[1])
    except ValueError:
        return None

    return col, row


def origin_to_canvas(origin, rows):
    """Rechnet einen Ursprung `(spalte, zeile_von_unten)` in die Rasterkoordinate des SVG um.

    Einzige Stelle für diese Umrechnung (Renderer und Rand-Schätzung rufen sie
    direkt nach `_resolve_axis_state` auf). Das SVG zählt Zeilen von oben, die
    Geometry-DSL von unten: `(0, 0)` = linke untere Ecke.

    Args:
        origin: `(spalte, zeile)` aus `_parse_origin` oder `None`.
        rows: Höhe des Rasters in Rastereinheiten.

    Returns:
        `(spalte, rows - zeile)` bzw. `None`.
    """
    if origin is None:
        return None
    return origin[0], float(rows) - origin[1]


def _resolve_axis_state(options):
    """Löst den Drei-Zustands-Achsenmodus auf: `"disabled"` | `"active"` | `"broken"`.

    - `"disabled"`: `axis` ist nicht gesetzt/falsy -- Geometry-Objekte
      interpretieren ihre Koordinaten roh im Rasterkoordinatensystem.
    - `"active"`: `axis=true` UND `origin` parst erfolgreich zu `(col, row)`
      -- Objekte interpretieren ihre Koordinaten als mathematische
      Koordinaten, umgerechnet über `origin`/`step_x`/`step_y`.
    - `"broken"`: `axis=true`, aber `origin` fehlt oder ist nicht im Format
      `"col,row"` parsebar. Absichtlich **kein** stiller Rückfall auf
      Rasterkoordinaten (der würde eine kaputte Konfiguration verschleiern)
      -- Aufrufer rendern in diesem Zustand *nichts* vom Geometry-Payload
      (siehe `_render_grid_primitives_svg`); der Validator meldet `OP005`.

    Von Renderer (`render_geometry_answer`, `_render_grid_primitives_svg`)
    UND Validator (`blatt_validator_block_options.py`) aufgerufen -- exakt
    dieselbe Funktion, damit beide Seiten strukturell nicht auseinanderlaufen
    können. Bewusst OHNE `cols`/`rows`-Parameter: `_parse_origin` braucht
    die Rastergröße nie, also braucht auch diese Funktion sie nie.
    """
    axis_enabled = _option_is_enabled(options.get("axis"), default=False)
    if not axis_enabled:
        return "disabled", None
    origin = _parse_origin(options.get("origin"))
    if origin is None:
        return "broken", None
    return "active", origin


def _clamp_axis_origin(origin_x, origin_y, cols, rows):
    """Klemmt nur die sichtbare Achsenposition auf das Raster.

    Der *logische* Ursprung (z. B. `origin="20,20"` bei einem 10x10-Raster)
    darf außerhalb des sichtbaren Bereichs liegen — die Achse selbst muss
    aber innerhalb des Rasters gezeichnet werden, damit sie überhaupt
    sichtbar ist. Diese Funktion berechnet genau diese geklemmte Position.
    """
    return (
        _clamp_to_range(origin_x, 0.0, float(cols)),
        _clamp_to_range(origin_y, 0.0, float(rows)),
    )


def _clamp_to_range(value, lower, upper):
    """Klemmt einen Skalar in den geschlossenen Bereich `[lower, upper]`."""
    return max(lower, min(upper, float(value)))


def _resolve_axis_name(options, key, aliases=(), default=""):
    """Löst einen textuellen Achsennamen aus den Block-Optionen auf.

    Unterstützt Alias-Schlüssel (z. B. `x_label`/`axis_x_label` als
    historische Alternativen zu `axis_label_x`), damit ältere Dokumente
    weiter funktionieren, ohne dass die Validierungslogik mehrere
    kanonische Namen kennen muss.
    """
    value = options.get(key)
    if value is None:
        for alias in aliases:
            candidate = options.get(alias)
            if candidate is not None:
                value = candidate
                break
    if value is None:
        return default

    text = str(value).strip()
    return text or default


def _choose_axis_label_stride(tick_count):
    """Wählt eine Beschriftungs-Kadenz, die bei vielen Ticks lesbar bleibt.

    Bei mehr als `max_labels` sichtbaren Ticks würden sich Achsenlabels
    überlappen; die Stride sorgt dafür, dass nur jeder n-te Tick ein Label
    bekommt.
    """
    max_labels = 12
    if tick_count <= max_labels:
        return 1
    return int(math.ceil(tick_count / max_labels))


def _should_render_axis_label(logical_value, stride):
    """Entscheidet, ob ein Tick bei gegebener Stride ein Textlabel bekommt.

    Nur ganzzahlige logische Werte (innerhalb einer Fließkomma-Toleranz)
    werden überhaupt beschriftet — Zwischenschritte durch `step_x`/`step_y`
    unter 1 sollen keine Bruchzahl-Labels erzeugen.
    """
    rounded = int(round(logical_value))
    if abs(logical_value - rounded) > 1e-9:
        return False
    return rounded % max(1, stride) == 0


def _is_inside_axis_label_safe_area(position, limit):
    """Erlaubt Labels auf dem gesamten sichtbaren Achsensegment.

    Getrennte Funktion (statt Inline-Vergleich), damit sich die
    Sicherheitsgrenze für Labels später unabhängig von der reinen
    Sichtbarkeitsprüfung des Rasters anpassen lässt.
    """
    return 0.0 <= float(position) <= float(limit)


def _iter_axis_tick_positions(origin, limit, step_value):
    """Liefert sichtbare Tick-Koordinaten als `(grid_pos, logical_value)`-Tupel.

    `max_ticks` begrenzt die Anzahl hart, damit ein sehr kleiner `step_value`
    (z. B. `step_x=0.001`) nicht zu einer unbegrenzt langen Liste und
    entsprechend langsamem Rendering führt.
    """
    ticks = []
    max_ticks = 240

    start_index = int(math.floor((-origin) * step_value))
    end_index = int(math.ceil((limit - origin) * step_value))

    for logical in range(start_index, end_index + 1):
        grid_pos = origin + (logical / step_value)
        if 0.0 <= grid_pos <= float(limit):
            ticks.append((grid_pos, float(logical)))
        if len(ticks) >= max_ticks:
            break

    return ticks


def _format_axis_label(value):
    """Formatiert Achsenlabels mit Ganzzahl-Präferenz und kompakten Dezimalstellen.

    Ganzzahlige Werte werden ohne Nachkommastellen dargestellt; alles
    andere wird auf zwei Nachkommastellen gerundet und trailing zeros
    entfernt (`1.50` → `1.5`, `1.00` → `1`).
    """
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _render_axis_ticks_and_labels(
    logical_origin_x,
    logical_origin_y,
    axis_origin_x,
    axis_origin_y,
    cols,
    rows,
    step_x,
    step_y,
):
    """Rendert Tick-Striche und Wertelabels für ein Koordinatensystem.

    `logical_origin_*` ist der ungeklemmte, mathematische Ursprung (kann
    außerhalb des Rasters liegen), `axis_origin_*` die geklemmte, sichtbar
    gezeichnete Achsenposition — beide werden gebraucht, weil Ticks anhand
    des logischen Ursprungs positioniert, aber am sichtbaren Achsenkreuz
    angezeichnet werden.

    Liefert `(shapes, label_specs, obstacles)`: die Tick-Zahlenwerte sind
    Text-Labels wie jedes andere Geometry-Label und gehören in der Z-Order
    ganz nach oben, nicht in die Achsen-Bodenschicht (siehe
    `_render_grid_primitives_svg`) -- nur die Tick-Striche selbst bleiben
    unten. Tick-Zahlen sind feste Labels (`movable=False`): das Layout
    verschiebt sie nie, behandelt sie aber wie Tick-Striche als Hindernis
    der Achsen-Stufe.
    """
    shapes, labels, obstacles = [], [], []
    tick_pad = stroke_pad(0.7)
    x_positions = _iter_axis_tick_positions(logical_origin_x, cols, step_x)
    y_positions = _iter_axis_tick_positions(logical_origin_y, rows, step_y)
    x_label_stride = _choose_axis_label_stride(len(x_positions))
    y_label_stride = _choose_axis_label_stride(len(y_positions))

    for gx, logical_x in x_positions:
        shapes.append(
            f"<line class='grid-axis-tick' x1='{gx:.4f}' y1='{axis_origin_y - 0.18:.4f}' x2='{gx:.4f}' y2='{axis_origin_y + 0.18:.4f}' />"
        )
        obstacles.append(Obstacle(TIER_AXIS, "segment", (gx, axis_origin_y - 0.18, gx, axis_origin_y + 0.18), tick_pad))
        if _should_render_axis_label(logical_x, x_label_stride) and _is_inside_axis_label_safe_area(
            gx, cols
        ):
            labels.append(LabelSpec(
                text=_format_axis_label(logical_x), css_class="grid-axis-label", x=gx, y=axis_origin_y + 0.1,
                kind="tick", anchor=(gx, axis_origin_y), movable=False,
            ))

    for gy, logical_y in y_positions:
        shapes.append(
            f"<line class='grid-axis-tick' x1='{axis_origin_x - 0.18:.4f}' y1='{gy:.4f}' x2='{axis_origin_x + 0.18:.4f}' y2='{gy:.4f}' />"
        )
        obstacles.append(Obstacle(TIER_AXIS, "segment", (axis_origin_x - 0.18, gy, axis_origin_x + 0.18, gy), tick_pad))
        if _should_render_axis_label(logical_y, y_label_stride) and _is_inside_axis_label_safe_area(
            gy, rows
        ):
            labels.append(LabelSpec(
                text=_format_axis_label(-logical_y), css_class="grid-axis-label grid-axis-label-y",
                x=axis_origin_x - 0.28, y=gy + 0.04, kind="tick", anchor=(axis_origin_x, gy), movable=False,
            ))

    return shapes, labels, obstacles
