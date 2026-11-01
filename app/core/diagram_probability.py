"""`:::probabilitytree`: Baumdiagramm für Wahrscheinlichkeiten.

Syntax: Ergebnisse eingerückt, die Wahrscheinlichkeit steht hinter dem Doppelpunkt.

    Rot: 1/3
        Rot: 1/4
        Blau: 3/4
    Blau: %{2/3}

Lücken gelten für Ergebnis und Wahrscheinlichkeit. Der Validator rechnet nach, ob sich
die Äste einer Verzweigung zu 1 addieren.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .diagram_layout_tree import tree_layout
from .diagram_numbers import format_number, parse_number
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell

_ROOT = "\0"
_NODE_HEIGHT = 24.0
_ROOT_SIZE = 8.0
_BRANCH_GAP = 62.0


@dataclass
class Branch:
    """Ein Ast mit Ergebnis, Wahrscheinlichkeit und Folgeästen."""

    line: int
    key: str
    outcome: Cell
    probability: Cell
    children: list["Branch"] = field(default_factory=list)


def parse(content) -> tuple[list[Branch], list[ParseIssue]]:
    """Parst die Äste fehlertolerant (`PB002`, `PB003`)."""
    roots: list[Branch] = []
    issues: list[ParseIssue] = []
    stack: list[tuple[int, Branch]] = []
    for source in iter_source_lines(content):
        name, colon, probability = source.text.partition(":")
        if not colon or not name.strip() or not probability.strip():
            issues.append(ParseIssue("PB002", "error", source.number, "Erwartet `Ergebnis: Wahrscheinlichkeit`, zum Beispiel `Rot: 1/3`."))
            continue
        branch = Branch(source.number, f"{source.number}", make_cell(name.strip(), source.show), make_cell(probability.strip(), source.show))
        while stack and stack[-1][0] >= source.width:
            stack.pop()
        if source.width and not stack:
            issues.append(ParseIssue("PB003", "error", source.number, "Eingerückter Ast ohne Ast darüber."))
        (stack[-1][1].children if stack else roots).append(branch)
        stack.append((source.width, branch))
    return roots, issues


def _check_group(collect, branches: list[Branch], where: str) -> None:
    """Prüft eine Verzweigung: lesbare Werte, Summe 1 (`PB004`, `PB005`)."""
    values = [parse_number(branch.probability.text) for branch in branches]
    outcomes = [branch.outcome.text for branch in branches]
    for name in {n for n in outcomes if outcomes.count(n) > 1}:
        collect.add("PB006", f"`{name}` steht {where} doppelt.", anchor=f"PB006:{branches[0].line}:{name}")
    for branch, value in zip(branches, values):
        if value is None or not 0 <= value <= 1:
            collect.add("PB004", f"`{branch.probability.text}` ist keine Wahrscheinlichkeit zwischen 0 und 1.", severity="error", anchor=f"PB004:{branch.line}")
    if all(value is not None for value in values) and sum(values) != 1:
        collect.add("PB005", f"Die Äste {where} ergeben zusammen {format_number(sum(values))}, nicht 1.", anchor=f"PB005:{branches[0].line}")
    for branch in branches:
        if branch.children:
            _check_group(collect, branch.children, f"unter `{branch.outcome.text}`")


def check(collect, _options, roots: list[Branch]) -> None:
    """Rechnet alle Verzweigungen nach, auch die mit Lücken."""
    _check_group(collect, roots, "am Anfang")


def _walk(branches: list[Branch]):
    """Alle Äste in Tiefensuche."""
    for branch in branches:
        yield branch
        yield from _walk(branch.children)


def render(options, content, include_solutions=False) -> str:
    """Rendert den Baum von links nach rechts; ein leerer Block ergibt nichts."""
    roots, _issues = parse(content)
    if not roots:
        return ""
    sizes = {_ROOT: (_ROOT_SIZE, _ROOT_SIZE)}
    children = {_ROOT: [branch.key for branch in roots]}
    for branch in _walk(roots):
        sizes[branch.key] = (text_width(branch.outcome.text) + 12, _NODE_HEIGHT)
        children[branch.key] = [child.key for child in branch.children]
    widest = max(text_width(branch.probability.text) for branch in _walk(roots))
    layout = tree_layout(sizes, children, _ROOT, direction="LR", gap_major=max(_BRANCH_GAP, widest + 34), gap_minor=8.0)
    canvas = Canvas(include_solutions)

    def draw_branches(parent_key: str, branches: list[Branch]) -> None:
        px, py = layout.centers[parent_key]
        parent_right = px + sizes[parent_key][0] / 2
        for branch in branches:
            x, y = layout.centers[branch.key]
            left = x - sizes[branch.key][0] / 2
            canvas.line(parent_right, py, left, y)
            label_width = text_width(branch.probability.text) + 8
            middle_x, middle_y = (parent_right + left) / 2, (py + y) / 2
            side = -1 if y <= py else 1
            canvas.label(branch.probability, middle_x, middle_y + side * (LINE_HEIGHT / 2 + 2), label_width)
            canvas.label(branch.outcome, x, y, sizes[branch.key][0])
            draw_branches(branch.key, branch.children)

    draw_branches(_ROOT, roots)
    rx, ry = layout.centers[_ROOT]
    canvas.ellipse(rx, ry, _ROOT_SIZE / 2, _ROOT_SIZE / 2, "diagram-solid")
    return canvas.finish("probabilitytree", options, layout.width, layout.height)
