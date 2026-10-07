"""Parsing und Rendering der Geometry-DSL-Objekte `circles` (Vollkreis, Ellipse, Bogen).

Ausgelagert aus `answer_grid_shapes.py` (300-Zeilen-Konvention), als dort für
das Label-Layout die Konturabtastung (`_circle_outline`) hinzukam. Nutzt
dieselben Bausteine wie die übrigen `_parse_*`-Funktionen (`_as_float`,
`_normalize_show_mode`, `_is_visible`, `_GeometryCoordinateSystem` aus
`answer_grid_entries.py`; `parse_svg_color`/`parse_svg_thickness` aus
`answer_special_shared.py`; die neutralen Validitätsprädikate aus
`answer_grid_validity.py`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .answer_grid_entries import _as_float, _is_visible, _normalize_show_mode
from .answer_grid_label_model import TIER_LINE, LabelSpec, polyline_obstacles, stroke_pad
from .answer_grid_svg_style import _svg_fill_style_attr, _svg_shape_style_attr
from .answer_grid_validity import (
    _circle_angle_fields_are_valid,
    _circle_center_and_radius_are_valid,
    _circle_is_full,
)
from .answer_special_shared import parse_svg_color, parse_svg_thickness


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
    """Section-Renderer für `circles`: liefert `(shapes, label_specs, obstacles)` (siehe Z-Order-Regel).

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

    Kontur bzw. Bogen werden für das Label-Layout polygonal abgetastet
    (`_circle_outline`); das Label ist ein Flächenlabel mit Standardposition
    im Mittelpunkt.
    """
    entries = _parse_circles(raw_entries, coord_system, include_solutions)
    shapes, labels, obstacles = [], [], []
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

        outline = _circle_outline(circle)
        is_full = circle.start_angle is None or circle.end_angle is None
        obstacles.extend(polyline_obstacles(outline, TIER_LINE, stroke_pad(circle.thickness or 1.1), closed=is_full))
        if circle.label:
            labels.append(LabelSpec(
                text=circle.label, css_class=f"grid-circle-label grid-mode-{circle.mode}", x=label_x, y=label_y,
                kind="area", anchor=(label_x, label_y), style_attr=_svg_fill_style_attr(circle.color),
                area=outline if is_full else _circle_outline(replace(circle, start_angle=None, end_angle=None)),
            ))
    return shapes, labels, obstacles


_OUTLINE_STEPS = 72


def _circle_outline(circle):
    """Polygonale Abtastung von Kreis/Ellipse bzw. Bogen (aufsteigende Winkel, wie gezeichnet)."""
    if circle.start_angle is None or circle.end_angle is None:
        start, span = 0.0, 360.0
    else:
        start = circle.start_angle
        span = (circle.end_angle - circle.start_angle) % 360.0 or 360.0
    steps = max(4, int(math.ceil(_OUTLINE_STEPS * span / 360.0)))
    if span >= 360.0:
        steps = _OUTLINE_STEPS
    count = steps if span >= 360.0 else steps + 1
    return tuple(
        (
            circle.cx + circle.rx * math.cos(math.radians(start + span * index / steps)),
            circle.cy - circle.ry * math.sin(math.radians(start + span * index / steps)),
        )
        for index in range(count)
    )
