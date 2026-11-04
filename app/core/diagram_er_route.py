"""Kantenführung der ER-Diagramme: rechtwinklig von der Entität zu einer Rautenecke (GO S. 8).

Die Suche in `diagram_er_layout` bewertet genau diese Wege, und `diagram_er` zeichnet
sie. So sieht die Bewertung dasselbe wie das Blatt; vorher bewertete die Suche gerade
Mittelpunktstrecken, und gezeichnete Kanten liefen unbemerkt durch Rauten.
"""

from __future__ import annotations

import math

from .diagram_route import Box, diamond_corner

_INSET = 10.0
"""Abstand eines L-Ansatzes in Fächern von der Entitätsecke, je Verschachtelung mehr."""
APPROACH = 12.0
"""Senkrechtes Endstück eines Z-Wegs vor der Rautenspitze; das Layout hält es frei."""


def _corner_for(size, center, entity, other, taken) -> tuple[tuple[float, float], str]:
    """Rautenecke der Kante zu `entity` und die Wegform dorthin.

    Returns:
        `(ecke, form)`; `form` ist `horizontal` (Ankunft von der Seite), `vertical` (von
        oben oder unten) oder `z`: Die Raute sitzt schräg zwischen ihren Entitäten, beide
        Kanten kommen von oben bzw. unten (`_z_route`).
    """
    (rx, ry), (width, height) = center, size
    between_x = (entity[0] - rx) * (other[0] - rx) < 0 and abs(entity[0] - rx) > width / 2
    between_y = (entity[1] - ry) * (other[1] - ry) < 0 and abs(entity[1] - ry) > height / 2
    if between_x and between_y:
        return (rx, ry + math.copysign(height / 2, entity[1] - ry)), "z"
    if between_x:
        return (rx + math.copysign(width / 2, entity[0] - rx), ry), "horizontal"
    if between_y:
        return (rx, ry + math.copysign(height / 2, entity[1] - ry)), "vertical"
    corner = diamond_corner(rx, ry, width / 2, height / 2, entity, taken)
    return corner, "horizontal" if corner[1] == ry else "vertical"


def _z_route(box: Box, corner, inset: float | None) -> list[tuple[float, float]]:
    """Weg zur oberen bzw. unteren Ecke einer Raute, die schräg zwischen zwei Entitäten sitzt.

    Aus der Unter- bzw. Oberseite nahe der zugewandten Ecke kurz senkrecht, dann waagerecht
    bis über die Rautenspitze und hinein. Die Raute teilt sich ihren Zwischenraum meist mit
    den Rauten senkrechter Beziehungen (2x2-Raster: Person, Kind, Adresse, Gruppe); auf
    Höhe ihrer Mitte liefe ein L an deren Ecken vorbei, so läuft der Weg über bzw. unter ihnen.
    """
    cx, cy = corner
    downward = cy > box.cy
    step = min(box.width / 4 if inset is None else inset, box.width / 2)
    x = box.right - step if cx > box.cx else box.left + step
    level = cy - APPROACH if downward else cy + APPROACH
    return [(x, box.bottom if downward else box.top), (x, level), (cx, level), corner]


def _orthogonal(box: Box, corner, horizontal: bool, inset: float | None) -> list[tuple[float, float]]:
    """Rechtwinkliger Weg vom Rand der Entität zur Rautenecke.

    Gerade, wenn die Ecke irgendwo neben der Entität liegt (waagerechte Ankunft) bzw.
    über oder unter ihr, auch knapp an deren Ecke: Ein L mit Stummel wäre schlimmer. Sonst
    ein L aus der Ober- oder Unterseite bzw. aus der Seite, `inset` von der zugewandten
    Ecke der Entität entfernt; ohne `inset` ein Viertel der Seite. Nie aus der Mitte: Dort
    setzt oft schon eine gerade Kante an, und die beiden Linien lägen aufeinander.
    """
    cx, cy = corner
    if horizontal:
        if box.top < cy < box.bottom:
            return [(box.right if cx > box.cx else box.left, cy), corner]
        step = min(box.width / 4 if inset is None else inset, box.width / 2)
        x = box.right - step if cx > box.cx else box.left + step
        return [(x, box.bottom if cy > box.cy else box.top), (x, cy), corner]
    if box.left < cx < box.right:
        return [(cx, box.bottom if cy > box.cy else box.top), corner]
    step = min(box.height / 4 if inset is None else inset, box.height / 2)
    y = box.bottom - step if cy > box.cy else box.top + step
    return [(box.right if cx > box.cx else box.left, y), (cx, y), corner]


def route_edges(sizes, centers, groups) -> dict[tuple[str, str], list[tuple[float, float]]]:
    """Rechtwinklige Wege aller nicht rekursiven Kanten je `(entität, raute)`.

    Rauten eines Fächers, die nicht auf Höhe der Entität liegen, erreicht ein L aus Ober-
    oder Unterseite; äußere Rauten setzen weiter innen an, so umschließen ihre L die
    inneren, ohne sie zu kreuzen.

    Args:
        sizes: Formgröße je Entität und Raute.
        centers: Mittelpunkte.
        groups: `relation_groups`.
    """
    routes = {}
    for first, second, relations in groups:
        middle = (len(relations) - 1) / 2
        for index, relation in enumerate(relations):
            inset = _INSET * max(1, math.ceil(abs(index - middle))) if len(relations) > 1 else None
            taken: list[tuple[float, float]] = []
            for entity, other in ((first, second), (second, first)):
                corner, form = _corner_for(sizes[relation], centers[relation], centers[entity], centers[other], taken)
                taken.append(corner)
                box = Box(*centers[entity], *sizes[entity])
                routes[(entity, relation)] = _z_route(box, corner, inset) if form == "z" else _orthogonal(box, corner, form == "horizontal", inset)
    return routes
