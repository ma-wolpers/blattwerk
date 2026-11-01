"""`:::flowchart`: Flussdiagramm aus demselben Text wie `:::structogram`.

Quelle ist unverändert `parse_struktogramm`, also gelten dieselben Schlüsselwörter und
dieselbe Einrückung. Gezeichnet wird wie im Aktivitätsdiagramm: Rechtecke für
Anweisungen, Rauten für Bedingungen, Rücklauf bei Schleifen.

Jedes Element wird zu einem `_Part`: Es kennt seine Größe und die Stelle, an der der
Ablauf oben hinein und unten hinaus führt. So setzen sich Schachtelungen ohne
allgemeines Graph-Layout zusammen, und Linien können sich nicht kreuzen.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from .answer_special_struktogramm import signature_html
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import Cell
from .struktogramm_parse import Branch, Loop, Statement, Switch, parse_struktogramm
from .struktogramm_validation import check_structogram

parse = parse_struktogramm


def check(collect, options, elements: list) -> None:
    """Eine angegebene `signature=` gilt wie beim Struktogramm, sie ist hier nur freiwillig."""
    if str(options.get("signature") or "").strip():
        check_structogram(collect, options, elements)


_MAX_TEXT = 190.0
_PADDING = 9.0
_DIAMOND_HEIGHT = 46.0
_GAP = 18.0
_COLUMN_GAP = 22.0
_TIP_MARGIN = 12.0
_LOOP_MARGIN = 22.0
_TERMINAL_RADIUS = 7.0
_MARGIN = 10.0


@dataclass
class _Part:
    """Ein zeichenbarer Abschnitt; `draw(canvas, x, y)` setzt ihn an die linke obere Ecke."""

    width: float
    height: float
    anchor: float
    draw: Callable[[Canvas, float, float], None]


_EMPTY = _Part(0.0, 0.0, 0.0, lambda _canvas, _x, _y: None)


def _text_box(cell: Cell) -> tuple[float, float]:
    """Breite und Höhe des Texts; lange Texte brechen um."""
    width = text_width(cell.text)
    lines = max(1, math.ceil(width / _MAX_TEXT))
    return min(width, _MAX_TEXT), lines * LINE_HEIGHT


def _statement(cell: Cell, rounded: bool = True) -> _Part:
    """Anweisung als Rechteck mit runden Ecken."""
    text_w, text_h = _text_box(cell)
    width, height = text_w + 2 * _PADDING, text_h + 2 * _PADDING

    def draw(canvas: Canvas, x: float, y: float) -> None:
        canvas.rect(x + width / 2, y + height / 2, width, height, radius=6.0 if rounded else 0.0, css="diagram-tone-1" if rounded else "diagram-tone-3")
        canvas.label(cell, x + width / 2, y + height / 2, text_w + 4, text_h, wrap=text_h > LINE_HEIGHT)

    return _Part(width, height, width / 2, draw)


def _diamond_size(cell: Cell) -> tuple[float, float, float]:
    """Breite und Höhe der Raute sowie die Breite des Texts darin."""
    text_w, text_h = _text_box(cell)
    return text_w * 1.5 + 30, max(_DIAMOND_HEIGHT, text_h * 2 + 18), text_w + 4


def _draw_diamond(canvas: Canvas, cell: Cell, cx: float, cy: float) -> tuple[float, float]:
    """Raute mit Text; liefert halbe Breite und Höhe."""
    width, height, text_w = _diamond_size(cell)
    half_w, half_h = width / 2, height / 2
    canvas.polygon([(cx, cy - half_h), (cx + half_w, cy), (cx, cy + half_h), (cx - half_w, cy)], "diagram-tone-2")
    canvas.label(cell, cx, cy, text_w, height, wrap=_text_box(cell)[1] > LINE_HEIGHT)
    return half_w, half_h


def _flow_arrow(canvas: Canvas, points) -> None:
    """Streckenzug mit Pfeil am Ende."""
    canvas.polyline(points)
    canvas.arrow(points[-1], points[-2], "solid")


def _sequence(elements: list) -> _Part:
    """Folge untereinander, alle Anker auf einer Senkrechten."""
    parts = [_element(element) for element in elements]
    if not parts:
        return _EMPTY
    anchor = max(part.anchor for part in parts)
    width = max(anchor + part.width - part.anchor for part in parts)
    height = sum(part.height for part in parts) + _GAP * (len(parts) - 1)

    def draw(canvas: Canvas, x: float, y: float) -> None:
        cursor = y
        for index, part in enumerate(parts):
            part.draw(canvas, x + anchor - part.anchor, cursor)
            cursor += part.height
            if index < len(parts) - 1:
                _flow_arrow(canvas, [(x + anchor, cursor), (x + anchor, cursor + _GAP)])
                cursor += _GAP

    return _Part(width, height, anchor, draw)


def _columns(head: Cell, bodies: list[tuple[Cell | str, _Part]]) -> _Part:
    """Verzweigung: Raute oben, Spalten darunter, alle laufen unten zusammen."""
    dia_w, dia_h, _text = _diamond_size(head)
    half = dia_w / 2
    count = len(bodies)
    widths = [max(part.width, text_width(_label_text(label)) + 6) for label, part in bodies]
    anchors = [part.anchor if part.width else width / 2 for width, (_label, part) in zip(widths, bodies)]
    lefts: list[float] = []
    cursor = 0.0
    for width in widths:
        lefts.append(cursor)
        cursor += width + _COLUMN_GAP
    span = cursor - _COLUMN_GAP
    first, last = lefts[0] + anchors[0], lefts[-1] + anchors[-1]
    center = (first + last) / 2 if count > 1 else first
    shift = max(0.0, half + _TIP_MARGIN - (center - first)) if count == 2 else 0.0
    if count == 2:
        lefts[1] += 2 * shift
        lefts = [lefts[0], lefts[1]]
        first, last = lefts[0] + anchors[0], lefts[1] + anchors[1]
        center = (first + last) / 2
        span = lefts[1] + widths[1]
    offset = max(0.0, half - center)
    total_width = max(span + offset, center + offset + half)
    body_height = max(part.height for _label, part in bodies)
    drop = _GAP + LINE_HEIGHT
    height = dia_h + drop + body_height + _GAP + _GAP

    def draw(canvas: Canvas, x: float, y: float) -> None:
        cx = x + center + offset
        cy = y + dia_h / 2
        half_w, half_h = _draw_diamond(canvas, head, cx, cy)
        bottom = y + height - _GAP
        for index, (label, part) in enumerate(bodies):
            column = x + offset + lefts[index]
            ax = column + anchors[index]
            top = y + dia_h + drop
            part_x = column + anchors[index] - part.anchor
            if count == 2:
                tip = (cx - half_w, cy) if index == 0 else (cx + half_w, cy)
                _flow_arrow(canvas, [tip, (ax, cy), (ax, top)])
                align_x = ax + (-1 if index == 0 else 1) * (text_width(_label_text(label)) / 2 + 7)
                canvas.label(label, align_x, top - LINE_HEIGHT / 2, text_width(_label_text(label)) + 6)
            else:
                _flow_arrow(canvas, [(cx, cy + half_h), (ax, top - LINE_HEIGHT), (ax, top)])
                canvas.label(label, ax + text_width(_label_text(label)) / 2 + 9, top - LINE_HEIGHT / 2, text_width(_label_text(label)) + 6)
            part.draw(canvas, part_x, top)
            canvas.polyline([(ax, top + part.height), (ax, bottom), (cx, bottom)])
        canvas.line(cx, bottom, cx, y + height)

    return _Part(total_width, height, center + offset, draw)


def _label_text(label) -> str:
    """Text einer Spaltenbeschriftung, egal ob Zelle oder fester Text."""
    return label.text if isinstance(label, Cell) else str(label)


def _branch(branch: Branch) -> _Part:
    """`wenn`: wahr links, falsch rechts (wie im Struktogramm)."""
    return _columns(branch.condition, [("wahr", _sequence(branch.yes)), ("falsch", _sequence(branch.no))])


def _switch(switch: Switch) -> _Part:
    """`auswahl`: eine Spalte je Fall, `sonst` zuletzt."""
    bodies: list[tuple[Cell | str, _Part]] = [(case.value, _sequence(case.body)) for case in switch.cases]
    if switch.default is not None:
        bodies.append(("sonst", _sequence(switch.default)))
    return _columns(switch.expression, bodies or [("", _EMPTY)])


def _head_loop(loop: Loop) -> _Part:
    """Kopfgesteuert: Raute, Rumpf darunter, Rücklauf links, Ausgang rechts."""
    body = _sequence(loop.body)
    dia_w, dia_h, _text = _diamond_size(loop.text)
    half = dia_w / 2
    left = max(half, body.anchor) + _LOOP_MARGIN
    right = max(half, body.width - body.anchor) + _LOOP_MARGIN + text_width("falsch")
    arrive = _GAP
    height = arrive + dia_h + _GAP + LINE_HEIGHT + body.height + 2 * _GAP

    def draw(canvas: Canvas, x: float, y: float) -> None:
        cx = x + left
        cy = y + arrive + dia_h / 2
        canvas.line(cx, y, cx, y + arrive)
        half_w, half_h = _draw_diamond(canvas, loop.text, cx, cy)
        top = cy + half_h + _GAP + LINE_HEIGHT - _GAP
        canvas.label("wahr", cx + 20, cy + half_h + LINE_HEIGHT / 2, 36.0)
        _flow_arrow(canvas, [(cx, cy + half_h), (cx, top)])
        body.draw(canvas, cx - body.anchor, top)
        turn = top + body.height + _GAP / 2
        _flow_arrow(canvas, [(cx, top + body.height), (cx, turn), (x + 2, turn), (x + 2, y + arrive / 2), (cx, y + arrive / 2)])
        exit_x = x + left + right - 2
        canvas.label("falsch", cx + half_w + text_width("falsch") / 2 + 3, cy - LINE_HEIGHT / 2, text_width("falsch") + 6)
        canvas.polyline([(cx + half_w, cy), (exit_x, cy), (exit_x, y + height - _GAP / 2), (cx, y + height - _GAP / 2), (cx, y + height)])

    return _Part(left + right, height, left, draw)


def _foot_loop(loop: Loop) -> _Part:
    """Fußgesteuert: Rumpf, Raute darunter, Rücklauf links, Ausgang unten."""
    body = _sequence(loop.body)
    dia_w, dia_h, _text = _diamond_size(loop.text)
    half = dia_w / 2
    left = max(half, body.anchor) + _LOOP_MARGIN + text_width("falsch")
    right = max(half, body.width - body.anchor)
    arrive = _GAP
    height = arrive + body.height + _GAP + dia_h + _GAP + LINE_HEIGHT

    def draw(canvas: Canvas, x: float, y: float) -> None:
        cx = x + left
        canvas.line(cx, y, cx, y + arrive)
        top = y + arrive
        body.draw(canvas, cx - body.anchor, top)
        cy = top + body.height + _GAP + dia_h / 2
        _flow_arrow(canvas, [(cx, top + body.height), (cx, cy - dia_h / 2)])
        half_w, half_h = _draw_diamond(canvas, loop.text, cx, cy)
        canvas.label("falsch", cx - half_w - text_width("falsch") / 2 - 3, cy - LINE_HEIGHT / 2, text_width("falsch") + 6)
        _flow_arrow(canvas, [(cx - half_w, cy), (x + 2, cy), (x + 2, y + arrive / 2), (cx, y + arrive / 2)])
        canvas.label("wahr", cx + 20, cy + half_h + LINE_HEIGHT / 2, 36.0)
        canvas.line(cx, cy + half_h, cx, y + height)

    return _Part(left + right, height, left, draw)


def _element(element) -> _Part:
    """Dispatch auf den Elementtyp."""
    if isinstance(element, Statement):
        return _statement(element.cell, rounded=element.kind == "plain")
    if isinstance(element, Loop):
        return _head_loop(element) if element.kind == "head" else _foot_loop(element)
    if isinstance(element, Branch):
        return _branch(element)
    return _switch(element)


def render(options, content, include_solutions=False) -> str:
    """Rendert das Flussdiagramm mit Start- und Endmarke; ein leerer Block ergibt nichts."""
    elements, _issues = parse_struktogramm(content)
    if not elements:
        return ""
    flow = _sequence(elements)
    canvas = Canvas(include_solutions)
    terminal = 2 * _TERMINAL_RADIUS + _GAP
    cx = _MARGIN + flow.anchor
    top = _MARGIN + terminal
    canvas.ellipse(cx, _MARGIN + _TERMINAL_RADIUS, _TERMINAL_RADIUS, _TERMINAL_RADIUS, "diagram-solid")
    _flow_arrow(canvas, [(cx, _MARGIN + 2 * _TERMINAL_RADIUS), (cx, top)])
    flow.draw(canvas, _MARGIN, top)
    bottom = top + flow.height
    _flow_arrow(canvas, [(cx, bottom), (cx, bottom + _GAP)])
    canvas.ellipse(cx, bottom + _GAP + _TERMINAL_RADIUS, _TERMINAL_RADIUS, _TERMINAL_RADIUS)
    canvas.ellipse(cx, bottom + _GAP + _TERMINAL_RADIUS, _TERMINAL_RADIUS - 3, _TERMINAL_RADIUS - 3, "diagram-solid")
    width = flow.width + 2 * _MARGIN
    height = bottom + _GAP + 2 * _TERMINAL_RADIUS + _MARGIN
    return canvas.finish("flowchart", options, width, height, signature_html(options))
