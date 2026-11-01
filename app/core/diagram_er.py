"""`:::erdiagram`: ER-Diagramm nach GO Informatik S. 8.

Syntax (dieselben Beziehungszeilen wie beim Klassendiagramm):

    entität Klasse
        __Bezeichnung__
        Klassenraum
    Klasse 1 - gehoertZu - n Schueler
        seitSchuljahr

Gestalt: Entitäten als Rechtecke, Beziehungen als Rauten, Attribute als Ovale,
Schlüssel unterstrichen (vorhandenes `__…__`), Kardinalitäten an den Kanten. Die
Attribute liegen rings um ihren Knoten dort, wo keine Kante verläuft.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .diagram_edges import parse_edge_line
from .diagram_layout_tree import free_layout
from .diagram_route import Box, box_exit, diamond_exit
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell

_HEADER_RE = re.compile(r"^entität\s+(.+)$", re.IGNORECASE)
_CARDINALITY = r"(?:\d+|[a-z]|\*|[%§&]\{[^}]*\})"
_LEFT_END_RE = re.compile(rf"^(.+?)\s+({_CARDINALITY})$")
_RIGHT_END_RE = re.compile(rf"^({_CARDINALITY})\s+(.+)$")
_ENTITY_HEIGHT = 32.0
_DIAMOND_HEIGHT = 42.0
_OVAL_HEIGHT = 28.0
_RING_GAP = 15.0
_CARD_DISTANCE = 13.0
_MARGIN = 10.0
_ANGLE_STEPS = 16
_RECURSIVE_DROP = 34.0
"""Abstand einer rekursiven Raute von ihrer Entität."""
_MAX_RINGS = 6
_SEGMENT_SAMPLES = 24


@dataclass
class ErNode:
    """Entität (`diamond=False`) oder Beziehung (`diamond=True`) mit ihren Attributen."""

    name: str
    title: Cell
    diamond: bool = False
    attributes: list[Cell] = field(default_factory=list)
    declared: bool = True


@dataclass(frozen=True)
class ErLink:
    """Kante zwischen Entität und Beziehungsraute; `cardinality` steht an der Entität."""

    entity: str
    relation: str
    cardinality: Cell | None


@dataclass
class ErModel:
    """Geparstes ER-Diagramm."""

    nodes: dict[str, ErNode] = field(default_factory=dict)
    links: list[ErLink] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Leer heißt: nichts zu zeichnen."""
        return bool(self.nodes)


def _split_end(text: str, pattern: re.Pattern, name_group: int, card_group: int) -> tuple[str, str]:
    """Trennt Name und Kardinalität eines Beziehungsendes; ohne Kardinalität bleibt sie leer."""
    match = pattern.match(text)
    return (match.group(name_group), match.group(card_group)) if match else (text, "")


def _add_relation(model: ErModel, source, names, issues) -> ErNode | None:
    """Legt Raute und Kanten für `A 1 - rel - n B` an."""
    if len(names) != 3:
        issues.append(ParseIssue("ER002", "error", source.number, "Erwartet `entität Name` oder `A 1 - beziehung - n B`."))
        return None
    left, left_card = _split_end(names[0], _LEFT_END_RE, 1, 2)
    right, right_card = _split_end(names[2], _RIGHT_END_RE, 2, 1)
    key = f"{names[1]}#{source.number}"
    node = ErNode(key, make_cell(names[1], source.show), diamond=True)
    model.nodes[key] = node
    for entity, card in ((left, left_card), (right, right_card)):
        if entity not in model.nodes:
            model.nodes[entity] = ErNode(entity, make_cell(entity), declared=False)
        model.links.append(ErLink(entity, key, make_cell(card, source.show) if card else None))
    return node


