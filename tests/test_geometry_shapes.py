"""Tests für die neuen `:::geometry`-Objekttypen `polygons`/`circles`."""

from app.core.blatt_kern_answer_dispatch import _render_answer_block


def test_polygon_valid_triangle_renders_as_polygon_element():
    html = _render_answer_block(
        {"type": "geometry", "width": "10", "height": "10"},
        "polygons:\n  - {vertices: [{x: 0, y: 0}, {x: 4, y: 0}, {x: 2, y: 4}]}\n",
        include_solutions=False,
    )
    assert "grid-polygon" in html
    assert "<polygon" in html


def test_polygon_valid_pentagon_renders():
    html = _render_answer_block(
        {"type": "geometry", "width": "10", "height": "10"},
        "polygons:\n  - {vertices: [{x: 0, y: 0}, {x: 2, y: 0}, {x: 3, y: 2}, {x: 1, y: 4}, {x: -1, y: 2}]}\n",
        include_solutions=False,
    )
    assert "grid-polygon" in html


def test_polygon_one_invalid_vertex_rejects_entire_entry_not_just_the_point():
    # 5 vertices, one malformed -- must NOT silently render a repaired 4-vertex polygon.
    html = _render_answer_block(
        {"type": "geometry", "width": "10", "height": "10"},
        "polygons:\n"
        "  - vertices:\n"
        "      - {x: 0, y: 0}\n"
        "      - {x: 4, y: 0}\n"
        "      - {x: bad, y: 4}\n"
        "      - {x: 4, y: 4}\n"
        "      - {x: 0, y: 4}\n",
        include_solutions=False,
    )
    assert "grid-polygon" not in html


def test_polygon_fewer_than_three_valid_vertices_is_not_rendered():
    html = _render_answer_block(
        {"type": "geometry", "width": "10", "height": "10"},
        "polygons:\n  - {vertices: [{x: 0, y: 0}, {x: 1, y: 1}]}\n",
        include_solutions=False,
    )
    assert "grid-polygon" not in html


def test_polygon_concave_label_at_true_centroid_not_vertex_mean():
    # Grid-space (already flipped) vertices A(0,0) B(2,1) C(4,0) D(2,4).
    # Hand-computed shoelace centroid: (2.0, 1.6667). Vertex mean would be (2.0, 1.25).
    # With height=10 (canvas_height), feed y = 10 - target_y so coord_system.point()
    # (bottom-left, y-up) maps back to the exact grid-space example above.
    html = _render_answer_block(
        {"type": "geometry", "width": "10", "height": "10"},
        "polygons:\n"
        "  - vertices:\n"
        "      - {x: 0, y: 10}\n"
        "      - {x: 2, y: 9}\n"
        "      - {x: 4, y: 10}\n"
        "      - {x: 2, y: 6}\n"
        "    label: 'S'\n",
        include_solutions=False,
    )
    assert "x='2.0000' y='1.6667'" in html
    assert "x='2.0000' y='1.2500'" not in html


def test_polygon_self_intersecting_is_accepted_and_rendered():
    html = _render_answer_block(
        {"type": "geometry", "width": "10", "height": "10"},
        "polygons:\n  - {vertices: [{x: 0, y: 0}, {x: 4, y: 4}, {x: 4, y: 0}, {x: 0, y: 4}]}\n",
        include_solutions=False,
    )
    assert "grid-polygon" in html


def test_polygon_fill_is_rendered_in_style_attribute():
    html = _render_answer_block(
        {"type": "geometry", "width": "10", "height": "10"},
        "polygons:\n  - {vertices: [{x: 0, y: 0}, {x: 4, y: 0}, {x: 2, y: 4}], fill: '#00ff00'}\n",
        include_solutions=False,
    )
    assert "fill:#00ff00" in html


def test_polygon_invalid_fill_is_not_emitted_into_style_attribute():
    html = _render_answer_block(
        {"type": "geometry", "width": "10", "height": "10"},
        "polygons:\n  - {vertices: [{x: 0, y: 0}, {x: 4, y: 0}, {x: 2, y: 4}], fill: 'red;}body{display:none'}\n",
        include_solutions=True,
    )
    assert "red;}body{display:none" not in html
    assert "display:none" not in html


def test_polygon_axis_mode_uses_math_coordinates():
    html = _render_answer_block(
        {"type": "geometry", "width": "10", "height": "10", "axis": "true", "origin": "5,5"},
        "polygons:\n  - {vertices: [{x: 0, y: 0}, {x: 2, y: 0}, {x: 0, y: 2}]}\n",
        include_solutions=False,
    )
    # origin (5,5): (0,0)->(5,5), (2,0)->(7,5), (0,2)->(5,3)
    assert "5.0000,5.0000" in html
    assert "7.0000,5.0000" in html
    assert "5.0000,3.0000" in html


