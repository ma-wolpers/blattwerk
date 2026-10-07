"""Parsing und Rendering der Geometry-DSL-Objekte `polygons` (Kreise: `answer_grid_circles.py`).

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

from dataclasses import dataclass

from .answer_grid_entries import _as_float, _is_visible, _normalize_show_mode
from .answer_grid_label_model import TIER_LINE, LabelSpec, polyline_obstacles, stroke_pad
from .answer_grid_svg_style import _svg_fill_style_attr, _svg_shape_style_attr
from .answer_grid_validity import _polygon_vertices_are_valid
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
    """Section-Renderer für `polygons`: liefert `(shapes, label_specs, obstacles)` (siehe Z-Order-Regel).

    Immer als geschlossene Fläche gerendert (SVG `<polygon>` verbindet
    automatisch den letzten mit dem ersten Punkt) -- selbstüberschneidende
    Konturen werden dabei ohne weitere Prüfung genau so gezeichnet, wie
    angegeben (keine komplexe Geometrieprüfung, bewusste Produktentscheidung).
    Das Label ist ein Flächenlabel (Standard: Schwerpunkt); die Kanten sind
    Linien-Hindernisse.
    """
    entries = _parse_polygons(raw_entries, coord_system, include_solutions)
    shapes, labels, obstacles = [], [], []
    for polygon in entries:
        points_attr = " ".join(f"{vx:.4f},{vy:.4f}" for vx, vy in polygon.vertices)
        style = _svg_shape_style_attr(polygon.color, polygon.thickness, polygon.fill)
        shapes.append(
            f"<polygon class='grid-polygon grid-mode-{polygon.mode}'{style} points='{points_attr}' />"
        )
        obstacles.extend(polyline_obstacles(polygon.vertices, TIER_LINE, stroke_pad(polygon.thickness or 1.1), closed=True))
        if polygon.label:
            label_x, label_y = _polygon_centroid(polygon.vertices)
            labels.append(LabelSpec(
                text=polygon.label, css_class=f"grid-polygon-label grid-mode-{polygon.mode}", x=label_x, y=label_y,
                kind="area", anchor=(label_x, label_y), style_attr=_svg_fill_style_attr(polygon.color),
                area=polygon.vertices,
            ))
    return shapes, labels, obstacles
