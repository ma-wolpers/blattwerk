"""Kantenführung der Diagramme: Austrittspunkte am Knoten, rechtwinklige Linien, Bögen."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    """Rechteck um einen Mittelpunkt."""

    cx: float
    cy: float
    width: float
    height: float

    @property
    def left(self) -> float:
        """Linke Kante."""
        return self.cx - self.width / 2

    @property
    def right(self) -> float:
        """Rechte Kante."""
        return self.cx + self.width / 2

    @property
    def top(self) -> float:
        """Obere Kante."""
        return self.cy - self.height / 2

    @property
    def bottom(self) -> float:
        """Untere Kante."""
        return self.cy + self.height / 2


def box_exit(box: Box, toward) -> tuple[float, float]:
    """Schnittpunkt der Rechteckkante mit der Linie vom Mittelpunkt nach `toward`."""
    dx, dy = toward[0] - box.cx, toward[1] - box.cy
    if not dx and not dy:
        return box.cx, box.cy
    scale = min(box.width / 2 / abs(dx) if dx else math.inf, box.height / 2 / abs(dy) if dy else math.inf)
    return box.cx + dx * scale, box.cy + dy * scale


def ellipse_exit(cx, cy, rx, ry, toward) -> tuple[float, float]:
    """Schnittpunkt des Ellipsenrands mit der Linie vom Mittelpunkt nach `toward`."""
    dx, dy = toward[0] - cx, toward[1] - cy
    if not dx and not dy:
        return cx, cy
    scale = 1.0 / math.hypot(dx / rx, dy / ry)
    return cx + dx * scale, cy + dy * scale


def diamond_exit(cx, cy, half_width, half_height, toward) -> tuple[float, float]:
    """Schnittpunkt des Rautenrands mit der Linie vom Mittelpunkt nach `toward`."""
    dx, dy = toward[0] - cx, toward[1] - cy
    if not dx and not dy:
        return cx, cy
    scale = 1.0 / (abs(dx) / half_width + abs(dy) / half_height)
    return cx + dx * scale, cy + dy * scale


def orthogonal_route(start: Box, end: Box) -> list[tuple[float, float]]:
    """Rechtwinklige Linie von `start` nach `end` (GO-Klassendiagramm).

    Überlappen sich die Boxen in einer Achse, reicht eine gerade Linie durch die Mitte
    des gemeinsamen Bereichs; sonst ein Z aus drei Strecken.
    """
    overlap_left, overlap_right = max(start.left, end.left), min(start.right, end.right)
    if overlap_left < overlap_right:
        x = (overlap_left + overlap_right) / 2
        return [(x, start.bottom), (x, end.top)] if start.cy < end.cy else [(x, start.top), (x, end.bottom)]
    overlap_top, overlap_bottom = max(start.top, end.top), min(start.bottom, end.bottom)
    if overlap_top < overlap_bottom:
        y = (overlap_top + overlap_bottom) / 2
        return [(start.right, y), (end.left, y)] if start.cx < end.cx else [(start.left, y), (end.right, y)]
    first = (start.cx, start.bottom if start.cy < end.cy else start.top)
    last = (end.cx, end.top if start.cy < end.cy else end.bottom)
    middle = (first[1] + last[1]) / 2
    return [first, (first[0], middle), (last[0], middle), last]


def box_self_loop(box: Box, reach: float = 26.0) -> list[tuple[float, float]]:
    """Selbstkante links am Rechteck (GO: zwei waagerechte Stücke und ein senkrechtes)."""
    upper = box.cy - box.height / 5
    lower = box.cy + box.height / 5
    outside = box.left - reach
    return [(box.left, upper), (outside, upper), (outside, lower), (box.left, lower)]


def curve_points(start, end, bend: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Kontroll- und Scheitelpunkt eines quadratischen Bogens von `start` nach `end`.

    Args:
        start: Anfang.
        end: Ende.
        bend: Ausbuchtung senkrecht zur Linie; das Vorzeichen wählt die Seite.

    Returns:
        `(kontrollpunkt, scheitelpunkt)`; der Scheitel trägt die Beschriftung.
    """
    mid_x, mid_y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy) or 1.0
    normal_x, normal_y = -dy / length, dx / length
    control = (mid_x + normal_x * bend * 2, mid_y + normal_y * bend * 2)
    apex = (mid_x + normal_x * bend, mid_y + normal_y * bend)
    return control, apex
