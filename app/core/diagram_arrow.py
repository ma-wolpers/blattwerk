"""`:::arrowdiagram`: Pfeildiagramm für Relationen, Zuordnungen und Funktionen.

Syntax: `1 -> 2`; `3 -> _` zeigt ein Element ohne Pfeil, `_ -> 4` eines rechts. Die Spalten
stehen in der Reihenfolge des ersten Auftretens. `left=` und `right=` beschriften die
Mengen. `%` am Zeilenanfang lässt den Pfeil im Arbeitsblatt weg, die Elemente bleiben.
`kind=function` prüft, dass jedes Element links genau einen Pfeil hat.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .diagram_edges import parse_edge_line
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import ParseIssue, iter_source_lines, plain_cell

_NONE = "_"
_ROW = 28.0
_COLUMN_GAP = 110.0
_PADDING = 18.0
_MARGIN = 12.0
_TITLE = 24.0


@dataclass(frozen=True)
class Link:
    """Ein Pfeil; `gap` heißt: nur in der Lösung sichtbar."""

    line: int
    source: str
    target: str
    gap: bool


@dataclass
class ArrowModel:
    """Elemente der beiden Spalten und die Pfeile dazwischen."""

    left: list[str] = field(default_factory=list)
    right: list[str] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Leer heißt: keine Elemente."""
        return bool(self.left or self.right)


def parse(content) -> tuple[ArrowModel, list[ParseIssue]]:
    """Parst die Zeilen fehlertolerant (`AR002`)."""
    model = ArrowModel()
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        edge = parse_edge_line(source.text, ("->",))
        if edge is None or len(edge.names) != 2:
            issues.append(ParseIssue("AR002", "error", source.number, "Erwartet `1 -> 2`, `3 -> _` oder `_ -> 4`."))
            continue
        first, second = edge.names
        if first != _NONE and first not in model.left:
            model.left.append(first)
        if second != _NONE and second not in model.right:
            model.right.append(second)
        if _NONE not in (first, second):
            model.links.append(Link(source.number, first, second, source.show == "solution"))
    return model, issues


def check(collect, options, model: ArrowModel) -> None:
    """Prüft doppelte Pfeile (`AR003`) und bei `kind=function` die Eindeutigkeit (`AR004`)."""
    seen = set()
    for link in model.links:
        if (link.source, link.target) in seen:
            collect.add("AR003", f"Der Pfeil `{link.source} -> {link.target}` steht doppelt.", anchor=f"AR003:{link.line}")
        seen.add((link.source, link.target))
    if str(options.get("kind") or "") == "function":
        for name in model.left:
            count = len({link.target for link in model.links if link.source == name})
            if count != 1:
                collect.add("AR004", f"`{name}` hat {count} Pfeile; bei einer Funktion gehört zu jedem Element links genau einer.", anchor=f"AR004:{name}")


def render(options, content, include_solutions=False) -> str:
    """Rendert die beiden Mengen und die Pfeile; ein leerer Block ergibt nichts."""
    model, _issues = parse(content)
    if not model:
        return ""
    options = options or {}
    rows = max(len(model.left), len(model.right), 1)
    inner = rows * _ROW + 2 * _PADDING
    left_w = max((text_width(n) for n in model.left), default=20.0) + 2 * _PADDING
    right_w = max((text_width(n) for n in model.right), default=20.0) + 2 * _PADDING
    top = _MARGIN + _TITLE
    middle_y = top + inner / 2
    lx = _MARGIN + left_w / 2
    rx = lx + left_w / 2 + _COLUMN_GAP + right_w / 2
    canvas = Canvas(include_solutions)
    canvas.ellipse(lx, middle_y, left_w / 2, inner / 2, "diagram-line")
    canvas.ellipse(rx, middle_y, right_w / 2, inner / 2, "diagram-line")
    for key, x in (("left", lx), ("right", rx)):
        if options.get(key):
            canvas.label(plain_cell(str(options[key])), x, _MARGIN + LINE_HEIGHT / 2, text_width(str(options[key])) + 10, weight="bold")

    def y_of(index: int, count: int) -> float:
        return middle_y + (index - (count - 1) / 2) * _ROW

    left_y = {name: y_of(i, len(model.left)) for i, name in enumerate(model.left)}
    right_y = {name: y_of(i, len(model.right)) for i, name in enumerate(model.right)}
    for name, y in left_y.items():
        canvas.label(plain_cell(name), lx, y, left_w)
    for name, y in right_y.items():
        canvas.label(plain_cell(name), rx, y, right_w)
    start_x = lx + (left_w / 2 - _PADDING) + 6
    end_x = rx - (right_w / 2 - _PADDING) - 6
    for link in model.links:
        if link.gap and not include_solutions:
            continue
        start, end = (start_x, left_y[link.source]), (end_x, right_y[link.target])
        canvas.line(*start, *end)
        canvas.arrow(end, start, "solid")
    return canvas.finish("arrowdiagram", options, rx + right_w / 2 + _MARGIN, top + inner + _MARGIN)
