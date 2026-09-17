"""Tests for `build_editable_slide()` -- the pure `python-pptx` shape
construction from already-EMU-positioned `RenderableElement`s. No
Playwright/browser needed: elements are fabricated directly, and the
resulting python-pptx `Slide` is inspected via python-pptx's own API.
"""

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN

from app.core.blatt_kern_pptx_export import build_editable_slide
from app.core.blatt_kern_pptx_export_editable import RenderableElement, TextRun

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
