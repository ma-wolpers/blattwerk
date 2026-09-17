"""Unit tests for the pure DOM-classification-result -> EMU conversion
logic (`blatt_kern_pptx_export_editable_convert.py`). No browser/Playwright
needed -- these feed `build_slide_elements` the same shape of dict
`_CLASSIFY_JS` (`page.evaluate(...)`) would return, fabricated directly.
"""

from app.core.blatt_kern_pptx_export_editable_convert import (
    _IMAGE_ONLY_BLOCK_TYPES,
    _is_bold,
    _is_italic,
    _parse_background_rgb,
    _parse_rgb,
    build_slide_elements,
    merge_nearby_grid_edges,
)

# A 16:9 slide's EMU size, matching `_PAGE_SIZE_CM["presentation_16_9"]`.
_SLIDE_WIDTH_EMU = 12_192_120
_SLIDE_HEIGHT_EMU = 6_858_000


def _run(text="Hallo", font_size_px=16, weight="400", style="normal", color="rgb(17, 17, 17)"):
    return {"text": text, "fontSizePx": font_size_px, "fontWeight": weight, "fontStyle": style, "color": color}


def _text_entry(index, x, y, width, height, text="Hallo", font_size_px=16, weight="400", color="rgb(17, 17, 17)", align="left", runs=None):
    return {
        "index": index, "kind": "text",
        "rect": {"x": x, "y": y, "width": width, "height": height},
        "align": align,
        "runs": runs if runs is not None else [_run(text=text, font_size_px=font_size_px, weight=weight, color=color)],
    }


def _image_entry(index, x, y, width, height):
    return {"index": index, "kind": "image", "rect": {"x": x, "y": y, "width": width, "height": height}}


def test_parse_rgb_reads_rgb_triplet():
    assert _parse_rgb("rgb(34, 34, 34)") == (34, 34, 34)


def test_parse_rgb_reads_rgba_ignoring_alpha():
    assert _parse_rgb("rgba(255, 0, 128, 0.5)") == (255, 0, 128)


def test_parse_rgb_falls_back_to_black_for_unparseable_input():
    assert _parse_rgb("") == (0, 0, 0)
    assert _parse_rgb(None) == (0, 0, 0)
    assert _parse_rgb("currentcolor") == (0, 0, 0)


def test_is_bold_recognizes_keyword_and_numeric_weights():
    assert _is_bold("bold") is True
    assert _is_bold("bolder") is True
    assert _is_bold("700") is True
    assert _is_bold("600") is True
    assert _is_bold("400") is False
    assert _is_bold("normal") is False
    assert _is_bold(None) is False


def test_is_italic_recognizes_italic_and_oblique_keywords():
    assert _is_italic("italic") is True
    assert _is_italic("oblique") is True
    assert _is_italic("normal") is False
    assert _is_italic(None) is False


def test_build_slide_elements_scales_position_and_size_proportionally():
    # A 1000px-wide "viewport" slide -> half-width EMU box should land at
    # exactly half of the target EMU width, regardless of the arbitrary
    # viewport pixel size used to render it.
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [_text_entry(0, x=0, y=0, width=500, height=100)],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    assert len(built) == 1
    assert built[0]["left_emu"] == 0
    assert built[0]["width_emu"] == round(_SLIDE_WIDTH_EMU / 2)


def test_build_slide_elements_font_size_scales_with_geometry():
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [_text_entry(0, x=0, y=0, width=200, height=50, font_size_px=20)],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    scale = _SLIDE_WIDTH_EMU / 1000
    expected_pt = 20 * scale / 12700
    assert built[0]["runs"][0]["font_size_pt"] == expected_pt


def test_build_slide_elements_drops_zero_size_elements():
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [
            _text_entry(0, x=0, y=0, width=0, height=50),
            _text_entry(1, x=0, y=0, width=50, height=0),
            _text_entry(2, x=0, y=0, width=50, height=50),
        ],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    assert len(built) == 1


def test_build_slide_elements_drops_text_entries_with_empty_text():
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [_text_entry(0, x=0, y=0, width=50, height=50, runs=[_run(text="")])],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    assert built == []


def test_build_slide_elements_keeps_image_entries_without_text_fields():
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [_image_entry(0, x=10, y=10, width=100, height=100)],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    assert len(built) == 1
    assert built[0]["kind"] == "image"
    assert built[0]["index"] == 0
    assert "text" not in built[0]


def test_build_slide_elements_returns_empty_for_degenerate_slide_size():
    raw_slide = {"slideWidth": 0, "slideHeight": 0, "elements": [_text_entry(0, 0, 0, 50, 50)]}

    assert build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU) == []


