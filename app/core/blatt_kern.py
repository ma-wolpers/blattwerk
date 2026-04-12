"""Façade module preserving legacy imports for worksheet generation."""

from __future__ import annotations

from .blatt_kern_io import (
    BuildDiagnostic,
    InspectedDocument,
    annotate_pdf_running_elements,
    annotate_pdf_running_elements_with_retry,
    apply_image_size_options,
    absolutize_local_image_sources,
    build_help_cards,
    build_worksheet,
    find_chromium_executable,
    inspect_markdown_document,
    inspect_markdown_text,
    verify_pdf_running_elements,
    wait_for_file_stable,
    write_pdf_from_html,
)
from .blatt_kern_render import (
    collect_help_blocks,
    render_help_cards_html,
    render_html,
)
from .blatt_kern_shared import parse_blocks, parse_options, split_front_matter

__all__ = [
    "build_worksheet",
    "build_help_cards",
    "inspect_markdown_document",
    "inspect_markdown_text",
    "BuildDiagnostic",
    "InspectedDocument",
    "render_html",
    "render_help_cards_html",
    "collect_help_blocks",
    "split_front_matter",
    "parse_options",
    "parse_blocks",
    "absolutize_local_image_sources",
    "apply_image_size_options",
    "find_chromium_executable",
    "write_pdf_from_html",
    "wait_for_file_stable",
    "annotate_pdf_running_elements",
    "annotate_pdf_running_elements_with_retry",
    "verify_pdf_running_elements",
]
