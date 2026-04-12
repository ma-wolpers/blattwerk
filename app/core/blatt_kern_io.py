"""Compatibility façade for IO, HTML post-processing, and PDF helpers."""

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
    CHROMIUM_COMMAND_CANDIDATES,
    CHROMIUM_PATH_CANDIDATES,
    annotate_pdf_running_elements,
    annotate_pdf_running_elements_with_retry,
    find_chromium_executable,
    verify_pdf_running_elements,
    wait_for_file_stable,
    write_pdf_from_html,
)
