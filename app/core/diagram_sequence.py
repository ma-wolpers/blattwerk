"""`:::sequencediagram`: Sequenzdiagramm aus kurzen Zeilen.

Syntax: `A -> B: Nachricht` (Aufruf), `A --> B: Antwort` (gestrichelte Rückgabe),
`A -> A: Text` (an sich selbst), `teilnehmer A` legt die Reihenfolge fest. Ohne Angabe
gilt die Reihenfolge des ersten Auftretens.

GRENZE(v1): keine `alt`-/`loop`-Rahmen und keine Aktivierungsbalken; die Wunschliste
verlangt nur die einfache Schreibweise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .diagram_edges import parse_edge_line
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell

_PARTICIPANT_RE = re.compile(r"^teilnehmer\s+(.+)$", re.IGNORECASE)
_MIN_COLUMN = 90.0
_HEAD_HEIGHT = 30.0
_ROW = 34.0
_SELF_WIDTH = 28.0
_SELF_HEIGHT = 18.0
_MARGIN = 12.0


@dataclass(frozen=True)
class Message:
    """Eine Nachricht; `reply` ist die gestrichelte Rückgabe `-->`."""

    source: str
    target: str
    reply: bool
    label: Cell | None


@dataclass
class SequenceModel:
    """Teilnehmer in Reihenfolge und Nachrichten."""

    participants: list[str] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Leer heißt: keine Teilnehmer."""
        return bool(self.participants)

    def add_participant(self, name: str) -> None:
        """Merkt sich einen Teilnehmer beim ersten Auftreten."""
        if name not in self.participants:
            self.participants.append(name)


def parse(content) -> tuple[SequenceModel, list[ParseIssue]]:
    """Parst den Blockinhalt fehlertolerant (`SQ002`)."""
    model = SequenceModel()
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        participant = _PARTICIPANT_RE.match(source.text)
        if participant:
            model.add_participant(participant.group(1).strip())
            continue
        edge = parse_edge_line(source.text, ("-->", "->"))
        if edge is None or len(edge.names) != 2:
            issues.append(ParseIssue("SQ002", "error", source.number, "Erwartet `A -> B: Nachricht`, `A --> B: Antwort` oder `teilnehmer A`."))
            continue
        model.add_participant(edge.names[0])
        model.add_participant(edge.names[1])
        label = make_cell(edge.label, source.show) if edge.label else None
        model.messages.append(Message(edge.names[0], edge.names[1], edge.operators[0] == "-->", label))
    return model, issues


def check(collect, _options, model: SequenceModel) -> None:
    """Warnt vor Teilnehmern ohne Nachricht (`SQ003`)."""
    active = {name for message in model.messages for name in (message.source, message.target)}
    for name in model.participants:
        if name not in active:
            collect.add("SQ003", f"`{name}` sendet und empfängt keine Nachricht.", anchor=f"SQ003:{name}")
    open_calls: dict[tuple[str, str], int] = {}
    for message in model.messages:
        if message.reply:
            key = (message.target, message.source)
            if open_calls.get(key, 0) <= 0:
                collect.add("SQ004", f"`{message.source} --> {message.target}` antwortet auf keinen Aufruf davor.", anchor=f"SQ004:{message.source}:{message.target}")
            else:
                open_calls[key] -= 1
        else:
            key = (message.source, message.target)
            open_calls[key] = open_calls.get(key, 0) + 1


def _column_centers(model: SequenceModel) -> dict[str, float]:
    """Spalten so breit, dass Köpfe und Beschriftungen zwischen zwei Lebenslinien passen."""
    names = model.participants
    gaps = [_MIN_COLUMN] * max(0, len(names) - 1)
    for index, name in enumerate(names[:-1]):
        gaps[index] = max(gaps[index], (text_width(name) + text_width(names[index + 1])) / 2 + 34)
    for message in model.messages:
        if message.label is None:
            continue
        first, second = sorted((names.index(message.source), names.index(message.target)))
        need = text_width(message.label.text) + 16
        if first == second:
            if first < len(gaps):
                gaps[first] = max(gaps[first], need + _SELF_WIDTH)
            continue
        share = need / (second - first)
        for index in range(first, second):
            gaps[index] = max(gaps[index], share)
    centers: dict[str, float] = {}
    cursor = _MARGIN + (text_width(names[0]) + 18) / 2
    for index, name in enumerate(names):
        centers[name] = cursor
        if index < len(gaps):
            cursor += gaps[index]
    return centers


def _draw_message(canvas: Canvas, message: Message, centers, y: float) -> None:
    """Pfeil einer Nachricht in Zeile `y`, Beschriftung darüber."""
    start, end = centers[message.source], centers[message.target]
    if start == end:
        points = [(start, y), (start + _SELF_WIDTH, y), (start + _SELF_WIDTH, y + _SELF_HEIGHT), (start, y + _SELF_HEIGHT)]
        canvas.polyline(points, dashed=message.reply)
        canvas.arrow(points[-1], points[-2], "open" if message.reply else "solid")
        if message.label is not None:
            width = text_width(message.label.text) + 8
            canvas.label(message.label, start + _SELF_WIDTH + width / 2 + 2, y + _SELF_HEIGHT / 2, width)
        return
    canvas.line(start, y, end, y, dashed=message.reply)
    canvas.arrow((end, y), (start, y), "open" if message.reply else "solid")
    if message.label is not None:
        canvas.label(message.label, (start + end) / 2, y - LINE_HEIGHT / 2 - 1, text_width(message.label.text) + 8)


def render(options, content, include_solutions=False) -> str:
    """Rendert das Sequenzdiagramm; ein leerer Block ergibt nichts."""
    model, _issues = parse(content)
    if not model:
        return ""
    centers = _column_centers(model)
    canvas = Canvas(include_solutions)
    first_row = _MARGIN + _HEAD_HEIGHT + _ROW * 0.75
    rows = []
    cursor = first_row
    for message in model.messages:
        rows.append(cursor)
        cursor += _ROW + (_SELF_HEIGHT if message.source == message.target else 0.0)
    bottom = cursor - _ROW * 0.4
    for name, x in centers.items():
        canvas.line(x, _MARGIN + _HEAD_HEIGHT, x, bottom, dashed=True)
    for message, y in zip(model.messages, rows):
        _draw_message(canvas, message, centers, y)
    widest_right = 0.0
    for name, x in centers.items():
        head_width = text_width(name) + 18
        canvas.rect(x, _MARGIN + _HEAD_HEIGHT / 2, head_width, _HEAD_HEIGHT, css="diagram-tone-3")
        canvas.label(name, x, _MARGIN + _HEAD_HEIGHT / 2, head_width)
        widest_right = max(widest_right, x + head_width / 2)
    for message in model.messages:
        if message.source == message.target:
            label_width = text_width(message.label.text) + 8 if message.label is not None else 0.0
            widest_right = max(widest_right, centers[message.source] + _SELF_WIDTH + label_width + 4)
    return canvas.finish("sequencediagram", options, widest_right + _MARGIN, bottom + _MARGIN)
