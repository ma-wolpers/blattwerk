"""`:::timeline`: Zeitstrahl mit einem Ereignis pro Zeile.

Syntax: `1789: Französische Revolution`, auch `-44: Caesar`, `44 v. Chr.: Caesar` oder
`14.07.1789: Sturm auf die Bastille`. `scale=even` (Standard) verteilt die Ereignisse
gleichmäßig, `scale=proportional` maßstäblich. Lücken: `%` am Zeilenanfang blendet das
Ereignis im Arbeitsblatt aus, die Marke bleibt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .diagram_svg import DATA_TONES, LINE_HEIGHT, Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell

_EVENT_RE = re.compile(r"^(-?\d{1,4}(?:\s*v\.\s*Chr\.)?|\d{1,2}\.\d{1,2}\.\d{1,4})\s*:\s*(.+)$")
_BC_RE = re.compile(r"\s*v\.\s*Chr\.$")
_LABEL_WIDTH = 118.0
_STEP = 104.0
_RAIL_Y_GAP = 12.0
_TICK = 5.0
_MARGIN = 14.0
_MIN_DISTANCE = _LABEL_WIDTH / 2
_LABEL_LINES = 4
_TEXT_GAP = 3.0


@dataclass(frozen=True)
class Event:
    """Ein Ereignis; `value` ist die Zeit als Zahl für Maßstab und Reihenfolge."""

    line: int
    value: float
    time: Cell
    text: Cell


def time_value(key: str) -> float:
    """Zeit als Jahreszahl mit Bruchteil; `v. Chr.` zählt negativ."""
    if "." in key and not _BC_RE.search(key):
        day, month, year = key.split(".")
        return int(year) + (int(month) - 1) / 12 + (int(day) - 1) / 372
    value = int(_BC_RE.sub("", key))
    return -value if _BC_RE.search(key) else value


def _valid_date(key: str) -> bool:
    """Prüft Tag und Monat eines Datums; Jahreszahlen sind immer gültig."""
    if "." not in key or _BC_RE.search(key):
        return True
    day, month, year = (int(part) for part in key.split("."))
    try:
        date(year or 1, month, day)
    except ValueError:
        return False
    return True


def parse(content) -> tuple[list[Event], list[ParseIssue]]:
    """Parst die Ereignisse fehlertolerant (`TL002`)."""
    events: list[Event] = []
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        match = _EVENT_RE.match(source.text)
        if not match:
            issues.append(ParseIssue("TL002", "error", source.number, "Erwartet `1789: Ereignis`, `44 v. Chr.: Ereignis` oder `14.07.1789: Ereignis`."))
            continue
        key = match.group(1).strip()
        if not _valid_date(key):
            issues.append(ParseIssue("TL004", "error", source.number, f"`{key}` ist kein gültiges Datum."))
            continue
        events.append(Event(source.number, time_value(key), make_cell(key), make_cell(match.group(2).strip(), source.show)))
    return events, issues


def check(collect, _options, events: list[Event]) -> None:
    """Warnt, wenn Ereignisse nicht zeitlich aufsteigend stehen (`TL003`)."""
    for earlier, later in zip(events, events[1:]):
        if later.value < earlier.value:
            collect.add("TL003", f"Zeile {later.line} im Block liegt zeitlich vor der Zeile davor.", anchor=f"TL003:{later.line}")


def _positions(events: list[Event], proportional: bool) -> list[float]:
    """x-Position je Ereignis; maßstäblich, aber nie enger als `_MIN_DISTANCE`."""
    start = _MARGIN + _LABEL_WIDTH / 2
    if not proportional or len(events) < 2:
        return [start + index * _STEP for index in range(len(events))]
    low, high = min(e.value for e in events), max(e.value for e in events)
    span = (high - low) or 1.0
    length = _STEP * (len(events) - 1)
    places = [start + (event.value - low) / span * length for event in events]
    for index in range(1, len(places)):
        places[index] = max(places[index], places[index - 1] + _MIN_DISTANCE)
    return places


def render(options, content, include_solutions=False) -> str:
    """Rendert den Zeitstrahl, Ereignisse abwechselnd darüber und darunter."""
    events, _issues = parse(content)
    if not events:
        return ""
    proportional = str((options or {}).get("scale") or "even") == "proportional"
    ordered = sorted(events, key=lambda event: event.value) if proportional else events
    places = _positions(ordered, proportional)
    text_height = _LABEL_LINES * LINE_HEIGHT
    rail = _MARGIN + text_height + LINE_HEIGHT + _RAIL_Y_GAP
    canvas = Canvas(include_solutions)
    end = places[-1] + _LABEL_WIDTH / 2
    canvas.line(_MARGIN, rail, end, rail, css="diagram-accent")
    canvas.arrow((end, rail), (_MARGIN, rail), "solid")
    for index, (event, x) in enumerate(zip(ordered, places)):
        canvas.line(x, rail - _TICK, x, rail + _TICK)
        above = index % 2 == 0
        side = -1 if above else 1
        time_y = rail + side * (_TICK + LINE_HEIGHT / 2 + 1)
        canvas.rect(x, time_y, text_width(event.time.text) * 1.1 + 10, LINE_HEIGHT, radius=5.0, css=DATA_TONES[index % len(DATA_TONES)])
        canvas.label(event.time, x, time_y, text_width(event.time.text) + 8, weight="bold")
        text_y = time_y + side * (LINE_HEIGHT / 2 + text_height / 2 + _TEXT_GAP)
        canvas.label(event.text, x, text_y, _LABEL_WIDTH - 4, text_height, wrap=True, anchor="bottom" if above else "top")
    height = rail + _TICK + LINE_HEIGHT + text_height + _MARGIN
    return canvas.finish("timeline", options, end + _MARGIN, height)
