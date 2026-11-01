"""`:::memorydiagram`: Speicherbild für Reihungen, Variablen, Referenzen, Stapel und Schlangen.

Syntax je Zeile:

    reihung r: 3, 5, 7
    variable x: 5
    referenz p -> r
    stapel s: 1, 2, 3
    schlange q: 1, 2, 3

Reihungen zeigen die Indizes, ein Stapel steht hochkant mit dem letzten Wert oben, eine
Schlange ist an beiden Enden offen. Werte dürfen Lücken sein (`%{5}`), mit `%` am
Zeilenanfang ist die ganze Zeile eine Lücke.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .diagram_edges import parse_edge_line
from .diagram_numbers import split_numbers
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell, plain_cell

_ENTRY_RE = re.compile(r"^(reihung|variable|stapel|schlange)\s+([^:]+?)\s*:\s*(.*)$", re.IGNORECASE)
_REFERENCE_RE = re.compile(r"^referenz\s+(.+)$", re.IGNORECASE)
_CELL_W, _CELL_H = 42.0, 26.0
_NAME_GAP = 10.0
_ROW_GAP = 22.0
_INDEX_H = 15.0
_MARGIN = 12.0
_ROUTE_GAP = 14.0
_ROUTE_STEP = 8.0
_QUEUE_STUB = 18.0
"""Pfeilstück an beiden Enden einer Schlange: rein links, raus rechts."""


@dataclass(frozen=True)
class Entry:
    """Ein Speicherobjekt; `kind` ist `reihung`, `variable`, `stapel` oder `schlange`."""

    line: int
    kind: str
    name: str
    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class Reference:
    """Referenzvariable `name`, die auf `target` zeigt."""

    line: int
    name: str
    target: str


@dataclass
class MemoryModel:
    """Objekte und Referenzen in Schreibreihenfolge (`order` mischt beide)."""

    order: list = field(default_factory=list)

    def __bool__(self) -> bool:
        """Leer heißt: nichts zu zeichnen."""
        return bool(self.order)


def parse(content) -> tuple[MemoryModel, list[ParseIssue]]:
    """Parst die Zeilen fehlertolerant (`MM002`)."""
    model = MemoryModel()
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        reference = _REFERENCE_RE.match(source.text)
        if reference:
            edge = parse_edge_line(reference.group(1), ("->",))
            if edge is None or len(edge.names) != 2:
                issues.append(ParseIssue("MM002", "error", source.number, "Erwartet `referenz p -> r`."))
                continue
            model.order.append(Reference(source.number, edge.names[0], edge.names[1]))
            continue
        entry = _ENTRY_RE.match(source.text)
        if not entry:
            issues.append(ParseIssue("MM002", "error", source.number, "Erwartet `reihung r: 1, 2`, `variable x: 5`, `referenz p -> r`, `stapel s: 1, 2` oder `schlange q: 1, 2`."))
            continue
        cells = tuple(make_cell(part, source.show) for part in split_numbers(entry.group(3)))
        model.order.append(Entry(source.number, entry.group(1).lower(), entry.group(2), cells))
    return model, issues


def check(collect, _options, model: MemoryModel) -> None:
    """Prüft Referenzziele (`MM003`), doppelte Namen (`MM004`) und einzelne Variablen (`MM005`)."""
    names: set[str] = set()
    for item in model.order:
        if item.name in names:
            collect.add("MM004", f"`{item.name}` kommt doppelt vor.", severity="error", anchor=f"MM004:{item.name}")
        names.add(item.name)
        if isinstance(item, Entry) and item.kind == "variable" and len(item.cells) != 1:
            collect.add("MM005", f"Die Variable `{item.name}` braucht genau einen Wert.", severity="error", anchor=f"MM005:{item.name}")
    for item in model.order:
        if isinstance(item, Reference) and item.target not in names and item.target != "null":
            collect.add("MM003", f"Das Ziel `{item.target}` von `{item.name}` steht nicht im Bild.", severity="error", anchor=f"MM003:{item.name}")


def _height(item) -> float:
    """Höhe einer Zeile im Bild."""
    if isinstance(item, Entry) and item.kind == "stapel":
        return _CELL_H * max(1, len(item.cells))
    if isinstance(item, Entry) and item.kind == "reihung":
        return _CELL_H + _INDEX_H
    return _CELL_H


def _draw_entry(canvas: Canvas, entry: Entry, x: float, y: float) -> tuple[float, float]:
    """Zeichnet ein Objekt ab `(x, y)`; liefert rechte Kante und Höhe der Ankermitte."""
    if entry.kind == "stapel":
        cells = list(entry.cells)
        for index, cell in enumerate(reversed(cells)):
            cy = y + _CELL_H * (index + 0.5)
            canvas.rect(x + _CELL_W / 2, cy, _CELL_W, _CELL_H)
            canvas.label(cell, x + _CELL_W / 2, cy, _CELL_W)
        return x + _CELL_W, y + _CELL_H / 2
    cy = y + _CELL_H / 2
    width = 0.0
    if entry.kind == "schlange":
        canvas.line(x, cy, x + _QUEUE_STUB, cy)
        canvas.arrow((x + _QUEUE_STUB, cy), (x, cy), "open")
        x += _QUEUE_STUB
    for index, cell in enumerate(entry.cells):
        cell_w = max(_CELL_W, text_width(cell.text) + 10)
        canvas.rect(x + width + cell_w / 2, cy, cell_w, _CELL_H)
        canvas.label(cell, x + width + cell_w / 2, cy, cell_w)
        if entry.kind == "reihung":
            canvas.label(plain_cell(str(index)), x + width + cell_w / 2, y + _CELL_H + _INDEX_H / 2, cell_w)
        width += cell_w
    if entry.kind == "schlange":
        canvas.line(x + width, cy, x + width + _QUEUE_STUB, cy)
        canvas.arrow((x + width + _QUEUE_STUB, cy), (x + width, cy), "open")
        width += _QUEUE_STUB
    return x + width, cy


def render(options, content, include_solutions=False) -> str:
    """Rendert das Speicherbild; ein leerer Block ergibt nichts."""
    model, _issues = parse(content)
    if not model:
        return ""
    canvas = Canvas(include_solutions)
    column = max(text_width(item.name) for item in model.order) + 8
    x = _MARGIN + column + _NAME_GAP
    anchors: dict[str, tuple[float, float]] = {}
    origins: list[tuple[Reference, float]] = []
    cursor = _MARGIN
    right = x
    for item in model.order:
        height = _height(item)
        name_y = cursor + _CELL_H / 2 if isinstance(item, Reference) or item.kind != "stapel" else cursor + height / 2
        canvas.label(plain_cell(item.name), _MARGIN + column / 2, name_y, column, align="right")
        if isinstance(item, Reference):
            canvas.rect(x + _CELL_W / 2, cursor + _CELL_H / 2, _CELL_W, _CELL_H)
            canvas.ellipse(x + _CELL_W / 2, cursor + _CELL_H / 2, 3.0, 3.0, "diagram-solid")
            origins.append((item, cursor + _CELL_H / 2))
            anchors[item.name] = (x + _CELL_W, cursor + _CELL_H / 2)
            right = max(right, x + _CELL_W)
        else:
            edge_x, edge_y = _draw_entry(canvas, item, x, cursor)
            anchors[item.name] = (edge_x, edge_y)
            right = max(right, edge_x)
        cursor += height + _ROW_GAP
    route = right + _ROUTE_GAP
    for index, (reference, y) in enumerate(origins):
        lane = route + index * _ROUTE_STEP
        start = (x + _CELL_W / 2, y)
        if reference.target == "null":
            canvas.line(*start, start[0] + _CELL_W, y)
            canvas.label(plain_cell("null"), start[0] + _CELL_W + 16, y, 30.0)
            right = max(right, start[0] + _CELL_W + 32)
            continue
        target = anchors.get(reference.target)
        if target is None:
            continue
        points = [start, (lane, y), (lane, target[1]), target]
        canvas.polyline(points)
        canvas.arrow(points[-1], points[-2], "solid")
    width = max(right, route + len(origins) * _ROUTE_STEP) + _MARGIN
    return canvas.finish("memorydiagram", options, width, cursor - _ROW_GAP + _MARGIN + LINE_HEIGHT / 2)
