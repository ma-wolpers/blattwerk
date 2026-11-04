"""`:::erdiagram`: ER-Diagramm nach GO Informatik S. 8.

Syntax (dieselben Beziehungszeilen wie beim Klassendiagramm):

    entität Klasse
        __Bezeichnung__
        Klassenraum
    Klasse 1 - gehoertZu - n Schueler
        seitSchuljahr

Gestalt: Entitäten als Rechtecke, Beziehungen als Rauten, Attribute als Ovale,
Schlüssel unterstrichen (vorhandenes `__…__`), Kardinalitäten an den Kanten. Die
Anordnung (`diagram_er_layout`) hält das Diagramm flach und vermeidet Kreuzungen. Danach
kommen die Beschriftungen: Kardinalitäten neben ihre Kante, wo nichts anderes steht,
Attribute rings um ihren Knoten dort, wo weder eine Kante noch eine andere Beschriftung
liegt und ihre Verbindungslinie keine Kante kreuzt.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from functools import lru_cache

from .diagram_edges import parse_edge_line
from .diagram_er_layout import arrange, recursive_pairs, relation_groups
from .diagram_er_route import route_edges
from .diagram_er_shapes import RING_GAP, attribute_box, oval_size, shape_size, title_box
from .diagram_layout import Layout
from .diagram_route import Box, box_exit, diamond_corner, rects_overlap, segment_hits_rect, segments_cross
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell

_HEADER_RE = re.compile(r"^entität\s+(.+)$", re.IGNORECASE)
_CARDINALITY = r"(?:\d+|[a-z]|\*|[%§&]\{[^}]*\})"
_LEFT_END_RE = re.compile(rf"^(.+?)\s+({_CARDINALITY})$")
_RIGHT_END_RE = re.compile(rf"^({_CARDINALITY})\s+(.+)$")
_CARD_DISTANCE = 13.0
_CARD_SIDE = 9.0
"""Abstand der Kardinalität seitlich von ihrer Kante."""
_MARGIN = 10.0
_ANGLE_STEPS = 24
_MAX_RINGS = 6


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
        edge = parse_edge_line(source.text, ("-",), labels=False)
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


def _attribute_blocked(rect, placed, segments) -> bool:
    """Ein Oval darf nie etwas überdecken, auch keine Kante: Sie verschwände dahinter."""
    return any(rects_overlap(rect, other, 2) for other in placed) or any(segment_hits_rect(segment, rect, 2) for segment in segments)


def _attribute_conflicts(rect, connector, own, placed, segments, connectors) -> int:
    """Zählt, was ein Attribut-Oval samt Verbindungslinie an diesem Platz stört.

    Gezählt werden Kanten, die die Verbindungslinie kreuzen, gekreuzte andere
    Verbindungslinien und fremde Formen oder Beschriftungen, an denen die Verbindungslinie
    zu knapp vorbeiläuft. Läuft sie mitten hindurch, zählt das dreifach: Eine Linie hinter
    einem anderen Oval sähe aus wie ein zusammengesetztes Attribut. Überdeckungen und
    Kanten unter dem Oval schließt der Aufrufer vorher ganz aus (`_attribute_blocked`).
    """
    edges = sum(2 for segment in segments if segments_cross(connector, segment))
    lines = sum(2 for other in connectors if segments_cross(connector, other))
    near = sum(
        3 if segment_hits_rect(connector, other) else 1
        for other in placed
        if other is not own and segment_hits_rect(connector, other, 6)
    )
    return edges + lines + near


def _place_attributes(node: ErNode, center, blocked_angles, placed, segments, connectors) -> list[tuple[Cell, float, float, float]]:
    """Verteilt Attribute auf einen Ring; freie Winkel zuerst, weit weg von den Kanten.

    Findet sich auf dem Ring kein störungsfreier Platz, rückt der Ring nach außen. Nach
    `_MAX_RINGS` Ringen gewinnt der Platz mit den wenigsten Störungen, möglichst weit
    innen; nur wenn auch der nicht existiert, geht es weiter nach außen. Plätze links und
    rechts gewinnen bei Gleichstand, weil sie das Diagramm nicht höher machen. Breite Ovale
    kommen zuerst an die Reihe, sie finden am schwersten Platz.

    Returns:
        `(zelle, x, y, breite)` je Attribut.
    """
    shape_width, shape_height = shape_size(node)
    own = next(rect for rect in placed if rect[:2] == center and rect[2:] == (shape_width, shape_height))
    result = []
    used = list(blocked_angles)
    for cell in sorted(node.attributes, key=lambda cell: -oval_size(cell)[0]):
        width, height = oval_size(cell)
        ring = 1
        chosen = None
        fallback = None
        while chosen is None:
            rx = (shape_width + width) / 2 + RING_GAP * ring
            ry = (shape_height + height) / 2 + RING_GAP * ring
            candidates = []
            for step in range(_ANGLE_STEPS):
                angle = 2 * math.pi * step / _ANGLE_STEPS - math.pi / 2
                x, y = center[0] + rx * math.cos(angle), center[1] + ry * math.sin(angle)
                if _attribute_blocked((x, y, width, height), placed, segments):
                    continue
                clearance = min((abs(math.atan2(math.sin(angle - a), math.cos(angle - a))) for a in used), default=math.pi)
                spot = (-round(clearance, 3), abs(math.sin(angle)), step, angle, x, y)
                conflicts = _attribute_conflicts((x, y, width, height), (center, (x, y)), own, placed, segments, connectors)
                if not conflicts:
                    candidates.append(spot)
                elif fallback is None or (conflicts, ring) < fallback[:2]:
                    fallback = (conflicts, ring, spot)
            if candidates:
                chosen = min(candidates)[-3:]
            elif ring >= _MAX_RINGS and fallback is not None:
                chosen = fallback[2][-3:]
            ring += 1
        angle, x, y = chosen
        used.append(angle)
        placed.append((x, y, width, height))
        connectors.append((center, (x, y)))
        result.append((cell, x, y, width))
    return result


def _cardinality_spot(cell: Cell, points, placed, segments) -> tuple[float, float, float, float]:
    """Platz der Kardinalität nahe der Entität, seitlich neben der Kante.

    Probiert beide Seiten der Kante und dann wachsende Abstände von der Entität, bis die
    Beschriftung weder andere Beschriftungen noch fremde Kanten berührt.

    Returns:
        `(x, y, breite, höhe)`; die Breite ist die des Texts.
    """
    start, end = points[0], points[1]
    length = math.hypot(end[0] - start[0], end[1] - start[1]) or 1.0
    ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
    width = text_width(cell.text)
    own = list(zip(points, points[1:]))
    spots = []
    for along in (_CARD_DISTANCE * step for step in range(1, 6)):
        for side in (1, -1):
            spots.append((start[0] + ux * along - uy * _CARD_SIDE * side, start[1] + uy * along + ux * _CARD_SIDE * side, width, LINE_HEIGHT - 4))
    for rect in spots:
        if not any(rects_overlap(rect, other, 3) for other in placed) and not any(segment_hits_rect(segment, rect, 1) for segment in segments if segment not in own):
            return rect
    return spots[0]


def _recursive_route(model: ErModel, link: ErLink, centers, order: int) -> list[tuple[float, float]]:
    """Rechteckige Schleife zur rekursiven Raute: aus der Entität senkrecht hinaus, waagerecht in die Ecke.

    Die erste Kante nimmt die linke, die zweite die rechte Rautenecke (GO).
    """
    ex, ey = centers[link.entity]
    rx, ry = centers[link.relation]
    entity_w, entity_h = shape_size(model.nodes[link.entity])
    relation_w = shape_size(model.nodes[link.relation])[0]
    sign = -1 if order == 0 else 1
    start = (ex + sign * entity_w / 3, ey + (entity_h / 2 if ry > ey else -entity_h / 2))
    end = (rx + sign * relation_w / 2, ry)
    return [start, (start[0], end[1]), end]


def _all_routes(model: ErModel, centers) -> list[tuple[ErLink, list[tuple[float, float]]]]:
    """Alle Kanten mit ihren Punkten; zwei Kanten derselben Raute zur selben Entität sind rekursiv."""
    sizes = {name: shape_size(node) for name, node in model.nodes.items()}
    straight = route_edges(sizes, centers, relation_groups(model))
    recursive = recursive_pairs(model)
    routes = []
    seen: dict[tuple[str, str], int] = {}
    for link in model.links:
        pair = (link.entity, link.relation)
        order = seen.get(pair, 0)
        seen[pair] = order + 1
        routes.append((link, _recursive_route(model, link, centers, order) if pair in recursive else straight[pair]))
    return routes


def _attribute_blocks(routes) -> dict[str, list[float]]:
    """Winkel, in denen vom Knoten aus Kanten laufen; dort liegen keine Attribute."""
    blocked: dict[str, list[float]] = {}
    for link, points in routes:
        for name, first, second in ((link.entity, points[0], points[1]), (link.relation, points[-1], points[-2])):
            blocked.setdefault(name, []).append(math.atan2(second[1] - first[1], second[0] - first[0]))
    return blocked


def _wrapped_label(canvas: Canvas, cell: Cell, cx, cy, shape_width: float, box: tuple[float, int]) -> None:
    """Beschriftung einer Form; mehrzeilig in der Breite der breitesten geschätzten Zeile.

    Einzeilig bleibt das Feld so breit wie die Form und bricht nie um.
    """
    text_width_, lines = box
    if lines == 1:
        canvas.label(cell, cx, cy, shape_width)
    else:
        canvas.label(cell, cx, cy, text_width_ + 6, lines * LINE_HEIGHT, wrap=True)


@lru_cache(maxsize=32)
def _arrangement(content: str) -> Layout:
    """Anordnung je Blockinhalt; Arbeitsblatt- und Lösungsfassung teilen sie.

    Die Suche ist der teure Teil des Renderns und hängt nur vom Inhalt ab. Aufrufer
    lesen das Ergebnis nur.
    """
    return arrange(parse(content)[0])


def render(options, content, include_solutions=False) -> str:
    """Rendert das ER-Diagramm; ein leerer Block ergibt nichts.

    Erst stehen alle Plätze fest (Formen, Kardinalitäten, Attribute), dann rückt alles
    so, dass die äußerste Beschriftung am Rand liegt: Ein Attribut, das nach außen
    ausweichen musste, wird so nie abgeschnitten.
    """
    model, _issues = parse(content)
    if not model:
        return ""
    centers = _arrangement(str(content or "")).centers
    routes = _all_routes(model, centers)
    segments = [pair for _link, points in routes for pair in zip(points, points[1:])]
    placed = [(*centers[name], *shape_size(node)) for name, node in model.nodes.items()]
    cards = []
    for link, points in routes:
        if link.cardinality is not None:
            rect = _cardinality_spot(link.cardinality, points, placed, segments)
            placed.append(rect)
            cards.append((link.cardinality, rect))
    blocked = _attribute_blocks(routes)
    connectors: list = []
    ovals = []
    for name, node in model.nodes.items():
        for cell, x, y, width in _place_attributes(node, centers[name], blocked.get(name, []), placed, segments, connectors):
            ovals.append((name, cell, x, y, width))

    left = min(x - w / 2 for x, _y, w, _h in placed) - _MARGIN
    top = min(y - h / 2 for _x, y, _w, h in placed) - _MARGIN
    canvas = Canvas(include_solutions)
    for _link, points in routes:
        canvas.polyline([(x - left, y - top) for x, y in points])
    taken_corners: dict[str, list[tuple[float, float]]] = {}
    for link, points in routes:
        taken_corners.setdefault(link.relation, []).append(points[-1])
    for owner, _cell, x, y, _width in ovals:
        node_w, node_h = shape_size(model.nodes[owner])
        if model.nodes[owner].diamond:
            start = diamond_corner(*centers[owner], node_w / 2, node_h / 2, (x, y), taken_corners.get(owner, ()))
        else:
            start = box_exit(Box(*centers[owner], node_w, node_h), (x, y))
        canvas.line(start[0] - left, start[1] - top, x - left, y - top)
    for name, node in model.nodes.items():
        cx, cy = centers[name][0] - left, centers[name][1] - top
        width, height = shape_size(node)
        if node.diamond:
            canvas.polygon([(cx, cy - height / 2), (cx + width / 2, cy), (cx, cy + height / 2), (cx - width / 2, cy)], "diagram-tone-4")
        else:
            canvas.rect(cx, cy, width, height, css="diagram-tone-3")
        _wrapped_label(canvas, node.title, cx, cy, width, title_box(node))
    for cell, (x, y, width, _height) in cards:
        canvas.label(cell, x - left, y - top, width + 8)
    for _owner, cell, x, y, width in ovals:
        height = oval_size(cell)[1]
        canvas.ellipse(x - left, y - top, width / 2, height / 2, "diagram-tone-1" if "__" in cell.text else "diagram-shape diagram-lift")
        _wrapped_label(canvas, cell, x - left, y - top, width, attribute_box(cell))
    right = max(x + w / 2 for x, _y, w, _h in placed) + _MARGIN
    bottom = max(y + h / 2 for _x, y, _w, h in placed) + _MARGIN
    return canvas.finish("erdiagram", options, right - left, bottom - top)
