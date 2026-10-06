"""Geometry-Konvention: (0, 0) ist die linke untere Ecke, die Zeile zählt von unten.

Gilt für `origin` (Achsenmodus) und für alle Sektionen ohne Achse, auch
`points[].col`/`row` (bis 2026-10-06 zählten beide von oben).
"""

from __future__ import annotations

import re

from app.core.answer_grid_axis import origin_to_canvas
from app.core.answer_grid_plot import render_geometry_answer


def _render(options, content):
    return render_geometry_answer({"width": "10", "height": "10", **options}, content, False, False)


def _point_center(svg):
    """Mittelpunkt der Punktmarkierung (ein Kreuz aus zwei Linien `grid-point`)."""
    match = re.search(r"class='grid-point[^']*' x1='([0-9.\-]+)' y1='([0-9.\-]+)' x2='([0-9.\-]+)' y2='([0-9.\-]+)'", svg)
    assert match, svg
    x1, y1, x2, y2 = (float(value) for value in match.groups())
    return round((x1 + x2) / 2, 4), round((y1 + y2) / 2, 4)


def test_origin_to_canvas_counts_rows_from_bottom():
    assert origin_to_canvas((0.0, 0.0), 10) == (0.0, 10.0)
    assert origin_to_canvas((3.0, 7.0), 10) == (3.0, 3.0)
    assert origin_to_canvas(None, 10) is None


def test_axis_origin_zero_zero_is_bottom_left_corner():
    svg = _render({"axis": "true", "origin": "0,0"}, "")
    assert "<line class='grid-axis' x1='0' y1='10.0000' x2='10.0000' y2='10.0000' />" in svg
    assert "<line class='grid-axis' x1='0.0000' y1='0' x2='0.0000' y2='10.0000' />" in svg


def test_axis_point_above_origin_is_drawn_higher():
    svg = _render({"axis": "true", "origin": "2,3"}, "points:\n  - {x: 0, y: 2}\n")
    assert _point_center(svg) == (2.0, 5.0)  # Zeile 3+2 = 5 von unten -> SVG-y 10-5


def test_points_without_axis_use_bottom_left_like_other_sections():
    svg = _render({}, "points:\n  - {col: 1, row: 2}\n")
    assert _point_center(svg) == (1.0, 8.0)
    svg_alias = _render({}, "points:\n  - {x: 1, y: 2}\n")
    assert _point_center(svg_alias) == (1.0, 8.0)