def parse(content) -> tuple[ErModel, list[ParseIssue]]:
    """Parst den Blockinhalt fehlertolerant (`ER002`-`ER004`)."""
    model = ErModel()
    issues: list[ParseIssue] = []
    current: ErNode | None = None
    for source in iter_source_lines(content):
        if source.width:
            if current is None:
                issues.append(ParseIssue("ER003", "error", source.number, "Eingerücktes Attribut ohne Entität oder Beziehung darüber."))
            else:
                current.attributes.append(make_cell(source.text, source.show))
            continue
        header = _HEADER_RE.match(source.text)
        if header:
            name = header.group(1).strip()
            if name in model.nodes and model.nodes[name].declared:
                issues.append(ParseIssue("ER004", "error", source.number, f"`{name}` ist schon definiert."))
            current = ErNode(name, make_cell(name, source.show))
            model.nodes[name] = current
            continue
        edge = parse_edge_line(source.text, ("-",))
        if edge is None:
            issues.append(ParseIssue("ER002", "error", source.number, "Erwartet `entität Name` oder `A 1 - beziehung - n B`."))
            current = None
            continue
        current = _add_relation(model, source, edge.names, issues)
    return model, issues


def check(collect, _options, model: ErModel) -> None:
    """GO-Prüfungen: Kardinalitäten und Schlüsselattribute sind im Normalfall Pflicht."""
    for node in model.nodes.values():
        if node.diamond:
            continue
        if not node.declared:
            collect.add("ER005", f"`{node.name}` kommt nur in einer Beziehung vor und hat keine Attribute.", anchor=f"ER005:{node.name}")
        elif not any("__" in cell.text for cell in node.attributes):
            collect.add("ER006", f"`{node.name}` hat kein Schlüsselattribut (`__Name__`, GO).", anchor=f"ER006:{node.name}")
    for link in model.links:
        if link.cardinality is None:
            collect.add("ER007", f"An der Kante zu `{link.entity}` fehlt die Kardinalität (GO).", anchor=f"ER007:{link.relation}:{link.entity}")
    linked = {link.entity for link in model.links}
    for node in model.nodes.values():
        if not node.diamond and node.name not in linked:
            collect.add("ER008", f"`{node.name}` hat keine Beziehung.", anchor=f"ER008:{node.name}")
        names = [cell.text.replace("__", "").strip() for cell in node.attributes]
        for name in {n for n in names if names.count(n) > 1}:
            collect.add("ER009", f"Das Attribut `{name}` steht bei `{node.title.text}` doppelt.", anchor=f"ER009:{node.name}:{name}")


def _shape_size(node: ErNode) -> tuple[float, float]:
    """Größe von Rechteck oder Raute ohne die Attribute."""
    width = text_width(node.title.text)
    return (width * 1.5 + 28, _DIAMOND_HEIGHT) if node.diamond else (max(width + 22, 64.0), _ENTITY_HEIGHT)


def _oval_size(cell: Cell) -> tuple[float, float]:
    """Größe eines Attribut-Ovals."""
    return text_width(cell.text.replace("__", "")) + 22, _OVAL_HEIGHT


def _halo(node: ErNode, recursive_width: float) -> tuple[float, float]:
    """Äußere Größe inklusive Attributring und rekursiver Raute (`recursive_width` > 0).

    Das Layout rechnet damit, damit nichts kollidiert.
    """
    width, height = _shape_size(node)
    if recursive_width:
        width = max(width, recursive_width + width / 3)
        height += 2 * (_RECURSIVE_DROP + _DIAMOND_HEIGHT)
    if not node.attributes:
        return width, height
    widest = max(_oval_size(cell)[0] for cell in node.attributes)
    return width + 2 * (widest + _RING_GAP), height + 2 * (_OVAL_HEIGHT + _RING_GAP)


def _hits_segment(rect, segment) -> bool:
    """Prüft, ob die Strecke das Rechteck `(x, y, breite, höhe)` schneidet (Abtastung)."""
    (x1, y1), (x2, y2) = segment
    for step in range(_SEGMENT_SAMPLES + 1):
        share = step / _SEGMENT_SAMPLES
        if abs(x1 + (x2 - x1) * share - rect[0]) < rect[2] / 2 + 2 and abs(y1 + (y2 - y1) * share - rect[1]) < rect[3] / 2 + 2:
            return True
    return False


def _overlap(a, b) -> bool:
    """Prüft, ob sich zwei Rechtecke `(x, y, breite, höhe)` um den Mittelpunkt schneiden."""
    return abs(a[0] - b[0]) < (a[2] + b[2]) / 2 + 2 and abs(a[1] - b[1]) < (a[3] + b[3]) / 2 + 2


