"""Parsing der Geometry-DSL-Objekte: Punkte, Sequenzen, Strecken, Funktionsgraphen.

Normative Quelle für "was ist ein gültiger YAML-Eintrag" je Geometry-Sektion
(`points`, `sequence`, `pairs`, `functions`) — sowohl der Renderer
(`answer_grid_primitives.py`) als auch der Validator
(`blatt_validator_yaml_entries.py`) beziehen ihr Wissen über erlaubte Felder
von hier, damit keine zweite, potenziell abweichende Kopie dieser Liste
entsteht.
"""

from __future__ import annotations

from .answer_special_shared import parse_svg_color, parse_svg_thickness


GEOMETRY_ENTRY_ALLOWED_KEYS = {
    "points": {"x", "y", "col", "row", "label", "show", "color", "thickness"},
    "sequence": {"x", "y", "label", "show", "color", "thickness"},
    "pairs": {"x1", "y1", "x2", "y2", "line", "label", "show", "color", "thickness"},
    "functions": {"expr", "domain", "label", "show", "color", "thickness"},
}
"""Normative Menge erlaubter YAML-Keys je Geometry-Sektion.

Einzige Quelle für "welche Felder darf ein Eintrag in dieser Sektion
haben" — lebt hier neben den `_parse_*`-Funktionen, die diese Felder
tatsächlich lesen, statt in einem separaten Schema-Modul oder im
Validator. `blatt_validator_yaml_entries.py` importiert dieses Dict, um
unbekannte Keys zu erkennen (Diagnose `AN011`); Parser und Validator
können dadurch nicht auseinanderlaufen. Ein Test
(`tests/test_blatt_validator.py`) füllt pro Sektion einen Eintrag mit
*allen* hier gelisteten Keys und prüft sowohl, dass der Validator keine
`AN011`-Diagnose meldet, als auch, dass die jeweilige `_parse_*`-Funktion
kein Feld verliert — das hält beide Seiten nachweisbar synchron.
"""


