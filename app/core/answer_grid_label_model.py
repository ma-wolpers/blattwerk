"""Szenenmodell der Geometry-Labels: Label-Beschreibungen, Hindernisse, Textbox-Schätzung.

Die Section-Renderer (`answer_grid_primitives`, `answer_grid_shapes`,
`answer_grid_axis_names`) liefern neben ihren SVG-Shapes keine fertigen
`<text>`-Strings mehr, sondern `LabelSpec`s und `Obstacle`s. Daraus setzt
`answer_grid_label_layout` die Positionen fest (`labels=auto`) oder übernimmt
die bisherigen festen Versätze (`labels=fixed`), und `emit_label` erzeugt das
SVG -- mit `labels=fixed` byte-identisch zur früheren Ausgabe.

Koordinaten sind SVG-Rastereinheiten (1 Einheit = 1 Zelle, y nach unten); die
Umrechnung aus Nutzerkoordinaten (y nach oben, Ursprung links unten) passiert
vorher ausschließlich in `_GeometryCoordinateSystem.point()`.

Hindernis-Stufen (`TIER_*`) sind zugleich die Priorität im Kostentupel des
Layouts: Punktkreuze sind am stärksten geschützt, dann andere Labels, dann
Linien/Kurven/Kanten/Pfeilspitzen, zuletzt Achsen, Ticks und Tick-Zahlen. Das
Hintergrundraster ist kein Hindernis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

TIER_POINT = 0
TIER_LABEL = 1
TIER_LINE = 2
TIER_AXIS = 3
TIER_COUNT = 4

POINT_CROSS_HALF = 0.18
"""Halbe Kantenlänge eines Punktkreuzes (`answer_grid_primitives`)."""

MIN_PX_PER_UNIT = 11.0
"""Konservative Untergrenze Bildschirm-px je Rastereinheit (kleinste übliche `scale` ≈ 0,3 cm).

Linien nutzen `vector-effect: non-scaling-stroke`, ihre Breite ist also in px
angegeben; umgerechnet in Rastereinheiten ist sie bei kleinen Zellen am
breitesten -- mit dieser Untergrenze ist die Aufblähung nie zu knapp.
"""
OBSTACLE_SAFETY = 0.06
LABEL_PADDING = 0.05
TEXT_HEIGHT_FACTOR = 1.15

LABEL_ANCHORS = {
    "grid-point-label": ("start", "middle", 0.60),
    "grid-segment-label": ("start", "middle", 0.60),
    "grid-function-label": ("start", "middle", 0.60),
    "grid-polygon-label": ("middle", "middle", 0.60),
    "grid-circle-label": ("middle", "middle", 0.60),
    "grid-axis-label": ("middle", "hanging", 0.66),
    "grid-axis-label-y": ("end", "middle", 0.66),
    "grid-axis-name": ("start", "hanging", 0.78),
}
"""Ausrichtung (`text-anchor`, `dominant-baseline`) und Schriftgröße je Label-Klasse.

