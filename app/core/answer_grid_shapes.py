"""Parsing und Rendering der Geometry-DSL-Objekte `polygons`/`circles`.

Ausgelagert aus `answer_grid_entries.py`/`answer_grid_primitives.py` (300-
Zeilen-Konvention) -- die normativen, renderer-unabhängigen Validitäts-
prädikate (`_polygon_vertices_are_valid` u. a.) leben in einem eigenen,
ebenfalls neutralen Modul (`answer_grid_validity.py`), damit der Validator
sie importieren kann, ohne von diesem Renderer-Modul abzuhängen. Nutzt
dieselben Bausteine wie die übrigen `_parse_*`-Funktionen (`_as_float`,
`_normalize_show_mode`, `_is_visible`, `_GeometryCoordinateSystem` aus
`answer_grid_entries.py`; `parse_svg_color`/`parse_svg_thickness` aus
`answer_special_shared.py`; `_svg_shape_style_attr`/`_svg_fill_style_attr`
aus `answer_grid_svg_style.py`) statt eine zweite Kopie dieser
Grundbausteine zu führen.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape

from .answer_grid_entries import _as_float, _is_visible, _normalize_show_mode
from .answer_grid_svg_style import _svg_fill_style_attr, _svg_shape_style_attr
from .answer_grid_validity import (
    _circle_angle_fields_are_valid,
    _circle_center_and_radius_are_valid,
    _circle_is_full,
    _polygon_vertices_are_valid,
)
from .answer_special_shared import parse_svg_color, parse_svg_thickness


@dataclass(frozen=True)
class ParsedPolygon:
    """Ein geparstes `polygons[]`-Objekt, bereits in Rasterkoordinaten.

    `@dataclass(frozen=True)`, nicht `NamedTuple` -- folgt derselben
    Konvention wie `BlockOptionSpec`/`GeometryEntrySpec` im übrigen
    `app/core`, statt eine zweite Struktur-Konvention einzuführen.
    """

    vertices: tuple[tuple[float, float], ...]
    label: str
    color: str | None
    thickness: float | None
    fill: str | None
    mode: str


def _polygon_centroid(vertices):
    """Berechnet den Flächenschwerpunkt eines Polygons (Shoelace-Formel).

    Für einfache (nicht selbstüberschneidende) Polygone -- konvex oder
    konkav -- entspricht das exakt dem echten geometrischen
    Flächenschwerpunkt. Selbstüberschneidende Konturen sind ausdrücklich
    ohne Geometrieprüfung erlaubt (siehe `_parse_polygons`); für sie gibt
    es keine einzige, eindeutig definierte Fläche, auf die sich ein
    physikalischer Schwerpunkt beziehen könnte -- dieselbe Formel liefert
    trotzdem deterministisch einen wohldefinierten mathematischen Anker
    (den signed-area-Zentroid der gegebenen Punktfolge), der in diesem
    Fall aber NICHT als "der echte Flächenschwerpunkt" im physikalischen
    Sinn zu verstehen ist -- nur als konsistenter, vorhersagbarer
    Ankerpunkt für die Label-Platzierung. Es wird bewusst keine
    zusätzliche Geometriezerlegung eingeführt, um das zu "reparieren".

    Im entarteten Nullflächen-Fall (alle Eckpunkte kollinear) fällt NUR
    der Label-Anker auf den arithmetischen Mittelwert der Eckpunkte
    zurück -- die Kontur selbst wird davon unabhängig unverändert aus den
    gegebenen Vertices gezeichnet.
    """
    n = len(vertices)
    signed_area = 0.0
    centroid_x = 0.0
    centroid_y = 0.0
    for i in range(n):
        x_i, y_i = vertices[i]
        x_next, y_next = vertices[(i + 1) % n]
        cross = x_i * y_next - x_next * y_i
        signed_area += cross
        centroid_x += (x_i + x_next) * cross
        centroid_y += (y_i + y_next) * cross
    signed_area *= 0.5

    if abs(signed_area) < 1e-9:
        return sum(v[0] for v in vertices) / n, sum(v[1] for v in vertices) / n

    return centroid_x / (6.0 * signed_area), centroid_y / (6.0 * signed_area)


def _parse_polygons(raw_polygons, coord_system, include_solutions):
    """Parst `polygons`-Einträge zu `ParsedPolygon`; ein ungültiger Vertex verwirft den GESAMTEN Eintrag.

    Kein Teil-Repair (siehe `_polygon_vertices_are_valid`): entweder sind
    ALLE Vertices gültig, dann wird das komplette Polygon übernommen, oder
    der Eintrag wird komplett übersprungen (Validator meldet `AN017`).
    Funktioniert in beiden Achsenzuständen über `coord_system.point()`
    (mathematische Koordinaten im Achsenmodus, sonst Rasterkoordinaten mit
    Ursprung unten links) -- kein `col`/`row`-Alias auf Vertex-Ebene, da es
    hier (anders als bei `points`) keine Namenskollision zu vermeiden gibt.
    """
    if not isinstance(raw_polygons, list):
        return []

    parsed = []
    for item in raw_polygons:
        if not isinstance(item, dict):
            continue
        mode = _normalize_show_mode(item.get("show"))
        if not _is_visible(mode, include_solutions):
            continue

        raw_vertices = item.get("vertices")
        if not _polygon_vertices_are_valid(raw_vertices):
            continue

        vertices = tuple(
            coord_system.point(_as_float(vertex["x"]), _as_float(vertex["y"])) for vertex in raw_vertices
        )
        parsed.append(
            ParsedPolygon(
                vertices=vertices,
                label=str(item.get("label", "")).strip(),
                color=parse_svg_color(item.get("color")),
                thickness=parse_svg_thickness(item.get("thickness")),
                fill=parse_svg_color(item.get("fill")),
                mode=mode,
            )
        )
    return parsed


def _render_polygons_section(raw_entries, coord_system, cols, rows, include_solutions):
    """Section-Renderer für `polygons`: liefert `(shapes, labels)` getrennt (siehe Z-Order-Regel).

    Immer als geschlossene Fläche gerendert (SVG `<polygon>` verbindet
    automatisch den letzten mit dem ersten Punkt) -- selbstüberschneidende
    Konturen werden dabei ohne weitere Prüfung genau so gezeichnet, wie
    angegeben (keine komplexe Geometrieprüfung, bewusste Produktentscheidung).
    """
    entries = _parse_polygons(raw_entries, coord_system, include_solutions)
    shapes, labels = [], []
    for polygon in entries:
        points_attr = " ".join(f"{vx:.4f},{vy:.4f}" for vx, vy in polygon.vertices)
        style = _svg_shape_style_attr(polygon.color, polygon.thickness, polygon.fill)
        shapes.append(
            f"<polygon class='grid-polygon grid-mode-{polygon.mode}'{style} points='{points_attr}' />"
        )
        if polygon.label:
            label_x, label_y = _polygon_centroid(polygon.vertices)
            labels.append(
                f"<text class='grid-polygon-label grid-mode-{polygon.mode}'{_svg_fill_style_attr(polygon.color)} "
                f"x='{label_x:.4f}' y='{label_y:.4f}'>{escape(polygon.label)}</text>"
            )
    return shapes, labels


@dataclass(frozen=True)
class ParsedCircle:
    """Ein geparstes `circles[]`-Objekt (Vollkreis/Ellipse/Bogen), bereits in Rasterkoordinaten.

    `start_angle`/`end_angle` sind entweder beide `None` (Vollkreis/Ellipse)
    oder beide gesetzt (Bogen) -- niemals nur eines (siehe
    `_circle_angle_fields_are_valid`, das solche Einträge bereits im
    Parser aussortiert).
    """

    cx: float
    cy: float
    rx: float
    ry: float
    start_angle: float | None
    end_angle: float | None
    label: str
    color: str | None
    thickness: float | None
    fill: str | None
    mode: str


def _parse_circles(raw_circles, coord_system, include_solutions):
    """Parst `circles`-Einträge zu `ParsedCircle`; unvollständige/ungültige Angaben verwerfen den GESAMTEN Eintrag.

    Winkelregeln (siehe `_circle_angle_fields_are_valid`/`_circle_is_full`):
    beide Winkel fehlen ODER sind gleich modulo 360° -> Vollkreis/Ellipse;
    beide gesetzt und ungleich -> Bogen; genau einer gesetzt, oder beide
    gesetzt aber mindestens einer nicht parsebar -> Eintrag verworfen
    (Validator meldet `AN018`). Kein `col`/`row`-Alias für `cx`/`cy` --
    anders als bei `points` gibt es hier keine Namenskollision zu vermeiden.
    """
    if not isinstance(raw_circles, list):
        return []

    parsed = []
    for item in raw_circles:
        if not isinstance(item, dict):
            continue
        mode = _normalize_show_mode(item.get("show"))
        if not _is_visible(mode, include_solutions):
            continue
        if not _circle_center_and_radius_are_valid(item) or not _circle_angle_fields_are_valid(item):
            continue

        cx = _as_float(item["cx"])
        cy = _as_float(item["cy"])
        r = _as_float(item["r"])
        cgx, cgy = coord_system.point(cx, cy)
        rx, ry = coord_system.radius(r)

        start_angle = _as_float(item.get("start_angle"))
        end_angle = _as_float(item.get("end_angle"))
        if _circle_is_full(start_angle, end_angle):
            start_angle, end_angle = None, None

        parsed.append(
            ParsedCircle(
                cx=cgx,
                cy=cgy,
                rx=rx,
                ry=ry,
                start_angle=start_angle,
                end_angle=end_angle,
                label=str(item.get("label", "")).strip(),
                color=parse_svg_color(item.get("color")),
                thickness=parse_svg_thickness(item.get("thickness")),
                fill=parse_svg_color(item.get("fill")),
                mode=mode,
            )
        )
    return parsed


def _render_circles_section(raw_entries, coord_system, cols, rows, include_solutions):
    """Section-Renderer für `circles`: liefert `(shapes, labels)` getrennt (siehe Z-Order-Regel).

    Winkelkonvention: Grad, `0°` = Osten (positive x-Achse-Richtung),
    wachsend entgegen dem Uhrzeigersinn (Schulmathematik-/Einheitskreis-
    Konvention). Da SVG-`y` nach unten wächst: `gx = cx + rx·cos(θ)`,
    `gy = cy − ry·sin(θ)`. Der Bogen läuft immer von `start_angle`
    AUFSTEIGEND zu `end_angle` (bei `end < start` über 360° hinweg, "der
    lange Weg"); `sweep-flag` ist deshalb IMMER `0` (eine mathematisch
    entgegen-dem-Uhrzeigersinn verlaufende Bewegung erscheint in SVG-
    Bildschirmkoordinaten mit y-nach-unten als "gegen den SVG-Sweep-Sinn").
    `large_arc_flag = 1`, wenn die normierte Winkelspanne `> 180°` ist,
    sonst `0`. Negative Winkel und Winkel `> 360°` brauchen keine
    Sonderbehandlung: `cos`/`sin` sind für beliebige reelle Eingaben
    periodisch, nur die Spannweiten-Berechnung braucht das `% 360`.

    Kreis-vs-Ellipse-Entscheidung über `math.isclose` (nicht `==` oder eine
    feste absolute Epsilon) -- robust für beliebig kleine/große Radien.
    """
    entries = _parse_circles(raw_entries, coord_system, include_solutions)
    shapes, labels = [], []
    for circle in entries:
        style = _svg_shape_style_attr(circle.color, circle.thickness, circle.fill)
        if circle.start_angle is None or circle.end_angle is None:
            if math.isclose(circle.rx, circle.ry, rel_tol=1e-9):
                shapes.append(
                    f"<circle class='grid-circle grid-mode-{circle.mode}'{style} "
                    f"cx='{circle.cx:.4f}' cy='{circle.cy:.4f}' r='{circle.rx:.4f}' />"
                )
            else:
                shapes.append(
                    f"<ellipse class='grid-circle grid-mode-{circle.mode}'{style} "
                    f"cx='{circle.cx:.4f}' cy='{circle.cy:.4f}' rx='{circle.rx:.4f}' ry='{circle.ry:.4f}' />"
                )
            label_x, label_y = circle.cx, circle.cy
        else:
            start_x = circle.cx + circle.rx * math.cos(math.radians(circle.start_angle))
            start_y = circle.cy - circle.ry * math.sin(math.radians(circle.start_angle))
            end_x = circle.cx + circle.rx * math.cos(math.radians(circle.end_angle))
            end_y = circle.cy - circle.ry * math.sin(math.radians(circle.end_angle))
            large_arc_flag = 1 if (circle.end_angle - circle.start_angle) % 360.0 > 180.0 else 0
            shapes.append(
                f"<path class='grid-arc grid-mode-{circle.mode}'{style} "
                f"d='M {start_x:.4f} {start_y:.4f} A {circle.rx:.4f} {circle.ry:.4f} 0 {large_arc_flag} 0 "
                f"{end_x:.4f} {end_y:.4f}' />"
            )
            label_x, label_y = circle.cx, circle.cy

        if circle.label:
            labels.append(
                f"<text class='grid-circle-label grid-mode-{circle.mode}'{_svg_fill_style_attr(circle.color)} "
                f"x='{label_x:.4f}' y='{label_y:.4f}'>{escape(circle.label)}</text>"
            )
    return shapes, labels
