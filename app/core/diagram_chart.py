"""`:::chart`: Statistikdiagramme aus kurzen Datenzeilen.

`type=` wählt die Darstellung:

* `bar`: `Äpfel: 12`
* `pie`: `Äpfel: 12` (Anteile werden berechnet)
* `box`: `Klasse 8a: 3, 5, 7, 9, 12` (Rohdaten; Quartile siehe `five_numbers`)
* `histogram`: `0-10: 4` (aneinandergrenzende Klassen)
* `scatter`: `1,5; 3` (x; y)

`%` am Zeilenanfang macht einen Wert zur Lücke: Der Balken oder Punkt fehlt im
Arbeitsblatt, die Beschriftung bleibt. `gaps=values` blendet nur die Zahlen aus.
Die Töne kommen aus dem Farbprofil; im Schwarz-Weiß-Profil sind sie grau.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from fractions import Fraction

from .diagram_numbers import five_numbers, format_number, nice_ticks, parse_number, split_numbers
from .diagram_svg import LINE_HEIGHT, TONES, Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell, plain_cell

_INTERVAL_RE = re.compile(r"^(-?\d+(?:[.,]\d+)?)\s*-\s*(-?\d+(?:[.,]\d+)?)$")
_PLOT_W, _PLOT_H = 360.0, 200.0
_LEFT, _TOP, _BOTTOM = 44.0, 14.0, 34.0
_MARGIN = 12.0
_PIE_R = 92.0
_BOX_ROW = 46.0
_LABEL_COLUMN = 90.0
_POINT = 3.5
_BOX_MIN_VALUES = 5


@dataclass(frozen=True)
class Row:
    """Eine Datenzeile: Beschriftung und Zahlen; `gap` heißt Lücke im Arbeitsblatt."""

    line: int
    label: str
    values: tuple[Fraction, ...]
    gap: bool
    percent: bool = False


def parse(content) -> tuple[list[Row], list[ParseIssue]]:
    """Parst die Zeilen fehlertolerant (`CH002`); der Typ kommt erst in `check` dazu."""
    rows: list[Row] = []
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        label, colon, rest = source.text.partition(":")
        parts = split_numbers(rest if colon else source.text)
        values = [parse_number(part) for part in parts]
        if not parts or any(value is None for value in values):
            issues.append(ParseIssue("CH002", "error", source.number, "Erwartet `Name: 12`, `Name: 3, 5, 7`, `0-10: 4` oder `1,5; 3`."))
            continue
        rows.append(Row(source.number, label.strip() if colon else "", tuple(values), source.show == "solution", any(part.endswith("%") for part in parts)))
    return rows, issues


def _chart_type(options) -> str:
    """Gewählte Darstellung; ohne Angabe Balken."""
    return str((options or {}).get("type") or "bar").lower()


def check(collect, options, rows: list[Row]) -> None:
    """Prüft die Zeilen gegen `type` (`CH003`-`CH006`)."""
    kind = _chart_type(options)
    if kind in ("bar", "pie", "histogram"):
        for row in rows:
            if len(row.values) != 1 or not row.label:
                collect.add("CH003", f"Zeile {row.line} im Block braucht bei `type={kind}` genau `Name: Zahl`.", severity="error", anchor=f"CH003:{row.line}")
            elif row.values[0] < 0:
                collect.add("CH004", f"Zeile {row.line} im Block: negative Werte passen nicht zu `type={kind}`.", severity="error", anchor=f"CH004:{row.line}")
    if kind == "scatter":
        for row in rows:
            if len(row.values) != 2:
                collect.add("CH003", f"Zeile {row.line} im Block braucht bei `type=scatter` genau `x; y`.", severity="error", anchor=f"CH003:{row.line}")
    if kind == "pie" and rows and sum(row.values[0] for row in rows) == 0:
        collect.add("CH004", "Im Kreisdiagramm ist die Summe 0.", severity="error")
    if kind == "histogram":
        _check_intervals(collect, rows)
    if kind in ("bar", "pie", "box", "histogram"):
        labels = [row.label for row in rows]
        for label in {name for name in labels if name and labels.count(name) > 1}:
            collect.add("CH007", f"`{label}` steht doppelt.", anchor=f"CH007:{label}")
    if kind == "box":
        for row in rows:
            if len(row.values) < _BOX_MIN_VALUES:
                collect.add("CH008", f"`{row.label}` hat {len(row.values)} Werte; ein Boxplot braucht mindestens {_BOX_MIN_VALUES}.", anchor=f"CH008:{row.line}")
    if kind == "pie" and rows and all(row.percent for row in rows) and sum(row.values[0] for row in rows) != 1:
        collect.add("CH009", f"Die Prozentangaben ergeben {format_number(sum(row.values[0] for row in rows) * 100)} %, nicht 100 %.")


def _intervals(rows: list[Row]) -> list[tuple[float, float] | None]:
    """Klassengrenzen je Zeile, `None` bei falscher Schreibweise."""
    found = []
    for row in rows:
        match = _INTERVAL_RE.match(row.label)
        found.append((float(match.group(1).replace(",", ".")), float(match.group(2).replace(",", "."))) if match else None)
    return found


def _check_intervals(collect, rows: list[Row]) -> None:
    """Histogramm: Klassen müssen `a-b` sein und lückenlos aneinandergrenzen."""
    intervals = _intervals(rows)
    for row, interval in zip(rows, intervals):
        if interval is None or interval[0] >= interval[1]:
            collect.add("CH005", f"`{row.label}` ist keine Klasse der Form `0-10`.", severity="error", anchor=f"CH005:{row.line}")
    known = [i for i in intervals if i is not None]
    if len({round(high - low, 9) for low, high in known}) > 1:
        collect.add("CH010", "Die Klassen sind unterschiedlich breit, die Balken stehen aber gleich breit. Die Höhen sind dann nicht vergleichbar.")
    for earlier, later in zip(known, known[1:]):
        if earlier[1] != later[0]:
            collect.add("CH006", f"Die Klassen schließen nicht lückenlos an: {earlier[1]:g} und {later[0]:g}.", anchor=f"CH006:{later[0]}")


def _value_cell(value: Fraction, row: Row, hide: bool) -> Cell:
    """Zahl über dem Balken; als Lücke, wenn `gaps=values` oder die Zeile es verlangt."""
    text = format_number(value)
    return make_cell(f"%{{{text}}}") if hide or row.gap else plain_cell(text)


def _axes(canvas: Canvas, ticks: list[float], x0: float, y0: float, width: float, height: float) -> None:
    """Senkrechte Achse mit Marken und waagerechte Grundlinie."""
    low, high = ticks[0], ticks[-1]
    canvas.line(x0, y0, x0, y0 - height)
    canvas.line(x0, y0, x0 + width, y0)
    for tick in ticks:
        y = y0 - (tick - low) / ((high - low) or 1) * height
        canvas.line(x0 - 3, y, x0, y)
        canvas.label(f"{tick:g}".replace(".", ","), x0 - 24, y, 38.0, align="right")


def _render_bars(canvas: Canvas, rows: list[Row], options, adjacent: bool) -> tuple[float, float]:
    """Balken oder Histogramm (`adjacent`: ohne Abstand, Klassengrenzen an den Kanten)."""
    hide = str(options.get("gaps") or "") == "values"
    ticks = nice_ticks(0.0, float(max(row.values[0] for row in rows)))
    x0, y0 = _MARGIN + _LEFT, _TOP + _PLOT_H
    _axes(canvas, ticks, x0, y0, _PLOT_W, _PLOT_H)
    slot = _PLOT_W / len(rows)
    bar = slot if adjacent else slot * 0.62
    for index, row in enumerate(rows):
        cx = x0 + slot * (index + 0.5)
        height = float(row.values[0]) / ticks[-1] * _PLOT_H
        if not (row.gap and not canvas.include_solutions):
            canvas.rect(cx, y0 - height / 2, bar, height, css=f"diagram-bar {TONES[0 if adjacent else index % len(TONES)]}")
        canvas.label(_value_cell(row.values[0], row, hide), cx, y0 - height - LINE_HEIGHT / 2 - 1, slot)
        if not adjacent:
            canvas.label(row.label, cx, y0 + LINE_HEIGHT / 2 + 3, slot, LINE_HEIGHT * 2, wrap=True)
    if adjacent:
        intervals = _intervals(rows)
        edges = [i[0] for i in intervals if i] + [intervals[-1][1]] if intervals and intervals[-1] else []
        for index, edge in enumerate(edges):
            x = x0 + slot * index
            canvas.line(x, y0, x, y0 + 3)
            canvas.label(f"{edge:g}".replace(".", ","), x, y0 + LINE_HEIGHT / 2 + 3, slot)
    return x0 + _PLOT_W + _MARGIN, y0 + _BOTTOM + _MARGIN


def _render_pie(canvas: Canvas, rows: list[Row], options) -> tuple[float, float]:
    """Kreis mit Sektoren; Anteile außen, Sektoren nur durch Linien getrennt."""
    total = sum(row.values[0] for row in rows)
    if not total:
        return 0.0, 0.0
    hide = str(options.get("gaps") or "") == "values"
    reach = max(text_width(row.label) for row in rows) + 44
    cx, cy = _MARGIN + reach + _PIE_R, _MARGIN + 30 + _PIE_R
    angle = -math.pi / 2
    for index, row in enumerate(rows):
        share = row.values[0] / total
        sweep = float(share) * 2 * math.pi
        hidden = row.gap and not canvas.include_solutions
        if len(rows) == 1 and not hidden:
            canvas.ellipse(cx, cy, _PIE_R, _PIE_R, TONES[0])
        elif sweep and not hidden:
            canvas.sector(cx, cy, _PIE_R, angle, angle + sweep, TONES[index % len(TONES)])
        elif sweep:
            canvas.sector(cx, cy, _PIE_R, angle, angle + sweep, "diagram-shape")
        middle = angle + sweep / 2
        percent = format_number(share * 100) + " %"
        text = f"%{{{percent}}}" if hide or row.gap else percent
        canvas.label(make_cell(text), cx + _PIE_R * 0.62 * math.cos(middle), cy + _PIE_R * 0.62 * math.sin(middle), 70.0)
        label_x = cx + (_PIE_R + 8) * math.cos(middle)
        label_y = cy + (_PIE_R + 12) * math.sin(middle)
        width = text_width(row.label) + 6
        canvas.label(row.label, label_x + (width / 2 if math.cos(middle) >= 0 else -width / 2), label_y, width)
        angle += sweep
    return cx + _PIE_R + reach + _MARGIN, cy + _PIE_R + 30 + _MARGIN


def _render_box(canvas: Canvas, rows: list[Row]) -> tuple[float, float]:
    """Boxplots untereinander auf einer gemeinsamen Achse."""
    data = [value for row in rows for value in row.values]
    ticks = nice_ticks(float(min(data)), float(max(data)), 8)
    low, high = ticks[0], ticks[-1]
    label_column = max(_LABEL_COLUMN, max(text_width(row.label) for row in rows) + 10)
    x0 = _MARGIN + label_column

    def x_of(value) -> float:
        return x0 + (float(value) - low) / ((high - low) or 1) * _PLOT_W

    y = _MARGIN + _BOX_ROW / 2
    for index, row in enumerate(rows):
        canvas.label(row.label, _MARGIN + label_column / 2, y, label_column, align="left")
        if not (row.gap and not canvas.include_solutions):
            minimum, q1, mid, q3, maximum = five_numbers(list(row.values))
            canvas.line(x_of(minimum), y, x_of(q1), y)
            canvas.line(x_of(q3), y, x_of(maximum), y)
            for value in (minimum, maximum):
                canvas.line(x_of(value), y - 8, x_of(value), y + 8)
            canvas.rect((x_of(q1) + x_of(q3)) / 2, y, x_of(q3) - x_of(q1), 26.0, css=TONES[index % len(TONES)])
            canvas.line(x_of(mid), y - 13, x_of(mid), y + 13)
        y += _BOX_ROW
    axis_y = y - _BOX_ROW / 2 + 8
    canvas.line(x0, axis_y, x0 + _PLOT_W, axis_y)
    for tick in ticks:
        canvas.line(x_of(tick), axis_y, x_of(tick), axis_y + 3)
        canvas.label(f"{tick:g}".replace(".", ","), x_of(tick), axis_y + LINE_HEIGHT / 2 + 3, 40.0)
    return x0 + _PLOT_W + _MARGIN + 14, axis_y + LINE_HEIGHT + 4 + _MARGIN


def _render_scatter(canvas: Canvas, rows: list[Row]) -> tuple[float, float]:
    """Streudiagramm: Punkte als Kreuze, Lücken fehlen im Arbeitsblatt."""
    points = [row for row in rows if len(row.values) == 2]
    if not points:
        return 0.0, 0.0
    x_ticks = nice_ticks(min(0.0, float(min(r.values[0] for r in points))), float(max(r.values[0] for r in points)))
    y_ticks = nice_ticks(min(0.0, float(min(r.values[1] for r in points))), float(max(r.values[1] for r in points)))
    x0, y0 = _MARGIN + _LEFT, _TOP + _PLOT_H
    _axes(canvas, y_ticks, x0, y0, _PLOT_W, _PLOT_H)

    def place(row: Row) -> tuple[float, float]:
        x = x0 + (float(row.values[0]) - x_ticks[0]) / (x_ticks[-1] - x_ticks[0]) * _PLOT_W
        y = y0 - (float(row.values[1]) - y_ticks[0]) / (y_ticks[-1] - y_ticks[0]) * _PLOT_H
        return x, y

    for tick in x_ticks:
        x = x0 + (tick - x_ticks[0]) / (x_ticks[-1] - x_ticks[0]) * _PLOT_W
        canvas.line(x, y0, x, y0 + 3)
        canvas.label(f"{tick:g}".replace(".", ","), x, y0 + LINE_HEIGHT / 2 + 3, 40.0)
    for row in points:
        if row.gap and not canvas.include_solutions:
            continue
        x, y = place(row)
        canvas.line(x - _POINT, y - _POINT, x + _POINT, y + _POINT, css="diagram-accent")
        canvas.line(x - _POINT, y + _POINT, x + _POINT, y - _POINT, css="diagram-accent")
    return x0 + _PLOT_W + _MARGIN + 14, y0 + _BOTTOM + _MARGIN


def render(options, content, include_solutions=False) -> str:
    """Rendert das Diagramm; unpassende Zeilen werden übergangen, der Validator meldet sie."""
    rows, _issues = parse(content)
    kind = _chart_type(options)
    usable = [row for row in rows if len(row.values) == 1 and row.values[0] >= 0] if kind in ("bar", "pie", "histogram") else rows
    if not usable:
        return ""
    canvas = Canvas(include_solutions)
    if kind == "pie":
        width, height = _render_pie(canvas, usable, options or {})
    elif kind == "box":
        width, height = _render_box(canvas, usable)
    elif kind == "scatter":
        width, height = _render_scatter(canvas, usable)
    else:
        width, height = _render_bars(canvas, usable, options or {}, adjacent=kind == "histogram")
    if not width:
        return ""
    return canvas.finish("chart", options, width, height)
