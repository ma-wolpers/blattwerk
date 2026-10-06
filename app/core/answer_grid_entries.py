"""Parsing der Geometry-DSL-Objekte: Punkte, Sequenzen, Strecken, Funktionsgraphen, Polygone, Kreise/Bögen.

Normative Quelle für "was ist ein gültiger YAML-Eintrag" je Geometry-Sektion
(`points`, `sequence`, `pairs`, `functions`, `polygons`, `circles`) — sowohl
der Renderer (`answer_grid_primitives.py`, `answer_grid_shapes.py`) als
auch der Validator (`blatt_validator_yaml_entries.py`) beziehen ihr Wissen
über erlaubte Felder von hier, damit keine zweite, potenziell abweichende
Kopie dieser Liste entsteht. Enthält außerdem `_GeometryCoordinateSystem`,
die einzige Stelle, an der die Umrechnung Objekt-Koordinaten ->
Rasterkoordinaten passiert. Die reinen, renderer-unabhängigen
Validitätsprädikate für `polygons`/`circles` leben in einem eigenen,
ebenfalls neutralen Modul (`answer_grid_validity.py`, 300-Zeilen-
Konvention) statt hier -- Details dort.
"""

from __future__ import annotations

from dataclasses import dataclass

from .answer_special_shared import parse_svg_color, parse_svg_thickness