def _place_attributes(node: ErNode, center, blocked_angles, placed, segments) -> list[tuple[Cell, float, float, float]]:
    """Verteilt Attribute auf einen Ring; freie Winkel zuerst, weit weg von den Kanten.

    Findet sich auf dem Ring kein freier Platz, rückt der Ring nach außen. Nach
    `_MAX_RINGS` Versuchen zählt nur noch der Abstand zu anderen Formen.

    Returns:
        `(zelle, x, y, breite)` je Attribut.
    """
    shape_width, shape_height = _shape_size(node)
    result = []
    used = list(blocked_angles)
    for cell in node.attributes:
        width, height = _oval_size(cell)
        ring = 1.0
        chosen = None
        while chosen is None:
            rx = (shape_width + width) / 2 + _RING_GAP * ring
            ry = (shape_height + height) / 2 + _RING_GAP * ring
            candidates = []
            for step in range(_ANGLE_STEPS):
                angle = 2 * math.pi * step / _ANGLE_STEPS - math.pi / 2
                x, y = center[0] + rx * math.cos(angle), center[1] + ry * math.sin(angle)
                rect = (x, y, width, height)
                if any(_overlap(rect, other) for other in placed):
                    continue
                if ring <= _MAX_RINGS and any(_hits_segment(rect, segment) for segment in segments):
                    continue
                clearance = min((abs(math.atan2(math.sin(angle - a), math.cos(angle - a))) for a in used), default=math.pi)
                candidates.append((-clearance, step, angle, x, y))
            if candidates:
                _score, _step, angle, x, y = min(candidates)
                chosen = (x, y, angle)
            else:
                ring += 1.0
        x, y, angle = chosen
        used.append(angle)
        placed.append((x, y, width, height))
        result.append((cell, x, y, width))
    return result


def _draw_cardinality(canvas: Canvas, cell: Cell, start, end) -> None:
    """Kardinalität nahe der Entität, seitlich neben der Kante."""
    length = math.hypot(end[0] - start[0], end[1] - start[1]) or 1.0
    ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
    x = start[0] + ux * _CARD_DISTANCE - uy * 9
    y = start[1] + uy * _CARD_DISTANCE + ux * 9
    canvas.label(cell, x, y, text_width(cell.text) + 8)


def _link_route(model: ErModel, link: ErLink, centers, order: int, recursive: bool) -> list[tuple[float, float]]:
    """Punkte einer Kante von der Entität zur Raute; rekursiv als rechtwinklige Linie."""
    entity, relation = model.nodes[link.entity], model.nodes[link.relation]
    ex, ey = centers[link.entity]
    rx, ry = centers[link.relation]
    entity_w, entity_h = _shape_size(entity)
    relation_w, relation_h = _shape_size(relation)
    if recursive:
        sign = -1 if order == 0 else 1
        start = (ex + sign * entity_w / 3, ey + (entity_h / 2 if ry > ey else -entity_h / 2))
        end = (rx + sign * relation_w / 2, ry)
        return [start, (start[0], end[1]), end]
    return [box_exit(Box(ex, ey, entity_w, entity_h), (rx, ry)), diamond_exit(rx, ry, relation_w / 2, relation_h / 2, (ex, ey))]


def _all_routes(model: ErModel, centers) -> list[tuple[ErLink, list[tuple[float, float]]]]:
    """Alle Kanten mit ihren Punkten; zwei Kanten derselben Raute zur selben Entität sind rekursiv."""
    routes = []
    seen: dict[tuple[str, str], int] = {}
    for link in model.links:
        pair = (link.entity, link.relation)
        order = seen.get(pair, 0)
        seen[pair] = order + 1
        recursive = pair in _recursive_pairs(model)
        routes.append((link, _link_route(model, link, centers, order, recursive)))
    return routes


def _recursive_pairs(model: ErModel) -> set[tuple[str, str]]:
    """Paare aus Entität und Raute, die zweimal vorkommen (rekursive Beziehung)."""
    seen: set[tuple[str, str]] = set()
    repeated: set[tuple[str, str]] = set()
    for link in model.links:
        pair = (link.entity, link.relation)
        (repeated if pair in seen else seen).add(pair)
    return repeated