def test_build_slide_elements_maps_text_align_values():
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [
            _text_entry(0, 0, 0, 50, 50, align="start"),
            _text_entry(1, 0, 0, 50, 50, align="end"),
            _text_entry(2, 0, 0, 50, 50, align="center"),
            _text_entry(3, 0, 0, 50, 50, align="justify"),
            _text_entry(4, 0, 0, 50, 50, align="weird-unknown-value"),
        ],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    assert [entry["align"] for entry in built] == ["left", "right", "center", "justify", "left"]


def test_build_slide_elements_preserves_multiple_runs_in_order_with_own_formatting():
    # A paragraph with "**fett** normal *kursiv*" -- _CLASSIFY_JS would emit
    # one run per formatting span, each carrying its OWN computed style
    # (see `buildRuns` in blatt_kern_pptx_export_editable_convert.py). This
    # proves the Python-side conversion keeps run order, text, and the
    # bold/italic flags per-run rather than collapsing to the paragraph's
    # own style (the pre-B3 behaviour this replaces).
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [
            _text_entry(
                0, x=0, y=0, width=200, height=50,
                runs=[
                    _run(text="fett", weight="bold", style="normal"),
                    _run(text=" normal ", weight="400", style="normal"),
                    _run(text="kursiv", weight="400", style="italic"),
                ],
            )
        ],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    assert len(built) == 1
    runs = built[0]["runs"]
    assert [run["text"] for run in runs] == ["fett", " normal ", "kursiv"]
    assert [run["bold"] for run in runs] == [True, False, False]
    assert [run["italic"] for run in runs] == [False, False, True]


def test_build_slide_elements_single_run_paragraph_stays_a_one_element_run_list():
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [_text_entry(0, x=0, y=0, width=200, height=50, text="Unformatiert")],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    assert len(built[0]["runs"]) == 1
    assert built[0]["runs"][0]["text"] == "Unformatiert"


def test_image_only_block_types_excludes_text_capable_answer_and_content_blocks():
    # Text-capable blocks must never accidentally end up in the image
    # allow-list -- their content is meant to become editable text.
    for block_type in ("task", "subtask", "info", "material", "solution", "writebox", "mc", "cloze", "ordering", "help"):
        assert block_type not in _IMAGE_ONLY_BLOCK_TYPES


def test_image_only_block_types_includes_documented_visual_blocks():
    for block_type in ("geometry", "grid", "dots", "crossword", "wordsearch", "qrcode"):
        assert block_type in _IMAGE_ONLY_BLOCK_TYPES


def test_image_only_block_types_no_longer_includes_table():
    # B4: `:::table` gets a real, cell-based PPTX table now, not a
    # screenshot -- regression guard against accidentally re-adding it.
    assert "table" not in _IMAGE_ONLY_BLOCK_TYPES


def _table_cell(x, y, width, height, text="Zelle", weight="400", align="left", background="rgba(0, 0, 0, 0)"):
    return {
        "rect": {"x": x, "y": y, "width": width, "height": height},
        "text": text, "fontWeight": weight, "textAlign": align, "backgroundColor": background,
    }


def _table_entry(index, x, y, width, height, cells):
    return {"index": index, "kind": "table", "rect": {"x": x, "y": y, "width": width, "height": height}, "cells": cells}


def test_merge_nearby_grid_edges_collapses_subpixel_clusters_but_keeps_distinct_lines():
    edges = [100.0, 100.02, 199.999, 200.001, 300.0]

    merged = merge_nearby_grid_edges(edges, tolerance=0.5)

    assert merged == [100.0, 199.999, 300.0]


def test_merge_nearby_grid_edges_handles_empty_and_single_edge():
    assert merge_nearby_grid_edges([]) == []
    assert merge_nearby_grid_edges([42.0]) == [42.0]


def test_parse_background_rgb_reads_opaque_color():
    assert _parse_background_rgb("rgb(230, 230, 250)") == (230, 230, 250)


def test_parse_background_rgb_returns_none_for_fully_transparent():
    # Chromium's default computed backgroundColor for an element with no
    # own `background-color` -- must NOT be read as literal black.
    assert _parse_background_rgb("rgba(0, 0, 0, 0)") is None


def test_parse_background_rgb_returns_none_for_unparseable_input():
    assert _parse_background_rgb("") is None
    assert _parse_background_rgb(None) is None


