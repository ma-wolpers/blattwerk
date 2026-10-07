"""Reine, renderer-unabhängige Validitätsprädikate für `polygons`/`circles`-Einträge.

Ausgelagert aus `answer_grid_entries.py` (300-Zeilen-Konvention). Bleibt
trotzdem ein von `answer_grid_shapes.py`/`answer_grid_circles.py` (Renderer/Parser) UNABHÄNGIGES
Modul: sowohl der Parser (`_parse_polygons`/`_parse_circles`,
`answer_grid_shapes.py`/`answer_grid_circles.py`) als auch der Validator (`AN017`/`AN018`,
`blatt_validator_yaml_entries.py`) importieren dieselben Funktionen von
hier, damit kein zweites, potenziell abweichendes Regelwerk entsteht und
der Validator nie von einem Renderer-Modul abhängen muss.
"""

from __future__ import annotations

from .answer_grid_entries import _as_float


def _polygon_vertices_are_valid(raw_vertices):
    """Prüft, ob `vertices` mindestens 3 Einträge hat und JEDER Eintrag ein Dict mit numerischem `x`/`y` ist.

    Bewusst KEIN Teil-Repair: ist auch nur ein Eckpunkt ungültig, gilt das
    gesamte Polygon als ungültig (der Aufrufer verwirft den kompletten
    Eintrag), statt heimlich ein anderes, kleineres Polygon aus den
    verbleibenden gültigen Eckpunkten zu bilden.
    """
    if not isinstance(raw_vertices, list) or len(raw_vertices) < 3:
        return False
    for vertex in raw_vertices:
        if not isinstance(vertex, dict):
            return False
        if _as_float(vertex.get("x")) is None or _as_float(vertex.get("y")) is None:
            return False
    return True


def _circle_center_and_radius_are_valid(entry):
    """Prüft, ob `cx`/`cy`/`r` numerisch sind und `r > 0` gilt."""
    cx = _as_float(entry.get("cx"))
    cy = _as_float(entry.get("cy"))
    r = _as_float(entry.get("r"))
    return cx is not None and cy is not None and r is not None and r > 0


def _circle_angle_fields_are_valid(entry):
    """Prüft, ob `start_angle`/`end_angle` entweder BEIDE fehlen oder BEIDE vorhanden und numerisch parsebar sind.

    Presence (`is not None` auf dem ROHEN `entry.get(...)`-Wert) und
    Parsability (`_as_float(...) is not None`) werden bewusst getrennt
    geprüft -- ein vorhandener, aber nicht parsebarer Wert (z. B.
    `start_angle: "abc"`) darf NICHT wie ein fehlendes Feld behandelt
    werden, sonst würde ein offensichtlicher Tippfehler stillschweigend
    als "beide fehlen -> Vollkreis" durchgehen. Genau ein Feld gesetzt
    (unabhängig davon, ob parsebar) ist ebenfalls ungültig.
    """
    raw_start = entry.get("start_angle")
    raw_end = entry.get("end_angle")
    start_present = raw_start is not None
    end_present = raw_end is not None
    if not start_present and not end_present:
        return True
    if start_present != end_present:
        return False
    return _as_float(raw_start) is not None and _as_float(raw_end) is not None


def _describe_circle_angle_problem(entry):
    """Liefert eine präzise Fehlerbeschreibung, wenn `_circle_angle_fields_are_valid()` `False` liefert, sonst `None`.

    Unterscheidet "nur einer gesetzt" von "beide gesetzt, aber mindestens
    einer ungültig" -- eine einzige generische Meldung für beide Fälle
    würde beim Debuggen unnötig im Unklaren lassen, welcher der beiden
    Fehler tatsächlich vorliegt.
    """
    raw_start = entry.get("start_angle")
    raw_end = entry.get("end_angle")
    start_present = raw_start is not None
    end_present = raw_end is not None
    if start_present != end_present:
        set_name, missing_name = ("start_angle", "end_angle") if start_present else ("end_angle", "start_angle")
        return f"nur `{set_name}` ist gesetzt, `{missing_name}` fehlt -- beide oder keiner sind erlaubt"
    if start_present and end_present:
        if _as_float(raw_start) is None or _as_float(raw_end) is None:
            return (
                f"`start_angle`/`end_angle` sind gesetzt, aber nicht beide numerisch parsebar "
                f"(`start_angle={raw_start}`, `end_angle={raw_end}`)"
            )
    return None


def _circle_is_full(start_angle, end_angle):
    """Vollkreis: beide Winkel fehlen (`None`) ODER sind gleich modulo 360° (z. B. `0`/`360`)."""
    if start_angle is None or end_angle is None:
        return True
    return abs((end_angle - start_angle) % 360.0) < 1e-9