def _as_float(value):
    """Konvertiert einen Wert nach `float`, liefert `None` statt einer Exception."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_positive_float(value, default):
    """Parst einen strikt positiven `float`, sonst `default`.

    Wird u. a. für `step_x`/`step_y` verwendet — ein Schritt von `0` oder
    negativ ergäbe eine Division durch Null bzw. eine invertierte Achse,
    daher der harte Fallback statt einer Fehlermeldung an dieser Stelle
    (Validierung der Roheingabe passiert separat im Validator).
    """
    parsed = _as_float(value)
    if parsed is None or parsed <= 0:
        return default
    return parsed


def _parse_domain(domain_text):
    """Parst den textuellen Funktions-Definitionsbereich `min:max` (auch `min..max`) als `float`-Tupel."""
    normalized = domain_text.replace("..", ":")
    parts = [part.strip() for part in normalized.split(":") if part.strip()]
    if len(parts) != 2:
        return None, None

    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None


def _inside_grid(x_value, y_value, cols, rows):
    """Prüft, ob ein Punkt innerhalb des sichtbaren Rasterbereichs liegt."""
    return 0.0 <= x_value <= float(cols) and 0.0 <= y_value <= float(rows)


def _normalize_show_mode(show_value):
    """Normalisiert Marker-Sichtbarkeit (`§`/`%`/`&`) auf `worksheet|solution|both`.

    Ein nicht erkannter Wert liefert `"invalid"` statt eines Fehlers —
    die eigentliche Diagnose für ungültige `show`-Werte übernimmt der
    Validator (`AN007`); diese Funktion muss beim Rendern robust bleiben,
    auch wenn ein Dokument (noch) nicht valide ist.
    """
    normalized = str(show_value or "&").strip()
    if normalized == "§":
        return "worksheet"
    if normalized == "%":
        return "solution"
    if normalized == "&":
        return "both"
    return "invalid"


def _is_visible(show_value, include_solutions):
    """Wertet Marker-basierte Sichtbarkeit (`§`, `%`, `&`) für den aktuellen Renderlauf aus."""
    if show_value in {"worksheet", "solution", "both", "invalid"}:
        normalized = show_value
    else:
        normalized = _normalize_show_mode(show_value)
    if normalized == "worksheet":
        return not include_solutions
    if normalized == "solution":
        return include_solutions
    if normalized == "both":
        return True
    return False


def _parse_points(raw_points, axis_enabled, origin, step_x, step_y, include_solutions):
    """Parst `points`-Einträge zu Grid-Tupeln `(x, y, label, color, thickness, mode)`.

    Im Achsenmodus (`axis_enabled`) werden mathematische Koordinaten
    (`x`/`y`) über `origin`/`step_x`/`step_y` in Rasterkoordinaten
    umgerechnet; ohne Achse werden direkte Rasterkoordinaten (`col`/`row`,
    mit `x`/`y` als Alias) erwartet. `color`/`thickness` sind optional und
    werden über `parse_svg_color`/`parse_svg_thickness` sanitized; `None`
    bedeutet "kein gültiger Wert gesetzt", der Renderer fällt dann auf den
    bisherigen Theme-Default zurück.
    """
    if not isinstance(raw_points, list):
        return []

    parsed = []
    for item in raw_points:
        if not isinstance(item, dict):
            continue
        mode = _normalize_show_mode(item.get("show"))
        if not _is_visible(mode, include_solutions):
            continue

        if axis_enabled:
            x = _as_float(item.get("x"))
            y = _as_float(item.get("y"))
            if x is None or y is None or origin is None:
                continue
            gx = origin[0] + (x / step_x)
            gy = origin[1] - (y / step_y)
        else:
            gx = _as_float(item.get("col", item.get("x")))
            gy = _as_float(item.get("row", item.get("y")))
            if gx is None or gy is None:
                continue

        label = str(item.get("label", "")).strip()
        color = parse_svg_color(item.get("color"))
        thickness = parse_svg_thickness(item.get("thickness"))
        parsed.append((gx, gy, label, color, thickness, mode))

    return parsed


def _parse_sequence(raw_sequence, axis_enabled, origin, step_x, step_y, include_solutions):
    """Parst eine `sequence`-Liste aus `(x, y)`-Werten zu einer sortierbaren Polylinie.

    Nur im Achsenmodus sinnvoll (ohne mathematischen Ursprung gibt es keine
    eindeutige Sortierreihenfolge über `x`), daher `[]` ohne `axis_enabled`.
    `color`/`thickness` gelten hier für die aus den Punkten gebildete
    Verbindungslinie (siehe `_render_grid_primitives_svg`), nicht für die
    einzelnen Punktmarkierungen.
    """
    if not axis_enabled or origin is None or not isinstance(raw_sequence, list):
        return []

    parsed = []
    for item in raw_sequence:
        if not isinstance(item, dict):
            continue
        mode = _normalize_show_mode(item.get("show"))
        if not _is_visible(mode, include_solutions):
            continue
        x = _as_float(item.get("x"))
        y = _as_float(item.get("y"))
        if x is None or y is None:
            continue
        gx = origin[0] + (x / step_x)
        gy = origin[1] - (y / step_y)
        label = str(item.get("label", "")).strip()
        color = parse_svg_color(item.get("color"))
        thickness = parse_svg_thickness(item.get("thickness"))
        parsed.append((gx, gy, label, color, thickness, mode))
    return parsed


def _parse_pairs(raw_pairs, axis_enabled, origin, step_x, step_y, include_solutions):
    """Parst `pairs`-Einträge (Strecken) als `(x1, y1, x2, y2, label, color, thickness, mode, line_style)`.

    `line_style` fällt bei fehlendem oder ungültigem `line`-Wert still auf
    `"dashed"` zurück — das ist der bestehende Default-Fallback für die
    *Rendering*-Ebene; eine spätere Phase ergänzt eine Validator-Diagnose
    für ungültige `line`-Werte, ohne diesen Rendering-Fallback zu ändern.
    """
    if not axis_enabled or origin is None or not isinstance(raw_pairs, list):
        return []

    parsed = []
    for item in raw_pairs:
        if not isinstance(item, dict):
            continue
        mode = _normalize_show_mode(item.get("show"))
        if not _is_visible(mode, include_solutions):
            continue
        x1 = _as_float(item.get("x1"))
        y1 = _as_float(item.get("y1"))
        x2 = _as_float(item.get("x2"))
        y2 = _as_float(item.get("y2"))
        if x1 is None or y1 is None or x2 is None or y2 is None:
            continue
        raw_line = str(item.get("line", "dashed")).strip().lower()
        line_style = raw_line if raw_line in ("solid", "dashed") else "dashed"
        gx1 = origin[0] + (x1 / step_x)
        gy1 = origin[1] - (y1 / step_y)
        gx2 = origin[0] + (x2 / step_x)
        gy2 = origin[1] - (y2 / step_y)
        label = str(item.get("label", "")).strip()
        color = parse_svg_color(item.get("color"))
        thickness = parse_svg_thickness(item.get("thickness"))
        parsed.append((gx1, gy1, gx2, gy2, label, color, thickness, mode, line_style))
    return parsed


def _parse_functions(raw_functions, axis_enabled, include_solutions):
    """Parst `functions`-Deskriptoren als `(expr, x_min, x_max, label, color, thickness, mode)`.

    Nur im Achsenmodus sinnvoll, da Funktionsgraphen ohne mathematisches
    Koordinatensystem nicht definiert sind.
    """
    if not axis_enabled or not isinstance(raw_functions, list):
        return []

    parsed = []
    for item in raw_functions:
        if not isinstance(item, dict):
            continue
        mode = _normalize_show_mode(item.get("show"))
        if not _is_visible(mode, include_solutions):
            continue

        expr = str(item.get("expr", "")).strip()
        if not expr:
            continue

        domain = str(item.get("domain", "")).strip() or "-10:10"
        x_min, x_max = _parse_domain(domain)
        if x_min is None or x_max is None or x_min >= x_max:
            continue

        label = str(item.get("label", "")).strip()
        color = parse_svg_color(item.get("color"))
        thickness = parse_svg_thickness(item.get("thickness"))
        parsed.append((expr, x_min, x_max, label, color, thickness, mode))

    return parsed