Spiegelt `assets/worksheet.css` (Test `test_label_anchors_match_css`); bei
mehreren Klassen gewinnt die spezifischste (letzte passende) wie im CSS. Ein
explizites SVG-Attribut `text-anchor` (Achsennamen) überschreibt die Tabelle.
"""

_CHAR_WIDTH_CLASSES = (
    ("iIl.,:;|!'`", 0.32),
    ("fjrt()[]{}/\\-", 0.42),
    ("mwMW@%", 0.98),
    ("0123456789", 0.60),
    (" ", 0.30),
)
_UPPER_WIDTH = 0.80
_DEFAULT_WIDTH = 0.64


@dataclass(frozen=True)
class LabelSpec:
    """Ein Text-Label der Szene samt Standardposition und Platzierungsregeln.

    `x`/`y` ist die bisherige (feste) Textposition -- die Standardposition, die
    `labels=fixed` unverändert ausgibt. `anchor` ist der Bezugspunkt des
    Objekts (Punkt, Streckenmitte, Kurvenende, Schwerpunkt, Pfeilspitze).
    `area` enthält bei Flächenlabels die Kontur (Polygon/abgetasteter Kreis),
    damit das Layout Kandidaten im Inneren bevorzugen kann. `movable=False`
    (Tick-Zahlen) heißt: bleibt fest und zählt nur als Hindernis.
    """

    text: str
    css_class: str
    x: float
    y: float
    kind: str
    anchor: tuple[float, float]
    style_attr: str = ""
    extra_attrs: str = ""
    movable: bool = True
    area: tuple[tuple[float, float], ...] | None = None

    @property
    def alignment(self) -> tuple[str, str, float]:
        """`(h_align, v_align, font_px)` aus `LABEL_ANCHORS`, ggf. mit explizitem `text-anchor`."""
        h_align, v_align, font_px = "start", "auto", 0.60
        for css_name in self.css_class.split():
            if css_name in LABEL_ANCHORS:
                h_align, v_align, font_px = LABEL_ANCHORS[css_name]
        if "text-anchor='end'" in self.extra_attrs:
            h_align = "end"
        elif "text-anchor='start'" in self.extra_attrs:
            h_align = "start"
        return h_align, v_align, font_px


@dataclass(frozen=True)
class Obstacle:
    """Ein Hindernis: `shape` ∈ {"disc", "segment", "rect"} mit Koordinaten und Aufblähung.

    * disc: `(cx, cy, r)`
    * segment: `(x1, y1, x2, y2)`
    * rect: `(x0, y0, x1, y1)`

    `pad` ist die Aufblähung um halbe Strichbreite plus Sicherheitsabstand;
    `bbox` die bereits aufgeblähte Hüllbox für den schnellen Vorfilter.
    """

    tier: int
    shape: str
    coords: tuple[float, ...]
    pad: float = 0.0
    bbox: tuple[float, float, float, float] = field(init=False)

    def __post_init__(self):
        if self.shape == "disc":
            cx, cy, r = self.coords
            box = (cx - r, cy - r, cx + r, cy + r)
        elif self.shape == "segment":
            x1, y1, x2, y2 = self.coords
            box = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        else:
            box = self.coords
        pad = self.pad
        object.__setattr__(self, "bbox", (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad))


def stroke_pad(stroke_px: float) -> float:
    """Aufblähung einer Linie: halbe Strichbreite (px → Rastereinheiten, konservativ) + Sicherheitsabstand."""
    return max(0.0, float(stroke_px)) / 2.0 / MIN_PX_PER_UNIT + OBSTACLE_SAFETY


def polyline_obstacles(points, tier: int, pad: float, closed: bool = False) -> list[Obstacle]:
    """Zerlegt eine Polylinie (bzw. geschlossene Kontur) in Segment-Hindernisse, in Punktreihenfolge."""
    sequence = list(points)
    if closed and len(sequence) > 2:
        sequence.append(sequence[0])
    return [
        Obstacle(tier, "segment", (x1, y1, x2, y2), pad)
        for (x1, y1), (x2, y2) in zip(sequence, sequence[1:])
    ]


def point_cross_obstacle(px: float, py: float, stroke_px: float = 1.15) -> Obstacle:
    """Punktkreuz als Scheibe (Eckabstand des Kreuzes plus Strich), Stufe `TIER_POINT`."""
    return Obstacle(TIER_POINT, "disc", (px, py, POINT_CROSS_HALF * 1.4143), stroke_pad(stroke_px))


def estimate_text_width(text: str, font_px: float) -> float:
    """Konservative Textbreite in Rastereinheiten (Zeichenklassen statt echter Font-Metrik).

    Die Faktoren liegen über den Breiten von Helvetica-Bold (Test gegen
    PyMuPDF-Metrik); andere Schriftprofile sind meist schmaler. Eine zu
    breite Schätzung kostet nur etwas Abstand, eine zu schmale würde echte
    Überlappungen verbergen.
    """
    total = 0.0
    for char in text:
        width = None
        for chars, factor in _CHAR_WIDTH_CLASSES:
            if char in chars:
                width = factor
                break
        if width is None:
            width = _UPPER_WIDTH if char.isupper() else _DEFAULT_WIDTH
        total += width
    return total * font_px


def text_box(spec: LabelSpec, x: float, y: float) -> tuple[float, float, float, float]:
    """Hüllbox `(x0, y0, x1, y1)` des Labels, wenn sein Text an `(x, y)` steht (inkl. Polsterung)."""
    h_align, v_align, font_px = spec.alignment
    width = estimate_text_width(spec.text, font_px)
    height = font_px * TEXT_HEIGHT_FACTOR
    if h_align == "middle":
        x0 = x - width / 2.0
    elif h_align == "end":
        x0 = x - width
    else:
        x0 = x
    if v_align == "hanging":
        y0 = y
    elif v_align == "middle":
        y0 = y - height / 2.0
    else:  # alphabetische Grundlinie: Text steht überwiegend oberhalb von y
        y0 = y - height * 0.8
    return (x0 - LABEL_PADDING, y0 - LABEL_PADDING, x0 + width + LABEL_PADDING, y0 + height + LABEL_PADDING)


def text_position_for_box_center(spec: LabelSpec, cx: float, cy: float) -> tuple[float, float]:
    """Umkehrung von `text_box`: Textposition, deren Hüllbox ihren Mittelpunkt bei `(cx, cy)` hat."""
    x0, y0, x1, y1 = text_box(spec, 0.0, 0.0)
    return cx - (x0 + x1) / 2.0, cy - (y0 + y1) / 2.0


def emit_label(spec: LabelSpec, x: float, y: float) -> str:
    """SVG-`<text>` eines Labels -- exakt im bisherigen Format (Attributreihenfolge class, style, x, y)."""
    return (
        f"<text class='{spec.css_class}'{spec.style_attr} x='{x:.4f}' y='{y:.4f}'{spec.extra_attrs}>"
        f"{escape(spec.text)}</text>"
    )
