"""Tests for `build_editable_slide()` -- the pure `python-pptx` shape
construction from already-EMU-positioned `RenderableElement`s. No
Playwright/browser needed: elements are fabricated directly, and the
resulting python-pptx `Slide` is inspected via python-pptx's own API.
"""

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN

from app.core.blatt_kern_pptx_export import build_editable_slide
from app.core.blatt_kern_pptx_export_editable import RenderableElement, TableCell, TableData, TextRun

_ONE_PX_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _blank_slide():
    prs = Presentation()
    return prs.slides.add_slide(prs.slide_layouts[6])


def _text_element(
    text="Hallo Welt", align="left", bold=False, italic=False, color=(17, 17, 17), font_size_pt=12.0
):
    return RenderableElement(
        kind="text",
        left_emu=100_000, top_emu=200_000, width_emu=1_000_000, height_emu=300_000,
        align=align,
        runs=[TextRun(text=text, font_size_pt=font_size_pt, bold=bold, italic=italic, color_rgb=color)],
    )


def _image_element(image_bytes=_ONE_PX_PNG):
    return RenderableElement(
        kind="image",
        left_emu=50_000, top_emu=60_000, width_emu=400_000, height_emu=500_000,
        image_bytes=image_bytes,
    )


def _table_element(cells, rows=2, cols=2, column_widths_emu=None, row_heights_emu=None):
    return RenderableElement(
        kind="table",
        left_emu=100_000, top_emu=200_000, width_emu=2_000_000, height_emu=1_000_000,
        table=TableData(
            rows=rows, cols=cols,
            column_widths_emu=column_widths_emu or [1_000_000] * cols,
            row_heights_emu=row_heights_emu or [500_000] * rows,
            cells=cells,
        ),
    )


def test_text_element_becomes_a_real_textbox_with_correct_text():
    slide = _blank_slide()

    build_editable_slide(slide, [_text_element(text="Rechne aus.")])

    shapes = list(slide.shapes)
    assert len(shapes) == 1
    assert shapes[0].has_text_frame
    assert shapes[0].text_frame.text == "Rechne aus."


def test_text_element_position_and_size_are_preserved_in_emu():
    slide = _blank_slide()
    element = _text_element()

    build_editable_slide(slide, [element])

    shape = list(slide.shapes)[0]
    assert shape.left == element.left_emu
    assert shape.top == element.top_emu
    assert shape.width == element.width_emu
    assert shape.height == element.height_emu


def test_text_element_carries_font_size_bold_color_and_alignment():
    slide = _blank_slide()
    build_editable_slide(slide, [_text_element(bold=True, color=(255, 0, 0), font_size_pt=18.5, align="center")])

    run = list(slide.shapes)[0].text_frame.paragraphs[0].runs[0]
    assert run.font.bold is True
    assert run.font.color.rgb == (255, 0, 0)
    assert round(run.font.size.pt, 1) == 18.5
    assert list(slide.shapes)[0].text_frame.paragraphs[0].alignment == PP_ALIGN.CENTER


def test_text_element_carries_italic_flag():
    slide = _blank_slide()
    build_editable_slide(slide, [_text_element(italic=True)])

    run = list(slide.shapes)[0].text_frame.paragraphs[0].runs[0]
    assert run.font.italic is True


def test_multiple_runs_produce_multiple_paragraph_runs_with_own_formatting():
    slide = _blank_slide()
    element = RenderableElement(
        kind="text",
        left_emu=100_000, top_emu=200_000, width_emu=1_000_000, height_emu=300_000,
        align="left",
        runs=[
            TextRun(text="fett", font_size_pt=12.0, bold=True, italic=False, color_rgb=(0, 0, 0)),
            TextRun(text=" normal ", font_size_pt=12.0, bold=False, italic=False, color_rgb=(0, 0, 0)),
            TextRun(text="kursiv", font_size_pt=12.0, bold=False, italic=True, color_rgb=(0, 0, 0)),
        ],
    )

    build_editable_slide(slide, [element])

    runs = list(slide.shapes)[0].text_frame.paragraphs[0].runs
    assert [run.text for run in runs] == ["fett", " normal ", "kursiv"]
    assert runs[0].font.bold is True and runs[0].font.italic is not True
    assert runs[1].font.bold is not True and runs[1].font.italic is not True
    assert runs[2].font.bold is not True and runs[2].font.italic is True


def test_text_element_word_wrap_enabled_and_auto_size_disabled():
    # v1 uses fixed geometry (the extracted box), not PowerPoint auto-fit --
    # see the editable-export module's documented v1 limitations.
    slide = _blank_slide()
    build_editable_slide(slide, [_text_element()])

    text_frame = list(slide.shapes)[0].text_frame
    assert text_frame.word_wrap is True


def test_image_element_becomes_a_picture_shape_with_correct_geometry():
    slide = _blank_slide()
    element = _image_element()

    build_editable_slide(slide, [element])

    shapes = list(slide.shapes)
    assert len(shapes) == 1
    assert shapes[0].shape_type == MSO_SHAPE_TYPE.PICTURE
    assert shapes[0].left == element.left_emu
    assert shapes[0].top == element.top_emu
    assert shapes[0].width == element.width_emu
    assert shapes[0].height == element.height_emu


