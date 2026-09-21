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
