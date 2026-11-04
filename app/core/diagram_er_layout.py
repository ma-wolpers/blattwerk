"""Anordnung der ER-Diagramme: Entitäten im Raster, Beziehungsrauten in den Zwischenräumen.

Warum kein Federmodell: Es kennt weder die Höhe noch Kreuzungen, und mehrere
Beziehungen zwischen denselben Entitäten lägen deckungsgleich übereinander. Hier liegen
die Entitäten auf Rasterzellen, und eine Suche vertauscht Zellen, solange die Kosten
sinken. Die Kosten zählen Kanten durch fremde Formen, Kreuzungen, Überlappungen und vor
allem die Höhe: ER-Diagramme sollen flach sein und dürfen dafür breiter werden.

Eine Raute steht mitten im Zwischenraum ihrer beiden Entitäten; stehen die Entitäten
schräg zueinander, sitzt sie im Knick eines L wie im GO-Beispiel. Mehrere Beziehungen
zwischen denselben Entitäten fächern sich auf: übereinander, wenn die Entitäten
nebeneinander oder schräg stehen, nebeneinander, wenn sie übereinander stehen. Die
Zwischenräume wachsen mit, damit die Rauten samt ihren Attributen Platz haben.

Rein und deterministisch: Startreihenfolge ist eine Breitensuche in Schreibreihenfolge,
die Suche probiert Zellen in fester Reihenfolge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .diagram_layout import Layout
from .diagram_route import Box, diamond_corner, rects_overlap, segment_hits_rect, segments_cross, segments_overlap
from .diagram_svg import text_width

ENTITY_HEIGHT = 32.0
DIAMOND_HEIGHT = 42.0
OVAL_HEIGHT = 28.0
RING_GAP = 15.0
"""Abstand des Attributrings von seiner Form."""
RECURSIVE_DROP = 34.0
"""Abstand einer rekursiven Raute von ihrer Entität."""
_PAD = 14.0
"""Luft zwischen einer Raute und den Formen neben ihr."""
_MIN_GAP = 36.0
_FAN_GAP = 10.0
_INSET = 10.0
"""Abstand eines L-Ansatzes in Fächern von der Entitätsecke, je Verschachtelung mehr."""
_ALIGN = 4.0
"""So weit innerhalb der Entitätskante muss eine Rautenecke liegen, damit die Kante gerade läuft."""
_MAX_ROWS = 4
_ROUNDS = 12
_COST_HIT = 2000.0
"""Kante durch eine fremde Form: fast immer unlesbar."""
_COST_OVERLAP = 2000.0
_COST_CROSS = 500.0
_ASPECT = 2.4
"""Angestrebtes Verhältnis Breite zu Höhe: flacher als eine 16:9-Folie, aber nicht endlos breit."""
_COST_SIZE = 1.0
"""Gewicht der wirksamen Größe `max(breite / _ASPECT, höhe)`; sie bestimmt, wie stark das
Diagramm beim Einpassen schrumpft."""
_COST_HEIGHT = 0.3
"""Bei gleicher wirksamer Größe gewinnt das flachere Diagramm."""
_COST_LENGTH = 0.05
"""Gleichstandsbrecher: verbundene Entitäten rücken zusammen. Bewusst klein, eine lange
gerade Kante ist besser als ein höheres Diagramm."""


def shape_size(node) -> tuple[float, float]:
    """Größe von Rechteck oder Raute ohne die Attribute."""
    width = text_width(node.title.text)
    return (width * 1.5 + 28, DIAMOND_HEIGHT) if node.diamond else (max(width + 22, 64.0), ENTITY_HEIGHT)


def oval_size(cell) -> tuple[float, float]:
    """Größe eines Attribut-Ovals."""
    return text_width(cell.text.replace("__", "")) + 22, OVAL_HEIGHT


def footprint(node, recursive_width: float = 0.0) -> tuple[float, float]:
    """Äußere Größe inklusive Attributring und rekursiver Raute (`recursive_width` > 0).

    Das Layout hält diesen Platz frei, damit die Attribute später ringsum Platz finden:
    seitlich das breiteste Oval auf der einen und das zweitbreiteste auf der anderen
    Seite, darüber und darunter je eine Ovalhöhe. Eine rekursive Raute braucht oben und
    unten mehr; Attribute weichen ihr seitlich aus, also zählt dort das Größere von beidem.
    Reicht das im Einzelfall nicht, weicht die Attributplatzierung nach außen aus, und der
    Rand wächst mit.
    """
    width, height = shape_size(node)
    above = OVAL_HEIGHT + RING_GAP if node.attributes else 0.0
    if recursive_width:
        width = max(width, recursive_width + width / 3)
        above = max(above, RECURSIVE_DROP + DIAMOND_HEIGHT)
    if not node.attributes:
        return width, height + 2 * above
    widths = sorted((oval_size(cell)[0] for cell in node.attributes), reverse=True)
    sides = widths[0] + (widths[1] if len(widths) > 1 else widths[0])
    return width + sides + 2 * RING_GAP, height + 2 * above


def recursive_pairs(model) -> set[tuple[str, str]]:
    """Paare aus Entität und Raute, die zweimal vorkommen (rekursive Beziehung)."""
    seen: set[tuple[str, str]] = set()
    repeated: set[tuple[str, str]] = set()
    for link in model.links:
        pair = (link.entity, link.relation)
        (repeated if pair in seen else seen).add(pair)
    return repeated


@dataclass(frozen=True)
class _Plan:
    """Was die Suche über das Diagramm wissen muss.

    Attributes:
        entities: Entitäten im Raster, in Schreibreihenfolge.
        sizes: Größe jeder Form im Raster (Entitäten und Rauten) ohne Attribute.
        footprints: Platzbedarf jeder Form im Raster samt Attributen.
        groups: `(a, b, rauten)` je Entitätspaar; rekursive Beziehungen fehlen.
    """

    entities: list[str]
    sizes: dict[str, tuple[float, float]]
    footprints: dict[str, tuple[float, float]]
    groups: list[tuple[str, str, list[str]]]


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


def _plan(model) -> tuple[_Plan, set[tuple[str, str]]]:
    """Sammelt Größen und Entitätspaare; liefert auch die rekursiven Paare."""
    recursive = recursive_pairs(model)
    hanging = {relation for _entity, relation in recursive}
    loop_of = {entity: relation for entity, relation in recursive}
    entities = [name for name, node in model.nodes.items() if not node.diamond]
    sizes, footprints = {}, {}
    for name, node in model.nodes.items():
        if name in hanging:
            continue
        loop = loop_of.get(name)
        sizes[name] = shape_size(node)
        footprints[name] = footprint(node, shape_size(model.nodes[loop])[0] if loop else 0.0)
    return _Plan(entities, sizes, footprints, relation_groups(model)), recursive


def _between(values, extents, gaps, first: int, second: int) -> float:
    """Lage einer Raute auf einer Achse: Mitte der Zelle, des Zwischenraums oder der Strecke."""
    if first == second:
        return values[first]
    low, high = min(first, second), max(first, second)
    if high - low == 1:
        return values[low] + extents[low] / 2 + gaps[low] / 2
    return (values[first] + values[second]) / 2


def _stack(plan: _Plan, relations, sideways: bool) -> tuple[float, float]:
    """Gesamtgröße eines Rautenfächers; `sideways` legt die Rauten nebeneinander."""
    sizes = [plan.footprints[relation] for relation in relations]
    if sideways:
        return sum(w for w, _h in sizes) + _FAN_GAP * (len(sizes) - 1), max(h for _w, h in sizes)
    return max(w for w, _h in sizes), sum(h for _w, h in sizes) + _FAN_GAP * (len(sizes) - 1)


def _axis(extents, gaps) -> tuple[list[float], float]:
    """Mittelpunkte aufeinanderfolgender Spalten oder Zeilen und ihre Gesamtlänge."""
    values, cursor = [], 0.0
    for index, extent in enumerate(extents):
        values.append(cursor + extent / 2)
        cursor += extent + (gaps[index] if index < len(gaps) else 0.0)
    return values, cursor


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


def _geometry(plan: _Plan, cells) -> Layout:
    """Mittelpunkte aller Formen im Raster; leere Spalten und Zeilen entfallen."""
    cols = sorted({col for _row, col in cells.values()})
    rows = sorted({row for row, _col in cells.values()})
    col_of = {entity: cols.index(cells[entity][1]) for entity in plan.entities}
    row_of = {entity: rows.index(cells[entity][0]) for entity in plan.entities}
    widths, heights = [0.0] * len(cols), [0.0] * len(rows)
    for entity in plan.entities:
        widths[col_of[entity]] = max(widths[col_of[entity]], plan.footprints[entity][0])
        heights[row_of[entity]] = max(heights[row_of[entity]], plan.footprints[entity][1])
    corner_cells = _corner_cells(plan, col_of, row_of)
    col_gaps, row_gaps = [_MIN_GAP] * (len(cols) - 1), [_MIN_GAP] * (len(rows) - 1)
    for (first, second, relations), corner in zip(plan.groups, corner_cells):
        (left, right), (top, bottom) = sorted((col_of[first], col_of[second])), sorted((row_of[first], row_of[second]))
        fan_width, fan_height = _stack(plan, relations, sideways=left == right)
        if corner is not None:
            widths[corner[0]] = max(widths[corner[0]], fan_width)
            heights[corner[1]] = max(heights[corner[1]], fan_height)
            continue
        if left == right:
            widths[left] = max(widths[left], fan_width)
        elif right - left == 1:
            col_gaps[left] = max(col_gaps[left], fan_width + 2 * _PAD)
        if top == bottom:
            heights[top] = max(heights[top], fan_height)
        elif bottom - top == 1:
            row_gaps[top] = max(row_gaps[top], fan_height + 2 * _PAD)
    xs, width = _axis(widths, col_gaps)
    ys, height = _axis(heights, row_gaps)
    centers = {entity: (xs[col_of[entity]], ys[row_of[entity]]) for entity in plan.entities}
    for (first, second, relations), corner in zip(plan.groups, corner_cells):
        if corner is not None:
            x, y = xs[corner[0]], ys[corner[1]]
        else:
            x = _between(xs, widths, col_gaps, col_of[first], col_of[second])
            y = _between(ys, heights, row_gaps, row_of[first], row_of[second])
        sideways = col_of[first] == col_of[second]
        axis = 0 if sideways else 1
        cursor = -_stack(plan, relations, sideways)[axis] / 2
        for relation in relations:
            offset = cursor + plan.footprints[relation][axis] / 2
            cursor += plan.footprints[relation][axis] + _FAN_GAP
            centers[relation] = (x + offset, y) if sideways else (x, y + offset)
    return Layout(centers, width, height)


def _cost(plan: _Plan, cells) -> float:
    """Bewertet eine Belegung; kleiner ist besser (Gewichte siehe `_COST_*`)."""
    layout = _geometry(plan, cells)
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
    spots = [(name, (*centers[name], *plan.footprints[name])) for name in centers]
    overlaps = sum(1 for index, (name, rect) in enumerate(spots) for other_name, other in spots[index + 1:] if (name not in cells or other_name not in cells) and rects_overlap(rect, other))
    length = sum(math.dist(*segment) for _relation, _entity, segment in segments)
    return (
        _COST_HIT * hits + _COST_OVERLAP * overlaps + _COST_CROSS * crossings
        + _COST_SIZE * max(layout.width / _ASPECT, layout.height) + _COST_HEIGHT * layout.height + _COST_LENGTH * length
    )


def _corner_for(size, center, entity, other, taken) -> tuple[tuple[float, float], bool]:
    """Rautenecke der Kante zu `entity` und ob die Kante dort waagerecht ankommt.

    Liegt die Raute zwischen ihren beiden Entitäten, zeigen die Ecken zu ihnen (links und
    rechts bzw. oben und unten); sonst gewinnt die freie Ecke in Richtung der Entität.
    """
    (rx, ry), (width, height) = center, size
    if (entity[0] - rx) * (other[0] - rx) < 0 and abs(entity[0] - rx) > width / 2:
        return (rx + math.copysign(width / 2, entity[0] - rx), ry), True
    if (entity[1] - ry) * (other[1] - ry) < 0 and abs(entity[1] - ry) > height / 2:
        return (rx, ry + math.copysign(height / 2, entity[1] - ry)), False
    corner = diamond_corner(rx, ry, width / 2, height / 2, entity, taken)
    return corner, corner[1] == ry


def _orthogonal(box: Box, corner, horizontal: bool, inset: float | None) -> list[tuple[float, float]]:
    """Rechtwinkliger Weg vom Rand der Entität zur Rautenecke (GO).

    Gerade, wenn die Ecke neben der Entität liegt (waagerechte Ankunft) bzw. über oder
    unter ihr; sonst ein L aus der Ober- oder Unterseite bzw. aus der Seite, `inset` von
    der Ecke der Entität entfernt, ohne `inset` aus der Mitte.
    """
    cx, cy = corner
    if horizontal:
        if box.top + _ALIGN <= cy <= box.bottom - _ALIGN:
            return [(box.right if cx > box.cx else box.left, cy), corner]
        step = min(inset or box.width / 2, box.width / 2)
        x = box.right - step if cx > box.cx else box.left + step
        return [(x, box.bottom if cy > box.cy else box.top), (x, cy), corner]
    if box.left + _ALIGN <= cx <= box.right - _ALIGN:
        return [(cx, box.bottom if cy > box.cy else box.top), corner]
    step = min(inset or box.height / 2, box.height / 2)
    y = box.bottom - step if cy > box.cy else box.top + step
    return [(box.right if cx > box.cx else box.left, y), (cx, y), corner]


def route_edges(sizes, centers, groups) -> dict[tuple[str, str], list[tuple[float, float]]]:
    """Rechtwinklige Wege aller nicht rekursiven Kanten je `(entität, raute)`.

    Die Suche bewertet genau diese Wege, die Zeichnung zeichnet sie: So sieht die
    Bewertung dasselbe wie das Blatt. Rauten eines Fächers, die nicht auf Höhe der Entität
    liegen, erreicht ein L aus Ober- oder Unterseite; äußere Rauten setzen weiter innen an,
    so umschließen ihre L die inneren, ohne sie zu kreuzen.

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
                corner, horizontal = _corner_for(sizes[relation], centers[relation], centers[entity], centers[other], taken)
                taken.append(corner)
                routes[(entity, relation)] = _orthogonal(Box(*centers[entity], *sizes[entity]), corner, horizontal, inset)
    return routes


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


