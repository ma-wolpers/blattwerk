"""`:::fractions`: Bruchdarstellungen als Kreise oder Balken.

Syntax: je Zeile ein Bruch, `3/4`. `shape=circle|bar` wählt die Form, `filled=false` lässt
alle Teile leer zum Selbstausmalen, `%` am Zeilenanfang macht Färbung und Beschriftung nur
im Arbeitsblatt zur Lücke. Unechte Brüche wie `5/4` zeigen mehrere Ganze.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import ParseIssue, iter_source_lines, make_cell

_FRACTION_RE = re.compile(r"^(\d+)\s*/\s*(\d+)$")
_MAX_DENOMINATOR = 60
_MAX_WHOLES = 12
"""Mehr Ganze passen nicht sinnvoll auf eine Zeile."""
_RADIUS = 38.0
_BAR_W, _BAR_H = 160.0, 28.0
_GAP = 12.0
_MARGIN = 10.0
_FALSE_VALUES = ("0", "false", "no", "off", "nein")


@dataclass(frozen=True)
class Item:
    """Ein Bruch; `gap` heißt: Färbung und Text nur in der Lösung."""

    line: int
    numerator: int
    denominator: int
    gap: bool


def parse(content) -> tuple[list[Item], list[ParseIssue]]:
    """Parst die Brüche fehlertolerant (`FR002`, `FR003`)."""
    items: list[Item] = []
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        match = _FRACTION_RE.match(source.text)
        if not match:
            issues.append(ParseIssue("FR002", "error", source.number, "Erwartet einen Bruch wie `3/4`."))
            continue
        numerator, denominator = int(match.group(1)), int(match.group(2))
        if not 0 < denominator <= _MAX_DENOMINATOR:
            issues.append(ParseIssue("FR003", "error", source.number, f"Der Nenner muss zwischen 1 und {_MAX_DENOMINATOR} liegen."))
            continue
        if numerator > denominator * _MAX_WHOLES:
            issues.append(ParseIssue("FR004", "error", source.number, f"`{source.text}` ergibt mehr als {_MAX_WHOLES} Ganze."))
            continue
        items.append(Item(source.number, numerator, denominator, source.show == "solution"))
    return items, issues


def _draw_circle(canvas: Canvas, cx: float, cy: float, parts: int, colored: int) -> None:
    """Kreis mit `parts` gleichen Teilen, davon `colored` gefärbt."""
    step = 2 * math.pi / parts
    for index in range(parts):
        start = -math.pi / 2 + index * step
        if index < colored:
            if parts == 1:
                canvas.ellipse(cx, cy, _RADIUS, _RADIUS, "diagram-fill")
            else:
                canvas.sector(cx, cy, _RADIUS, start, start + step, "diagram-fill")
    canvas.ellipse(cx, cy, _RADIUS, _RADIUS, "diagram-line")
    if parts > 1:
        for index in range(parts):
            angle = -math.pi / 2 + index * step
            canvas.line(cx, cy, cx + _RADIUS * math.cos(angle), cy + _RADIUS * math.sin(angle))


def _draw_bar(canvas: Canvas, x: float, cy: float, parts: int, colored: int) -> None:
    """Balken mit `parts` gleichen Teilen, davon `colored` gefärbt."""
    step = _BAR_W / parts
    for index in range(parts):
        canvas.rect(x + step * (index + 0.5), cy, step, _BAR_H, css="diagram-fill" if index < colored else "diagram-line")


def render(options, content, include_solutions=False) -> str:
    """Zeichnet je Bruch eine Zeile aus Ganzen plus Beschriftung; leerer Block ergibt nichts."""
    items, _issues = parse(content)
    if not items:
        return ""
    options = options or {}
    bar = str(options.get("shape") or "circle") == "bar"
    empty = str(options.get("filled") or "").lower() in _FALSE_VALUES
    canvas = Canvas(include_solutions)
    shape_w = _BAR_W if bar else 2 * _RADIUS
    shape_h = _BAR_H if bar else 2 * _RADIUS
    cursor = _MARGIN
    width = 0.0
    for item in items:
        wholes = max(1, math.ceil(item.numerator / item.denominator))
        colorless = empty or (item.gap and not include_solutions)
        remaining = 0 if colorless else item.numerator
        cy = cursor + shape_h / 2
        x = _MARGIN
        for _ in range(wholes):
            colored = min(remaining, item.denominator)
            if bar:
                _draw_bar(canvas, x, cy, item.denominator, colored)
            else:
                _draw_circle(canvas, x + _RADIUS, cy, item.denominator, colored)
            remaining -= colored
            x += shape_w + _GAP
        text = f"{item.numerator}/{item.denominator}"
        label = make_cell(f"%{{{text}}}" if item.gap else text)
        label_width = text_width(text) + 12
        canvas.label(label, x + label_width / 2, cy, label_width)
        width = max(width, x + label_width)
        cursor += shape_h + _GAP + (LINE_HEIGHT / 2 if bar else 0.0)
    return canvas.finish("fractions", options, width + _MARGIN, cursor - _GAP + _MARGIN)
