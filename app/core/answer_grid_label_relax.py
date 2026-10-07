"""Kräfte-Relaxation des Label-Layouts (kleines Kräftesystem mit monotoner Annahme).

Läuft nur für Labels, die nach der Kandidatenwahl noch eine Kollision der
Stufen 1–3 haben (Punktkreuz, anderes Label, Linie). Je Schritt wirken auf ein
solches Label:

* Abstoßung von überlappenden anderen Labels (entlang der Mittelpunktsdifferenz),
* Abstoßung von überdeckten Hindernissen (weg vom nächsten Hindernispunkt),
* eine Feder zurück zur gewählten Kandidatenposition.

Die Summe wird gedämpft und in der Länge begrenzt. Ein Schritt wird **nur**
angenommen, wenn er das Kostentupel des Labels verbessert, kein anderes Label
stärker überdeckt (Stufe 2 aller anderen bleibt gleich oder sinkt) und die
harten Nebenbedingungen erfüllt -- das Ergebnis ist dadurch nie schlechter als
die Kandidatenwahl. Feste Iterationszahl, feste Reihenfolge, keine
Zufallswerte: deterministisch.
"""

from __future__ import annotations

import math

from .answer_grid_label_candidates import cost, has_collision, is_admissible
from .answer_grid_label_geometry import (
    box_center,
    boxes_intersection_area,
    nearest_point_on_obstacle,
    obstacle_overlap,
)
from .answer_grid_label_model import TIER_AXIS, text_box

ITERATIONS = 40
DAMPING = 0.5
SPRING = 0.15
MAX_STEP = 0.25
_EPSILON = 1e-9


def _unit(dx: float, dy: float, fallback=(1.0, -1.0)) -> tuple[float, float]:
    length = math.hypot(dx, dy)
    if length < _EPSILON:
        fx, fy = fallback
        norm = math.hypot(fx, fy)
        return fx / norm, fy / norm
    return dx / length, dy / length


def _force(spec, position, home, context, other_boxes) -> tuple[float, float]:
    """Resultierende Kraft auf ein Label an `position` (Feder zu `home`)."""
    box = text_box(spec, *position)
    cx, cy = box_center(box)
    fx = SPRING * (home[0] - position[0])
    fy = SPRING * (home[1] - position[1])
    for other in other_boxes:
        overlap = boxes_intersection_area(box, other)
        if overlap > 0:
            ox, oy = box_center(other)
            ux, uy = _unit(cx - ox, cy - oy)
            push = math.sqrt(overlap)
            fx, fy = fx + ux * push, fy + uy * push
    for obstacle in context.obstacles:
        if obstacle.tier >= TIER_AXIS:
            continue
        overlap = obstacle_overlap(box, obstacle)
        if overlap > 0:
            nx, ny = nearest_point_on_obstacle(obstacle, cx, cy)
            ux, uy = _unit(cx - nx, cy - ny, fallback=(spec.x - spec.anchor[0], spec.y - spec.anchor[1]))
            fx, fy = fx + ux * overlap, fy + uy * overlap
    return fx, fy


def _overlap_with_members(boxes, label_index, members) -> float:
    """Stufe-2-Überdeckung eines Labels mit allen anderen beweglichen Labels."""
    return sum(boxes_intersection_area(boxes[label_index], boxes[other]) for other in members if other != label_index)


def relax(specs, positions, homes, context, members, active) -> list[tuple[float, float]]:
    """Verbessert kollidierende Labels schrittweise; liefert neue Positionen (gleiche Reihenfolge).

    Args:
        specs/positions: alle Labels der Szene und ihre aktuellen Positionen.
        homes: Kandidatenpositionen (Federanker) je Label.
        context: Hindernisse, feste Boxen, Zone (`LayoutContext`).
        members: Indizes aller beweglichen Labels (zählen gegenseitig als Stufe 2).
        active: Indizes der Labels, die bewegt werden dürfen (die kollidierenden).
    """
    positions = list(positions)
    for _iteration in range(ITERATIONS):
        moved = False
        for index in active:
            spec = specs[index]
            boxes = {i: text_box(specs[i], *positions[i]) for i in members}
            others = [boxes[i] for i in members if i != index]
            current = cost(spec, positions[index], context, others, 0)
            if not has_collision(current):
                continue
            fx, fy = _force(spec, positions[index], homes[index], context, others)
            fx, fy = fx * DAMPING, fy * DAMPING
            length = math.hypot(fx, fy)
            if length < _EPSILON:
                continue
            if length > MAX_STEP:
                fx, fy = fx / length * MAX_STEP, fy / length * MAX_STEP
            proposal = (positions[index][0] + fx, positions[index][1] + fy)
            if not is_admissible(spec, proposal, context.zone):
                continue
            if cost(spec, proposal, context, others, 0)[:4] >= current[:4]:
                continue
            trial = dict(boxes)
            trial[index] = text_box(spec, *proposal)
            if any(
                _overlap_with_members(trial, other, members) > _overlap_with_members(boxes, other, members) + _EPSILON
                for other in members
                if other != index
            ):
                continue
            positions[index] = proposal
            moved = True
        if not moved:
            break
    return positions
