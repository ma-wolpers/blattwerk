from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

try:
    import fitz
except Exception:  # pragma: no cover - environment-dependent optional import
    fitz = None

from .model import Diagnostic, InspectionResult
from .column_widths import resolve_column_width_percentages
from .pdf_export import write_pdf_from_html
from .render_html import (
    DEFAULT_ANT_MARKER_LABEL,
    DEFAULT_BODY_FONT_SIZE_PT,
    DEFAULT_PAGE_MARGIN_CM,
    DEFAULT_PHASE_ROW_SEPARATOR_MODE,
    DEFAULT_PHASE_ROW_SPACING_PX,
    DEFAULT_S_MARKER_LABEL,
    render_document_html,
)
from .validator import inspect_kurzentwerfer_text


def inspect_source(source: str) -> InspectionResult:
    """Inspect source text and return diagnostics plus validated model."""

    return inspect_kurzentwerfer_text(source)


def render_html_from_source(
    source: str,
    *,
    column_widths_text: str | None = None,
    show_document_header: bool = False,
    body_font_size_pt: float = DEFAULT_BODY_FONT_SIZE_PT,
    page_margin_cm: float = DEFAULT_PAGE_MARGIN_CM,
    phase_row_separator_mode: str = DEFAULT_PHASE_ROW_SEPARATOR_MODE,
    phase_row_spacing_px: int = DEFAULT_PHASE_ROW_SPACING_PX,
    s_marker_label: str = DEFAULT_S_MARKER_LABEL,
    ant_marker_label: str = DEFAULT_ANT_MARKER_LABEL,
) -> tuple[str | None, InspectionResult]:
    """Inspect source and render HTML if no blocking diagnostics exist."""

    inspection = inspect_source(source)
    if inspection.has_errors or inspection.document is None:
        return None, inspection

    if not inspection.document.phases and not inspection.document.rows:
        diagnostics = list(inspection.diagnostics)
        diagnostics.append(
            Diagnostic(
                code="KZF220",
                severity="error",
                message="Dokument enthaelt keine renderbaren Phasen/Zeilen.",
            )
        )
        return None, InspectionResult(document=inspection.document, diagnostics=tuple(diagnostics))

    column_widths = resolve_column_width_percentages(column_widths_text)
    return (
        render_document_html(
            inspection.document,
            column_width_percentages=column_widths,
            show_document_header=show_document_header,
            body_font_size_pt=body_font_size_pt,
            page_margin_cm=page_margin_cm,
            phase_row_separator_mode=phase_row_separator_mode,
            phase_row_spacing_px=phase_row_spacing_px,
            s_marker_label=s_marker_label,
            ant_marker_label=ant_marker_label,
        ),
        inspection,
    )


def export_pdf_from_source(
    source: str,
    output_path: Path,
    *,
    column_widths_text: str | None = None,
    show_document_header: bool = False,
    body_font_size_pt: float = DEFAULT_BODY_FONT_SIZE_PT,
    page_margin_cm: float = DEFAULT_PAGE_MARGIN_CM,
    phase_row_separator_mode: str = DEFAULT_PHASE_ROW_SEPARATOR_MODE,
    phase_row_spacing_px: int = DEFAULT_PHASE_ROW_SPACING_PX,
    s_marker_label: str = DEFAULT_S_MARKER_LABEL,
    ant_marker_label: str = DEFAULT_ANT_MARKER_LABEL,
) -> tuple[bool, InspectionResult]:
    """Inspect and export source text as PDF."""

    html, inspection = render_html_from_source(
        source,
        column_widths_text=column_widths_text,
        show_document_header=show_document_header,
        body_font_size_pt=body_font_size_pt,
        page_margin_cm=page_margin_cm,
        phase_row_separator_mode=phase_row_separator_mode,
        phase_row_spacing_px=phase_row_spacing_px,
        s_marker_label=s_marker_label,
        ant_marker_label=ant_marker_label,
    )
    if html is None:
        return False, inspection

    write_pdf_from_html(html, Path(output_path))
    return True, inspection


def build_preview_images(
    source: str,
    *,
    column_widths_text: str | None = None,
    show_document_header: bool = False,
    body_font_size_pt: float = DEFAULT_BODY_FONT_SIZE_PT,
    page_margin_cm: float = DEFAULT_PAGE_MARGIN_CM,
    phase_row_separator_mode: str = DEFAULT_PHASE_ROW_SEPARATOR_MODE,
    phase_row_spacing_px: int = DEFAULT_PHASE_ROW_SPACING_PX,
    s_marker_label: str = DEFAULT_S_MARKER_LABEL,
    ant_marker_label: str = DEFAULT_ANT_MARKER_LABEL,
    dpi: int = 145,
) -> tuple[list[Image.Image], InspectionResult]:
    """Build preview pages as PIL images from source text."""

    html, inspection = render_html_from_source(
        source,
        column_widths_text=column_widths_text,
        show_document_header=show_document_header,
        body_font_size_pt=body_font_size_pt,
        page_margin_cm=page_margin_cm,
        phase_row_separator_mode=phase_row_separator_mode,
        phase_row_spacing_px=phase_row_spacing_px,
        s_marker_label=s_marker_label,
        ant_marker_label=ant_marker_label,
    )
    if html is None:
        return [], inspection

    if fitz is None:
        diagnostics = list(inspection.diagnostics)
        diagnostics.append(
            Diagnostic(
                code="KZF200",
                severity="error",
                message="PyMuPDF ist nicht verfuegbar. Vorschau kann nicht gerendert werden.",
            )
        )
        return [], InspectionResult(document=inspection.document, diagnostics=tuple(diagnostics))

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        temp_pdf_path = Path(tmp_pdf.name)

    try:
        write_pdf_from_html(html, temp_pdf_path)
        pages: list[Image.Image] = []
        with fitz.open(temp_pdf_path) as pdf_doc:
            for page_index in range(pdf_doc.page_count):
                page = pdf_doc.load_page(page_index)
                pixmap = page.get_pixmap(dpi=dpi, alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                pages.append(image)
        return pages, inspection
    finally:
        try:
            temp_pdf_path.unlink(missing_ok=True)
        except Exception:
            pass
