from app.core.blatt_kern_layout_render import render_columns_container
from app.core.blatt_kern_shared import parse_blocks, split_sections


def test_parse_blocks_maps_double_dash_to_soft_section_break_marker():
    blocks = parse_blocks("Einleitung\n--\nFortsetzung\n")

    assert len(blocks) == 1
    block_type, _, content = blocks[0]
    assert block_type == "raw"
    assert "<!--BLATTWERK_SECTION_BREAK-->" in content


def test_split_sections_inserts_gap_for_hr_breaks():
    html = split_sections("<p>A</p><hr><p>B</p>")

    assert html.count("<section class='ab-section'>") == 2
    assert "ab-section-gap" in html


def test_split_sections_uses_soft_break_without_extra_gap():
    html = split_sections("<p>A</p><!--BLATTWERK_SECTION_BREAK--><p>B</p>")

    assert html.count("<section class='ab-section'>") == 2
    assert "ab-section-gap" not in html


def test_render_columns_container_supports_gap_option():
    columns_blocks = [[("raw", {}, "Spalte 1")], [("raw", {}, "Spalte 2")]]

    html = render_columns_container(
        columns_blocks,
        {"widths": "1 1", "gap": "1cm"},
        include_solutions=False,
    )

    assert "--col-template:1fr 1fr" in html
    assert "--col-gap:1cm" in html


def test_render_columns_container_ignores_invalid_gap_option():
    columns_blocks = [[("raw", {}, "Spalte 1")], [("raw", {}, "Spalte 2")]]

    html = render_columns_container(
        columns_blocks,
        {"widths": "1 1", "gap": "invalid"},
        include_solutions=False,
    )

    assert "--col-template:1fr 1fr" in html
    assert "--col-gap:" not in html
