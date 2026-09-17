"""PPTX export: two rendering paths.

`build_presentation_pptx(..., editable=False)` (default) renders each
presentation slide as an image and packages them into a python-pptx
presentation -- the original, always-available raster path
(`_build_presentation_pptx_raster`).

`build_presentation_pptx(..., editable=True)` attempts the experimental
editable export instead (`blatt_kern_pptx_export_editable.py`): real
PowerPoint text boxes for supported text, individual cropped image shapes
for everything else, per the support matrix documented there. It degrades
gracefully in two stages -- see that module's docstring for the full A/B/C
model:

- Stage A/B (editable pipeline started successfully): per-slide, either
  real shapes (`build_editable_slide`) or -- if that one slide's
  extraction hit a recoverable Playwright error -- a single-slide raster
  fallback (`SlideExtractionResult.raster_image_bytes`), reported via a
  `PPTX001` diagnostic.
- Stage C (the editable pipeline couldn't even start -- no Playwright, no
  browser, launch/navigation failure): falls through to
  `_build_presentation_pptx_raster` entirely, reported via a `PPTX002`
  diagnostic.

A fallback is never silent: every `PPTX001`/`PPTX002` lands in
`diagnostics_out` (surfaced to the user via
`blatt_ui_export.py::_show_compile_overflow_warnings`, whose code filter
was extended to include them -- see that function).
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

from .blatt_kern_pptx_export_editable import EditableExportUnavailable, extract_slide_elements
from .blatt_validator_types import BuildDiagnostic
from .build_requests import WorksheetBuildRequest, build_worksheet_from_request


# Slide dimensions in cm for each page format
_PAGE_SIZE_CM = {
    "presentation_16_9":  (33.867, 19.05),
    "presentation_16_10": (30.48,  19.05),
    "presentation_4_3":   (25.4,   19.05),
    "a4_portrait":        (21.0,   29.7),
    "a5_landscape":       (21.0,   14.8),
}

# 1 cm = 360000 EMU (English Metric Units, the unit python-pptx uses)
_CM_TO_EMU = 360_000


def _cm_to_emu(value_cm: float) -> int:
    return round(value_cm * _CM_TO_EMU)


def _slide_size_emu(page_format: str) -> tuple[int, int]:
    width_cm, height_cm = _PAGE_SIZE_CM.get(page_format, _PAGE_SIZE_CM["presentation_16_9"])
    return _cm_to_emu(width_cm), _cm_to_emu(height_cm)


def build_presentation_pptx(
    input_path: Path,
    output_path: Path,
    page_format: str = "presentation_16_9",
    print_profile: str = "standard",
    design=None,
    include_solutions: bool = False,
    black_screen_mode: str = "none",
    presentation_section_separator: str = "dot",
    presentation_hide_future_sections: bool = False,
    presentation_ignore_framebreaks: bool = False,
    metadata_defaults: dict | None = None,
    diagnostics_out=None,
    copyright_text_override: str | None = None,
    render_dpi: int = 200,
    editable: bool = False,
) -> None:
    """Writes a .pptx file for the given presentation document.

    `editable=True` attempts the experimental editable export first and
    falls back to the raster path on any Stage-C condition (see module
    docstring) -- `editable=False` (default) goes straight to the raster
    path, unchanged from before this parameter existed.
    """

    build_kwargs = dict(
        input_path=input_path,
        page_format=page_format,
        print_profile=print_profile,
        design=design,
        include_solutions=include_solutions,
        black_screen_mode=black_screen_mode,
        presentation_section_separator=presentation_section_separator,
        presentation_hide_future_sections=presentation_hide_future_sections,
        presentation_ignore_framebreaks=presentation_ignore_framebreaks,
        metadata_defaults=metadata_defaults,
        copyright_text_override=copyright_text_override,
    )

    if editable:
        try:
            _build_presentation_pptx_editable(
                output_path=output_path, diagnostics_out=diagnostics_out, **build_kwargs
            )
            return
        except EditableExportUnavailable as exc:
            if diagnostics_out is not None:
                diagnostics_out.append(
                    BuildDiagnostic(
                        code="PPTX002",
                        message=(
                            f"Editierbarer PPTX-Export nicht moeglich ({exc}) -- "
                            "vollstaendiges Bild-PPTX wurde stattdessen erstellt."
                        ),
                        severity="warning",
                    )
                )
            # Falls through to the raster path below -- Stage C.

    _build_presentation_pptx_raster(
        output_path=output_path, diagnostics_out=diagnostics_out, render_dpi=render_dpi, **build_kwargs
    )


def _build_presentation_pptx_editable(
    *,
    input_path: Path,
    output_path: Path,
    page_format: str,
    print_profile: str,
    design,
    include_solutions: bool,
    black_screen_mode: str,
    presentation_section_separator: str,
    presentation_hide_future_sections: bool,
    presentation_ignore_framebreaks: bool,
    metadata_defaults: dict | None,
    copyright_text_override: str | None,
    diagnostics_out,
) -> None:
    """Stage A/B: real text-box/image-shape export via
    `blatt_kern_pptx_export_editable.py`. Raises
    `EditableExportUnavailable` (Stage C trigger) if the pipeline can't
    even start -- callers handle that by falling back to the raster path,
    this function itself never does.
    """

    try:
        from pptx import Presentation
        from pptx.util import Emu
    except ImportError as exc:
        raise RuntimeError(
            "python-pptx ist nicht installiert. Installiere es mit: pip install python-pptx"
        ) from exc

    slide_width_emu, slide_height_emu = _slide_size_emu(page_format)

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        temp_html_path = Path(tmp.name)

    try:
        build_worksheet_from_request(
            WorksheetBuildRequest(
                input_path=input_path,
                output_path=temp_html_path,
                include_solutions=include_solutions,
                page_format=page_format,
                print_profile=print_profile,
                design=design,
                metadata_defaults=metadata_defaults or {},
                copyright_text_override=copyright_text_override,
                black_screen_mode=black_screen_mode,
                diagnostics_out=diagnostics_out,
                presentation_section_separator=presentation_section_separator,
                presentation_hide_future_sections=presentation_hide_future_sections,
                presentation_ignore_framebreaks=presentation_ignore_framebreaks,
            )
        )

        results = extract_slide_elements(temp_html_path, slide_width_emu, slide_height_emu)
    finally:
        try:
            temp_html_path.unlink(missing_ok=True)
        except Exception:
            pass

    if not results:
        raise ValueError("Das Dokument hat keine Folien – PPTX kann nicht erstellt werden.")

    prs = Presentation()
    prs.slide_width = Emu(slide_width_emu)
    prs.slide_height = Emu(slide_height_emu)
    blank_layout = prs.slide_layouts[6]

    for slide_index, result in enumerate(results):
        slide = prs.slides.add_slide(blank_layout)
        if result.elements is not None:
            build_editable_slide(slide, result.elements)
            continue

        # Stage B: this one slide couldn't be extracted -- rasterize just
        # it, the rest of the presentation stays editable.
        buf = io.BytesIO(result.raster_image_bytes or b"")
        if buf.getbuffer().nbytes:
            slide.shapes.add_picture(
                buf, left=Emu(0), top=Emu(0), width=Emu(slide_width_emu), height=Emu(slide_height_emu)
            )
        if diagnostics_out is not None:
            diagnostics_out.append(
                BuildDiagnostic(
                    code="PPTX001",
                    message=(
                        f"Folie {slide_index + 1} als Bild eingebettet (Grund: {result.raster_reason}) "
                        "-- Text auf dieser Folie ist nicht editierbar."
                    ),
                    severity="warning",
                )
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))


def build_editable_slide(slide, elements) -> None:
    """Adds `elements` (a `list[RenderableElement]`, already EMU-positioned
    by `blatt_kern_pptx_export_editable.py`) to an existing (blank)
    python-pptx `slide` as text boxes and pictures -- pure `python-pptx`
    construction, no DOM/browser logic. Shapes are added in the order
    `elements` is given in (document order, from extraction), which
    approximates normal non-overlapping CSS document-flow stacking; no
    stronger z-index/stacking guarantee is made (see the editable-export
    module's support matrix).
    """

    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
    from pptx.util import Emu, Pt

    align_map = {
        "left": PP_ALIGN.LEFT,
        "center": PP_ALIGN.CENTER,
        "right": PP_ALIGN.RIGHT,
        "justify": PP_ALIGN.JUSTIFY,
    }

    for element in elements:
        if element.kind == "image":
            if not element.image_bytes:
                continue
            slide.shapes.add_picture(
                io.BytesIO(element.image_bytes),
                left=Emu(element.left_emu),
                top=Emu(element.top_emu),
                width=Emu(element.width_emu),
                height=Emu(element.height_emu),
            )
            continue

        if not element.runs:
            continue
        textbox = slide.shapes.add_textbox(
            Emu(element.left_emu), Emu(element.top_emu), Emu(element.width_emu), Emu(element.height_emu)
        )
        text_frame = textbox.text_frame
        text_frame.word_wrap = True
        text_frame.auto_size = MSO_AUTO_SIZE.NONE
        text_frame.margin_left = 0
        text_frame.margin_right = 0
        text_frame.margin_top = 0
        text_frame.margin_bottom = 0
        paragraph = text_frame.paragraphs[0]
        paragraph.alignment = align_map.get(element.align, PP_ALIGN.LEFT)
        # One `add_run()` per `TextRun` -- python-pptx supports multiple
        # runs per paragraph unrestricted; a plain, unformatted paragraph
        # is simply a one-run list, no special-casing needed here.
        for text_run in element.runs:
            run = paragraph.add_run()
            run.text = text_run.text
            run.font.size = Pt(text_run.font_size_pt)
            run.font.bold = text_run.bold
            run.font.italic = text_run.italic
            run.font.color.rgb = RGBColor(*text_run.color_rgb)


def _build_presentation_pptx_raster(
    *,
    input_path: Path,
    output_path: Path,
    page_format: str,
    print_profile: str,
    design,
    include_solutions: bool,
    black_screen_mode: str,
    presentation_section_separator: str,
    presentation_hide_future_sections: bool,
    presentation_ignore_framebreaks: bool,
    metadata_defaults: dict | None,
    copyright_text_override: str | None,
    diagnostics_out,
    render_dpi: int,
) -> None:
    """Stage C / default path: render every page of the document to an
    image and write a .pptx file. Each rendered page becomes one slide --
    the slide dimensions match the chosen page_format so the images fill
    the slides exactly without borders. Unchanged from before the
    experimental editable export existed; this is what `editable=False`
    (the default) always runs, and what `editable=True` falls back to.
    """

    import fitz  # PyMuPDF
    from PIL import Image

    try:
        from pptx import Presentation
        from pptx.util import Emu
    except ImportError as exc:
        raise RuntimeError(
            "python-pptx ist nicht installiert. "
            "Installiere es mit: pip install python-pptx"
        ) from exc

    # 1. Render to a temporary PDF via the normal pipeline
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        temp_pdf_path = Path(tmp.name)

    try:
        build_worksheet_from_request(
            WorksheetBuildRequest(
                input_path=input_path,
                output_path=temp_pdf_path,
                include_solutions=include_solutions,
                page_format=page_format,
                print_profile=print_profile,
                design=design,
                metadata_defaults=metadata_defaults or {},
                copyright_text_override=copyright_text_override,
                black_screen_mode=black_screen_mode,
                diagnostics_out=diagnostics_out,
                presentation_section_separator=presentation_section_separator,
                presentation_hide_future_sections=presentation_hide_future_sections,
                presentation_ignore_framebreaks=presentation_ignore_framebreaks,
            )
        )

        # 2. Convert each PDF page to a PIL image
        slide_images: list[Image.Image] = []
        with fitz.open(temp_pdf_path) as doc:
            for page_index in range(len(doc)):
                page = doc.load_page(page_index)
                pix = page.get_pixmap(dpi=render_dpi, alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                slide_images.append(img)

    finally:
        try:
            temp_pdf_path.unlink(missing_ok=True)
        except Exception:
            pass

    if not slide_images:
        raise ValueError("Das Dokument hat keine Seiten – PPTX kann nicht erstellt werden.")

    # 3. Build the PPTX
    slide_width_emu, slide_height_emu = _slide_size_emu(page_format)

    prs = Presentation()
    prs.slide_width = Emu(slide_width_emu)
    prs.slide_height = Emu(slide_height_emu)

    blank_layout = prs.slide_layouts[6]  # completely blank layout

    for img in slide_images:
        slide = prs.slides.add_slide(blank_layout)

        # Save image to an in-memory buffer
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        # Fill entire slide with the image
        slide.shapes.add_picture(
            buf,
            left=Emu(0),
            top=Emu(0),
            width=Emu(slide_width_emu),
            height=Emu(slide_height_emu),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
