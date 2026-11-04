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


def diamond_corner(cx, cy, half_width, half_height, toward, taken=()) -> tuple[float, float]:
    """Ecke der Raute, die am meisten in Richtung `toward` zeigt (ER-Kanten enden an Ecken).

    Verglichen wird in Rautenmaßen; so läuft die Linie von der gewählten Ecke nach
    `toward` nie durch die Raute. `taken` sind schon belegte Ecken, sie kommen nur infrage,
    wenn alle belegt sind.
    """
    dx, dy = (toward[0] - cx) / half_width, (toward[1] - cy) / half_height
    corners = [((cx + half_width, cy), dx), ((cx - half_width, cy), -dx), ((cx, cy + half_height), dy), ((cx, cy - half_height), -dy)]
    free = [entry for entry in corners if entry[0] not in taken] or corners
    return max(free, key=lambda entry: entry[1])[0]


def rects_overlap(first, second, pad: float = 0.0) -> bool:
    """Prüft, ob sich zwei Rechtecke `(mitte_x, mitte_y, breite, höhe)` überlappen.

    `pad` verlangt zusätzlich so viel Luft dazwischen.
    """
    return abs(first[0] - second[0]) < (first[2] + second[2]) / 2 + pad and abs(first[1] - second[1]) < (first[3] + second[3]) / 2 + pad


def segments_cross(first, second) -> bool:
    """Prüft, ob sich zwei Strecken echt kreuzen; gemeinsame Endpunkte und Berührungen zählen nicht."""
    (ax, ay), (bx, by) = first
    (cx, cy), (dx, dy) = second

    def side(px, py, qx, qy, rx, ry) -> float:
        return (qx - px) * (ry - py) - (qy - py) * (rx - px)

    return side(cx, cy, dx, dy, ax, ay) * side(cx, cy, dx, dy, bx, by) < 0 and side(ax, ay, bx, by, cx, cy) * side(ax, ay, bx, by, dx, dy) < 0


def segments_overlap(first, second, tolerance: float = 1.0) -> bool:
    """Prüft, ob zwei waagerechte oder zwei senkrechte Strecken ein Stück weit aufeinanderliegen.

    Solche Linien sähen aus wie eine; `segments_cross` erkennt sie nicht.
    """
    for along, across in ((0, 1), (1, 0)):
        if abs(first[0][across] - first[1][across]) < tolerance and abs(second[0][across] - second[1][across]) < tolerance and abs(first[0][across] - second[0][across]) < tolerance:
            low = max(min(first[0][along], first[1][along]), min(second[0][along], second[1][along]))
            high = min(max(first[0][along], first[1][along]), max(second[0][along], second[1][along]))
            if high - low > tolerance:
                return True
    return False


def segment_hits_rect(segment, rect, pad: float = 0.0) -> bool:
    """Prüft, ob die Strecke das Rechteck `(mitte_x, mitte_y, breite, höhe)` berührt (Liang-Barsky).

    `pad` vergrößert das Rechteck ringsum, damit Linien nicht knapp an Formen vorbeischrammen.
    """
    (x1, y1), (x2, y2) = segment
    cx, cy, width, height = rect
    dx, dy = x2 - x1, y2 - y1
    low, high = 0.0, 1.0
    for step, room in ((-dx, x1 - cx + width / 2 + pad), (dx, cx + width / 2 + pad - x1), (-dy, y1 - cy + height / 2 + pad), (dy, cy + height / 2 + pad - y1)):
        if not step:
            if room < 0:
                return False
            continue
        share = room / step
        if step < 0:
            low = max(low, share)
        else:
            high = min(high, share)
        if low > high:
            return False
    return True


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


def edge_label_center(start, end, middle, width: float, height: float) -> tuple[float, float]:
    """Mittelpunkt einer Beschriftung neben einer Kante, oberhalb oder rechts davon.

    Args:
        start: Anfang der Kante.
        end: Ende der Kante.
        middle: Punkt auf der Kante, an dem die Beschriftung sitzt.
        width: Breite der Beschriftung.
        height: Höhe der Beschriftung.
    """
    length = math.hypot(end[0] - start[0], end[1] - start[1]) or 1.0
    normal_x, normal_y = -(end[1] - start[1]) / length, (end[0] - start[0]) / length
    if normal_y > 0 or (not normal_y and normal_x < 0):
        normal_x, normal_y = -normal_x, -normal_y
    return middle[0] + normal_x * (width / 2 + 3), middle[1] + normal_y * (height / 2 + 3)
