"""`:::termtree`: Rechenbaum aus einem getippten Term wie `(3+4)*2`.

Die Zahlen stehen oben, die Äste laufen nach unten zum Ergebnis zusammen und zeigen so
die Rechenreihenfolge. Die Ergebnisse berechnet Blattwerk exakt, sie sind nie getippt.
Eine Zeile ist ein Term. `gaps=results` lässt die Zwischenergebnisse im Arbeitsblatt
offen, `leaves` die Zahlen, `all` beides.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .diagram_expression import Expr, ExpressionError, Grammar, parse_expression
from .diagram_layout_tree import tree_layout
from .diagram_numbers import format_number, parse_number
from .diagram_svg import Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell, plain_cell

_GRAMMAR = Grammar(
    levels=((("+", "-"), False), (("*", "/"), False), (("^",), True)),
    prefix=("-",),
    aliases={"·": "*", ":": "/", "x": "*", "×": "*"},
    atom=r"\d+(?:[.,]\d+)?|[^\W\d_x]\w*",
)
_OPERATOR_SIGN = {"+": "+", "-": "−", "*": "·", "/": ":", "^": "^"}
_MAX_EXPONENT = 64
"""Größere Potenzen wären nicht mehr lesbar und könnten das Rendern blockieren (`9^9^9`)."""
_BOX_HEIGHT = 24.0
_OP_RADIUS = 10.0
_MIN_BOX = 34.0
_MARGIN = 12.0
_RECORD_GAP = 26.0
_CAPTION = 22.0


@dataclass(frozen=True)
class Term:
    """Ein geparster Term mit Quelltext und Zeile."""

    line: int
    text: str
    expression: Expr


def parse(content) -> tuple[list[Term], list[ParseIssue]]:
    """Parst die Terme fehlertolerant (`TT002`)."""
    terms: list[Term] = []
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        try:
            terms.append(Term(source.number, source.text, parse_expression(source.text, _GRAMMAR)))
        except ExpressionError as error:
            issues.append(ParseIssue("TT002", "error", source.number, str(error)))
    return terms, issues


def evaluate(expression: Expr) -> Fraction | None:
    """Exakter Wert; `None` bei Variablen, Division durch 0 oder gebrochenem Exponenten."""
    if expression.is_leaf:
        return parse_number(expression.value)
    values = [evaluate(child) for child in expression.children]
    if any(value is None for value in values):
        return None
    if len(values) == 1:
        return -values[0]
    first, second = values
    if expression.value == "+":
        return first + second
    if expression.value == "-":
        return first - second
    if expression.value == "*":
        return first * second
    if expression.value == "/":
        return first / second if second else None
    if second.denominator != 1 or abs(second) > _MAX_EXPONENT or (not first and second < 0):
        return None
    return first ** int(second)


def _contains_zero_division(expression: Expr) -> bool:
    """Prüft, ob irgendwo durch einen Wert 0 geteilt wird."""
    if expression.is_leaf:
        return False
    if expression.value == "/" and len(expression.children) == 2 and evaluate(expression.children[1]) == 0:
        return True
    return any(_contains_zero_division(child) for child in expression.children)


def _has_variable(expression: Expr) -> bool:
    """Prüft, ob ein Blatt keine Zahl ist."""
    if expression.is_leaf:
        return parse_number(expression.value) is None
    return any(_has_variable(child) for child in expression.children)


def check(collect, _options, terms: list[Term]) -> None:
    """Warnt vor Division durch 0 (`TT003`) und Variablen ohne Ergebnis (`TT004`)."""
    for term in terms:
        if _contains_zero_division(term.expression):
            collect.add("TT003", f"In `{term.text}` wird durch 0 geteilt.", severity="error", anchor=f"TT003:{term.line}")
        elif evaluate(term.expression) is None and not _has_variable(term.expression):
            collect.add("TT005", f"`{term.text}` lässt sich nicht berechnen: Potenzen brauchen ganze Exponenten bis {_MAX_EXPONENT}.", severity="error", anchor=f"TT005:{term.line}")
        elif _has_variable(term.expression):
            collect.add("TT004", f"`{term.text}` enthält Variablen, deshalb bleiben die Ergebnisse leer.", anchor=f"TT004:{term.line}")


def _result_cell(expression: Expr, hidden: bool) -> Cell:
    """Zelle eines Knotens; `hidden` macht sie zur Lücke (nur Lösung)."""
    value = evaluate(expression)
    text = expression.value if value is None and expression.is_leaf else format_number(value) if value is not None else ""
    if hidden and text:
        return make_cell(f"%{{{text}}}")
    return plain_cell(text)


class _TreeDrawer:
    """Ordnet einen Term an und zeichnet ihn gespiegelt, das Ergebnis liegt unten."""

    def __init__(self, canvas: Canvas, gaps: str):
        """Merkt sich Zeichenfläche und Lückenart."""
        self.canvas = canvas
        self.gaps = gaps
        self.sizes: dict[str, tuple[float, float]] = {}
        self.children: dict[str, list[str]] = {}
        self.nodes: dict[str, Expr] = {}

    def collect(self, expression: Expr, key: str = "r") -> None:
        """Vergibt Schlüssel und Größen."""
        self.nodes[key] = expression
        value = evaluate(expression)
        text = expression.value if value is None else format_number(value)
        height = _BOX_HEIGHT if expression.is_leaf else _BOX_HEIGHT + 2 * _OP_RADIUS + 6
        self.sizes[key] = (max(_MIN_BOX, text_width(text) + 14), height)
        self.children[key] = [f"{key}{index}" for index in range(len(expression.children))]
        for index, child in enumerate(expression.children):
            self.collect(child, f"{key}{index}")

    def draw(self, top: float) -> tuple[float, float]:
        """Zeichnet ab Höhe `top`; liefert Breite und Höhe des Baums."""
        layout = tree_layout(self.sizes, self.children, "r", gap_major=22.0, gap_minor=16.0, margin=0.0)
        place = {key: (x + _MARGIN, top + layout.height - y) for key, (x, y) in layout.centers.items()}
        for key, expression in self.nodes.items():
            x, y = place[key]
            width, height = self.sizes[key]
            box_y = y + height / 2 - _BOX_HEIGHT / 2
            if expression.is_leaf:
                hidden = self.gaps in ("leaves", "all")
            else:
                hidden = self.gaps in ("results", "all")
                op_y = y - height / 2 + _OP_RADIUS
                for child in self.children[key]:
                    cx, cy = place[child]
                    self.canvas.line(cx, cy + self.sizes[child][1] / 2, x, op_y)
                self.canvas.line(x, op_y, x, box_y)
                self.canvas.ellipse(x, op_y, _OP_RADIUS, _OP_RADIUS, "diagram-tone-4")
                self.canvas.label(_OPERATOR_SIGN.get(expression.value, expression.value), x, op_y, 2 * _OP_RADIUS)
            tone = "diagram-tone-1" if expression.is_leaf else "diagram-tone-3" if key == "r" else "diagram-tone-2"
            self.canvas.rect(x, box_y, width, _BOX_HEIGHT, css=tone)
            self.canvas.label(_result_cell(expression, hidden), x, box_y, width)
        return layout.width + 2 * _MARGIN, layout.height


def render(options, content, include_solutions=False) -> str:
    """Rendert alle Terme untereinander; ein leerer Block ergibt nichts."""
    terms, _issues = parse(content)
    if not terms:
        return ""
    gaps = str((options or {}).get("gaps") or "none").lower()
    canvas = Canvas(include_solutions)
    cursor = _MARGIN
    width = 0.0
    for term in terms:
        caption = plain_cell(term.text)
        caption_width = text_width(term.text) + 10
        canvas.label(caption, _MARGIN + caption_width / 2, cursor + _CAPTION / 2 - 2, caption_width, weight="bold")
        drawer = _TreeDrawer(canvas, gaps)
        drawer.collect(term.expression)
        tree_width, tree_height = drawer.draw(cursor + _CAPTION)
        width = max(width, tree_width, caption_width + 2 * _MARGIN)
        cursor += _CAPTION + tree_height + _RECORD_GAP
    return canvas.finish("termtree", options, width, cursor - _RECORD_GAP + _MARGIN)
