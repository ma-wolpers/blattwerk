"""`:::classdiagram`: Klassendiagramm und Objektkarten nach GO Informatik S. 7.

Syntax:

    klasse Person
        - id: Ganzzahl
        ...
        c Person()
        + getName(): Zeichenkette
    Schueler -|> Person
    Person - Adresse
    objekt p42 : Person
        id = 123456789

Gestalt: Fächer für Name, Attribute und Operationen, Oberklasse über der Unterklasse,
hohles Dreieck an der Oberklasse, Assoziationen als einfache rechtwinklige Linien.
Eine Klasse, die nur in einer Beziehung vorkommt, erscheint als leeres Kästchen, der
Validator weist darauf hin. Objektkarten stehen mit runden Ecken unter den Klassen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .diagram_edges import parse_edge_line
from .diagram_layout import layered_layout
from .diagram_route import Box, box_self_loop, orthogonal_route
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell

_OPERATORS = ("-|>", "-")
_HEADER_RE = re.compile(r"^(klasse|objekt)\s+(.+)$", re.IGNORECASE)
_MEMBER_PREFIX_RE = re.compile(r"^(?:[-+]\s|c\s|\.\.\.$)")
_MEMBER_NAME_RE = re.compile(r"^[-+]\s*")
_PADDING = 7.0
_MIN_WIDTH = 70.0
_ROW_GAP = 28.0
_MARGIN = 34.0
"""Platz links für Selbstassoziationen."""


@dataclass
class ClassNode:
    """Eine Klasse oder Objektkarte; `compartments` sind die Fächer unter dem Namen."""

    name: str
    title: Cell
    is_object: bool = False
    attributes: list[Cell] = field(default_factory=list)
    operations: list[Cell] = field(default_factory=list)
    declared: bool = True

    @property
    def compartments(self) -> list[list[Cell]]:
        """Nicht leere Fächer; Klassen zeigen das Attributfach immer."""
        if self.is_object:
            return [self.attributes] if self.attributes else []
        return [self.attributes] + ([self.operations] if self.operations else [])


@dataclass(frozen=True)
class Relation:
    """Beziehung zweier Klassen; `inherits` ist Vererbung (`source` erbt von `target`)."""

    line: int
    source: str
    target: str
    inherits: bool
    label: Cell | None


@dataclass
class ClassModel:
    """Geparstes Klassendiagramm."""

    nodes: dict[str, ClassNode] = field(default_factory=dict)
    relations: list[Relation] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Leer heißt: nichts zu zeichnen."""
        return bool(self.nodes)


def _is_operation(text: str) -> bool:
    """Operationen haben Klammern oder das Konstruktor-Präfix `c`."""
    return "(" in text or text.startswith("c ")


def _add_member(node: ClassNode, text: str, show: str) -> None:
    """Sortiert eine Zeile ins passende Fach; `...` bleibt im aktuellen Fach."""
    cell = make_cell(text, show)
    if node.is_object or not (node.operations or _is_operation(text)):
        node.attributes.append(cell)
    else:
        node.operations.append(cell)


def _ensure_node(model: ClassModel, name: str) -> None:
    """Legt eine nur in Beziehungen genannte Klasse als leeres Kästchen an."""
    if name not in model.nodes:
        model.nodes[name] = ClassNode(name, make_cell(name), declared=False)


def parse(content) -> tuple[ClassModel, list[ParseIssue]]:
    """Parst den Blockinhalt fehlertolerant (`CD002`, `CD003`, `CD004`)."""
    model = ClassModel()
    issues: list[ParseIssue] = []
    current: ClassNode | None = None
    for source in iter_source_lines(content):
        if source.width:
            if current is None:
                issues.append(ParseIssue("CD003", "error", source.number, "Eingerückte Zeile ohne `klasse` oder `objekt` darüber."))
            else:
                _add_member(current, source.text, source.show)
            continue
        current = None
        header = _HEADER_RE.match(source.text)
        if header:
            kind, title = header.group(1).lower(), header.group(2).strip()
            name = title.split(":")[0].strip()
            if name in model.nodes and model.nodes[name].declared:
                issues.append(ParseIssue("CD004", "error", source.number, f"`{name}` ist schon definiert."))
            current = ClassNode(name, make_cell(title, source.show), is_object=kind == "objekt")
            model.nodes[name] = current
            continue
        edge = parse_edge_line(source.text, _OPERATORS)
        if edge is None or len(edge.names) != 2:
            issues.append(ParseIssue("CD002", "error", source.number, "Erwartet `klasse Name`, `objekt name : Klasse`, `A -|> B` oder `A - B`."))
            continue
        for name in edge.names:
            _ensure_node(model, name)
        label = make_cell(edge.label, source.show) if edge.label else None
        model.relations.append(Relation(source.number, edge.names[0], edge.names[1], edge.operators[0] == "-|>", label))
    return model, issues


