"""Zeichenfläche der Diagrammblöcke: SVG-Formen und HTML-Beschriftungen.

Warum `foreignObject` für Beschriftungen: Text soll Inline-Markup, Formeln und
Lücken beherrschen wie überall in Blattwerk (`diagram_text.render_cell`) und trotzdem
mit dem Diagramm mitskalieren. Der Spike in Chromium-PDF hat das bestätigt.

Alle Linien und Texte nutzen `currentColor`, Füllungen sind `none`. Damit gilt das
Schwarz-Weiß-Profil ohne Sonderfall, und keine Farbe trägt Bedeutung. Der Hintergrund
von Formen, die Linien überdecken, ist `--diagram-paper`.
"""

from __future__ import annotations

import math
import re
from html import escape

from .answer_grid_label_model import estimate_text_width
from .diagram_text import Cell, make_cell, render_cell

FONT_PX = 13.0
LINE_HEIGHT = 17.0
"""Zeilenhöhe in Einheiten der Zeichenfläche (`.diagram-label` setzt dieselbe Schrift)."""
ARROW_LENGTH = 10.0
ARROW_HALF_WIDTH = 4.5
WIDTH_RE = re.compile(r"^\d+(?:\.\d+)?(?:%|cm|mm|px|em|rem)$")
"""Erlaubte Werte der Option `width`; alles andere landet nie im `style`."""


def text_width(text: str) -> float:
    """Geschätzte Breite von `text` auf der Zeichenfläche (eher zu groß als zu klein)."""
    return estimate_text_width(str(text), FONT_PX)


def width_style(options) -> str:
    """CSS-Fragment für die Option `width`, leer bei fehlendem oder ungültigem Wert."""
    width = str((options or {}).get("width") or "").strip()
    return f"width:{width};" if WIDTH_RE.match(width) else ""


def _attr(value: float) -> str:
    """Koordinate kompakt und stabil formatieren (gleiche Eingabe, gleiche Ausgabe)."""
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _points(points) -> str:
    """Punktliste für `points=`."""
    return " ".join(f"{_attr(x)},{_attr(y)}" for x, y in points)


