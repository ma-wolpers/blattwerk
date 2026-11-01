"""`:::syntaxdiagram`: Syntaxdiagramme (Schienen) aus EBNF-ähnlichen Zeilen.

Syntax je Zeile: `Zahl = Ziffer { Ziffer }`. Dabei sind `"x"` Terminale, Namen
Nichtterminale, `|` Alternativen, `[ … ]` optional, `{ … }` Wiederholung und `( … )`
Gruppen. Terminale sind rund, Nichtterminale eckig gezeichnet.

Jeder Ausdruck wird zu einem `_Rail`: Größe plus Höhe der Hauptschiene, an der er ein-
und ausläuft. Damit setzen sich Ausdrücke beliebig tief zusammen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import ParseIssue, iter_source_lines, plain_cell

_RULE_RE = re.compile(r"^([^=]+?)\s*=\s*(.+)$")
_TOKEN_RE = re.compile(r'"[^"]*"|[|\[\]{}()]|[^\s|\[\]{}()"]+')
_BOX_HEIGHT = 26.0
_STUB = 14.0
_V_GAP = 10.0
_LOOP_OFFSET = 14.0
_MARGIN = 10.0


class GrammarError(ValueError):
    """Ein Ausdruck ist nicht wohlgeformt."""


@dataclass(frozen=True)
class Node:
    """Ausdrucksknoten: `kind` ist `terminal`, `name`, `seq`, `alt`, `opt` oder `rep`."""

    kind: str
    text: str = ""
    children: tuple = ()


@dataclass(frozen=True)
class Rule:
    """Eine Produktionsregel."""

    name: str
    expression: Node


class _Reader:
    """Rekursiver Abstieg über die Token einer Regel."""

    def __init__(self, tokens: list[str]):
        """Merkt sich die Token."""
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> str | None:
        """Nächstes Token oder `None`."""
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def alternatives(self) -> Node:
        """`a | b | c`."""
        options = [self.sequence()]
        while self.peek() == "|":
            self.pos += 1
            options.append(self.sequence())
        return options[0] if len(options) == 1 else Node("alt", children=tuple(options))

    def sequence(self) -> Node:
        """Folge von Elementen bis `|` oder schließender Klammer."""
        items = []
        while self.peek() not in (None, "|", "]", "}", ")"):
            items.append(self.item())
        if not items:
            raise GrammarError("Hier fehlt ein Ausdruck.")
        return items[0] if len(items) == 1 else Node("seq", children=tuple(items))

    def item(self) -> Node:
        """Einzelnes Element: Klammerausdruck, Terminal oder Name."""
        token = self.peek()
        self.pos += 1
        closers = {"[": ("]", "opt"), "{": ("}", "rep"), "(": (")", None)}
        if token in closers:
            closer, kind = closers[token]
            inner = self.alternatives()
            if self.peek() != closer:
                raise GrammarError(f"Es fehlt die schließende Klammer `{closer}`.")
            self.pos += 1
            return Node(kind, children=(inner,)) if kind else inner
        if token.startswith('"'):
            return Node("terminal", token.strip('"'))
        return Node("name", token)


def parse(content) -> tuple[list[Rule], list[ParseIssue]]:
    """Parst die Regeln fehlertolerant (`SY002`, `SY003`)."""
    rules: list[Rule] = []
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        match = _RULE_RE.match(source.text)
        if not match:
            issues.append(ParseIssue("SY002", "error", source.number, 'Erwartet `Name = Ausdruck`, zum Beispiel `Zahl = Ziffer { Ziffer }`.'))
            continue
        reader = _Reader(_TOKEN_RE.findall(match.group(2)))
        try:
            expression = reader.alternatives()
            if reader.peek() is not None:
                raise GrammarError(f"Unerwartetes `{reader.peek()}`.")
        except GrammarError as error:
            issues.append(ParseIssue("SY003", "error", source.number, str(error)))
            continue
        rules.append(Rule(match.group(1).strip(), expression))
    return rules, issues


@dataclass
class _Rail:
    """Zeichenbarer Ausdruck; `axis` ist die Höhe der Hauptschiene."""

    width: float
    height: float
    axis: float
    draw: Callable[[Canvas, float, float], None]


def _box(node: Node) -> _Rail:
    """Terminal rund, Nichtterminal eckig."""
    width = text_width(node.text) + (22 if node.kind == "terminal" else 16)

    def draw(canvas: Canvas, x: float, y: float) -> None:
        radius = _BOX_HEIGHT / 2 if node.kind == "terminal" else 0.0
        canvas.rect(x + width / 2, y + _BOX_HEIGHT / 2, width, _BOX_HEIGHT, radius=radius, css="diagram-shape")
        canvas.label(plain_cell(node.text), x + width / 2, y + _BOX_HEIGHT / 2, width)

    return _Rail(width, _BOX_HEIGHT, _BOX_HEIGHT / 2, draw)


def _sequence(node: Node) -> _Rail:
    """Elemente nacheinander auf einer Schiene."""
    rails = [_rail(child) for child in node.children]
    axis = max(rail.axis for rail in rails)
    below = max(rail.height - rail.axis for rail in rails)
    width = sum(rail.width for rail in rails) + _STUB * (len(rails) - 1)

    def draw(canvas: Canvas, x: float, y: float) -> None:
        cursor = x
        for index, rail in enumerate(rails):
            rail.draw(canvas, cursor, y + axis - rail.axis)
            cursor += rail.width
            if index < len(rails) - 1:
                canvas.line(cursor, y + axis, cursor + _STUB, y + axis)
                cursor += _STUB

    return _Rail(width, axis + below, axis, draw)


def _alternatives(node: Node) -> _Rail:
    """Alternativen untereinander, außen durch senkrechte Schienen verbunden."""
    rails = [_rail(child) for child in node.children]
    inner = max(rail.width for rail in rails)
    width = inner + 2 * _STUB
    height = sum(rail.height for rail in rails) + _V_GAP * (len(rails) - 1)
    axis = rails[0].axis

    def draw(canvas: Canvas, x: float, y: float) -> None:
        cursor = y
        ax = y + axis
        last_axis = ax
        for rail in rails:
            rail.draw(canvas, x + _STUB, cursor)
            row = cursor + rail.axis
            canvas.line(x, row, x + _STUB, row)
            canvas.line(x + _STUB + rail.width, row, x + width, row)
            last_axis = row
            cursor += rail.height + _V_GAP
        canvas.line(x, ax, x, last_axis)
        canvas.line(x + width, ax, x + width, last_axis)

    return _Rail(width, height, axis, draw)


def _optional(node: Node) -> _Rail:
    """Optional: Hauptschiene oben läuft vorbei, der Inhalt hängt darunter."""
    inner = _rail(node.children[0])
    width = inner.width + 2 * _STUB
    height = _V_GAP + inner.height
    axis = 0.0

    def draw(canvas: Canvas, x: float, y: float) -> None:
        canvas.line(x, y, x + width, y)
        row = y + _V_GAP + inner.axis
        canvas.line(x, y, x, row)
        canvas.line(x + width, y, x + width, row)
        canvas.line(x, row, x + _STUB, row)
        canvas.line(x + _STUB + inner.width, row, x + width, row)
        canvas.arrow((x + width / 2 + 5, y), (x, y), "solid")
        inner.draw(canvas, x + _STUB, y + _V_GAP)

    return _Rail(width, height, axis, draw)


def _repeat(node: Node) -> _Rail:
    """Wiederholung: optional wie `_optional`, dazu ein Rücklauf unter dem Inhalt."""
    inner = _rail(node.children[0])
    width = inner.width + 2 * _STUB
    height = _V_GAP + inner.height + _LOOP_OFFSET
    axis = 0.0

    def draw(canvas: Canvas, x: float, y: float) -> None:
        canvas.line(x, y, x + width, y)
        row = y + _V_GAP + inner.axis
        canvas.line(x, y, x, row)
        canvas.line(x + width, y, x + width, row)
        canvas.line(x, row, x + _STUB, row)
        canvas.line(x + _STUB + inner.width, row, x + width, row)
        back = y + _V_GAP + inner.height + _LOOP_OFFSET - 4
        canvas.polyline([(x + width - _STUB / 2, row), (x + width - _STUB / 2, back), (x + _STUB / 2, back), (x + _STUB / 2, row)])
        canvas.arrow((x + width / 2 - 5, back), (x + width, back), "solid")
        inner.draw(canvas, x + _STUB, y + _V_GAP)

    return _Rail(width, height, axis, draw)


def _rail(node: Node) -> _Rail:
    """Dispatch auf den Knotentyp."""
    if node.kind == "seq":
        return _sequence(node)
    if node.kind == "alt":
        return _alternatives(node)
    if node.kind == "opt":
        return _optional(node)
    if node.kind == "rep":
        return _repeat(node)
    return _box(node)


def render(options, content, include_solutions=False) -> str:
    """Rendert alle Regeln untereinander; ein leerer Block ergibt nichts."""
    rules, _issues = parse(content)
    if not rules:
        return ""
    canvas = Canvas(include_solutions)
    cursor = _MARGIN
    width = 0.0
    for rule in rules:
        rail = _rail(rule.expression)
        title_width = text_width(rule.name) * 1.15 + 6
        canvas.label(rule.name, _MARGIN + title_width / 2, cursor + LINE_HEIGHT / 2, title_width, weight="bold", align="left")
        cursor += LINE_HEIGHT + 4
        row = cursor + rail.axis
        canvas.line(_MARGIN, row, _MARGIN + _STUB, row)
        rail.draw(canvas, _MARGIN + _STUB, cursor)
        end = _MARGIN + _STUB + rail.width
        canvas.line(end, row, end + _STUB, row)
        canvas.arrow((end + _STUB, row), (end, row), "solid")
        width = max(width, end + _STUB, _MARGIN + title_width)
        cursor += rail.height + 16
    return canvas.finish("syntaxdiagram", options, width + _MARGIN, cursor)