def test_mixed_elements_produce_shapes_in_the_given_order():
    slide = _blank_slide()
    build_editable_slide(slide, [_text_element(text="Erst Text"), _image_element(), _text_element(text="Dann Text")])

    shapes = list(slide.shapes)
    assert len(shapes) == 3
    assert shapes[0].has_text_frame and shapes[0].text_frame.text == "Erst Text"
    assert shapes[1].shape_type == MSO_SHAPE_TYPE.PICTURE
    assert shapes[2].has_text_frame and shapes[2].text_frame.text == "Dann Text"


def test_image_element_without_bytes_is_skipped_not_crashed():
    slide = _blank_slide()
    build_editable_slide(slide, [_image_element(image_bytes=None)])

    assert list(slide.shapes) == []


def test_empty_element_list_produces_no_shapes():
    slide = _blank_slide()
    build_editable_slide(slide, [])

    assert list(slide.shapes) == []


def test_table_element_becomes_a_real_pptx_table_with_correct_geometry():
    element = _table_element(cells=[
        TableCell(row=0, col=0, row_span=1, col_span=1, text="A", bold=False, align="left", background_rgb=None),
        TableCell(row=0, col=1, row_span=1, col_span=1, text="B", bold=False, align="left", background_rgb=None),
        TableCell(row=1, col=0, row_span=1, col_span=1, text="C", bold=False, align="left", background_rgb=None),
        TableCell(row=1, col=1, row_span=1, col_span=1, text="D", bold=False, align="left", background_rgb=None),
    ])
    slide = _blank_slide()

    build_editable_slide(slide, [element])

    shapes = list(slide.shapes)
    assert len(shapes) == 1
    assert shapes[0].has_table
    assert shapes[0].left == element.left_emu and shapes[0].top == element.top_emu
    assert shapes[0].width == element.width_emu and shapes[0].height == element.height_emu
    table = shapes[0].table
    assert table.cell(0, 0).text == "A"
    assert table.cell(0, 1).text == "B"
    assert table.cell(1, 0).text == "C"
    assert table.cell(1, 1).text == "D"


def test_table_element_column_widths_and_row_heights_are_applied():
    element = _table_element(
        cells=[TableCell(row=0, col=0, row_span=1, col_span=1, text="X", bold=False, align="left", background_rgb=None)],
        column_widths_emu=[600_000, 1_400_000],
        row_heights_emu=[300_000, 700_000],
    )
    slide = _blank_slide()

    build_editable_slide(slide, [element])

    table = list(slide.shapes)[0].table
    assert table.columns[0].width == 600_000 and table.columns[1].width == 1_400_000
    assert table.rows[0].height == 300_000 and table.rows[1].height == 700_000


def test_table_element_carries_bold_alignment_and_background_per_cell():
    element = _table_element(cells=[
        TableCell(row=0, col=0, row_span=1, col_span=1, text="Kopf", bold=True, align="center", background_rgb=(230, 230, 250)),
        TableCell(row=1, col=0, row_span=1, col_span=1, text="Daten", bold=False, align="right", background_rgb=None),
    ], rows=2, cols=1)
    slide = _blank_slide()

    build_editable_slide(slide, [element])

    table = list(slide.shapes)[0].table
    header_cell = table.cell(0, 0)
    assert header_cell.text_frame.paragraphs[0].runs[0].font.bold is True
    assert header_cell.text_frame.paragraphs[0].alignment == PP_ALIGN.CENTER
    assert header_cell.fill.fore_color.rgb == (230, 230, 250)

    data_cell = table.cell(1, 0)
    assert data_cell.text_frame.paragraphs[0].runs[0].font.bold is not True
    assert data_cell.text_frame.paragraphs[0].alignment == PP_ALIGN.RIGHT


def test_table_element_merges_spanning_cell_across_rows_and_columns():
    # A colspan=2 "header" cell (logical row 0, spans both columns) above
    # two plain data cells in row 1 -- proves `.merge()` is actually wired
    # up, using ALL cells' row/col_span, not just a single-cell table.
    element = _table_element(cells=[
        TableCell(row=0, col=0, row_span=1, col_span=2, text="Ueberschrift", bold=False, align="left", background_rgb=None),
        TableCell(row=1, col=0, row_span=1, col_span=1, text="Links", bold=False, align="left", background_rgb=None),
        TableCell(row=1, col=1, row_span=1, col_span=1, text="Rechts", bold=False, align="left", background_rgb=None),
    ])
    slide = _blank_slide()

    build_editable_slide(slide, [element])

    table = list(slide.shapes)[0].table
    assert table.cell(0, 0).text == "Ueberschrift"
    assert table.cell(0, 0).is_spanned is False
    assert table.cell(0, 0).span_width == 2
    assert table.cell(0, 1).is_spanned is True
    assert table.cell(1, 0).text == "Links"
    assert table.cell(1, 1).text == "Rechts"


def test_table_element_without_cells_produces_no_shape():
    element = _table_element(cells=[])
    slide = _blank_slide()

    build_editable_slide(slide, [element])

    assert list(slide.shapes) == []