class Canvas:
    """Sammelt Formen und Beschriftungen und erzeugt daraus den fertigen Block.

    Args:
        include_solutions: Lösungsfassung (entscheidet über die Lückendarstellung).
    """

    def __init__(self, include_solutions: bool = False):
        """Legt eine leere Zeichenfläche an; die Größe ergibt sich beim Abschluss."""
        self.include_solutions = include_solutions
        self.parts: list[str] = []
        self.has_gap = False

    def _shape(self, tag: str, attributes: str, css: str = "diagram-line") -> None:
        """Hängt ein SVG-Element mit der Linienklasse `css` an."""
        self.parts.append(f"<{tag} class='{css}' {attributes} />")

    def line(self, x1, y1, x2, y2, dashed: bool = False) -> None:
        """Gerade Linie, optional gestrichelt."""
        css = "diagram-line diagram-dashed" if dashed else "diagram-line"
        self._shape("line", f"x1='{_attr(x1)}' y1='{_attr(y1)}' x2='{_attr(x2)}' y2='{_attr(y2)}'", css)

    def polyline(self, points, dashed: bool = False) -> None:
        """Streckenzug durch `points`."""
        css = "diagram-line diagram-dashed" if dashed else "diagram-line"
        self._shape("polyline", f"points='{_points(points)}'", css)

    def path(self, data: str, dashed: bool = False) -> None:
        """Beliebiger SVG-Pfad (z. B. Kurven für Schleifen)."""
        css = "diagram-line diagram-dashed" if dashed else "diagram-line"
        self._shape("path", f"d='{data}'", css)

    def rect(self, cx, cy, width, height, radius: float = 0.0, css: str = "diagram-line") -> None:
        """Rechteck um den Mittelpunkt `(cx, cy)`."""
        corner = f" rx='{_attr(radius)}'" if radius else ""
        self._shape(
            "rect",
            f"x='{_attr(cx - width / 2)}' y='{_attr(cy - height / 2)}' width='{_attr(width)}' height='{_attr(height)}'{corner}",
            css,
        )

    def ellipse(self, cx, cy, rx, ry, css: str = "diagram-shape") -> None:
        """Ellipse (mit Papierfüllung, damit sie Linien überdeckt)."""
        self._shape("ellipse", f"cx='{_attr(cx)}' cy='{_attr(cy)}' rx='{_attr(rx)}' ry='{_attr(ry)}'", css)

    def polygon(self, points, css: str = "diagram-shape") -> None:
        """Geschlossenes Vieleck (mit Papierfüllung)."""
        self._shape("polygon", f"points='{_points(points)}'", css)

    def arrow(self, tip, tail, kind: str = "open") -> None:
        """Pfeilspitze an `tip`, ausgerichtet von `tail` nach `tip`.

        Args:
            tip: Spitze.
            tail: Punkt auf der Linie davor (bestimmt nur die Richtung).
            kind: `open` (zwei Striche), `solid` (gefüllt) oder `hollow` (Dreieck mit
                Papierfüllung, für Vererbung).
        """
        angle = math.atan2(tip[1] - tail[1], tip[0] - tail[0])
        base_x = tip[0] - ARROW_LENGTH * math.cos(angle)
        base_y = tip[1] - ARROW_LENGTH * math.sin(angle)
        left = (base_x + ARROW_HALF_WIDTH * math.sin(angle), base_y - ARROW_HALF_WIDTH * math.cos(angle))
        right = (base_x - ARROW_HALF_WIDTH * math.sin(angle), base_y + ARROW_HALF_WIDTH * math.cos(angle))
        if kind == "open":
            self.polyline([left, tip, right])
        elif kind == "solid":
            self.polygon([left, tip, right], "diagram-solid")
        else:
            self.polygon([left, tip, right], "diagram-shape")

    def label(self, content, cx, cy, width, height=LINE_HEIGHT, align: str = "center", wrap: bool = False, weight: str = "") -> None:
        """Beschriftung als `foreignObject`, zentriert um `(cx, cy)`.

        Args:
            content: `Cell` oder reiner Text (wird zur Zelle ohne Marker).
            cx: Mittelpunkt x.
            cy: Mittelpunkt y.
            width: Breite des Felds.
            height: Höhe des Felds.
            align: `center`, `left` oder `right`.
            wrap: Text darf umbrechen (sonst bleibt er einzeilig und läuft über).
            weight: `bold` für Überschriften.
        """
        cell = content if isinstance(content, Cell) else make_cell(str(content))
        html, has_gap = render_cell(cell, self.include_solutions)
        if not html:
            return
        self.has_gap = self.has_gap or has_gap
        classes = ["diagram-label", f"diagram-{align}"]
        if wrap:
            classes.append("diagram-wrap")
        if weight == "bold":
            classes.append("diagram-bold")
        if has_gap:
            classes.append("diagram-gap")
        self.parts.append(
            f"<foreignObject x='{_attr(cx - width / 2)}' y='{_attr(cy - height / 2)}' width='{_attr(width)}' height='{_attr(height)}'>"
            f"<div xmlns='http://www.w3.org/1999/xhtml' class='{' '.join(classes)}'><span>{html}</span></div></foreignObject>"
        )

    def finish(self, name: str, options, width: float, height: float, header: str = "") -> str:
        """Schließt den Block ab.

        Args:
            name: Blockname (für die CSS-Klasse).
            options: Blockoptionen (`width`).
            width: Breite der Zeichenfläche; so breit wird das Diagramm höchstens.
            height: Höhe der Zeichenfläche.
            header: Fertiges HTML über dem Diagramm.
        """
        size = f"width:{_attr(width)}px;" if not width_style(options) else width_style(options)
        return (
            f"<div class='diagram diagram-{escape(name)}'>{header}"
            f"<svg class='diagram-svg' style='{size}' viewBox='0 0 {_attr(width)} {_attr(height)}' xmlns='http://www.w3.org/2000/svg'>"
            f"{''.join(self.parts)}</svg></div>"
        )
