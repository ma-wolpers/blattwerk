import re

from app.core.blatt_kern_answer_table import _render_answer_block


def test_grid_scale_option_sets_cell_size_variable():
    html = _render_answer_block(
        {"type": "grid_field", "rows": "2", "cols": "2", "scale": "0.4cm"},
        "",
        include_solutions=False,
    )

    assert "--cell-size:0.4cm" in html


def test_grid_scale_defaults_to_half_centimeter():
    html = _render_answer_block(
        {"type": "grid_field", "rows": "2", "cols": "2"},
        "",
        include_solutions=False,
    )

    assert "--cell-size:0.5cm" in html


def test_grid_scale_invalid_value_falls_back_to_default():
    html = _render_answer_block(
        {"type": "grid_field", "rows": "2", "cols": "2", "scale": "gross"},
        "",
        include_solutions=False,
    )

    assert "--cell-size:0.5cm" in html


def test_grid_axis_renders_ticks_and_labels_by_default():
    html = _render_answer_block(
        {
            "type": "grid_system",
            "rows": "10",
            "cols": "10",
            "axis": "true",
            "origin": "5,5",
            "step_x": "1",
            "step_y": "1",
        },
        "",
        include_solutions=False,
    )

    assert "grid-axis" in html
    assert "grid-axis-tick" in html
    assert "grid-axis-label" in html


def test_grid_axis_label_density_is_reduced_for_large_grids():
    html = _render_answer_block(
        {
            "type": "grid_system",
            "rows": "40",
            "cols": "40",
            "axis": "true",
            "origin": "20,20",
            "step_x": "1",
            "step_y": "1",
        },
        "",
        include_solutions=False,
    )

    x_label_count = html.count("class='grid-axis-label'")
    y_label_count = html.count("class='grid-axis-label grid-axis-label-y'")

    assert x_label_count <= 12
    assert y_label_count <= 12
    assert x_label_count > 0
    assert y_label_count > 0


def test_grid_axis_origin_outside_grid_clamps_visual_axis_only():
    html = _render_answer_block(
        {
            "type": "grid_system",
            "rows": "10",
            "cols": "10",
            "axis": "true",
            "origin": "-3,14",
            "step_x": "1",
            "step_y": "1",
        },
        "",
        include_solutions=False,
    )

    assert "<line class='grid-axis' x1='0' y1='10.0000' x2='10.0000' y2='10.0000' />" in html
    assert "<line class='grid-axis' x1='0.0000' y1='0' x2='0.0000' y2='10.0000' />" in html
    assert ">3</text>" in html
    assert ">14</text>" in html


def test_grid_axis_positive_y_points_upward():
    html = _render_answer_block(
        {
            "type": "grid_system",
            "rows": "10",
            "cols": "10",
            "axis": "true",
            "origin": "5,5",
            "step_x": "1",
            "step_y": "1",
        },
        """
points:
  - {x: 0, y: 1, label: P}
  - {x: 0, y: -1, label: N}
""",
        include_solutions=False,
    )

    p_match = re.search(
        r"<text class='grid-point-label grid-mode-both' x='[0-9.\-]+' y='([0-9.\-]+)'>P</text>",
        html,
    )
    n_match = re.search(
        r"<text class='grid-point-label grid-mode-both' x='[0-9.\-]+' y='([0-9.\-]+)'>N</text>",
        html,
    )

    assert p_match is not None
    assert n_match is not None
    assert float(p_match.group(1)) < float(n_match.group(1))
