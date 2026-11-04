"""Anordnung der ER-Diagramme: Entitäten im Raster, Beziehungsrauten in den Zwischenräumen.

Warum kein Federmodell: Es kennt weder Fläche noch Kreuzungen, und mehrere Beziehungen
zwischen denselben Entitäten lägen deckungsgleich übereinander. Hier liegen die
Entitäten auf Rasterzellen, und eine Suche vertauscht Zellen, solange die Kosten sinken.
Die Kosten zählen Kanten durch fremde Formen, Kreuzungen, Überlappungen und vor allem
die wirksame Größe: ER-Diagramme stehen meist auf A4-Arbeitsblättern, sollen flach sein
und dürfen dabei nicht so breit werden, dass die Schrift beim Einpassen winzig wird.

Eine Raute steht mitten im Zwischenraum ihrer beiden Entitäten; stehen die Entitäten
schräg zueinander, sitzt sie im Knick eines L wie im GO-Beispiel. Mehrere Beziehungen
zwischen denselben Entitäten fächern sich auf: übereinander, wenn die Entitäten
nebeneinander oder schräg stehen, nebeneinander, wenn sie übereinander stehen.

Platz wird nur reserviert, wo er gebraucht wird: Attribute einer Raute zwischen zwei
Entitäten nebeneinander stehen über oder unter ihr, zwischen zwei übereinander stehenden
daneben. Eine rekursive Raute hängt auf der Seite ihrer Entität, auf der weniger andere
Beziehungen liegen, und nur dort wird Platz für sie reserviert.

Rein und deterministisch: Startreihenfolge ist eine Breitensuche in Schreibreihenfolge,
die Suche probiert Zellen in fester Reihenfolge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .diagram_er_route import APPROACH, route_edges
from .diagram_er_shapes import RECURSIVE_DROP, attribute_ring, shape_size
from .diagram_layout import Layout
from .diagram_route import rects_overlap, segment_hits_rect, segments_cross, segments_overlap

_PAD = 14.0
"""Luft zwischen einer Raute und den Formen neben ihr."""
_MIN_GAP = 36.0
_FAN_GAP = 10.0
_MAX_ROWS = 4
_ROUNDS = 12
_COST_HIT = 2000.0
"""Kante durch eine fremde Form: fast immer unlesbar."""
_COST_OVERLAP = 2000.0
_COST_CROSS = 500.0
_ASPECT = 2.4
"""Breite, die so viel zählt wie eine Einheit Höhe: ER-Diagramme sollen flach sein, aber
nicht so breit, dass sie auf A4 winzig werden. Reine Fläche (`sqrt(breite * höhe)`) als
Maß ergab einzeilige Bandwürmer (1576x156)."""
_COST_SIZE = 1.0
"""Gewicht der wirksamen Größe `max(breite / _ASPECT, höhe)`: So stark schrumpft das
Diagramm beim Einpassen."""
_COST_HEIGHT = 0.3
"""Bei ähnlicher Fläche gewinnt das flachere Diagramm."""
_COST_LENGTH = 0.05
"""Gleichstandsbrecher: verbundene Entitäten rücken zusammen."""


def recursive_pairs(model) -> set[tuple[str, str]]:
    """Paare aus Entität und Raute, die zweimal vorkommen (rekursive Beziehung)."""
    seen: set[tuple[str, str]] = set()
    repeated: set[tuple[str, str]] = set()
    for link in model.links:
        pair = (link.entity, link.relation)
        (repeated if pair in seen else seen).add(pair)
    return repeated


def relation_groups(model) -> list[tuple[str, str, list[str]]]:
    """Beziehungen je Entitätspaar in Schreibreihenfolge, ohne rekursive.

    Mehrere Rauten in einer Gruppe bilden einen Fächer (Layout) und setzen gestaffelt an
    ihren Entitäten an (Kantenführung).
    """
    hanging = {relation for _entity, relation in recursive_pairs(model)}
    ends: dict[str, list[str]] = {}
    for link in model.links:
        ends.setdefault(link.relation, []).append(link.entity)
    groups: dict[frozenset, tuple[str, str, list[str]]] = {}
    for relation, (first, second) in ((r, e) for r, e in ends.items() if r not in hanging):
        groups.setdefault(frozenset((first, second)), (first, second, []))[2].append(relation)
    return list(groups.values())


@dataclass(frozen=True)
class _Plan:
    """Was die Suche über das Diagramm wissen muss.

    Attributes:
        entities: Entitäten im Raster, in Schreibreihenfolge.
        sizes: Formgröße jeder Entität und Raute ohne Attribute.
        rings: Platz der Attribute je Form (`attribute_ring`).
        groups: `(a, b, rauten)` je Entitätspaar; rekursive Beziehungen fehlen.
        loops: Rekursive Raute je Entität.
    """

    entities: list[str]
    sizes: dict[str, tuple[float, float]]
    rings: dict[str, tuple[float, float]]
    groups: list[tuple[str, str, list[str]]]
    loops: dict[str, str]


def _plan(model) -> _Plan:
    """Sammelt Größen, Entitätspaare und rekursive Beziehungen."""
    return _Plan(
        [name for name, node in model.nodes.items() if not node.diamond],
        {name: shape_size(node) for name, node in model.nodes.items()},
        {name: attribute_ring(node) for name, node in model.nodes.items()},
        relation_groups(model),
        {entity: relation for entity, relation in recursive_pairs(model)},
    )


def _print(plan: _Plan, name: str, sideways: bool = True, upright: bool = True) -> tuple[float, float]:
    """Platzbedarf einer Form samt Attributen, die daneben (`sideways`) bzw. darüber und darunter (`upright`) stehen."""
    (width, height), (sides, above) = plan.sizes[name], plan.rings[name]
    return width + (sides if sideways else 0.0), height + (2 * above if upright else 0.0)


def _loop_side(plan: _Plan, entity: str, row_of) -> int:
    """Seite der rekursiven Raute: oben (-1), wenn unten mehr Beziehungen liegen, sonst unten (+1)."""
    partners = [other for first, second, _relations in plan.groups for here, other in ((first, second), (second, first)) if here == entity]
    below = sum(1 for other in partners if row_of[other] > row_of[entity])
    above = sum(1 for other in partners if row_of[other] < row_of[entity])
    return -1 if below > above else 1


def _entity_extent(plan: _Plan, entity: str, side: int) -> tuple[float, float, float]:
    """Halbe Breite sowie Platz über und unter der Entität; die rekursive Raute nur auf `side`."""
    width, height = _print(plan, entity)
    loop = plan.loops.get(entity)
    if not loop:
        return width / 2, height / 2, height / 2
    (shape_w, shape_h), above = plan.sizes[entity], plan.rings[entity][1]
    loop_w, loop_h = plan.sizes[loop]
    hanging = shape_h / 2 + max(above, RECURSIVE_DROP + loop_h)
    rest = shape_h / 2 + above
    half = max(width, loop_w + shape_w / 3) / 2
    return (half, hanging, rest) if side < 0 else (half, rest, hanging)


def _fan(prints, relations, sideways: bool) -> tuple[list[float], tuple[float, float]]:
    """Versatz jeder Raute eines Fächers längs der Fächerachse und Platzbedarf `(breite, höhe)`.

    `sideways` legt die Rauten nebeneinander statt übereinander. Bei ungerader Zahl sitzt
    die mittlere Raute genau auf der Verbindungslinie ihrer Entitäten; bei ungleich hohen
    Rauten (eine zweizeilig) stünde sie sonst versetzt, und ihre Kante bekäme einen Knick.
    Der Platzbedarf ist symmetrisch um die Linie, also die weiter ausladende Seite doppelt.
    """
    axis = 0 if sideways else 1
    sizes = [prints[relation] for relation in relations]
    offsets, cursor = [], 0.0
    for size in sizes:
        offsets.append(cursor + size[axis] / 2)
        cursor += size[axis] + _FAN_GAP
    anchor = offsets[len(offsets) // 2] if len(offsets) % 2 else (cursor - _FAN_GAP) / 2
    offsets = [offset - anchor for offset in offsets]
    reach = 2 * max(abs(offset) + size[axis] / 2 for offset, size in zip(offsets, sizes))
    across = max(size[1 - axis] for size in sizes)
    return offsets, ((reach, across) if sideways else (across, reach))


def _axis(extents, gaps) -> tuple[list[float], float]:
    """Mittelpunkte aufeinanderfolgender Spalten oder Zeilen aus `(davor, danach)` und ihre Gesamtlänge."""
    values, cursor = [], 0.0
    for index, (before, after) in enumerate(extents):
        values.append(cursor + before)
        cursor += before + after + (gaps[index] if index < len(gaps) else 0.0)
    return values, cursor


def _between(values, extents, gaps, first: int, second: int) -> float:
    """Lage einer Raute auf einer Achse: Mitte der Zelle, des Zwischenraums oder der Strecke."""
    if first == second:
        return values[first]
    low, high = min(first, second), max(first, second)
    if high - low == 1:
        return values[low] + extents[low][1] + gaps[low] / 2
    return (values[first] + values[second]) / 2


def _grow(extent: list[float], before: float, after: float) -> None:
    """Vergrößert `[davor, danach]` einer Spalte oder Zeile, wo nötig."""
    extent[0], extent[1] = max(extent[0], before), max(extent[1], after)


def _corner_cells(plan: _Plan, col_of, row_of) -> list[tuple[int, int] | None]:
    """Zelle `(spalte, zeile)` je Gruppe, deren Entitäten schräg zueinander stehen.

    Die Raute sitzt dann im Knick eines L (GO: „unterrichtet“), beide Kanten laufen
    gerade: in der Spalte der einen und der Zeile der anderen Entität. Belegt eine Entität
    oder eine andere Raute diese Zelle, kommt die zweite L-Ecke infrage; sind beide belegt,
    bleibt nur `None` (Raute zwischen den beiden, Kanten mit Knick).
    """
    taken = {(col_of[entity], row_of[entity]) for entity in plan.entities}
    cells: list[tuple[int, int] | None] = []
    for first, second, _relations in plan.groups:
        cell = None
        if col_of[first] != col_of[second] and row_of[first] != row_of[second]:
            options = ((col_of[first], row_of[second]), (col_of[second], row_of[first]))
            cell = next((option for option in options if option not in taken), None)
            taken.add(cell)
        cells.append(cell)
    return cells


def _geometry(plan: _Plan, cells) -> tuple[Layout, dict[str, tuple[float, float]]]:
    """Mittelpunkte aller Formen im Raster; leere Spalten und Zeilen entfallen.

    Returns:
        `Layout` mit Entitäten, Rauten und rekursiven Rauten sowie der Platzbedarf jeder
        nicht rekursiven Raute, so wie ihre Lage ihn ergibt.
    """
    cols = sorted({col for _row, col in cells.values()})
    rows = sorted({row for row, _col in cells.values()})
    col_of = {entity: cols.index(cells[entity][1]) for entity in plan.entities}
    row_of = {entity: rows.index(cells[entity][0]) for entity in plan.entities}
    col_extents, row_extents = [[0.0, 0.0] for _ in cols], [[0.0, 0.0] for _ in rows]
    sides = {entity: _loop_side(plan, entity, row_of) for entity in plan.loops}
    for entity in plan.entities:
        half, up, down = _entity_extent(plan, entity, sides.get(entity, 1))
        _grow(col_extents[col_of[entity]], half, half)
        _grow(row_extents[row_of[entity]], up, down)
    corner_cells = _corner_cells(plan, col_of, row_of)
    col_gaps, row_gaps = [_MIN_GAP] * (len(cols) - 1), [_MIN_GAP] * (len(rows) - 1)
    prints: dict[str, tuple[float, float]] = {}
    for (first, second, relations), corner in zip(plan.groups, corner_cells):
        (left, right), (top, bottom) = sorted((col_of[first], col_of[second])), sorted((row_of[first], row_of[second]))
        free = corner is not None or (left != right and top != bottom)
        for relation in relations:
            prints[relation] = _print(plan, relation, sideways=free or left == right, upright=free or top == bottom)
        fan_width, fan_height = _fan(prints, relations, sideways=left == right)[1]
        if corner is not None:
            _grow(col_extents[corner[0]], fan_width / 2, fan_width / 2)
            _grow(row_extents[corner[1]], fan_height / 2, fan_height / 2)
            continue
        if left == right:
            _grow(col_extents[left], fan_width / 2, fan_width / 2)
        elif right - left == 1:
            col_gaps[left] = max(col_gaps[left], fan_width + 2 * _PAD)
        if top == bottom:
            _grow(row_extents[top], fan_height / 2, fan_height / 2)
        elif bottom - top == 1:
            approach = 2 * APPROACH if left != right else 0.0
            row_gaps[top] = max(row_gaps[top], fan_height + 2 * _PAD + approach)
    xs, width = _axis(col_extents, col_gaps)
    ys, height = _axis(row_extents, row_gaps)
    centers = {entity: (xs[col_of[entity]], ys[row_of[entity]]) for entity in plan.entities}
    for (first, second, relations), corner in zip(plan.groups, corner_cells):
        if corner is not None:
            x, y = xs[corner[0]], ys[corner[1]]
        else:
            x = _between(xs, col_extents, col_gaps, col_of[first], col_of[second])
            y = _between(ys, row_extents, row_gaps, row_of[first], row_of[second])
        sideways = col_of[first] == col_of[second]
        for relation, offset in zip(relations, _fan(prints, relations, sideways)[0]):
            centers[relation] = (x + offset, y) if sideways else (x, y + offset)
    for entity, loop in plan.loops.items():
        x, y = centers[entity]
        centers[loop] = (x, y + sides[entity] * (plan.sizes[entity][1] / 2 + RECURSIVE_DROP + plan.sizes[loop][1] / 2))
    return Layout(centers, width, height), prints


def _cost(plan: _Plan, cells) -> float:
    """Bewertet eine Belegung; kleiner ist besser (Gewichte siehe `_COST_*`)."""
    layout, prints = _geometry(plan, cells)
    centers = layout.centers
    routes = route_edges(plan.sizes, centers, plan.groups)
    segments = [(relation, entity, segment) for (entity, relation), points in routes.items() for segment in zip(points, points[1:])]
    shapes = [(name, (*centers[name], *plan.sizes[name])) for name in centers]
    hits = sum(1 for relation, entity, segment in segments for name, rect in shapes if name not in (relation, entity) and segment_hits_rect(segment, rect, _PAD / 2))
    crossings = sum(
        1
        for index, (relation, entity, segment) in enumerate(segments)
        for other_relation, other_entity, other in segments[index + 1:]
        if (relation != other_relation and entity != other_entity and segments_cross(segment, other))
        or ((relation, entity) != (other_relation, other_entity) and segments_overlap(segment, other))
    )
    spots = [(name, (*centers[name], *_print(plan, name))) for name in plan.entities]
    spots += [(name, (*centers[name], *size)) for name, size in prints.items()]
    overlaps = sum(1 for index, (name, rect) in enumerate(spots) for other_name, other in spots[index + 1:] if (name in prints or other_name in prints) and rects_overlap(rect, other))
    length = sum(math.dist(*segment) for _relation, _entity, segment in segments)
    return (
        _COST_HIT * hits + _COST_OVERLAP * overlaps + _COST_CROSS * crossings
        + _COST_SIZE * max(layout.width / _ASPECT, layout.height) + _COST_HEIGHT * layout.height + _COST_LENGTH * length
    )


def _start_order(plan: _Plan) -> list[str]:
    """Breitensuche ab der Entität mit den meisten Beziehungen, Gleichstand nach Schreibreihenfolge."""
    neighbours: dict[str, list[str]] = {entity: [] for entity in plan.entities}
    for first, second, _relations in plan.groups:
        neighbours[first].append(second)
        neighbours[second].append(first)
    order: list[str] = []
    for start in sorted(plan.entities, key=lambda entity: -len(neighbours[entity])):
        if start in order:
            continue
        order.append(start)
        queue = [start]
        while queue:
            for other in neighbours[queue.pop(0)]:
                if other not in order:
                    order.append(other)
                    queue.append(other)
    return order


def _climb(plan: _Plan, cells, slots) -> tuple[float, dict]:
    """Verschiebt oder vertauscht Entitäten, solange die Kosten sinken (erste Verbesserung zählt)."""
    cost = _cost(plan, cells)
    for _ in range(_ROUNDS):
        improved = False
        for entity in plan.entities:
            for slot in slots:
                here = cells[entity]
                if slot == here:
                    continue
                trial = dict(cells)
                occupant = next((other for other, spot in cells.items() if spot == slot), None)
                trial[entity] = slot
                if occupant:
                    trial[occupant] = here
                value = _cost(plan, trial)
                if value < cost - 1e-6:
                    cells, cost, improved = trial, value, True
        if not improved:
            break
    return cost, cells


def _starts(order: list[str], rows: int) -> list[dict[str, tuple[int, int]]]:
    """Startbelegungen für `rows` Zeilen: zeilenweise und schlangenförmig.

    Mehrere Starts, weil die Suche nur bergab geht: Von einer schlechten Belegung führt
    oft jeder einzelne Tausch erst durch eine Kante quer durch eine Form.
    """
    per_row = math.ceil(len(order) / rows)
    plain = {entity: (index // per_row, index % per_row) for index, entity in enumerate(order)}
    snake = {}
    for index, entity in enumerate(order):
        row, col = index // per_row, index % per_row
        snake[entity] = (row, per_row - 1 - col if row % 2 else col)
    return [plain, snake] if snake != plain else [plain]


def arrange(model) -> Layout:
    """Ordnet das ER-Diagramm kompakt an: keine Kanten durch Formen, wenige Kreuzungen.

    Probiert ein bis `_MAX_ROWS` Zeilen, jeweils mit einer freien Spalte als Spielraum, und
    Startreihenfolgen aus Breitensuche und Schreibreihenfolge; die günstigste Belegung gewinnt.

    Returns:
        `Layout` mit Mittelpunkten aller Entitäten und Rauten; der Ursprung liegt an der
        linken oberen Ecke des freigehaltenen Platzes, Ränder fügt der Aufrufer hinzu.
    """
    plan = _plan(model)
    orders = [_start_order(plan)]
    if plan.entities != orders[0]:
        orders.append(list(plan.entities))
    best: tuple[float, dict] | None = None
    for rows in range(1, min(len(plan.entities), _MAX_ROWS) + 1):
        cols = math.ceil(len(plan.entities) / rows) + (1 if rows > 1 else 0)
        slots = [(row, col) for row in range(rows) for col in range(cols)]
        for start in (start for order in orders for start in _starts(order, rows)):
            result = _climb(plan, start, slots)
            if best is None or result[0] < best[0] - 1e-6:
                best = result
    return _geometry(plan, best[1])[0]
