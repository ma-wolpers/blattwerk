"""Document-type aware preview image build dispatch."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Mapping

import fitz
from PIL import Image

from .kurzentwurf_runtime.build import build_preview_images as build_kurzentwerfer_preview_images

from .blatt_validator import BuildDiagnostic
from .build_requests import WorksheetBuildRequest, WorksheetDesignOptions, build_worksheet_from_request
from .kurzentwurf_settings import resolve_kurzentwurf_runtime_options
from .document_types import DOCUMENT_TYPE_KURZENTWURF


def build_preview_images_for_document(
    input_path: Path,
    *,
    document_type: str,
    include_solutions: bool,
    page_format: str,
    contrast_profile: str,
    worksheet_design: WorksheetDesignOptions,
    metadata_defaults: dict[str, str] | None = None,
    copyright_override: str | None = None,
    black_screen_mode: str = "none",
    presentation_section_separator: str = "dot",
    presentation_hide_future_sections: bool = False,
    kurzentwurf_options: Mapping[str, object] | None = None,
) -> tuple[list[Image.Image], list[BuildDiagnostic]]:
    """Build preview images for the active document family."""

    if str(document_type or "").strip().lower() == DOCUMENT_TYPE_KURZENTWURF:
        return _build_kurzentwurf_preview_images(input_path, kurzentwurf_options=kurzentwurf_options)

    return _build_worksheet_preview_images(
        input_path,
        include_solutions=include_solutions,
        page_format=page_format,
        contrast_profile=contrast_profile,
        worksheet_design=worksheet_design,
        metadata_defaults=metadata_defaults,
        copyright_override=copyright_override,
        black_screen_mode=black_screen_mode,
        presentation_section_separator=presentation_section_separator,
        presentation_hide_future_sections=presentation_hide_future_sections,
    )


def _build_worksheet_preview_images(
    input_path: Path,
    *,
    include_solutions: bool,
    page_format: str,
    contrast_profile: str,
    worksheet_design: WorksheetDesignOptions,
    metadata_defaults: dict[str, str] | None,
    copyright_override: str | None,
    black_screen_mode: str,
    presentation_section_separator: str,
    presentation_hide_future_sections: bool,
) -> tuple[list[Image.Image], list[BuildDiagnostic]]:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        temp_pdf_path = Path(tmp.name)

    try:
        compile_diagnostics: list[BuildDiagnostic] = []
        build_worksheet_from_request(
            WorksheetBuildRequest(
                input_path=input_path,
                output_path=temp_pdf_path,
                include_solutions=include_solutions,
                page_format=page_format,
                print_profile=contrast_profile,
                design=worksheet_design,
                metadata_defaults=metadata_defaults,
                copyright_text_override=copyright_override,
                black_screen_mode=black_screen_mode,
                presentation_section_separator=presentation_section_separator,
                presentation_hide_future_sections=presentation_hide_future_sections,
                diagnostics_out=compile_diagnostics,
            )
        )

        pages: list[Image.Image] = []
        with fitz.open(temp_pdf_path) as doc:
            for page_index in range(len(doc)):
                page = doc.load_page(page_index)
                pix = page.get_pixmap(dpi=150, alpha=False)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                pages.append(image)
        return pages, compile_diagnostics
    finally:
        try:
            temp_pdf_path.unlink(missing_ok=True)
        except Exception:
            pass


def _build_kurzentwurf_preview_images(
    input_path: Path,
    *,
    kurzentwurf_options: Mapping[str, object] | None = None,
) -> tuple[list[Image.Image], list[BuildDiagnostic]]:
    source = input_path.read_text(encoding="utf-8")
    runtime_options = resolve_kurzentwurf_runtime_options(kurzentwurf_options)
    pages, inspection = build_kurzentwerfer_preview_images(source, **runtime_options)

    diagnostics = [_to_build_diagnostic(diag) for diag in inspection.diagnostics]
    if inspection.has_errors:
        raise ValueError(_format_kurzentwurf_error_summary(diagnostics))
    return pages, diagnostics


def _to_build_diagnostic(diagnostic) -> BuildDiagnostic:
    line_number = getattr(diagnostic, "line", None)
    return BuildDiagnostic(
        code=str(getattr(diagnostic, "code", "KZF000") or "KZF000"),
        message=str(getattr(diagnostic, "message", "Kurzentwurf-Fehler") or "Kurzentwurf-Fehler"),
        severity=str(getattr(diagnostic, "severity", "warning") or "warning"),
        line_number=int(line_number) if isinstance(line_number, int) else None,
    )


def _format_kurzentwurf_error_summary(diagnostics: list[BuildDiagnostic]) -> str:
    if not diagnostics:
        return "Kurzentwurf konnte nicht gerendert werden."

    error_diagnostics = [diag for diag in diagnostics if str(diag.severity or "").lower() == "error"]
    relevant = error_diagnostics or diagnostics
    lines = []
    for diagnostic in relevant[:5]:
        location = f" Zeile {diagnostic.line_number}" if diagnostic.line_number is not None else ""
        lines.append(f"- {diagnostic.code}{location}: {diagnostic.message}")

    return "Kurzentwurf konnte nicht gerendert werden:\n\n" + "\n".join(lines)