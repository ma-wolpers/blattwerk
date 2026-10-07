"""Geometrische Grundoperationen des Label-Layouts (reine Funktionen, keine Gewichte).

Alle Maße sind in Rastereinheiten. Eine Label-Box ist ein achsenparalleles
Rechteck `(x0, y0, x1, y1)`. Die Überdeckungsmaße sind stetig (größer = mehr
überdeckt, 0 = frei), damit das Layout Kandidaten vergleichen und die
Relaxation Verbesserungen erkennen kann:

* Scheibe (Punktkreuz): Eindringtiefe der aufgeblähten Scheibe in die Box.
* Segment (Linie, Kurvenstück, Kante): Länge des Segmentstücks innerhalb der
  um die Aufblähung vergrößerten Box (Liang-Barsky-Clipping).
* Rechteck (Pfeilspitze, feste Tick-Zahl, anderes Label): Schnittfläche.
"""

from __future__ import annotations

import math


def boxes_intersection_area(a, b) -> float:
    """Schnittfläche zweier Rechtecke (0, wenn sie sich nicht schneiden)."""
    width = min(a[2], b[2]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[1], b[1])
    return width * height if width > 0 and height > 0 else 0.0


def boxes_touch(a, b) -> bool:
    """Ob sich zwei Rechtecke berühren oder überlappen (Vorfilter)."""
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def inflate(box, pad: float):
    """Rechteck um `pad` nach allen Seiten vergrößert."""
    return (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)


def disc_overlap(box, cx: float, cy: float, radius: float) -> float:
    """Eindringtiefe einer Scheibe in die Box; liegt der Mittelpunkt innen, zählt zusätzlich seine Tiefe."""
    nearest_x = min(max(cx, box[0]), box[2])
    nearest_y = min(max(cy, box[1]), box[3])
    distance = math.hypot(cx - nearest_x, cy - nearest_y)
    if distance > 0:
        return max(0.0, radius - distance)
    depth = min(cx - box[0], box[2] - cx, cy - box[1], box[3] - cy)
    return radius + max(0.0, depth)


def segment_length_inside(box, x1: float, y1: float, x2: float, y2: float) -> float:
    """Länge des Segments innerhalb der Box (Liang-Barsky); 0, wenn es die Box verfehlt."""
    dx, dy = x2 - x1, y2 - y1
    t_min, t_max = 0.0, 1.0
    for p, q in ((-dx, x1 - box[0]), (dx, box[2] - x1), (-dy, y1 - box[1]), (dy, box[3] - y1)):
        if p == 0:
            if q < 0:
                return 0.0
            continue
        t = q / p
        if p < 0:
            t_min = max(t_min, t)
        else:
            t_max = min(t_max, t)
        if t_min > t_max:
            return 0.0
    length = math.hypot(dx, dy) * (t_max - t_min)
    if length > 0:
        return length
    # Punktförmiges Segment innerhalb der Box: als minimale Überdeckung werten.
    return 1e-3 if box[0] <= x1 <= box[2] and box[1] <= y1 <= box[3] else 0.0


def obstacle_overlap(box, obstacle) -> float:
    """Überdeckungsmaß zwischen Label-Box und Hindernis (siehe Moduldocstring)."""
    if not boxes_touch(box, obstacle.bbox):
        return 0.0
    if obstacle.shape == "disc":
        cx, cy, radius = obstacle.coords
        return disc_overlap(box, cx, cy, radius + obstacle.pad)
    if obstacle.shape == "segment":
        return segment_length_inside(inflate(box, obstacle.pad), *obstacle.coords)
    return boxes_intersection_area(box, obstacle.bbox)


def nearest_point_on_obstacle(obstacle, px: float, py: float) -> tuple[float, float]:
    """Nächster Punkt des Hindernisses zu `(px, py)` (für die Abstoßungsrichtung der Relaxation)."""
    if obstacle.shape == "disc":
        return obstacle.coords[0], obstacle.coords[1]
    if obstacle.shape == "segment":
        x1, y1, x2, y2 = obstacle.coords
        dx, dy = x2 - x1, y2 - y1
        length_sq = dx * dx + dy * dy
        t = 0.0 if length_sq == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
        return x1 + t * dx, y1 + t * dy
    x0, y0, x1, y1 = obstacle.bbox
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0


def point_in_polygon(px: float, py: float, vertices) -> bool:
    """Even-odd-Test, ob `(px, py)` im (ggf. nicht konvexen) Polygon liegt."""
    inside = False
    count = len(vertices)
    for index in range(count):
        x1, y1 = vertices[index]
        x2, y2 = vertices[(index + 1) % count]
        if (y1 > py) != (y2 > py):
            x_cross = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if px < x_cross:
                inside = not inside
    return inside


def box_center(box) -> tuple[float, float]:
    """Mittelpunkt eines Rechtecks."""
    return (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0


def box_inside(box, zone) -> bool:
    """Ob das Rechteck vollständig in der Zone `(x0, y0, x1, y1)` liegt."""
    return box[0] >= zone[0] and box[1] >= zone[1] and box[2] <= zone[2] and box[3] <= zone[3]


def distance_point_to_box(px: float, py: float, box) -> float:
    """Abstand eines Punkts zur Box (0, wenn er darin liegt)."""
    nearest_x = min(max(px, box[0]), box[2])
    nearest_y = min(max(py, box[1]), box[3])
    return math.hypot(px - nearest_x, py - nearest_y)