GEOMETRY_ENTRY_ALLOWED_KEYS = {
    "points": {"x", "y", "col", "row", "label", "show", "color", "thickness"},
    "sequence": {"x", "y", "label", "show", "color", "thickness"},
    "pairs": {"x1", "y1", "x2", "y2", "line", "label", "show", "color", "thickness"},
    "polygons": {"vertices", "label", "show", "color", "thickness", "fill"},
    "circles": {"cx", "cy", "r", "start_angle", "end_angle", "label", "show", "color", "thickness", "fill"},
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


@dataclass(frozen=True)
class _GeometryCoordinateSystem:
    """Bündelt die Umrechnung Objekt-Koordinaten -> Rasterkoordinaten an EINER Stelle.

    Ersetzt das frühere Muster, `axis_enabled`/`origin`/`step_x`/`step_y`
    als lose Parameter durch jede `_parse_*`-Funktion einzeln
    durchzureichen -- die Umrechnungsformel existiert dadurch nur noch
    einmal (hier), statt in `_parse_points`/`_parse_sequence`/`_parse_pairs`
    und `_sample_function_points` (`answer_grid_function_eval.py`) separat
    dupliziert zu werden.

    `axis_active` ist nur im Tri-State `"active"` `True` (siehe
    `_resolve_axis_state`, `answer_grid_axis.py`) -- der Zustand `"broken"`
    erreicht das Parsing gar nicht erst, `_render_grid_primitives_svg`
    bricht dafür schon vorher ab.

    Eine einzige Konvention für alle Sektionen: `(0, 0)` ist die **linke
    untere** Ecke, `y` wächst nach oben -- ohne Achse direkt in Rastereinheiten,
    mit Achse relativ zu `origin` (dessen Zeile ebenfalls von unten zählt, siehe
    `answer_grid_axis.origin_to_canvas`). `origin` hier ist bereits die
    SVG-Rasterkoordinate. (Bis 2026-10-06 zählten `points[].col`/`row` und die
    `origin`-Zeile von oben; Bestandsdokumente wurden migriert.)
    """

    axis_active: bool
    origin: tuple[float, float] | None
    step_x: float
    step_y: float
    canvas_height: float

    def point(self, x, y):
        """Bildet eine Objekt-Koordinate `(x, y)` auf eine Rasterkoordinate ab."""
        if self.axis_active:
            return self.origin[0] + (x / self.step_x), self.origin[1] - (y / self.step_y)
        return x, self.canvas_height - y

    def radius(self, r):
        """Bildet einen skalaren Radius `r` auf `(rx, ry)` in Rastereinheiten ab.

        Im Achsenmodus ggf. anisotrop (unterschiedliche `step_x`/`step_y`
        ergeben eine Ellipse); ohne Achse ist die Rasterzelle immer
        quadratisch, daher `(r, r)`.
        """
        if self.axis_active:
            return r / self.step_x, r / self.step_y
        return r, r


def _parse_points(raw_points, coord_system, include_solutions):
    """Parst `points`-Einträge zu Grid-Tupeln `(x, y, label, color, thickness, mode)`.

    Im Achsenmodus (`coord_system.axis_active`) werden mathematische
    Koordinaten (`x`/`y`) umgerechnet; ohne Achse Rasterkoordinaten
    (`col`/`row`, mit `x`/`y` als Alias) mit Ursprung links unten -- in beiden
    Fällen über `coord_system.point()`, wie bei allen anderen Sektionen.
    `color`/`thickness` sind optional und werden über `parse_svg_color`/
    `parse_svg_thickness` sanitized; `None` bedeutet "kein gültiger Wert
    gesetzt", der Renderer fällt dann auf den bisherigen Theme-Default zurück.
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

        if coord_system.axis_active:
            x = _as_float(item.get("x"))
            y = _as_float(item.get("y"))
            if x is None or y is None:
                continue
            gx, gy = coord_system.point(x, y)
        else:
            col = _as_float(item.get("col", item.get("x")))
            row = _as_float(item.get("row", item.get("y")))
            if col is None or row is None:
                continue
            gx, gy = coord_system.point(col, row)

        label = str(item.get("label", "")).strip()
        color = parse_svg_color(item.get("color"))
        thickness = parse_svg_thickness(item.get("thickness"))
        parsed.append((gx, gy, label, color, thickness, mode))

    return parsed


def _parse_sequence(raw_sequence, coord_system, include_solutions):
    """Parst eine `sequence`-Liste aus `(x, y)`-Werten zu einer sortierbaren Polylinie.

    Funktioniert in beiden Achsenzuständen: im Achsenmodus mathematische
    Koordinaten über `coord_system.point()`, sonst Rasterkoordinaten mit
    Ursprung unten links (`(0, 0)`, y nach oben) -- derselbe Umrechnungsweg
    wie bei `pairs`. `color`/`thickness` gelten hier für die aus den
    Punkten gebildete Verbindungslinie (siehe `_render_grid_primitives_svg`),
    nicht für die einzelnen Punktmarkierungen.
    """
    if not isinstance(raw_sequence, list):
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
        gx, gy = coord_system.point(x, y)
        label = str(item.get("label", "")).strip()
        color = parse_svg_color(item.get("color"))
        thickness = parse_svg_thickness(item.get("thickness"))
        parsed.append((gx, gy, label, color, thickness, mode))
    return parsed


def _parse_pairs(raw_pairs, coord_system, include_solutions):
    """Parst `pairs`-Einträge (Strecken) als `(x1, y1, x2, y2, label, color, thickness, mode, line_style)`.

    Funktioniert in beiden Achsenzuständen: im Achsenmodus mathematische
    Koordinaten über `coord_system.point()`, sonst Rasterkoordinaten mit
    Ursprung unten links (`(0, 0)`, y nach oben) -- mathematisch identisch
    zum Achsenmodus-Pfad mit `origin=(0, canvas_height)`, `step_x=step_y=1`,
    nur ohne dass dafür ein Achsenkreuz gezeichnet wird (das bleibt
    ausschließlich an `axis_active` in `_render_grid_primitives_svg`
    gekoppelt). `line_style` fällt bei fehlendem oder ungültigem `line`-Wert
    still auf `"dashed"` zurück — das ist der bestehende Default-Fallback
    für die *Rendering*-Ebene, unabhängig von der separaten Validator-
    Diagnose (`AN012`) für ungültige `line`-Werte.
    """
    if not isinstance(raw_pairs, list):
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
        gx1, gy1 = coord_system.point(x1, y1)
        gx2, gy2 = coord_system.point(x2, y2)
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
