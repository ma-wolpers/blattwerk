"""Achsen-Geometrie für Grid-Koordinatensysteme: Ursprung, Ticks, Achsenbeschriftung.

Enthält alles, was mit der Umrechnung zwischen logischen Koordinaten
(mathematisches x/y) und Grid-Koordinaten (Spalte/Zeile im Raster) sowie der
visuellen Darstellung der Achsen selbst zu tun hat. Bewusst getrennt von
`answer_grid_entries.py` (Geometrie-Objekte wie Punkte/Strecken/Funktionen),
da Achsen-Rendering und Objekt-Parsing unabhängig veränderbar sein sollen.
"""

from __future__ import annotations

import math
from html import escape

from .answer_special_shared import _option_is_enabled


def _parse_origin(raw_origin):
    """Parst den Ursprung im Format `col,row` ohne Clamping auf die Rastergrenzen.

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

    Liefert `(shapes, labels)` getrennt statt einer flachen Liste: die
    Tick-Zahlenwerte sind Text-Labels wie jedes andere Geometry-Label und
    gehören in der Z-Order ganz nach oben, nicht in die Achsen-Bodenschicht
    (siehe `_render_grid_primitives_svg`) -- nur die Tick-Striche selbst
    bleiben unten.
    """
    shapes = []
    labels = []
    x_positions = _iter_axis_tick_positions(logical_origin_x, cols, step_x)
    y_positions = _iter_axis_tick_positions(logical_origin_y, rows, step_y)
    x_label_stride = _choose_axis_label_stride(len(x_positions))
    y_label_stride = _choose_axis_label_stride(len(y_positions))

    for gx, logical_x in x_positions:
        shapes.append(
            f"<line class='grid-axis-tick' x1='{gx:.4f}' y1='{axis_origin_y - 0.18:.4f}' x2='{gx:.4f}' y2='{axis_origin_y + 0.18:.4f}' />"
        )
        if _should_render_axis_label(logical_x, x_label_stride) and _is_inside_axis_label_safe_area(
            gx, cols
        ):
            labels.append(
                f"<text class='grid-axis-label' x='{gx:.4f}' y='{axis_origin_y + 0.1:.4f}'>{_format_axis_label(logical_x)}</text>"
            )

    for gy, logical_y in y_positions:
        shapes.append(
            f"<line class='grid-axis-tick' x1='{axis_origin_x - 0.18:.4f}' y1='{gy:.4f}' x2='{axis_origin_x + 0.18:.4f}' y2='{gy:.4f}' />"
        )
        if _should_render_axis_label(logical_y, y_label_stride) and _is_inside_axis_label_safe_area(
            gy, rows
        ):
            labels.append(
                f"<text class='grid-axis-label grid-axis-label-y' x='{axis_origin_x - 0.28:.4f}' y='{gy + 0.04:.4f}'>{_format_axis_label(-logical_y)}</text>"
            )

    return shapes, labels


def _render_axis_arrowheads_and_names(origin_x, origin_y, cols, rows, axis_label_x, axis_label_y):
    """Rendert Pfeilspitzen am positiven Achsenende sowie die Achsennamen (z. B. `x`, `y`).

    Pfeilspitzen werden nur gezeichnet, wenn zwischen Ursprung und Rasterrand
    genug Platz ist (`x_base < x_tip` / `y_tip < y_base`) — bei sehr kleinen
    Rastern oder einem Ursprung nahe am Rand würde eine erzwungene Pfeilspitze
    sonst invertiert oder verzerrt wirken.

    Liefert `(shapes, labels)` getrennt statt einer flachen Liste: die
    Achsennamen (`axis_label_x`/`axis_label_y`) sind Text-Labels wie jedes
    andere Geometry-Label und gehören in der Z-Order ganz nach oben, nicht
    in die Achsen-Bodenschicht -- nur die Pfeilspitzen selbst bleiben unten.
    """
    shapes = []
    labels = []

    x_tip = float(cols) + 0.34
    x_base = max(origin_x + 0.24, x_tip - 0.44)
    x_top = max(0.04, origin_y - 0.18)
    x_bottom = min(float(rows) - 0.04, origin_y + 0.18)
    if x_base < x_tip:
        shapes.append(
            "<polygon class='grid-axis' points='"
            f"{x_tip:.4f},{origin_y:.4f} {x_base:.4f},{x_top:.4f} {x_base:.4f},{x_bottom:.4f}' />"
        )
    if axis_label_x:
        x_name_y = origin_y - 0.28
        x_name_x = x_tip + 0.16
        labels.append(
            f"<text class='grid-axis-label grid-axis-name' x='{x_name_x:.4f}' y='{x_name_y:.4f}' text-anchor='start'>{escape(axis_label_x)}</text>"
        )

    y_tip = -0.34
    y_base = min(origin_y - 0.24, y_tip + 0.44)
    y_left = max(0.04, origin_x - 0.18)
    y_right = min(float(cols) - 0.04, origin_x + 0.18)
    if y_tip < y_base:
        shapes.append(
            "<polygon class='grid-axis' points='"
            f"{origin_x:.4f},{y_tip:.4f} {y_left:.4f},{y_base:.4f} {y_right:.4f},{y_base:.4f}' />"
        )
    if axis_label_y:
        y_name_x = origin_x - 0.1
        y_name_y = y_tip - 0.9
        labels.append(
            f"<text class='grid-axis-label grid-axis-name' x='{y_name_x:.4f}' y='{y_name_y:.4f}' text-anchor='end'>{escape(axis_label_y)}</text>"
        )

    return shapes, labels
