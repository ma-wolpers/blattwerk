"""Layouts ohne Ebenen-Vorgabe: Baum, Kreis und freie Anordnung (Federmodell).

Wie `diagram_layout` rein und deterministisch: Die freie Anordnung startet auf einem
Kreis in Schreibreihenfolge und rechnet eine feste Zahl von Schritten.
"""

from __future__ import annotations

import math

from .diagram_layout import Layout

_FORCE_STEPS = 240
_SEPARATION_STEPS = 60
PLACEHOLDER = "_"
"""Leeres Kind im Binärbaum: hält den Platz, wird aber nicht gezeichnet."""


def _bounded(positions, sizes, margin: float) -> Layout:
    """Verschiebt `positions` an den Rand und bestimmt die Gesamtgröße."""
    left = min(x - sizes[node][0] / 2 for node, (x, _y) in positions.items())
    top = min(y - sizes[node][1] / 2 for node, (_x, y) in positions.items())
    centers = {node: (x - left + margin, y - top + margin) for node, (x, y) in positions.items()}
    width = max(x + sizes[node][0] / 2 for node, (x, _y) in centers.items()) + margin
    height = max(y + sizes[node][1] / 2 for node, (_x, y) in centers.items()) + margin
    return Layout(centers, width, height)


def tree_layout(sizes, children, root, *, direction="TB", gap_major=46.0, gap_minor=20.0, margin=12.0) -> Layout:
    """Ordnet einen Baum an: Blätter nebeneinander, Eltern mittig über ihren Kindern.

    Args:
        sizes: `{knoten: (breite, höhe)}`; `PLACEHOLDER`-Kinder brauchen keinen Eintrag.
        children: `{knoten: [kinder]}` in Anzeigereihenfolge.
        root: Wurzel.
        direction: `TB` oder `LR`.
        gap_major: Abstand zwischen den Ebenen.
        gap_minor: Abstand zwischen Geschwistern.
        margin: Rand.

    Returns:
        `Layout` ohne Platzhalter.
    """
    horizontal = direction == "LR"
    extent_minor = lambda node: sizes[node][1 if horizontal else 0]  # noqa: E731
    extent_major = lambda node: sizes[node][0 if horizontal else 1]  # noqa: E731
    place: dict[str, tuple[float, int]] = {}
    cursor = [0.0]
    placeholder_width = max((extent_minor(node) for node in sizes), default=0.0)

    def visit(node: str, depth: int, seen: frozenset) -> float:
        kids = [kid for kid in children.get(node, ()) if kid not in seen]
        real = [kid for kid in kids if kid != PLACEHOLDER]
        if not real:
            center = cursor[0] + extent_minor(node) / 2
            cursor[0] += extent_minor(node) + gap_minor
        else:
            spots = []
            for kid in kids:
                if kid == PLACEHOLDER:
                    spots.append(cursor[0] + placeholder_width / 2)
                    cursor[0] += placeholder_width + gap_minor
                else:
                    spots.append(visit(kid, depth + 1, seen | {node}))
            center = (spots[0] + spots[-1]) / 2
        place[node] = (center, depth)
        return center

    visit(root, 0, frozenset())
    depths = max(depth for _center, depth in place.values()) + 1
    level = [max((extent_major(n) for n, (_c, d) in place.items() if d == i), default=0.0) for i in range(depths)]
    along = []
    running = 0.0
    for depth in range(depths):
        along.append(running + level[depth] / 2)
        running += level[depth] + gap_major
    if horizontal:
        positions = {node: (along[depth], center) for node, (center, depth) in place.items()}
    else:
        positions = {node: (center, along[depth]) for node, (center, depth) in place.items()}
    return _bounded(positions, sizes, margin)


def circle_layout(sizes, *, margin=30.0, gap=64.0) -> Layout:
    """Ordnet Knoten im Uhrzeigersinn auf einem Kreis an, beginnend oben."""
    nodes = list(sizes)
    largest = max(max(size) for size in sizes.values())
    radius = 0.0 if len(nodes) == 1 else (largest + gap) / (2 * math.sin(math.pi / len(nodes)))
    positions = {
        node: (radius * math.sin(2 * math.pi * i / len(nodes)), -radius * math.cos(2 * math.pi * i / len(nodes)))
        for i, node in enumerate(nodes)
    }
    return _bounded(positions, sizes, margin)


