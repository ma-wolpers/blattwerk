"""Label-Layout für `:::geometry` (`labels=auto|fixed`): semantische Invarianten statt Koordinaten.

Geprüft wird am Szenenmodell (dieselben Bausteine wie Renderer und Validator):
Label-Boxen überlappen nicht, Punktkreuze und Linien werden nicht überdeckt,
freie Standardpositionen bleiben, Flächenlabels liegen innen, Achsennamen
bleiben nahe ihrer Pfeilspitze, das Ergebnis ist deterministisch. Mit
`labels=fixed` gelten die bisherigen festen Positionen.
"""

from __future__ import annotations

import fitz
import pytest
import yaml

from app.core.answer_grid_frame import resolve_geometry_frame
from app.core.answer_grid_label_candidates import AXIS_NAME_MAX_GAP
from app.core.answer_grid_label_geometry import (
    boxes_intersection_area,
    distance_point_to_box,
    point_in_polygon,
    segment_length_inside,
)
from app.core.answer_grid_label_layout import layout_labels
from app.core.answer_grid_label_model import TIER_POINT, estimate_text_width, text_box
from app.core.answer_grid_plot import render_geometry_answer
from app.core.answer_grid_primitives import build_geometry_scene
from app.core.blatt_validator import inspect_markdown_text

AXIS = {"axis": "true", "origin": "5,4", "width": "12", "height": "8"}
HEAD = "---\ndocument_type: worksheet\nTitel: T\nFach: M\nThema: X\n---\n"


def _layout(options, content, include_solutions=False):
    frame = resolve_geometry_frame(options)
    scene = build_geometry_scene(options, yaml.safe_load(content) or {}, frame.height_units, frame.width_units, include_solutions)
    placement = layout_labels(scene.labels, scene.obstacles, frame.width_units, frame.height_units, frame.bleed_units, options.get("labels"))
    boxes = {spec.text: text_box(spec, *position) for spec, position in zip(scene.labels, placement.positions) if spec.movable}
    return scene, placement, boxes


def _assert_no_label_overlap(boxes):
    names = sorted(boxes)
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            assert boxes_intersection_area(boxes[first], boxes[second]) == 0, (first, second)


def test_close_points_get_non_overlapping_labels():
    _scene, placement, boxes = _layout(AXIS, "points:\n  - {x: 1, y: 2, label: A}\n  - {x: 1.2, y: 2.1, label: B}\n")
    _assert_no_label_overlap(boxes)
    assert placement.unresolved == []


def test_no_label_covers_any_point_cross():
    content = "points:\n" + "".join(f"  - {{x: {x}, y: {y}, label: P{i}}}\n" for i, (x, y) in enumerate([(0, 1), (1, 1), (0.5, 1.6), (1, 0.4)]))
    scene, _placement, boxes = _layout(AXIS, content)
    crosses = [obstacle for obstacle in scene.obstacles if obstacle.tier == TIER_POINT]
    specs = {spec.text: spec for spec in scene.labels}
    for name, box in boxes.items():
        for cross in crosses:
            assert segment_length_inside(box, *cross.coords) == 0, (name, cross.owner, specs[name].owner)
    _assert_no_label_overlap(boxes)


def test_segment_label_does_not_cross_its_horizontal_segment():
    scene, _placement, boxes = _layout({"width": "10", "height": "6"}, "pairs:\n  - {x1: 1, y1: 3, x2: 9, y2: 3, label: s}\n")
    segment = next(obstacle for obstacle in scene.obstacles if obstacle.shape == "segment")
    assert segment_length_inside(boxes["s"], *segment.coords) == 0


def test_free_default_position_is_kept():
    scene, placement, _boxes = _layout({"width": "10", "height": "6"}, "points:\n  - {col: 3, row: 3, label: A}\n")
    spec = scene.labels[0]
    assert placement.positions[0] == (spec.x, spec.y)


def test_labels_fixed_keeps_legacy_positions_even_when_overlapping():
    options = {**AXIS, "labels": "fixed"}
    scene, placement, _boxes = _layout(options, "points:\n  - {x: 1, y: 2, label: A}\n  - {x: 1.2, y: 2.1, label: B}\n")
    assert placement.positions == [(spec.x, spec.y) for spec in scene.labels]
    html = render_geometry_answer(options, "points:\n  - {x: 1, y: 2, label: A}\n", False, lambda text: text)
    assert "x='6.2400' y='1.7600'>A</text>" in html


def test_area_label_stays_inside_polygon_and_protects_inner_point():
    content = (
        "polygons:\n  - {vertices: [{x: 1, y: 1}, {x: 7, y: 1}, {x: 4, y: 7}], label: Dreieck}\n"
        "points:\n  - {x: 4, y: 3, label: M}\n"
    )
    scene, _placement, boxes = _layout({"width": "8", "height": "8"}, content)
    polygon = next(spec for spec in scene.labels if spec.text == "Dreieck")
    cx, cy = (boxes["Dreieck"][0] + boxes["Dreieck"][2]) / 2, (boxes["Dreieck"][1] + boxes["Dreieck"][3]) / 2
    assert point_in_polygon(cx, cy, polygon.area)
    cross = [obstacle for obstacle in scene.obstacles if obstacle.tier == TIER_POINT]
    assert all(segment_length_inside(boxes["Dreieck"], *obstacle.coords) == 0 for obstacle in cross)
    _assert_no_label_overlap(boxes)


def test_axis_names_stay_near_their_arrow_tip():
    options = {**AXIS, "axis_label_x": "t", "axis_label_y": "v in km/h"}
    scene, _placement, boxes = _layout(options, "points:\n  - {x: 6, y: 3, label: A}\n")
    for spec in scene.labels:
        if spec.kind == "axis_name":
            assert distance_point_to_box(spec.anchor[0], spec.anchor[1], boxes[spec.text]) <= AXIS_NAME_MAX_GAP


def test_layout_is_deterministic():
    content = "points:\n" + "".join(f"  - {{x: {i * 0.3}, y: {i * 0.2}, label: Q{i}}}\n" for i in range(8))
    first = render_geometry_answer(dict(AXIS), content, False, lambda text: text)
    second = render_geometry_answer(dict(AXIS), content, False, lambda text: text)
    assert first == second


def test_crowded_scene_reports_an019_and_fixed_does_not():
    crowd = "points:\n" + "".join(f"  - {{col: 1, row: 1, label: Langer Name {i}}}\n" for i in range(6))
    body = ":::geometry width=2 height=2\n" + crowd + ":::\n"
    assert "AN019" in [d.code for d in inspect_markdown_text(HEAD + body).diagnostics]
    fixed = ":::geometry width=2 height=2 labels=fixed\n" + crowd + ":::\n"
    assert "AN019" not in [d.code for d in inspect_markdown_text(HEAD + fixed).diagnostics]


def test_labels_option_is_validated():
    body = ":::geometry width=4 height=3 labels=wild\npoints:\n  - {col: 1, row: 1, label: A}\n:::\n"
    assert "OP002" in [d.code for d in inspect_markdown_text(HEAD + body).diagnostics]


@pytest.mark.parametrize("text", ["A", "P1", "Strecke g", "f(x)", "v in km/h", "WWW", "MMm", "Dreieck"])
def test_width_estimate_is_at_least_helvetica_bold(text):
    assert estimate_text_width(text, 1.0) >= fitz.get_text_length(text, fontname="hebo", fontsize=1.0)