# Circles/arcs -- setup shared by the worked examples below: cx=5, cy=5, r=2,
# no axis, height=10 -> coord_system.point(5, 5) = (5, 10-5) = (5, 5), rx=ry=2.

def _render_circle(payload_line, **extra_options):
    options = {"type": "geometry", "width": "10", "height": "10", **extra_options}
    return _render_answer_block(options, f"circles:\n  - {payload_line}\n", include_solutions=False)


def test_circle_full_no_angles_renders_circle_element():
    html = _render_circle("{cx: 5, cy: 5, r: 2}")
    assert "<circle class='grid-circle grid-mode-both' cx='5.0000' cy='5.0000' r='2.0000' />" in html


def test_circle_quarter_arc_0_to_90_matches_hand_computed_coordinates():
    html = _render_circle("{cx: 5, cy: 5, r: 2, start_angle: 0, end_angle: 90}")
    assert "d='M 7.0000 5.0000 A 2.0000 2.0000 0 0 0 5.0000 3.0000'" in html


def test_circle_arc_350_to_10_wraps_short_way_large_arc_flag_zero():
    html = _render_circle("{cx: 5, cy: 5, r: 2, start_angle: 350, end_angle: 10}")
    assert "d='M 6.9696 5.3473 A 2.0000 2.0000 0 0 0 6.9696 4.6527'" in html


def test_circle_arc_10_to_350_wraps_long_way_large_arc_flag_one():
    html = _render_circle("{cx: 5, cy: 5, r: 2, start_angle: 10, end_angle: 350}")
    assert "d='M 6.9696 4.6527 A 2.0000 2.0000 0 1 0 6.9696 5.3473'" in html


def test_circle_reflex_arc_0_to_270_large_arc_flag_one():
    html = _render_circle("{cx: 5, cy: 5, r: 2, start_angle: 0, end_angle: 270}")
    assert "d='M 7.0000 5.0000 A 2.0000 2.0000 0 1 0 5.0000 7.0000'" in html


def test_circle_negative_start_angle_minus90_to_0():
    html = _render_circle("{cx: 5, cy: 5, r: 2, start_angle: -90, end_angle: 0}")
    assert "d='M 5.0000 7.0000 A 2.0000 2.0000 0 0 0 7.0000 5.0000'" in html


def test_circle_angle_over_360_degrees_equivalent_to_normalized():
    html = _render_circle("{cx: 5, cy: 5, r: 2, start_angle: 0, end_angle: 450}")
    assert "d='M 7.0000 5.0000 A 2.0000 2.0000 0 0 0 5.0000 3.0000'" in html


def test_circle_start_equals_end_angle_renders_full_circle():
    html = _render_circle("{cx: 5, cy: 5, r: 2, start_angle: 45, end_angle: 45}")
    assert "<circle class='grid-circle grid-mode-both' cx='5.0000' cy='5.0000' r='2.0000' />" in html
    assert "grid-arc" not in html


def test_circle_only_start_angle_set_is_not_rendered():
    html = _render_circle("{cx: 5, cy: 5, r: 2, start_angle: 0}")
    assert "grid-circle" not in html
    assert "grid-arc" not in html


def test_circle_only_end_angle_set_is_not_rendered():
    html = _render_circle("{cx: 5, cy: 5, r: 2, end_angle: 90}")
    assert "grid-circle" not in html
    assert "grid-arc" not in html


def test_circle_missing_radius_is_not_rendered():
    html = _render_circle("{cx: 1, cy: 1}")
    assert "grid-circle" not in html
    assert "grid-arc" not in html


def test_circle_differing_step_x_step_y_renders_ellipse():
    html = _render_answer_block(
        {
            "type": "geometry",
            "width": "10",
            "height": "10",
            "axis": "true",
            "origin": "5,5",
            "step_x": "2",
            "step_y": "1",
        },
        "circles:\n  - {cx: 0, cy: 0, r: 4}\n",
        include_solutions=False,
    )
    assert "<ellipse class='grid-circle grid-mode-both' cx='5.0000' cy='5.0000' rx='2.0000' ry='4.0000' />" in html


def test_circle_label_is_rendered_at_center():
    html = _render_circle("{cx: 5, cy: 5, r: 2, label: 'K'}")
    assert "grid-circle-label" in html
    assert "x='5.0000' y='5.0000'>K</text>" in html


def test_circle_invalid_fill_is_not_emitted_into_style_attribute():
    html = _render_answer_block(
        {"type": "geometry", "width": "10", "height": "10"},
        "circles:\n  - {cx: 1, cy: 1, r: 1, fill: 'red;}body{display:none'}\n",
        include_solutions=True,
    )
    assert "red;}body{display:none" not in html
    assert "display:none" not in html
