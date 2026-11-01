"""`:::logicgates`: Logikschaltung aus einer Formel wie `Q = (A und B) oder nicht C`.

Operatoren: `und`, `oder`, `xoder`, `nand`, `nor`, `nicht`. `norm=iec` zeichnet die
rechteckigen Symbole, `norm=ansi` die geschwungenen. `truthtable=true` ergänzt die
Wahrheitstabelle, berechnet aus der Formel; ihre Ergebnisspalte ist mit `gaps=true` im
Arbeitsblatt leer.

GRENZE: Kommt eine Variable mehrfach vor, erscheint sie je Vorkommen als eigener
Eingang, statt dass eine Leitung sich verzweigt. Das bleibt lesbar und kreuzungsfrei.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from html import escape

from .diagram_expression import Expr, ExpressionError, Grammar, parse_expression
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import ParseIssue, iter_source_lines

_GRAMMAR = Grammar(
    levels=((("oder", "nor"), False), (("xoder",), False), (("und", "nand"), False)),
    prefix=("nicht",),
    aliases={"or": "oder", "and": "und", "xor": "xoder", "not": "nicht"},
    atom=r"[^\W\d_][\w]*",
)
_RULE_RE = re.compile(r"^\s*([^=]+?)\s*=\s*(.+)$")
_IEC_SYMBOL = {"und": "&", "nand": "&", "oder": "≥1", "nor": "≥1", "xoder": "=1", "nicht": "1"}
_NEGATED = {"nand", "nor", "nicht"}
_TRUE_VALUES = ("1", "true", "yes", "on", "ja")
_EVAL = {
    "und": lambda a, b: a and b,
    "oder": lambda a, b: a or b,
    "xoder": lambda a, b: a != b,
    "nand": lambda a, b: not (a and b),
    "nor": lambda a, b: not (a or b),
}
_GATE_W, _GATE_H = 44.0, 40.0
_BUBBLE = 4.0
_COLUMN = 92.0
_ROW = 34.0
_INPUT_LABEL = 30.0
_MARGIN = 10.0
MAX_TABLE_VARIABLES = 6


@dataclass(frozen=True)
class Circuit:
    """Eine Schaltung: Ausgangsname und Formel."""

    output: str
    expression: Expr


def parse(content) -> tuple[list[Circuit], list[ParseIssue]]:
    """Parst die Formeln fehlertolerant (`LG002`, `LG003`)."""
    circuits: list[Circuit] = []
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        match = _RULE_RE.match(source.text)
        if not match:
            issues.append(ParseIssue("LG002", "error", source.number, "Erwartet `Q = (A und B) oder nicht C`."))
            continue
        try:
            circuits.append(Circuit(match.group(1), parse_expression(match.group(2), _GRAMMAR)))
        except ExpressionError as error:
            issues.append(ParseIssue("LG003", "error", source.number, str(error)))
    return circuits, issues


def variables_of(expression: Expr) -> list[str]:
    """Variablen der Formel in Reihenfolge des ersten Auftretens."""
    if expression.is_leaf:
        return [expression.value]
    found: list[str] = []
    for child in expression.children:
        for name in variables_of(child):
            if name not in found:
                found.append(name)
    return found


def evaluate(expression: Expr, assignment: dict[str, bool]) -> bool:
    """Wertet die Formel für eine Belegung aus."""
    if expression.is_leaf:
        return assignment[expression.value]
    if expression.value == "nicht":
        return not evaluate(expression.children[0], assignment)
    first, second = expression.children
    return _EVAL[expression.value](evaluate(first, assignment), evaluate(second, assignment))


def check(collect, options, circuits: list[Circuit]) -> None:
    """Prüft Ausgänge, Rückkopplung, `gaps` und die Tabellengröße (`LG004`-`LG007`)."""
    outputs = [circuit.output for circuit in circuits]
    for name in {n for n in outputs if outputs.count(n) > 1}:
        collect.add("LG005", f"Der Ausgang `{name}` steht doppelt.", severity="error", anchor=f"LG005:{name}")
    for circuit in circuits:
        if circuit.output in variables_of(circuit.expression):
            collect.add("LG006", f"`{circuit.output}` hängt von sich selbst ab; die Tabelle und das Bild zeigen das nicht als Rückkopplung.", anchor=f"LG006:{circuit.output}")
    if _enabled(options, "gaps") and not _enabled(options, "truthtable"):
        collect.add("LG007", "`gaps=true` wirkt nur zusammen mit `truthtable=true`.")
    if not _enabled(options, "truthtable"):
        return
    for circuit in circuits:
        if len(variables_of(circuit.expression)) > MAX_TABLE_VARIABLES:
            collect.add("LG004", f"`{circuit.output}` hat mehr als {MAX_TABLE_VARIABLES} Variablen; die Tabelle entfällt.", anchor=f"LG004:{circuit.output}")


def _enabled(options, key: str) -> bool:
    """Boolesche Blockoption."""
    return str((options or {}).get(key) or "").strip().lower() in _TRUE_VALUES


def _depth(expression: Expr) -> int:
    """Gatterstufen bis zum tiefsten Eingang."""
    return 0 if expression.is_leaf else 1 + max(_depth(child) for child in expression.children)


def _leaves(expression: Expr) -> int:
    """Anzahl der Eingänge (Blätter)."""
    return 1 if expression.is_leaf else sum(_leaves(child) for child in expression.children)


def _gate_shape(canvas: Canvas, operator: str, x: float, y: float, norm: str) -> float:
    """Zeichnet ein Gatter mit linker Kante bei `x`; liefert die x-Position des Ausgangs."""
    half = _GATE_H / 2
    negated = operator in _NEGATED
    if norm == "iec":
        canvas.rect(x + _GATE_W / 2, y, _GATE_W, _GATE_H, css="diagram-shape")
        canvas.label(_IEC_SYMBOL[operator], x + _GATE_W / 2, y, _GATE_W)
        right = x + _GATE_W
    elif operator == "nicht":
        canvas.polygon([(x, y - half * 0.7), (x + _GATE_W * 0.8, y), (x, y + half * 0.7)])
        right = x + _GATE_W * 0.8
    elif operator in ("und", "nand"):
        canvas.path(f"M {x:.1f} {y - half:.1f} L {x + 18:.1f} {y - half:.1f} A {half:.1f} {half:.1f} 0 0 1 {x + 18:.1f} {y + half:.1f} L {x:.1f} {y + half:.1f} Z")
        right = x + 18 + half
    else:
        canvas.path(f"M {x:.1f} {y - half:.1f} Q {x + 24:.1f} {y - half:.1f} {x + _GATE_W:.1f} {y:.1f} Q {x + 24:.1f} {y + half:.1f} {x:.1f} {y + half:.1f} Q {x + 12:.1f} {y:.1f} {x:.1f} {y - half:.1f} Z")
        if operator == "xoder":
            canvas.path(f"M {x - 6:.1f} {y - half:.1f} Q {x + 6:.1f} {y:.1f} {x - 6:.1f} {y + half:.1f}")
        right = x + _GATE_W
    if negated:
        canvas.ellipse(right + _BUBBLE, y, _BUBBLE, _BUBBLE)
        right += 2 * _BUBBLE
    return right


class _Drawer:
    """Zeichnet einen Ausdrucksbaum von rechts nach links in feste Spalten."""

    def __init__(self, canvas: Canvas, norm: str, columns: int, top: float):
        """Merkt sich Zeichenfläche, Norm, Spaltenzahl und die Höhe des ersten Eingangs."""
        self.canvas = canvas
        self.norm = norm
        self.columns = columns
        self.next_row = top

    def draw(self, expression: Expr, column: int) -> tuple[float, float]:
        """Zeichnet den Teilbaum; liefert den Ausgangspunkt."""
        if expression.is_leaf:
            y = self.next_row
            self.next_row += _ROW
            self.canvas.label(expression.value, _MARGIN + _INPUT_LABEL / 2, y, _INPUT_LABEL)
            return _MARGIN + _INPUT_LABEL, y
        outputs = [self.draw(child, column + 1) for child in expression.children]
        y = sum(point[1] for point in outputs) / len(outputs)
        x = _MARGIN + _INPUT_LABEL + (self.columns - column - 1) * _COLUMN + _COLUMN - _GATE_W - 8
        count = len(outputs)
        for index, (start_x, start_y) in enumerate(outputs):
            pin_y = y + (_GATE_H / 4) * (2 * index - count + 1) if count > 1 else y
            knee = x - 10 - 5 * index
            self.canvas.polyline([(start_x, start_y), (knee, start_y), (knee, pin_y), (x, pin_y)])
        right = _gate_shape(self.canvas, expression.value, x, y, self.norm)
        return right, y


def _truth_table(circuit: Circuit, include_solutions: bool, hide_results: bool) -> str:
    """Wahrheitstabelle aus der Formel; `hide_results` lässt die Ergebnisse im Arbeitsblatt offen."""
    names = variables_of(circuit.expression)
    if len(names) > MAX_TABLE_VARIABLES:
        return ""
    head = "".join(f"<th>{escape(name)}</th>" for name in names + [circuit.output])
    rows = []
    for values in itertools.product((False, True), repeat=len(names)):
        cells = "".join(f"<td>{int(value)}</td>" for value in values)
        result = int(evaluate(circuit.expression, dict(zip(names, values))))
        if hide_results and not include_solutions:
            cells += f"<td><span class='diagram-hidden'>{result}</span></td>"
        else:
            cells += f"<td>{result}</td>"
        rows.append(f"<tr>{cells}</tr>")
    return f"<table class='diagram-table'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def render(options, content, include_solutions=False) -> str:
    """Rendert alle Schaltungen untereinander; ein leerer Block ergibt nichts."""
    circuits, _issues = parse(content)
    if not circuits:
        return ""
    norm = "ansi" if str((options or {}).get("norm") or "").lower() == "ansi" else "iec"
    canvas = Canvas(include_solutions)
    top = _MARGIN + _ROW / 2
    width = 0.0
    for circuit in circuits:
        columns = max(1, _depth(circuit.expression))
        drawer = _Drawer(canvas, norm, columns, top)
        end_x, end_y = drawer.draw(circuit.expression, 0)
        output_x = end_x + 20
        canvas.line(end_x, end_y, output_x, end_y)
        label_width = text_width(circuit.output) + 8
        canvas.label(circuit.output, output_x + label_width / 2, end_y, label_width)
        width = max(width, output_x + label_width)
        top = drawer.next_row + _ROW / 2
    height = top - _ROW / 2 + _MARGIN - LINE_HEIGHT / 2
    html = canvas.finish("logicgates", options, width + _MARGIN, height)
    if not _enabled(options, "truthtable"):
        return html
    tables = "".join(_truth_table(circuit, include_solutions, _enabled(options, "gaps")) for circuit in circuits)
    return f"{html}<div class='diagram-tables'>{tables}</div>"