def check(collect, _options, model: ClassModel) -> None:
    """GO-Prüfungen: Sichtbarkeit bei Mitgliedern, unbeschriftete Assoziationen, unbekannte Klassen."""
    for node in model.nodes.values():
        if not node.declared:
            collect.add("CD005", f"`{node.name}` kommt nur in einer Beziehung vor und erscheint als leere Klasse.", anchor=f"CD005:{node.name}")
        if node.is_object:
            continue
        for cell in node.attributes + node.operations:
            if not _MEMBER_PREFIX_RE.match(cell.text):
                collect.add("CD006", f"In `{node.name}` fehlt bei `{cell.text}` die Sichtbarkeit `+` oder `-` (GO).", anchor=f"CD006:{node.name}:{cell.text}")
    for relation in model.relations:
        if relation.label is not None:
            collect.add("CD007", "Assoziationen sind laut GO unspezifiziert; die Beschriftung kann entfallen.", anchor=f"CD007:{relation.line}")
    _check_objects(collect, model)
    _check_inheritance(collect, model)
    _check_members(collect, model)


def _inherited_attributes(model: ClassModel, name: str) -> tuple[set[str], bool]:
    """Attributnamen einer Klasse samt Oberklassen; `True`, wenn eine davon `...` enthält."""
    names: set[str] = set()
    open_ended = False
    pending = [name]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current in seen or current not in model.nodes:
            continue
        seen.add(current)
        for cell in model.nodes[current].attributes:
            if cell.text.strip() == "...":
                open_ended = True
            else:
                names.add(_MEMBER_NAME_RE.sub("", cell.text).split(":")[0].strip())
        pending.extend(r.target for r in model.relations if r.inherits and r.source == current)
    return names, open_ended


def _check_objects(collect, model: ClassModel) -> None:
    """Objektkarten müssen zu ihrer Klasse passen (`CD008`, `CD009`)."""
    for node in model.nodes.values():
        if not node.is_object:
            continue
        class_name = node.title.text.partition(":")[2].strip()
        if not class_name:
            continue
        if class_name not in model.nodes or model.nodes[class_name].is_object:
            collect.add("CD008", f"Die Klasse `{class_name}` von `{node.name}` steht nicht im Diagramm.", anchor=f"CD008:{node.name}")
            continue
        known, open_ended = _inherited_attributes(model, class_name)
        if open_ended:
            continue
        for cell in node.attributes:
            field_name = cell.text.partition("=")[0].strip()
            if field_name != "..." and field_name not in known:
                collect.add("CD009", f"`{field_name}` in `{node.name}` ist kein Attribut von `{class_name}`.", anchor=f"CD009:{node.name}:{field_name}")


def _check_inheritance(collect, model: ClassModel) -> None:
    """Vererbung darf keinen Kreis bilden (`CD010`, Fehler)."""
    parents: dict[str, list[str]] = {}
    for relation in model.relations:
        if relation.inherits:
            parents.setdefault(relation.source, []).append(relation.target)
    for start in parents:
        pending = list(parents[start])
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current == start:
                collect.add("CD010", f"`{start}` erbt über einen Kreis von sich selbst.", severity="error", anchor=f"CD010:{start}")
                break
            if current not in seen:
                seen.add(current)
                pending.extend(parents.get(current, []))


def _node_size(node: ClassNode) -> tuple[float, float]:
    """Breite und Höhe aus Texten und Fächern."""
    rows = [cell.text for compartment in node.compartments for cell in compartment]
    title_width = text_width(node.title.text) * (1.0 if node.is_object else 1.12)
    width = max([_MIN_WIDTH, title_width] + [text_width(text) for text in rows]) + 2 * _PADDING
    height = LINE_HEIGHT + 2 * _PADDING
    for compartment in node.compartments:
        height += max(1, len(compartment)) * LINE_HEIGHT + _PADDING
    return width, height


def _draw_node(canvas: Canvas, node: ClassNode, box: Box) -> None:
    """Zeichnet Rahmen, Name und Fächer."""
    if node.is_object:
        canvas.rect(box.cx, box.cy, box.width, box.height, radius=8.0, css="diagram-tone-2")
    else:
        canvas.rect(box.cx, box.cy, box.width, box.height, css="diagram-shape diagram-lift")
        canvas.rect(box.cx, box.top + _PADDING + LINE_HEIGHT / 2, box.width, LINE_HEIGHT + 2 * _PADDING, css=f"{'diagram-tone-3' if node.declared else 'diagram-tone-1'} diagram-flat diagram-keep-tint")
    cursor = box.top + _PADDING + LINE_HEIGHT / 2
    canvas.label(node.title, box.cx, cursor, box.width, weight="" if node.is_object else "bold")
    cursor += LINE_HEIGHT / 2 + _PADDING
    for compartment in node.compartments:
        canvas.line(box.left, cursor, box.right, cursor)
        cursor += _PADDING / 2
        for cell in compartment:
            canvas.label(cell, box.cx, cursor + LINE_HEIGHT / 2, box.width - 2 * _PADDING, align="left")
            cursor += LINE_HEIGHT
        if not compartment:
            cursor += LINE_HEIGHT
        cursor += _PADDING / 2


