"""Explicit core wiring surface for external callers.

This module is the only allowed re-export surface in app.core.
It provides a stable import path for high-level build/parse/render helpers.
"""

from __future__ import annotations

from .blatt_kern_io_build import (
    BuildDiagnostic,
    InspectedDocument,
    build_help_cards,
    build_worksheet,
    inspect_markdown_document,
    inspect_markdown_text,
)
from .blatt_kern_io_html import absolutize_local_image_sources, apply_image_size_options
from .blatt_kern_io_pdf import (
    annotate_pdf_running_elements,
    annotate_pdf_running_elements_with_retry,
    find_chromium_executable,
    verify_pdf_running_elements,
    wait_for_file_stable,
    write_pdf_from_html,
)
from .blatt_kern_help_render import collect_help_blocks, render_help_cards_html
from .blatt_kern_layout_render import render_html
from .blatt_kern_shared import parse_blocks, parse_options, split_front_matter

__all__ = [
    "BuildDiagnostic",
    "InspectedDocument",
    "absolutize_local_image_sources",
    "annotate_pdf_running_elements",
    "annotate_pdf_running_elements_with_retry",
    "apply_image_size_options",
    "build_help_cards",
    "build_worksheet",
    "collect_help_blocks",
    "find_chromium_executable",
    "inspect_markdown_document",
    "inspect_markdown_text",
    "parse_blocks",
    "parse_options",
    "render_help_cards_html",
    "render_html",
    "split_front_matter",
    "verify_pdf_running_elements",
    "wait_for_file_stable",
    "write_pdf_from_html",
]
