"""Document-type aware preview image build dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from PIL import Image

from .kurzentwurf_runtime.build import build_preview_images as build_kurzentwerfer_preview_images
from .pdf_raster import rasterize_pdf, temp_pdf_path

from .blatt_validator import BuildDiagnostic
from .block_computation_cache import BlockComputationCache
from .help_cards_appendix import HELP_APPENDIX_NONE
from .build_requests import WorksheetBuildRequest, WorksheetDesignOptions, build_worksheet_from_request
from .kurzentwurf_settings import resolve_kurzentwurf_runtime_options
from .document_type_registry import (
    PIPELINE_KURZENTWURF,
    PIPELINE_MARKDOWN,
    PIPELINE_SCHILD,
    PREVIEW_VARIANT_EXPECTATION,
    PREVIEW_VARIANT_WORKSHEET,
    spec_for_type,
)
from .exam_expectation_horizon import build_expectation_horizon
from .plain_markdown_render import build_plain_markdown
from .schild_render import build_schild


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
    presentation_ignore_framebreaks: bool = False,
    kurzentwurf_options: Mapping[str, object] | None = None,
    computation_cache: BlockComputationCache | None = None,
    preview_variant: str = PREVIEW_VARIANT_WORKSHEET,
    help_appendix: str = HELP_APPENDIX_NONE,
) -> tuple[list[Image.Image], list[BuildDiagnostic]]:
    """Build preview images for the active document family.

    `help_appendix` (`help_cards_appendix.HELP_APPENDIX_*`) appends the
    visible Lernhilfen after the worksheet pages, exactly as the PDF export
    does (same build). All pages are rasterized at the same dpi, so their
    pixel sizes keep the physical proportions (A6 card smaller than A4 page).

    `computation_cache` is only meaningful for the worksheet/presentation
    family (threaded through to `build_worksheet_from_request`); the
    Kurzentwurf runtime does not use the block computation cache.

    `preview_variant` (`document_type_registry.preview_variants`) selects the
    expectation horizon instead of the document itself; `include_solutions`
    stays the switch between worksheet and solution within the worksheet
    pipeline (callers derive it from the same variant).

    Raises:
        ValueError: for `expectation` on a type without an expectation
            horizon, or when blocking diagnostics prevent the build.
    """

    if preview_variant == PREVIEW_VARIANT_EXPECTATION:
        if not spec_for_type(document_type).expectation_horizon:
            raise ValueError(f"Dokumenttyp {document_type!r} hat keinen Erwartungshorizont.")
        return _build_expectation_horizon_preview_images(input_path)

    pipeline = spec_for_type(document_type).pipeline
    if pipeline == PIPELINE_KURZENTWURF:
        return _build_kurzentwurf_preview_images(input_path, kurzentwurf_options=kurzentwurf_options)
    if pipeline == PIPELINE_MARKDOWN:
        return _build_html_pipeline_preview_images(input_path, build_plain_markdown)
    if pipeline == PIPELINE_SCHILD:
        return _build_html_pipeline_preview_images(input_path, build_schild)

    return _build_worksheet_preview_images(
        input_path,
        document_type=document_type,
        include_solutions=include_solutions,
        page_format=page_format,
        contrast_profile=contrast_profile,
        worksheet_design=worksheet_design,
        metadata_defaults=metadata_defaults,
        copyright_override=copyright_override,
        black_screen_mode=black_screen_mode,
        presentation_section_separator=presentation_section_separator,
        presentation_hide_future_sections=presentation_hide_future_sections,
        presentation_ignore_framebreaks=presentation_ignore_framebreaks,
        computation_cache=computation_cache,
        help_appendix=help_appendix,
    )


def _build_worksheet_preview_images(
    input_path: Path,
    *,
    document_type: str,
    include_solutions: bool,
    page_format: str,
    contrast_profile: str,
    worksheet_design: WorksheetDesignOptions,
    metadata_defaults: dict[str, str] | None,
    copyright_override: str | None,
    black_screen_mode: str,
    presentation_section_separator: str,
    presentation_hide_future_sections: bool,
    presentation_ignore_framebreaks: bool = False,
    computation_cache: BlockComputationCache | None = None,
    help_appendix: str = HELP_APPENDIX_NONE,
) -> tuple[list[Image.Image], list[BuildDiagnostic]]:
    with temp_pdf_path() as pdf_path:
        compile_diagnostics: list[BuildDiagnostic] = []
        build_worksheet_from_request(
            WorksheetBuildRequest(
                input_path=input_path,
                output_path=pdf_path,
                include_solutions=include_solutions,
                page_format=page_format,
                print_profile=contrast_profile,
                design=worksheet_design,
                metadata_defaults=metadata_defaults,
                copyright_text_override=copyright_override,
                black_screen_mode=black_screen_mode,
                presentation_section_separator=presentation_section_separator,
                presentation_hide_future_sections=presentation_hide_future_sections,
                presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                diagnostics_out=compile_diagnostics,
                computation_cache=computation_cache,
                document_type=document_type,
                help_appendix=help_appendix,
            )
        )

        return rasterize_pdf(pdf_path), compile_diagnostics


def _build_html_pipeline_preview_images(input_path: Path, build) -> tuple[list[Image.Image], list[BuildDiagnostic]]:
    """Vorschau für Pipelines mit eigener `build(input, output.pdf)`-Funktion.

    Genutzt von schlichtem Markdown (`build_plain_markdown`), den Schildern
    (`build_schild`) und dem Erwartungshorizont
    (`_build_expectation_horizon_preview_images`): Die Vorschau ist die gerasterte
    Export-PDF, damit Vorschau und PDF garantiert identisch sind.

    Args:
        input_path: Quelldatei.
        build: Callable ``(input_path, pdf_path) -> Path``, das die PDF schreibt.
    """
    with temp_pdf_path() as pdf_path:
        build(input_path, pdf_path)
        return rasterize_pdf(pdf_path), []


def _build_expectation_horizon_preview_images(input_path: Path) -> tuple[list[Image.Image], list[BuildDiagnostic]]:
    """Vorschau des Erwartungshorizonts: die gerasterte Export-PDF (`build_expectation_horizon`).

    Gleiches Prinzip wie bei den Schildern (`_build_html_pipeline_preview_images`):
    Vorschau und Export sind garantiert identisch. Die Hinweise des Horizonts
    (z. B. fehlende Teilpunkte) kommen als Diagnosen zurück; blockierende
    Fehler werfen wie beim Export einen `ValueError`.
    """
    diagnostics: list[BuildDiagnostic] = []
    pages, _ = _build_html_pipeline_preview_images(
        input_path,
        lambda source, pdf_path: build_expectation_horizon(source, pdf_path, diagnostics_out=diagnostics),
    )
    return pages, diagnostics


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