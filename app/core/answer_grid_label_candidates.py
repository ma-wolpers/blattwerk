"""Kandidatenpositionen und lexikographisches Kostentupel des Label-Layouts.

Kostentupel (kleiner = besser, Vergleich lexikographisch, unabhängig von
Gewichten):

1. Überdeckung von Punktkreuzen (`TIER_POINT`)
2. Überdeckung anderer beweglicher Labels (`TIER_LABEL`)
3. Überdeckung von Linien, Kurven, Kanten, Pfeilspitzen (`TIER_LINE`)
4. Überdeckung von Achsen, Ticks und festen Tick-Zahlen (`TIER_AXIS`)
5. „nicht Standardposition“ (0/1)
6. Abstand zur Standardposition
7. Kandidatenindex (deterministischer Gleichstandsbrecher)

Damit gilt: Eine kollisionsfreie Standardposition gewinnt immer; bei exakt
gleicher Bewertung gewinnt die Standardposition, danach der kleinere Index.

Harte Nebenbedingungen (`is_admissible`): Die Label-Box liegt vollständig in
der Zone (Zeichenfläche plus bestehender Bleed-Rand); ein Achsenname liegt mit
seiner Box höchstens `AXIS_NAME_MAX_GAP` von seiner Pfeilspitze entfernt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .answer_grid_label_geometry import (
    boxes_intersection_area,
    box_inside,
    distance_point_to_box,
    obstacle_overlap,
    point_in_polygon,
    segment_length_inside,
)
from .answer_grid_label_model import (
    TIER_AXIS,
    TIER_COUNT,
    TIER_LABEL,
    text_box,
    text_position_for_box_center,
)

DIRECTIONS = ((1, -1), (1, 0), (1, 1), (0, -1), (0, 1), (-1, -1), (-1, 0), (-1, 1))
"""Richtungsfolge in SVG-Koordinaten (y nach unten): NO, O, SO, N, S, NW, W, SW."""
GAP_STEPS = (0.0, 0.25, 0.55)
POINT_BASE_GAP = 0.24
DEFAULT_BASE_GAP = 0.12
AREA_OFFSETS = (0.0, 0.35, -0.35, 0.7, -0.7, 1.05, -1.05)
AXIS_NAME_MAX_GAP = 0.6
EXTENDED_RADII = tuple(round(0.9 + 0.2 * step, 2) for step in range(9))
EXTENDED_DIRECTION_COUNT = 16
ROUND_DIGITS = 6


@dataclass(frozen=True)
class LayoutContext:
    """Feste Umgebung eines Layoutlaufs: Hindernisse, feste Label-Boxen (Tick-Zahlen), Zone."""

    obstacles: tuple
    fixed_boxes: tuple
    zone: tuple[float, float, float, float]


def _box_size(spec) -> tuple[float, float]:
    x0, y0, x1, y1 = text_box(spec, 0.0, 0.0)
    return x1 - x0, y1 - y0


def _around(spec, anchor, base_gap: float, gaps, directions) -> list[tuple[float, float]]:
    """Textpositionen, deren Box in Richtung `direction` mit Abstand `gap` neben `anchor` liegt."""
    width, height = _box_size(spec)
    positions = []
    for gap in gaps:
        for dx, dy in directions:
            cx = anchor[0] + dx * (width / 2.0 + base_gap + gap)
            cy = anchor[1] + dy * (height / 2.0 + base_gap + gap)
            positions.append(text_position_for_box_center(spec, cx, cy))
    return positions


def candidate_positions(spec) -> list[tuple[float, float]]:
    """Kandidaten in fester Reihenfolge; Index 0 ist immer die Standardposition.

    Flächenlabels (Polygon, Kreis): Raster von Versätzen um den Schwerpunkt,
    nur Positionen mit Box-Mittelpunkt im Inneren der Fläche. Alle anderen:
    acht Richtungen um den Anker in drei Abständen.
    """
    default = (spec.x, spec.y)
    if spec.kind == "area" and spec.area:
        offsets = sorted(
            ((dx, dy) for dy in AREA_OFFSETS for dx in AREA_OFFSETS),
            key=lambda offset: (round(math.hypot(*offset), ROUND_DIGITS), AREA_OFFSETS.index(offset[1]), AREA_OFFSETS.index(offset[0])),
        )
        inner = []
        for dx, dy in offsets:
            position = (spec.x + dx, spec.y + dy)
            box = text_box(spec, *position)
            if point_in_polygon((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0, spec.area):
                inner.append(position)
        return [default] + inner
    base_gap = POINT_BASE_GAP if spec.kind == "point" else DEFAULT_BASE_GAP
    return [default] + _around(spec, spec.anchor, base_gap, GAP_STEPS, DIRECTIONS)


def extended_positions(spec) -> list[tuple[float, float]]:
    """Fallback-Ringsuche: 16 Richtungen in wachsenden Abständen bis zum Maximalradius."""
    width, height = _box_size(spec)
    positions = []
    for radius in EXTENDED_RADII:
        for step in range(EXTENDED_DIRECTION_COUNT):
            angle = 2.0 * math.pi * step / EXTENDED_DIRECTION_COUNT
            cx = spec.anchor[0] + math.cos(angle) * (width / 2.0 + radius)
            cy = spec.anchor[1] - math.sin(angle) * (height / 2.0 + radius)
            positions.append(text_position_for_box_center(spec, cx, cy))
    return positions


def is_admissible(spec, position, zone) -> bool:
    """Harte Nebenbedingungen: Box in der Zone; Achsennamen nahe ihrer Pfeilspitze."""
    box = text_box(spec, *position)
    if not box_inside(box, zone):
        return False
    if spec.kind == "axis_name":
        return distance_point_to_box(spec.anchor[0], spec.anchor[1], box) <= AXIS_NAME_MAX_GAP
    return True


def _overlap_for(spec, box, obstacle) -> float:
    """Überdeckung; Hindernisse des eigenen Objekts zählen ohne Aufblähung (echte Geometrie)."""
    if obstacle.owner is not None and obstacle.owner == spec.owner:
        if obstacle.shape == "segment":
            return segment_length_inside(box, *obstacle.coords)
        if obstacle.shape == "rect":
            return boxes_intersection_area(box, obstacle.coords)
    return obstacle_overlap(box, obstacle)


def cost(spec, position, context: LayoutContext, other_boxes, index: int) -> tuple:
    """Lexikographisches Kostentupel einer Kandidatenposition (siehe Moduldocstring)."""
    box = text_box(spec, *position)
    tiers = [0.0] * TIER_COUNT
    for obstacle in context.obstacles:
        tiers[obstacle.tier] += _overlap_for(spec, box, obstacle)
    for fixed in context.fixed_boxes:
        tiers[TIER_AXIS] += boxes_intersection_area(box, fixed)
    for other in other_boxes:
        tiers[TIER_LABEL] += boxes_intersection_area(box, other)
    is_default = position[0] == spec.x and position[1] == spec.y
    distance = math.hypot(position[0] - spec.x, position[1] - spec.y)
    return tuple(round(value, ROUND_DIGITS) for value in tiers) + (
        0 if is_default else 1,
        round(distance, ROUND_DIGITS),
        index,
    )


def has_hard_collision(cost_tuple) -> bool:
    """Ob ein Punktkreuz oder ein anderes Label überdeckt wird (Stufen 1/2)."""
    return cost_tuple[0] > 0 or cost_tuple[1] > 0


def has_collision(cost_tuple) -> bool:
    """Ob eine Kollision der Stufen 1–3 besteht (Anlass für die Relaxation)."""
    return cost_tuple[0] > 0 or cost_tuple[1] > 0 or cost_tuple[2] > 0


def best_candidate(spec, positions, context: LayoutContext, other_boxes, start_index: int = 0):
    """Bester zulässiger Kandidat als `(position, cost)`; ``None``, wenn keiner zulässig ist."""
    best = None
    for offset, position in enumerate(positions):
        if not is_admissible(spec, position, context.zone):
            continue
        candidate_cost = cost(spec, position, context, other_boxes, start_index + offset)
        if best is None or candidate_cost < best[1]:
            best = (position, candidate_cost)
    return best
