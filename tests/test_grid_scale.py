import re

from app.core.blatt_kern_answer_table import _render_answer_block
from app.styles.blatt_styles import resolve_printable_width_cm


def test_grid_scale_option_sets_cell_size_variable():
    html = _render_answer_block(
        {"type": "grid", "rows": "2", "cols": "2", "scale": "0.4cm"},
        "",
        include_solutions=False,
    )

    assert "--cell-size:0.4cm" in html
    assert "class='grid-overlay-bg'" in html


def test_grid_scale_defaults_to_half_centimeter():
    html = _render_answer_block(
        {"type": "grid", "rows": "2", "cols": "2"},
        "",
        include_solutions=False,
    )

    assert "--cell-size:0.5cm" in html


def test_grid_scale_invalid_value_falls_back_to_default():
    html = _render_answer_block(
        {"type": "grid", "rows": "2", "cols": "2", "scale": "gross"},
        "",
        include_solutions=False,
    )

    assert "--cell-size:0.5cm" in html


def test_grid_without_cols_uses_auto_computed_column_count_for_default_scale():
    html = _render_answer_block(
        {"type": "grid", "rows": "8"},
        "",
        include_solutions=False,
    )

    assert "--cell-size:0.5cm" in html
    assert "--cols:36" in html


def test_grid_without_cols_uses_auto_computed_column_count_for_custom_scale():
    html = _render_answer_block(
        {"type": "grid", "rows": "8", "scale": "1cm"},
        "",
        include_solutions=False,
    )

    assert "--cell-size:1cm" in html
    assert "--cols:18" in html


def test_geometry_without_cols_keeps_default_column_count():
    html = _render_answer_block(
        {"type": "geometry", "rows": "8"},
        "",
        include_solutions=False,
    )

    assert "--cell-size:0.5cm" in html
    assert "--cols:20" in html


def test_grid_without_cols_uses_layout_context_for_page_format_and_hole_punch():
    a4_default_width = resolve_printable_width_cm("a4_portrait", hole_punch_enabled=False)
    a4_hole_width = resolve_printable_width_cm("a4_portrait", hole_punch_enabled=True)
    a5_landscape_width = resolve_printable_width_cm("a5_landscape", hole_punch_enabled=False)

    html_a4_default = _render_answer_block(
        {"type": "grid", "rows": "8", "_printable_width_cm": a4_default_width},
        "",
        include_solutions=False,
    )
    html_a4_hole = _render_answer_block(
        {
            "type": "grid",
            "rows": "8",
            "_printable_width_cm": a4_hole_width,
        },
        "",
        include_solutions=False,
    )
    html_a5_landscape = _render_answer_block(
        {"type": "grid", "rows": "8", "_printable_width_cm": a5_landscape_width},
        "",
        include_solutions=False,
    )

    assert "--cols:36" in html_a4_default
    assert "--cols:35" in html_a4_hole
    assert "--cols:39" in html_a5_landscape


def test_resolve_printable_width_cm_reflects_page_and_margin_profiles():
    assert resolve_printable_width_cm("a4_portrait", hole_punch_enabled=False) == 18.0
    assert resolve_printable_width_cm("a4_portrait", hole_punch_enabled=True) == 17.8
    assert round(resolve_printable_width_cm("a5_landscape", hole_punch_enabled=False), 4) == 19.8


def test_grid_axis_renders_ticks_and_labels_by_default():
    html = _render_answer_block(
        {
            "type": "geometry",
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
    assert "class='grid-overlay-bg'" in html


def test_grid_axis_label_density_is_reduced_for_large_grids():
    html = _render_answer_block(
        {
            "type": "geometry",
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
            "type": "geometry",
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
            "type": "geometry",
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


def test_grid_axis_border_keeps_labels_and_arrowheads_visible():
    html = _render_answer_block(
        {
            "type": "geometry",
            "rows": "10",
            "cols": "10",
            "axis": "true",
            "origin": "0,10",
            "step_x": "1",
            "step_y": "1",
            "axis_label_x": "t",
            "axis_label_y": "Amplitude",
        },
        "",
        include_solutions=False,
    )

    assert "class='grid-system-bleed' style='--grid-bleed-top:" in html
    assert "cm;--grid-bleed-right:" in html
    assert re.search(r"class='grid-axis-label' x='0\.0000' y='[0-9.\-]+'\>0</text>", html)
    assert "class='grid-axis-label grid-axis-label-y' x='-0.2800' y='10.0400'>0</text>" in html
    assert re.search(r"class='grid-axis-label' x='1\.0000' y='[0-9.\-]+'\>1</text>", html)
    assert "class='grid-axis-label grid-axis-label-y' x='-0.2800' y='9.0400'>1</text>" in html
    assert "viewBox='-" in html
    assert "10.3400,10.0000" in html
    assert "0.0000,-0.3400" in html
    assert re.search(r"class='grid-axis-label grid-axis-name' x='[0-9.\-]+' y='[0-9.\-]+' text-anchor='end'\>Amplitude</text>", html)