def _hang_recursive(model, centers, recursive) -> None:
    """Rekursive Rauten unter oder über ihre Entität, weg von deren übrigen Beziehungen."""
    for entity, relation in recursive:
        x, y = centers[entity]
        others = [centers[link.relation][1] for link in model.links if link.entity == entity and link.relation in centers and link.relation != relation]
        side = -1 if others and sum(others) / len(others) > y else 1
        centers[relation] = (x, y + side * (ENTITY_HEIGHT / 2 + RECURSIVE_DROP + DIAMOND_HEIGHT / 2))


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
    """Ordnet das ER-Diagramm flach an: wenige Zeilen, keine Kanten durch Formen, wenige Kreuzungen.

    Probiert ein bis `_MAX_ROWS` Zeilen, jeweils mit einer freien Spalte als Spielraum, und
    Startreihenfolgen aus Breitensuche und Schreibreihenfolge; die günstigste Belegung gewinnt.

    Returns:
        `Layout` mit Mittelpunkten aller Entitäten und Rauten; der Ursprung liegt an der
        linken oberen Ecke des freigehaltenen Platzes, Ränder fügt der Aufrufer hinzu.
    """
    plan, recursive = _plan(model)
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
    layout = _geometry(plan, best[1])
    centers = dict(layout.centers)
    _hang_recursive(model, centers, recursive)
    return Layout(centers, layout.width, layout.height)
