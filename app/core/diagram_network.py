"""`:::networkdiagram`: Netzwerkplan mit einfachen Symbolen aus kurzen Verbindungszeilen.

Syntax: `PC1 - Switch - Router` (Kette), optional `Drucker1: rechner` für ein anderes
Symbol. Das Symbol ergibt sich sonst aus dem Namensanfang. Ein Baum steht mit dem
Knoten mit den meisten Verbindungen oben, das ist meist der Router.
"""

from __future__ import annotations

import re

from .diagram_edges import parse_edge_line
from .diagram_graph_model import GraphEdge, GraphModel, auto_layout
from .diagram_route import Box, box_exit
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import ParseIssue, iter_source_lines

_SYMBOL_PREFIXES = (
    ("switch", ("switch", "hub")),
    ("router", ("router", "gateway")),
    ("server", ("server",)),
    ("internet", ("internet", "wan", "cloud")),
    ("drucker", ("drucker", "printer")),
    ("rechner", ("pc", "rechner", "laptop", "client", "computer", "host")),
)
_SYMBOLS = tuple(symbol for symbol, _prefixes in _SYMBOL_PREFIXES)
_DEFAULT_SYMBOL = "rechner"
_OVERRIDE_RE = re.compile(r"^(.+?)\s*:\s*(\w+)$")
_ICON_WIDTH, _ICON_HEIGHT = 44.0, 34.0
_GAP = 4.0


def symbol_for(name: str) -> str:
    """Symbol aus dem Namensanfang, unbekannte Namen gelten als Rechner."""
    lowered = name.lower()
    for symbol, prefixes in _SYMBOL_PREFIXES:
        if lowered.startswith(prefixes):
            return symbol
    return _DEFAULT_SYMBOL


class NetworkModel(GraphModel):
    """`GraphModel` plus ausdrücklich gesetzte Symbole."""

    def __init__(self):
        """Legt ein leeres Modell an."""
        super().__init__()
        self.symbols: dict[str, str] = {}


def parse(content) -> tuple[NetworkModel, list[ParseIssue]]:
    """Parst den Blockinhalt fehlertolerant (`NW002`, `NW003`)."""
    model = NetworkModel()
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        edge = parse_edge_line(source.text, ("-",))
        if edge is not None and not edge.label:
            for first, second in zip(edge.names, edge.names[1:]):
                model.add_node(first, source.show)
                model.add_node(second, source.show)
                model.edges.append(GraphEdge(source.number, first, second, False, None))
            continue
        override = _OVERRIDE_RE.match(source.text)
        if override is None:
            issues.append(ParseIssue("NW002", "error", source.number, "Erwartet `PC1 - Switch - Router` oder `Name: symbol`."))
            continue
        name, symbol = override.group(1), override.group(2).lower()
        if symbol not in _SYMBOLS:
            issues.append(ParseIssue("NW003", "error", source.number, f"Unbekanntes Symbol `{symbol}`. Möglich: {', '.join(_SYMBOLS)}."))
            continue
        model.add_node(name, source.show)
        model.symbols[name] = symbol
    return model, issues


def check(collect, _options, model: NetworkModel) -> None:
    """Doppelte Kabel, Geräte an sich selbst und Geräte ohne Verbindung (`NW004`-`NW006`)."""
    seen = set()
    connected = set()
    for edge in model.edges:
        if edge.source == edge.target:
            collect.add("NW005", f"`{edge.source}` ist mit sich selbst verbunden.", anchor=f"NW005:{edge.line}")
        key = frozenset((edge.source, edge.target))
        if key in seen:
            collect.add("NW004", f"Die Verbindung `{edge.source} - {edge.target}` steht doppelt.", anchor=f"NW004:{edge.line}")
        seen.add(key)
        connected.update((edge.source, edge.target))
    for name in model.nodes:
        if name not in connected:
            collect.add("NW006", f"`{name}` ist mit nichts verbunden.", anchor=f"NW006:{name}")


def _draw_symbol(canvas: Canvas, symbol: str, cx: float, cy: float) -> None:
    """Zeichnet ein Symbol in `_ICON_WIDTH` × `_ICON_HEIGHT` um `(cx, cy)`."""
    w, h = _ICON_WIDTH, _ICON_HEIGHT
    if symbol == "rechner":
        canvas.rect(cx, cy - 4, w * 0.8, h * 0.62, css="diagram-tone-3")
        canvas.line(cx, cy + h * 0.27 - 4, cx, cy + h * 0.45)
        canvas.line(cx - 10, cy + h * 0.45, cx + 10, cy + h * 0.45)
    elif symbol == "switch":
        canvas.rect(cx, cy, w, h * 0.5, css="diagram-tone-3")
        for offset in (-13.0, -4.0, 5.0, 14.0):
            canvas.line(cx + offset, cy - 4, cx + offset, cy + 4)
    elif symbol == "router":
        canvas.ellipse(cx, cy, w / 2 - 2, h / 2, "diagram-tone-4")
        canvas.line(cx - 12, cy, cx + 12, cy)
        canvas.line(cx, cy - 10, cx, cy + 10)
    elif symbol == "server":
        canvas.rect(cx, cy, w * 0.55, h, css="diagram-tone-3")
        for offset in (-8.0, 0.0, 8.0):
            canvas.line(cx - w * 0.2, cy + offset, cx + w * 0.2, cy + offset)
    elif symbol == "drucker":
        canvas.rect(cx, cy - 11, w * 0.45, h * 0.3, css="diagram-tone-3")
        canvas.rect(cx, cy + 2, w * 0.8, h * 0.45, css="diagram-tone-3")
    else:
        for dx, dy, rx, ry in ((-11, 2, 12, 10), (10, 3, 13, 10), (0, -5, 13, 11)):
            canvas.ellipse(cx + dx, cy + dy, rx, ry, "diagram-tone-2")


def render(options, content, include_solutions=False) -> str:
    """Rendert den Netzwerkplan; ein leerer Block ergibt nichts."""
    model, _issues = parse(content)
    if not model:
        return ""
    sizes = {
        name: (max(_ICON_WIDTH, text_width(name) + 6), _ICON_HEIGHT + _GAP + LINE_HEIGHT)
        for name in model.nodes
    }
    layout = auto_layout(sizes, [(edge.source, edge.target) for edge in model.edges], gap_major=36.0, gap_minor=26.0)
    canvas = Canvas(include_solutions)
    boxes = {name: Box(*layout.centers[name], *sizes[name]) for name in model.nodes}
    for edge in model.edges:
        start, end = boxes[edge.source], boxes[edge.target]
        canvas.line(*box_exit(start, (end.cx, end.cy)), *box_exit(end, (start.cx, start.cy)))
    for name, cell in model.nodes.items():
        box = boxes[name]
        icon_y = box.top + _ICON_HEIGHT / 2
        _draw_symbol(canvas, model.symbols.get(name) or symbol_for(name), box.cx, icon_y)
        canvas.label(cell, box.cx, box.bottom - LINE_HEIGHT / 2, box.width)
    return canvas.finish("networkdiagram", options, layout.width, layout.height)

