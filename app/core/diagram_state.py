"""`:::statediagram`: Automaten nach GO Informatik S. 12 (DEA, Mealy, Keller).

Syntax:

    start -> S0
    ende: S1
    S0 -> S0: a, b
    S0 -> S1: c

Gestalt: Zustände als Kreise von links nach rechts, Pfeil mit „Start“ am Startzustand,
Endzustände als Doppelkreis, Schleifen außen am Kreis. Mehrere Übergänge zwischen
denselben Zuständen teilen sich eine Kante mit gestapelter Beschriftung. `S0` erscheint
als S₀, `eps` als ε. Die Optionen `input`, `output`, `stack` geben die Alphabetzeilen.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from html import escape

from .diagram_edges import parse_edge_line
from .diagram_layout import layered_layout
from .diagram_route import curve_points, edge_label_center, ellipse_exit
from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell

_END_RE = re.compile(r"^ende\s*:\s*(.+)$", re.IGNORECASE)
_START_NAME = "start"
_INDEX_RE = re.compile(r"^([^\W\d_]+)(\d+)$")
_EPS_RE = re.compile(r"\beps\b")
_MEALY_RE = re.compile(r"^[^/]+/[^/]+$")
_PUSHDOWN_RE = re.compile(r"^\([^,]+,[^)]+\)\s*:\s*\S+$")
_ALPHABETS = (
    ("input", "Eingabealphabet Σ"),
    ("output", "Ausgabealphabet Ω"),
    ("stack", "Kelleralphabet Γ"),
)
_MIN_RADIUS = 19.0
_END_RING = 4.0
_START_ARROW = 42.0
_LOOP_RISE = 30.0
_BEND = 16.0
_DETOUR_CLEARANCE = 14.0
_MARGIN = 14.0


@dataclass
class Transition:
    """Alle Übergänge von `source` nach `target`; `labels` wird gestapelt."""

    line: int
    source: str
    target: str
    labels: list[Cell] = field(default_factory=list)


@dataclass
class StateModel:
    """Geparster Automat."""

    states: list[str] = field(default_factory=list)
    start: str | None = None
    ends: set[str] = field(default_factory=set)
    transitions: dict[tuple[str, str], Transition] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """Leer heißt: keine Zustände."""
        return bool(self.states)

    def add_state(self, name: str) -> None:
        """Merkt sich einen Zustand in Schreibreihenfolge."""
        if name not in self.states:
            self.states.append(name)


def parse(content) -> tuple[StateModel, list[ParseIssue]]:
    """Parst den Blockinhalt fehlertolerant (`ST002`, `ST003`)."""
    model = StateModel()
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        end = _END_RE.match(source.text)
        if end:
            names = [name.strip() for name in end.group(1).split(",") if name.strip()]
            model.ends.update(names)
            for name in names:
                model.add_state(name)
            continue
        edge = parse_edge_line(source.text, ("->",))
        if edge is None or len(edge.names) != 2:
            issues.append(ParseIssue("ST002", "error", source.number, "Erwartet `A -> B: Text`, `start -> A` oder `ende: A, B`."))
            continue
        first, second = edge.names
        if first.lower() == _START_NAME:
            if model.start is not None and model.start != second:
                issues.append(ParseIssue("ST003", "error", source.number, "Es gibt schon einen Startzustand."))
            model.start = second
            model.add_state(second)
            continue
        model.add_state(first)
        model.add_state(second)
        transition = model.transitions.setdefault((first, second), Transition(source.number, first, second))
        if edge.label:
            transition.labels.append(make_cell(_EPS_RE.sub("ε", edge.label), source.show))
    return model, issues


def _symbols(option) -> list[str]:
    """Zerlegt eine Alphabet-Angabe `a, b, c`."""
    return [symbol.strip() for symbol in str(option or "").split(",") if symbol.strip()]


def _check_dfa(collect, options, model: StateModel) -> None:
    """DEA: je Zustand und Zeichen genau ein Übergang; ein fehlender ist nur eine Warnung."""
    used: dict[tuple[str, str], str] = {}
    for transition in model.transitions.values():
        for cell in transition.labels:
            for symbol in _symbols(cell.text):
                if (transition.source, symbol) in used and used[(transition.source, symbol)] != transition.target:
                    collect.add("ST005", f"`{transition.source}` hat für `{symbol}` mehrere Übergänge.", anchor=f"ST005:{transition.source}:{symbol}")
                used[(transition.source, symbol)] = transition.target
    for state in model.states:
        for symbol in _symbols(options.get("input")):
            if (state, symbol) not in used:
                collect.add("ST006", f"`{state}` hat keinen Übergang für `{symbol}`. Das geht laut GO nur mit einer Erläuterung zum Fehlerzustand.", anchor=f"ST006:{state}:{symbol}")


def check(collect, options, model: StateModel) -> None:
    """Prüft Startzustand und, je nach `kind`, die Notation aus GO S. 12."""
    if model.start is None:
        collect.add("ST004", "Es fehlt der Startzustand (`start -> A`).")
    kind = str(options.get("kind") or "").strip().lower()
    if kind == "dfa":
        _check_dfa(collect, options, model)
    formats = {"mealy": (_MEALY_RE, "`Eingabe / Ausgabe`"), "pda": (_PUSHDOWN_RE, "`(oben, Eingabe) : Kellerwort`")}
    if kind in formats:
        pattern, shown = formats[kind]
        for transition in model.transitions.values():
            for cell in transition.labels:
                if not pattern.match(cell.text.strip()):
                    collect.add("ST007", f"`{cell.text}` hat nicht die Form {shown}.", anchor=f"ST007:{transition.line}:{cell.text}")


def _display_name(name: str) -> str:
    """`S0` wird über die vorhandene Tiefstellung zu S₀."""
    match = _INDEX_RE.match(name)
    return f"{match.group(1)}~{{{match.group(2)}}}" if match else name


def _radius(name: str) -> float:
    """Kreisradius passend zum Namen."""
    return max(_MIN_RADIUS, text_width(name) / 2 + 9)


def _stack_size(labels: list[Cell]) -> tuple[float, float]:
    """Breite und Höhe einer gestapelten Beschriftung."""
    return max((text_width(cell.text) for cell in labels), default=0.0) + 8, LINE_HEIGHT * len(labels)


def _draw_stack(canvas: Canvas, labels: list[Cell], cx: float, cy: float) -> None:
    """Zeichnet Beschriftungen untereinander, zentriert um `(cx, cy)`."""
    width, height = _stack_size(labels)
    top = cy - height / 2 + LINE_HEIGHT / 2
    for index, cell in enumerate(labels):
        canvas.label(cell, cx, top + index * LINE_HEIGHT, width)


def _draw_loop(canvas: Canvas, transition: Transition, cx: float, cy: float, radius: float) -> None:
    """Schleife oben am Kreis, Beschriftung darüber."""
    left = (cx - radius * 0.6, cy - radius * 0.8)
    right = (cx + radius * 0.6, cy - radius * 0.8)
    top = cy - radius - _LOOP_RISE
    canvas.path(f"M {left[0]:.1f} {left[1]:.1f} C {left[0] - 16:.1f} {top:.1f}, {right[0] + 16:.1f} {top:.1f}, {right[0]:.1f} {right[1]:.1f}")
    canvas.arrow(right, (right[0] + 7, right[1] - 16), "solid")
    height = _stack_size(transition.labels)[1]
    _draw_stack(canvas, transition.labels, cx, top + _LOOP_RISE * 0.22 - height / 2)


def _draw_transition(canvas: Canvas, transition: Transition, centers, radii, bend: float) -> None:
    """Gerade Kante oder Bogen (bei Hin- und Rückweg), Beschriftung neben der Mitte."""
    ax, ay = centers[transition.source]
    bx, by = centers[transition.target]
    ra, rb = radii[transition.source], radii[transition.target]
    if bend:
        control, apex = curve_points((ax, ay), (bx, by), bend)
        start = ellipse_exit(ax, ay, ra, ra, control)
        end = ellipse_exit(bx, by, rb, rb, control)
        canvas.path(f"M {start[0]:.1f} {start[1]:.1f} Q {control[0]:.1f} {control[1]:.1f} {end[0]:.1f} {end[1]:.1f}")
        canvas.arrow(end, control, "solid")
        middle = apex
    else:
        start = ellipse_exit(ax, ay, ra, ra, (bx, by))
        end = ellipse_exit(bx, by, rb, rb, (ax, ay))
        canvas.line(*start, *end)
        canvas.arrow(end, start, "solid")
        middle = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    if not transition.labels:
        return
    width, height = _stack_size(transition.labels)
    if bend:
        length = math.hypot(end[0] - start[0], end[1] - start[1]) or 1.0
        side = 1 if bend > 0 else -1
        center = (
            middle[0] - side * (end[1] - start[1]) / length * (width / 2 + 3),
            middle[1] + side * (end[0] - start[0]) / length * (height / 2 + 3),
        )
    else:
        center = edge_label_center(start, end, middle, width, height)
    _draw_stack(canvas, transition.labels, *center)


def _detour_bend(transition: Transition, centers, radii) -> float:
    """Ausbuchtung, die eine Kante um dazwischenliegende Zustände herumführt; 0 ohne Hindernis.

    Der Bogen läuft immer nach unten, denn oben sitzen die Schleifen.
    """
    ax, ay = centers[transition.source]
    bx, by = centers[transition.target]
    length = math.hypot(bx - ax, by - ay) or 1.0
    needed = 0.0
    for name, (cx, cy) in centers.items():
        if name in (transition.source, transition.target):
            continue
        share = ((cx - ax) * (bx - ax) + (cy - ay) * (by - ay)) / (length * length)
        if not 0.0 < share < 1.0:
            continue
        if math.hypot(cx - ax - share * (bx - ax), cy - ay - share * (by - ay)) < radii[name] + _DETOUR_CLEARANCE:
            needed = max(needed, radii[name] + _DETOUR_CLEARANCE)
    return needed if bx >= ax else -needed


def _alphabet_header(options) -> str:
    """Alphabetzeilen über dem Graphen (GO S. 12)."""
    rows = []
    for key, title in _ALPHABETS:
        symbols = _symbols((options or {}).get(key))
        if symbols:
            rows.append(f"<div>{escape(title)} = {{{escape(', '.join(symbols))}}}</div>")
    return f"<div class='diagram-caption'>{''.join(rows)}</div>" if rows else ""


def render(options, content, include_solutions=False) -> str:
    """Rendert den Automaten; ein leerer Block ergibt nichts."""
    model, _issues = parse(content)
    if not model:
        return ""
    radii = {name: _radius(name) + (_END_RING if name in model.ends else 0.0) for name in model.states}
    loops = {source for source, target in model.transitions if source == target}
    sizes = {}
    for name in model.states:
        diameter = 2 * radii[name]
        extra = 0.0
        if name in loops:
            extra = _LOOP_RISE + _stack_size(model.transitions[(name, name)].labels)[1] + 6
        sizes[name] = (diameter, diameter + 2 * extra)
    edges = [(source, target) for source, target in model.transitions if source != target]
    widest = max((_stack_size(t.labels)[0] for t in model.transitions.values()), default=0.0)
    layout = layered_layout(sizes, edges, direction="LR", gap_major=max(70.0, widest + 22), gap_minor=56.0, margin=_MARGIN)
    offset = _START_ARROW + 8 if model.start else 0.0
    centers = {name: (x + offset, y) for name, (x, y) in layout.centers.items()}

    canvas = Canvas(include_solutions)
    lowest = layout.height
    for (source, target), transition in model.transitions.items():
        if source == target:
            _draw_loop(canvas, transition, *centers[source], radii[source])
            continue
        detour = _detour_bend(transition, centers, radii)
        lowest = max(lowest, centers[source][1] + abs(detour) + _stack_size(transition.labels)[1] + 8 if detour else 0.0)
        _draw_transition(canvas, transition, centers, radii, detour or (_BEND if (target, source) in model.transitions else 0.0))
    for name in model.states:
        cx, cy = centers[name]
        canvas.ellipse(cx, cy, radii[name], radii[name])
        if name in model.ends:
            canvas.ellipse(cx, cy, radii[name] - _END_RING, radii[name] - _END_RING)
        canvas.label(make_cell(_display_name(name)), cx, cy, 2 * radii[name])
    if model.start:
        cx, cy = centers[model.start]
        tip = (cx - radii[model.start], cy)
        tail = (tip[0] - _START_ARROW, cy)
        canvas.line(*tail, *tip)
        canvas.arrow(tip, tail, "solid")
        canvas.label("Start", tail[0] + 4, cy - LINE_HEIGHT / 2 - 1, 40.0)
    return canvas.finish("statediagram", options, layout.width + offset, lowest, _alphabet_header(options))