def _attribute_blocks(routes) -> dict[str, list[float]]:
    """Winkel, in denen vom Knoten aus Kanten laufen; dort liegen keine Attribute."""
    blocked: dict[str, list[float]] = {}
    for link, points in routes:
        for name, first, second in ((link.entity, points[0], points[1]), (link.relation, points[-1], points[-2])):
            blocked.setdefault(name, []).append(math.atan2(second[1] - first[1], second[0] - first[0]))
    return blocked


def _layout_centers(model: ErModel):
    """Freies Layout; rekursive Rauten kommen danach fest neben ihre Entität, weg von den übrigen Kanten."""
    recursive = _recursive_pairs(model)
    relation_of = {entity: relation for entity, relation in recursive}
    hanging = {relation for _entity, relation in recursive}
    sizes = {}
    for name, node in model.nodes.items():
        if name in hanging:
            continue
        loop = relation_of.get(name)
        sizes[name] = _halo(node, _shape_size(model.nodes[loop])[0] if loop else 0.0)
    edges = [(link.entity, link.relation) for link in model.links if link.relation not in hanging]
    layout = free_layout(sizes, edges, spacing=70.0, margin=_MARGIN, gap=8.0)
    centers = dict(layout.centers)
    for entity, relation in recursive:
        x, y = centers[entity]
        others = [centers[link.relation][1] for link in model.links if link.entity == entity and link.relation not in hanging]
        side = -1 if others and sum(others) / len(others) > y else 1
        centers[relation] = (x, y + side * (_shape_size(model.nodes[entity])[1] / 2 + _RECURSIVE_DROP + _DIAMOND_HEIGHT / 2))
    return centers, layout


def render(options, content, include_solutions=False) -> str:
    """Rendert das ER-Diagramm; ein leerer Block ergibt nichts."""
    model, _issues = parse(content)
    if not model:
        return ""
    centers, layout = _layout_centers(model)
    routes = _all_routes(model, centers)
    blocked = _attribute_blocks(routes)
    segments = [pair for _link, points in routes for pair in zip(points, points[1:])]
    placed = [(centers[name][0], centers[name][1], *_shape_size(node)) for name, node in model.nodes.items()]
    ovals = []
    for name, node in model.nodes.items():
        for cell, x, y, width in _place_attributes(node, centers[name], blocked.get(name, []), placed, segments):
            ovals.append((name, cell, x, y, width))

    canvas = Canvas(include_solutions)
    for link, points in routes:
        canvas.polyline(points)
        if link.cardinality is not None:
            _draw_cardinality(canvas, link.cardinality, points[0], points[1])
    for owner, _cell, x, y, _width in ovals:
        node_w, node_h = _shape_size(model.nodes[owner])
        if model.nodes[owner].diamond:
            start = diamond_exit(*centers[owner], node_w / 2, node_h / 2, (x, y))
        else:
            start = box_exit(Box(*centers[owner], node_w, node_h), (x, y))
        canvas.line(*start, x, y)
    for name, node in model.nodes.items():
        cx, cy = centers[name]
        width, height = _shape_size(node)
        if node.diamond:
            canvas.polygon([(cx, cy - height / 2), (cx + width / 2, cy), (cx, cy + height / 2), (cx - width / 2, cy)], "diagram-tone-4")
        else:
            canvas.rect(cx, cy, width, height, css="diagram-tone-3")
        canvas.label(node.title, cx, cy, width)
    for _owner, cell, x, y, width in ovals:
        canvas.ellipse(x, y, width / 2, _OVAL_HEIGHT / 2, "diagram-tone-1" if "__" in cell.text else "diagram-shape")
        canvas.label(cell, x, y, width, LINE_HEIGHT)
    right = max(x + w / 2 for x, _y, w, _h in placed) + _MARGIN
    bottom = max(y + h / 2 for _x, y, _w, h in placed) + _MARGIN
    return canvas.finish("erdiagram", options, max(right, layout.width), max(bottom, layout.height))
