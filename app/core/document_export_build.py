"""Document-type aware export build helpers."""

from __future__ import annotations

from pathlib import Path
import tempfile
import zipfile

from PIL import Image

from kurzentwerfer.app.core.build import export_pdf_from_source, render_html_from_source

from .blatt_validator import BuildDiagnostic
from .build_requests import WorksheetBuildRequest, build_worksheet_from_request
from .document_preview_build import build_preview_images_for_document
from .document_types import DOCUMENT_TYPE_KURZENTWURF
from .export_path_guardrails import validate_export_output_path


def export_document_pdf(
    *,
    input_path: Path,
    output_path: Path,
    document_type: str,
    include_solutions: bool,
    worksheet_request: WorksheetBuildRequest,
) -> Path:
    """Export one document variant as PDF."""

    if str(document_type or "").strip().lower() == DOCUMENT_TYPE_KURZENTWURF:
        _ensure_supported_kurzentwurf_mode(include_solutions)
        return _export_kurzentwurf_pdf(input_path=input_path, output_path=output_path, diagnostics_out=worksheet_request.diagnostics_out)

    return Path(build_worksheet_from_request(worksheet_request))


def export_document_html(
    *,
    input_path: Path,
    output_path: Path,
    document_type: str,
    include_solutions: bool,
    worksheet_request: WorksheetBuildRequest,
) -> Path:
    """Export one document variant as HTML."""

    if str(document_type or "").strip().lower() == DOCUMENT_TYPE_KURZENTWURF:
        _ensure_supported_kurzentwurf_mode(include_solutions)
        return _export_kurzentwurf_html(input_path=input_path, output_path=output_path, diagnostics_out=worksheet_request.diagnostics_out)

    return Path(build_worksheet_from_request(worksheet_request))


def export_document_png(
    *,
    input_path: Path,
    output_path: Path,
    document_type: str,
    include_solutions: bool,
    page_format: str,
    contrast_profile: str,
    worksheet_design,
    metadata_defaults: dict[str, str] | None = None,
    copyright_override: str | None = None,
    black_screen_mode: str = "none",
    presentation_section_separator: str = "dot",
    presentation_hide_future_sections: bool = False,
    diagnostics_out: list[BuildDiagnostic] | None = None,
) -> list[Path]:
    """Export one document variant as one or more PNG files."""

    if str(document_type or "").strip().lower() == DOCUMENT_TYPE_KURZENTWURF:
        _ensure_supported_kurzentwurf_mode(include_solutions)

    pages, diagnostics = build_preview_images_for_document(
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
    )
    _extend_diagnostics(diagnostics_out, diagnostics)
    return _save_png_pages(output_path=output_path, pages=pages)


def export_document_png_zip(
    *,
    input_path: Path,
    output_path: Path,
    document_type: str,
    include_solutions: bool,
    page_format: str,
    contrast_profile: str,
    worksheet_design,
    metadata_defaults: dict[str, str] | None = None,
    copyright_override: str | None = None,
    black_screen_mode: str = "none",
    presentation_section_separator: str = "dot",
    presentation_hide_future_sections: bool = False,
    diagnostics_out: list[BuildDiagnostic] | None = None,
) -> Path:
    """Export one document variant as a ZIP archive with page PNGs."""

    if str(document_type or "").strip().lower() == DOCUMENT_TYPE_KURZENTWURF:
        _ensure_supported_kurzentwurf_mode(include_solutions)

    pages, diagnostics = build_preview_images_for_document(
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
    )
    _extend_diagnostics(diagnostics_out, diagnostics)
    return _save_png_zip(output_path=output_path, pages=pages)


def _export_kurzentwurf_pdf(*, input_path: Path, output_path: Path, diagnostics_out: list[BuildDiagnostic] | None) -> Path:
    target_path = validate_export_output_path(output_path.with_suffix(".pdf"), allowed_suffixes={".pdf"})
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source = input_path.read_text(encoding="utf-8")
    success, inspection = export_pdf_from_source(source, target_path)
    diagnostics = [_to_build_diagnostic(diag) for diag in inspection.diagnostics]
    _extend_diagnostics(diagnostics_out, diagnostics)
    if not success:
        raise ValueError(_format_kurzentwurf_export_error(diagnostics, "PDF"))
    return target_path


def _export_kurzentwurf_html(*, input_path: Path, output_path: Path, diagnostics_out: list[BuildDiagnostic] | None) -> Path:
    target_path = validate_export_output_path(output_path.with_suffix(".html"), allowed_suffixes={".html"})
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source = input_path.read_text(encoding="utf-8")
    html, inspection = render_html_from_source(source)
    diagnostics = [_to_build_diagnostic(diag) for diag in inspection.diagnostics]
    _extend_diagnostics(diagnostics_out, diagnostics)
    if html is None:
        raise ValueError(_format_kurzentwurf_export_error(diagnostics, "HTML"))
    target_path.write_text(html, encoding="utf-8")
    return target_path


def _save_png_pages(*, output_path: Path, pages: list[Image.Image]) -> list[Path]:
    target_path = validate_export_output_path(output_path.with_suffix(".png"), allowed_suffixes={".png"})
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not pages:
        raise ValueError("Export erzeugte keine Seiten.")

    created_files: list[Path] = []
    page_count = len(pages)
    for index, image in enumerate(pages, start=1):
        page_path = target_path if page_count == 1 else target_path.with_name(f"{target_path.stem}_{index:02d}{target_path.suffix}")
        image.save(page_path)
        created_files.append(page_path)
    return created_files


def _save_png_zip(*, output_path: Path, pages: list[Image.Image]) -> Path:
    target_path = validate_export_output_path(output_path.with_suffix(".zip"), allowed_suffixes={".zip"})
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not pages:
        raise ValueError("Export erzeugte keine Seiten.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, image in enumerate(pages, start=1):
                png_name = f"page_{index:03d}.png"
                png_path = tmp_dir_path / png_name
                image.save(png_path)
                archive.write(png_path, arcname=png_name)
    return target_path


def _ensure_supported_kurzentwurf_mode(include_solutions: bool):
    if include_solutions:
        raise ValueError("Kurzentwurf unterstuetzt keinen Loesungs- oder Beides-Export.")


def _extend_diagnostics(target: list[BuildDiagnostic] | None, diagnostics: list[BuildDiagnostic]):
    if target is None or not diagnostics:
        return
    target.extend(diagnostics)


def _to_build_diagnostic(diagnostic) -> BuildDiagnostic:
    line_number = getattr(diagnostic, "line", None)
    return BuildDiagnostic(
        code=str(getattr(diagnostic, "code", "KZF000") or "KZF000"),
        message=str(getattr(diagnostic, "message", "Kurzentwurf-Fehler") or "Kurzentwurf-Fehler"),
        severity=str(getattr(diagnostic, "severity", "warning") or "warning"),
        line_number=int(line_number) if isinstance(line_number, int) else None,
    )


def _format_kurzentwurf_export_error(diagnostics: list[BuildDiagnostic], export_kind: str) -> str:
    if not diagnostics:
        return f"Kurzentwurf konnte nicht als {export_kind} exportiert werden."

    error_diagnostics = [diag for diag in diagnostics if str(diag.severity or "").lower() == "error"]
    relevant = error_diagnostics or diagnostics
    lines = []
    for diagnostic in relevant[:5]:
        location = f" Zeile {diagnostic.line_number}" if diagnostic.line_number is not None else ""
        lines.append(f"- {diagnostic.code}{location}: {diagnostic.message}")
    return f"Kurzentwurf konnte nicht als {export_kind} exportiert werden:\n\n" + "\n".join(lines)