"""Pfeilspitzen und Achsennamen des Geometry-Koordinatensystems.

Ausgelagert aus `answer_grid_axis.py` (300-Zeilen-Konvention). Liefert die
Pfeilspitzen als SVG-Shapes, die Achsennamen als `LabelSpec`s (Standardposition
= bisheriger fester Versatz) und Hindernisse für das Label-Layout: Pfeilspitzen
zählen wie Linien (`TIER_LINE`). Die Achsennamen dürfen sich im Layout nur in
einem festen Radius um ihre Pfeilspitze bewegen (`kind="axis_name"`).
"""

from __future__ import annotations

from .answer_grid_label_model import TIER_LINE, LabelSpec, Obstacle, stroke_pad

_AXIS_STROKE_PX = 0.9


def _render_axis_arrowheads_and_names(origin_x, origin_y, cols, rows, axis_label_x, axis_label_y):
    """Rendert Pfeilspitzen am positiven Achsenende und beschreibt die Achsennamen (z. B. `x`, `y`).

    Pfeilspitzen werden nur gezeichnet, wenn zwischen Ursprung und Rasterrand
    genug Platz ist (`x_base < x_tip` / `y_tip < y_base`) — bei sehr kleinen
    Rastern oder einem Ursprung nahe am Rand würde eine erzwungene Pfeilspitze
    sonst invertiert oder verzerrt wirken.

    Liefert `(shapes, label_specs, obstacles)`: die Achsennamen
    (`axis_label_x`/`axis_label_y`) sind Text-Labels wie jedes andere
    Geometry-Label und gehören in der Z-Order ganz nach oben, nicht in die
    Achsen-Bodenschicht -- nur die Pfeilspitzen selbst bleiben unten. Der
    Anker eines Namens ist die Spitze seiner Achse.
    """
    shapes, labels, obstacles = [], [], []
    pad = stroke_pad(_AXIS_STROKE_PX)

    x_tip = float(cols) + 0.34
    x_base = max(origin_x + 0.24, x_tip - 0.44)
    x_top = max(0.04, origin_y - 0.18)
    x_bottom = min(float(rows) - 0.04, origin_y + 0.18)
    if x_base < x_tip:
        shapes.append(
            "<polygon class='grid-axis' points='"
            f"{x_tip:.4f},{origin_y:.4f} {x_base:.4f},{x_top:.4f} {x_base:.4f},{x_bottom:.4f}' />"
        )
        obstacles.append(Obstacle(TIER_LINE, "rect", (x_base, x_top, x_tip, x_bottom), pad, ("axis_name", (x_tip, origin_y))))
    if axis_label_x:
        labels.append(LabelSpec(
            text=axis_label_x, css_class="grid-axis-label grid-axis-name",
            x=x_tip + 0.16, y=origin_y - 0.28, kind="axis_name", anchor=(x_tip, origin_y),
            extra_attrs=" text-anchor='start'",
        ))

    y_tip = -0.34
    y_base = min(origin_y - 0.24, y_tip + 0.44)
    y_left = max(0.04, origin_x - 0.18)
    y_right = min(float(cols) - 0.04, origin_x + 0.18)
    if y_tip < y_base:
        shapes.append(
            "<polygon class='grid-axis' points='"
            f"{origin_x:.4f},{y_tip:.4f} {y_left:.4f},{y_base:.4f} {y_right:.4f},{y_base:.4f}' />"
        )
        obstacles.append(Obstacle(TIER_LINE, "rect", (y_left, y_tip, y_right, y_base), pad, ("axis_name", (origin_x, y_tip))))
    if axis_label_y:
        labels.append(LabelSpec(
            text=axis_label_y, css_class="grid-axis-label grid-axis-name",
            x=origin_x - 0.1, y=y_tip - 0.9, kind="axis_name", anchor=(origin_x, y_tip),
            extra_attrs=" text-anchor='end'",
        ))

    return shapes, labels, obstacles