def _draw_relation(canvas: Canvas, relation: Relation, boxes: dict[str, Box]) -> None:
    """Vererbung mit hohlem Dreieck an der Oberklasse, sonst eine einfache Linie."""
    start, end = boxes[relation.source], boxes[relation.target]
    points = box_self_loop(start) if relation.source == relation.target else orthogonal_route(start, end)
    canvas.polyline(points)
    if relation.inherits and relation.source != relation.target:
        canvas.arrow(points[-1], points[-2], "hollow")
    if relation.label is not None:
        middle = points[len(points) // 2]
        canvas.label(relation.label, middle[0], middle[1] - LINE_HEIGHT / 2, text_width(relation.label.text) + 8)


def render(options, content, include_solutions=False) -> str:
    """Rendert das Klassendiagramm; ein leerer Block ergibt nichts."""
    model, _issues = parse(content)
    if not model:
        return ""
    sizes = {name: _node_size(node) for name, node in model.nodes.items()}
    classes = {name: sizes[name] for name, node in model.nodes.items() if not node.is_object}
    objects = {name: sizes[name] for name, node in model.nodes.items() if node.is_object}
    rank_edges = [(r.target, r.source) for r in model.relations if r.inherits and r.source in classes and r.target in classes]
    order_edges = [(r.source, r.target) for r in model.relations if not r.inherits and r.source in classes and r.target in classes]
    layout = layered_layout(classes, rank_edges, order_edges)

    boxes = {name: Box(x + _MARGIN, y, *sizes[name]) for name, (x, y) in layout.centers.items()}
    width = layout.width + _MARGIN
    height = layout.height
    if objects:
        cursor = _MARGIN
        tallest = max(size[1] for size in objects.values())
        for name, (node_width, node_height) in objects.items():
            boxes[name] = Box(cursor + node_width / 2, height + _ROW_GAP / 2 + node_height / 2, node_width, node_height)
            cursor += node_width + _ROW_GAP
        width = max(width, cursor)
        height += _ROW_GAP + tallest
    canvas = Canvas(include_solutions)
    for relation in model.relations:
        _draw_relation(canvas, relation, boxes)
    for name, node in model.nodes.items():
        _draw_node(canvas, node, boxes[name])
    return canvas.finish("classdiagram", options, width, height)


def _member_name(cell: Cell) -> str:
    """Name eines Mitglieds ohne Sichtbarkeit und Konstruktor-Präfix."""
    return re.split(r"[(:]", re.sub(r"^(?:[-+]\s*|c\s+)", "", cell.text), maxsplit=1)[0].strip()


def _check_members(collect, model: ClassModel) -> None:
    """Mitglieder gegen Klasse und Beziehungen (`CD011`-`CD014`).

    Doppelte Attribute und falsche Konstruktornamen sind Versehen. Ein Attribut, dessen Typ
    eine andere Klasse des Diagramms nennt, verlangt laut GO eine Beziehung dorthin.
    """
    linked = {frozenset((r.source, r.target)) for r in model.relations}
    for node in model.nodes.values():
        if node.is_object:
            continue
        names = [_member_name(cell) for cell in node.attributes if cell.text.strip() != "..."]
        for name in {n for n in names if names.count(n) > 1}:
            collect.add("CD011", f"`{name}` steht in `{node.name}` doppelt.", anchor=f"CD011:{node.name}:{name}")
        for cell in node.operations:
            if cell.text.startswith("c ") and _member_name(cell) != node.name:
                collect.add("CD012", f"Der Konstruktor `{_member_name(cell)}` passt nicht zur Klasse `{node.name}`.", severity="error", anchor=f"CD012:{node.name}:{cell.text}")
        for cell in node.attributes:
            _name, _colon, kind = cell.text.partition(":")
            for other in model.nodes.values():
                if other.is_object or not re.search(rf"\b{re.escape(other.name)}\b", kind):
                    continue
                if frozenset((node.name, other.name)) not in linked:
                    collect.add("CD013", f"`{node.name}` nutzt `{other.name}` als Typ, aber es gibt keine Beziehung `{node.name} - {other.name}`.", anchor=f"CD013:{node.name}:{other.name}")
    for relation in model.relations:
        if relation.inherits and (model.nodes[relation.source].is_object or model.nodes[relation.target].is_object):
            collect.add("CD014", f"Objektkarten erben nicht: `{relation.source} -|> {relation.target}`.", severity="error", anchor=f"CD014:{relation.line}")
