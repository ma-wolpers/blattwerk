"""Invarianten der Mathe-Koordinaten: intern y nach oben, genau eine Umrechnung fürs SVG."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.answer_grid_axis import _clamp_axis_origin, _iter_axis_tick_positions
from app.core.answer_grid_coords import to_svg
from app.core.answer_grid_entries import _GeometryCoordinateSystem
from app.core.answer_grid_plot import render_geometry_answer

APP_CORE = Path(__file__).resolve().parents[1] / "app" / "core"


def _render(options, content):
    return render_geometry_answer({"width": "10", "height": "10", **options}, content, False, lambda *_args: "")


def _point_center(svg):
    x1, y1, x2, y2 = re.search(r"class='grid-point[^']*' x1='([\d.\-]+)' y1='([\d.\-]+)' x2='([\d.\-]+)' y2='([\d.\-]+)'", svg).groups()
    return (float(x1) + float(x2)) / 2, (float(y1) + float(y2)) / 2


def test_to_svg_inverts_y_only():
    assert to_svg(3.0, 7.0, 10) == (3.0, 3.0)
    assert to_svg(3.0, 0.0, 10) == (3.0, 10.0)
    assert to_svg(*to_svg(1.5, 2.5, 10), 10) == (1.5, 2.5)


def test_coordinate_system_stays_in_math_space():
    plain = _GeometryCoordinateSystem(axis_active=False, origin=None, step_x=1.0, step_y=1.0)
    assert plain.point(2.0, 3.0) == (2.0, 3.0)
    axis = _GeometryCoordinateSystem(axis_active=True, origin=(1.0, 2.0), step_x=2.0, step_y=0.5)
    assert axis.point(4.0, 1.0) == (3.0, 4.0)


def test_only_the_coords_module_inverts_y():
    """Die frühere zweite und dritte Umrechnung dürfen nicht zurückkehren."""
    for path in APP_CORE.glob("answer_grid_*.py"):
        source = path.read_text(encoding="utf-8")
        assert "canvas_height" not in source and "origin_to_canvas" not in source, path.name
        if path.name != "answer_grid_coords.py":
            assert not re.search(r"return .*float\(rows\) - ", source), path.name


@pytest.mark.parametrize("options", [{}, {"axis": "true", "origin": "2,3"}, {"axis": "true", "origin": "1.5,2.5", "step_y": "0.5"}])
def test_larger_y_is_drawn_higher(options):
    low = _point_center(_render(options, "points:\n  - {x: 1, y: 1}\n"))
    high = _point_center(_render(options, "points:\n  - {x: 1, y: 2}\n"))
    assert high[1] < low[1] and high[0] == low[0]


@pytest.mark.parametrize("origin", ["5,5", "2,7", "1.5,2.5"])
def test_radii_do_not_depend_on_the_origin(origin):
    svg = _render({"axis": "true", "origin": origin, "step_x": "1", "step_y": "2"}, "circles:\n  - {cx: 0, cy: 0, r: 2}\n  - {cx: 0, cy: 0, r: 1, start_angle: 0, end_angle: 90}\n")
    assert "rx='2.0000' ry='1.0000'" in svg
    assert " A 1.0000 0.5000 0 0 0 " in svg


def test_arc_at_90_degrees_ends_above_its_center():
    svg = _render({}, "circles:\n  - {cx: 5, cy: 5, r: 2, start_angle: 0, end_angle: 90}\n")
    assert "d='M 7.0000 5.0000 A 2.0000 2.0000 0 0 0 5.0000 3.0000'" in svg


def test_ticks_carry_math_values_and_mirror_with_the_origin():
    ticks = _iter_axis_tick_positions(3.0, 10, 1.0)
    assert (5.0, 2.0) in ticks and (0.0, -3.0) in ticks and (10.0, 7.0) in ticks
    down = _iter_axis_tick_positions(3.0, 10, 1.0, descending=True)
    assert down == list(reversed(ticks))
    mirrored = {(10 - position, -value) for position, value in _iter_axis_tick_positions(7.0, 10, 1.0)}
    assert mirrored == set(ticks)


def test_y_axis_tick_labels_show_math_values():
    svg = _render({"axis": "true", "origin": "0,2"}, "")
    assert re.search(r"grid-axis-label-y'[^>]* y='3\.0400'[^>]*>5</text>", svg)  # y=5: Zeile 7 von unten


def test_clamp_keeps_a_far_away_origin_on_the_visible_edge():
    assert _clamp_axis_origin(20.0, -4.0, 10, 10) == (10.0, 0.0)
    assert _clamp_axis_origin(3.0, 4.0, 10, 10) == (3.0, 4.0)
    svg = _render({"axis": "true", "origin": "3,-4"}, "")
    assert "<line class='grid-axis' x1='0' y1='10.0000' x2='10.0000' y2='10.0000' />" in svg