def _separate(positions, sizes, gap: float) -> None:
    """Schiebt überlappende Knoten auseinander (feste Schrittzahl, gleiche Reihenfolge)."""
    nodes = list(positions)
    for _ in range(_SEPARATION_STEPS):
        moved = False
        for i, first in enumerate(nodes):
            for second in nodes[i + 1:]:
                ax, ay = positions[first]
                bx, by = positions[second]
                need_x = (sizes[first][0] + sizes[second][0]) / 2 + gap - abs(ax - bx)
                need_y = (sizes[first][1] + sizes[second][1]) / 2 + gap - abs(ay - by)
                if need_x <= 0 or need_y <= 0:
                    continue
                moved = True
                if need_x < need_y:
                    shift = (need_x / 2) * (1 if ax >= bx else -1)
                    positions[first] = (ax + shift, ay)
                    positions[second] = (bx - shift, by)
                else:
                    shift = (need_y / 2) * (1 if ay >= by else -1)
                    positions[first] = (ax, ay + shift)
                    positions[second] = (bx, by - shift)
        if not moved:
            return


def free_layout(sizes, edges, *, spacing=110.0, margin=12.0, gap=26.0) -> Layout:
    """Freie Anordnung für allgemeine Graphen (Fruchterman-Reingold ohne Zufall).

    Args:
        sizes: `{knoten: (breite, höhe)}`.
        edges: Kanten `(a, b)`; Selbstkanten zählen nicht.
        spacing: Angestrebter Kantenabstand.
        margin: Rand.
        gap: Mindestabstand zwischen Knoten.

    Returns:
        `Layout` ohne überlappende Knoten.
    """
    nodes = list(sizes)
    radius = spacing * max(1.0, len(nodes) / 4)
    positions = {
        node: (radius * math.sin(2 * math.pi * i / len(nodes)), -radius * math.cos(2 * math.pi * i / len(nodes)))
        for i, node in enumerate(nodes)
    }
    pairs = [(a, b) for a, b in edges if a != b]
    for step in range(_FORCE_STEPS):
        temperature = spacing * (1.0 - step / _FORCE_STEPS)
        force = {node: [0.0, 0.0] for node in nodes}
        for i, first in enumerate(nodes):
            for second in nodes[i + 1:]:
                dx = positions[first][0] - positions[second][0]
                dy = positions[first][1] - positions[second][1]
                distance = math.hypot(dx, dy) or 0.01
                push = spacing * spacing / distance
                force[first][0] += dx / distance * push
                force[first][1] += dy / distance * push
                force[second][0] -= dx / distance * push
                force[second][1] -= dy / distance * push
        for first, second in pairs:
            dx = positions[first][0] - positions[second][0]
            dy = positions[first][1] - positions[second][1]
            distance = math.hypot(dx, dy) or 0.01
            pull = distance * distance / spacing
            force[first][0] -= dx / distance * pull
            force[first][1] -= dy / distance * pull
            force[second][0] += dx / distance * pull
            force[second][1] += dy / distance * pull
        for node in nodes:
            length = math.hypot(*force[node]) or 0.01
            limit = min(length, temperature)
            positions[node] = (
                positions[node][0] + force[node][0] / length * limit,
                positions[node][1] + force[node][1] / length * limit,
            )
    _separate(positions, sizes, gap)
    return _bounded(positions, sizes, margin)


def tree_children(nodes, edges, first_is_root: bool = False) -> tuple[str, dict[str, list[str]]] | None:
    """Prüft, ob `edges` einen zusammenhängenden Baum über `nodes` bilden.

    Gerichtete Kanten sind hier egal. Die Wurzel ist der erste Knoten (`first_is_root`, im
    Graphen schreibt man den Baum von oben nach unten), sonst der Knoten mit den meisten
    Kanten, damit in einem Netzwerk das zentrale Gerät oben steht.

    Returns:
        `(wurzel, kinder)` oder `None`, wenn es kein Baum ist.
    """
    nodes = list(nodes)
    pairs = [(a, b) for a, b in edges if a != b]
    if len(pairs) != len(nodes) - 1:
        return None
    neighbours: dict[str, list[str]] = {node: [] for node in nodes}
    for first, second in pairs:
        neighbours[first].append(second)
        neighbours[second].append(first)
    root = nodes[0] if first_is_root else max(nodes, key=lambda node: len(neighbours[node]))
    children: dict[str, list[str]] = {}
    seen = {root}
    queue = [root]
    while queue:
        node = queue.pop(0)
        children[node] = [other for other in neighbours[node] if other not in seen]
        seen.update(children[node])
        queue.extend(children[node])
    return (root, children) if len(seen) == len(nodes) else None
