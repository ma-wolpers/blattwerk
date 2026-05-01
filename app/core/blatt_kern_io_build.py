"""Worksheet/help-card build orchestration helpers."""

from __future__ import annotations

from pathlib import Path

from .export_path_guardrails import validate_export_output_path
from .blatt_kern_io_html import absolutize_local_image_sources, apply_image_size_options
from .blatt_kern_io_pdf import annotate_pdf_running_elements_with_retry, write_pdf_from_html
from .blatt_kern_help_render import collect_help_blocks, render_help_cards_html
from .blatt_kern_layout_render import render_html
from .blatt_kern_shared import get_copyright_text, normalize_document_mode
from .blatt_validator import (
    BuildDiagnostic,
    InspectedDocument,
    has_blocking_diagnostics,
    inspect_markdown_document,
    inspect_markdown_text,
    summarize_blocking_diagnostics,
)


def _raise_on_blocking_diagnostics(diagnostics):
    if not has_blocking_diagnostics(diagnostics):
        return
    summary = summarize_blocking_diagnostics(diagnostics)
    raise ValueError(f"Dokument enthaelt kritische Fehler und kann nicht gebaut werden:\n{summary}")


def _merge_metadata_defaults(meta: dict[str, object], metadata_defaults: dict[str, str] | None):
    """Merge default metadata values into parsed frontmatter when fields are missing."""

    if not metadata_defaults:
        return dict(meta)

    merged = dict(meta)
    for key, value in metadata_defaults.items():
        text = str(value or "").strip()
        if not text:
            continue
        existing = str(merged.get(key, "") or "").strip()
        if not existing:
            merged[key] = text
    return merged


def build_worksheet(
    md_path,
    out_path,
    include_solutions=False,
    page_format="a4_portrait",
    print_profile="standard",
    color_profile="indigo",
    font_profile="segoe",
    font_size_profile="normal",
    diagnostics_out=None,
    block_on_critical=True,
    metadata_defaults=None,
    copyright_text_override=None,
    black_screen_mode="none",
):
    """Erstellt aus einer Markdown-Datei eine HTML- oder PDF-Ausgabe."""
    md_file = Path(md_path)
    text = md_file.read_text(encoding="utf-8")
    inspected = inspect_markdown_text(text)
    meta = _merge_metadata_defaults(inspected.meta, metadata_defaults)
    document_mode = normalize_document_mode((meta or {}).get("mode"), default="worksheet")
    if document_mode == "presentation":
        include_solutions = False
    blocks = inspected.blocks
    if block_on_critical:
        _raise_on_blocking_diagnostics(inspected.diagnostics)
    if diagnostics_out is not None:
        diagnostics_out.extend(inspected.diagnostics)
    html = render_html(
        meta,
        blocks,
        include_solutions=include_solutions,
        page_format=page_format,
        print_profile=print_profile,
        color_profile=color_profile,
        font_profile=font_profile,
        font_size_profile=font_size_profile,
        black_screen_mode=black_screen_mode,
    )
    html = absolutize_local_image_sources(html, md_file.parent)
    html = apply_image_size_options(html)

    out_file = validate_export_output_path(
        out_path,
        allowed_suffixes={".pdf", ".html"},
    )
    suffix = out_file.suffix.lower()

    if suffix == ".html":
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(html, encoding="utf-8")
        return out_file

    if suffix == ".pdf":
        pdf_file = write_pdf_from_html(html, out_file)
        if document_mode != "presentation":
            annotate_pdf_running_elements_with_retry(
                pdf_file,
                meta.get("Titel", "").strip(),
                str(copyright_text_override or get_copyright_text(meta)),
                print_profile=print_profile,
                include_solutions=include_solutions,
            )
        return pdf_file

    raise ValueError("Ausgabedatei muss auf .pdf oder .html enden.")


def build_help_cards(
    md_path,
    out_path,
    include_solutions=False,
    page_format="a4_portrait",
    print_profile="standard",
    color_profile="indigo",
    font_profile="segoe",
    font_size_profile="normal",
    add_running_elements=True,
    diagnostics_out=None,
    block_on_critical=True,
    metadata_defaults=None,
    copyright_text_override=None,
):
    """Erstellt aus Hilfeblöcken einer Markdown-Datei eine HTML- oder PDF-Ausgabe."""

    md_file = Path(md_path)
    text = md_file.read_text(encoding="utf-8")
    inspected = inspect_markdown_text(text)
    meta = _merge_metadata_defaults(inspected.meta, metadata_defaults)
    blocks = inspected.blocks
    if block_on_critical:
        _raise_on_blocking_diagnostics(inspected.diagnostics)
    if diagnostics_out is not None:
        diagnostics_out.extend(inspected.diagnostics)

    help_blocks = collect_help_blocks(blocks, include_solutions=include_solutions)
    if not help_blocks:
        raise ValueError("Keine Hilfeblöcke gefunden.")

    html = render_help_cards_html(
        meta,
        blocks,
        include_solutions=include_solutions,
        page_format=page_format,
        print_profile=print_profile,
        color_profile=color_profile,
        font_profile=font_profile,
        font_size_profile=font_size_profile,
    )
    html = absolutize_local_image_sources(html, md_file.parent)
    html = apply_image_size_options(html)

    out_file = validate_export_output_path(
        out_path,
        allowed_suffixes={".pdf", ".html"},
    )
    suffix = out_file.suffix.lower()

    if suffix == ".html":
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(html, encoding="utf-8")
        return out_file

    if suffix == ".pdf":
        pdf_file = write_pdf_from_html(html, out_file)
        if add_running_elements:
            annotate_pdf_running_elements_with_retry(
                pdf_file,
                meta.get("Titel", "").strip(),
                str(copyright_text_override or get_copyright_text(meta)),
                print_profile=print_profile,
                include_solutions=include_solutions,
            )
        return pdf_file

    raise ValueError("Ausgabedatei muss auf .pdf oder .html enden.")