def test_build_slide_elements_reconstructs_simple_table_grid():
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [
            _table_entry(0, x=0, y=0, width=200, height=100, cells=[
                _table_cell(0, 0, 100, 50, text="A"),
                _table_cell(100, 0, 100, 50, text="B"),
                _table_cell(0, 50, 100, 50, text="C"),
                _table_cell(100, 50, 100, 50, text="D"),
            ])
        ],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    assert len(built) == 1
    table = built[0]["table"]
    assert table["rows"] == 2 and table["cols"] == 2
    assert len(table["column_widths_emu"]) == 2
    assert len(table["row_heights_emu"]) == 2
    cells_by_text = {cell["text"]: cell for cell in table["cells"]}
    assert cells_by_text["A"]["row"] == 0 and cells_by_text["A"]["col"] == 0
    assert cells_by_text["B"]["row"] == 0 and cells_by_text["B"]["col"] == 1
    assert cells_by_text["C"]["row"] == 1 and cells_by_text["C"]["col"] == 0
    assert cells_by_text["D"]["row"] == 1 and cells_by_text["D"]["col"] == 1
    assert all(cell["row_span"] == 1 and cell["col_span"] == 1 for cell in table["cells"])
    # Flat text only -- no per-cell inline-run list, the deliberate v1
    # distinction from `kind="text"`'s `runs` model (B3).
    assert all("runs" not in cell for cell in table["cells"])


def test_build_slide_elements_reconstructs_grid_with_colspan_and_rowspan_from_geometry():
    # Row 0 has ONE cell spanning both columns (colspan=2 in the source
    # HTML) -- its own rect alone reveals nothing about the 2-column grid
    # underneath, so the column boundary must come from row 1's cells
    # instead. Also one rowspan-2 cell in column 0 spanning both rows.
    # A first-row/first-column-only heuristic would get this wrong.
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [
            _table_entry(0, x=0, y=0, width=300, height=100, cells=[
                _table_cell(0, 0, 300, 50, text="Ueberschrift"),  # row 0, colspan 2
                _table_cell(0, 50, 100, 50, text="Links"),         # row 1, col 0 (rowspan irrelevant here)
                _table_cell(100, 50, 200, 50, text="Rechts"),      # row 1, col 1
            ])
        ],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    table = built[0]["table"]
    assert table["rows"] == 2 and table["cols"] == 2
    cells_by_text = {cell["text"]: cell for cell in table["cells"]}
    header = cells_by_text["Ueberschrift"]
    assert header["row"] == 0 and header["col"] == 0
    assert header["col_span"] == 2 and header["row_span"] == 1
    assert cells_by_text["Links"]["row"] == 1 and cells_by_text["Links"]["col"] == 0
    assert cells_by_text["Rechts"]["row"] == 1 and cells_by_text["Rechts"]["col"] == 1


def test_build_slide_elements_table_cell_style_reads_bold_align_and_background():
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [
            _table_entry(0, x=0, y=0, width=100, height=50, cells=[
                _table_cell(0, 0, 100, 50, text="Kopf", weight="600", align="center", background="rgb(230, 230, 250)"),
            ])
        ],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    cell = built[0]["table"]["cells"][0]
    assert cell["bold"] is True
    assert cell["align"] == "center"
    assert cell["background_rgb"] == (230, 230, 250)


def test_build_slide_elements_table_cell_without_background_stays_none():
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [
            _table_entry(0, x=0, y=0, width=100, height=50, cells=[
                _table_cell(0, 0, 100, 50, text="Daten", background="rgba(0, 0, 0, 0)"),
            ])
        ],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    assert built[0]["table"]["cells"][0]["background_rgb"] is None


def test_build_slide_elements_drops_table_entry_with_no_usable_cells():
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [_table_entry(0, x=0, y=0, width=100, height=50, cells=[])],
    }

    assert build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU) == []


def test_build_slide_elements_table_grid_merges_subpixel_shared_edges():
    # The shared edge between the two cells is reported as 99.999 by the
    # left cell and 100.001 by the right cell (realistic sub-pixel layout
    # rounding) -- must still resolve to ONE grid line, i.e. a 2-column
    # table, not three columns with a hairline gap column between them.
    raw_slide = {
        "slideWidth": 1000, "slideHeight": 562.5,
        "elements": [
            _table_entry(0, x=0, y=0, width=200, height=50, cells=[
                _table_cell(0, 0, 99.999, 50, text="Links"),
                _table_cell(100.001, 0, 99.999, 50, text="Rechts"),
            ])
        ],
    }

    built = build_slide_elements(raw_slide, _SLIDE_WIDTH_EMU, _SLIDE_HEIGHT_EMU)

    table = built[0]["table"]
    assert table["cols"] == 2
    cells_by_text = {cell["text"]: cell for cell in table["cells"]}
    assert cells_by_text["Links"]["col"] == 0
    assert cells_by_text["Rechts"]["col"] == 1
