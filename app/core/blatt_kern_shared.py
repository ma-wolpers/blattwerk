"""Shared parsing and metadata helpers for worksheet generation (öffentliche Fassade).

Schlanker Re-Export-Einstiegspunkt (300-Zeilen-Konvention): die eigentliche
Logik ist auf vier fokussierte Nachbarmodule verteilt —
`blatt_kern_shared_data.py` (Konstanten, u. a. `CONTROL_MARKERS`),
`blatt_kern_shared_parsing.py` (Frontmatter-/Block-Parser),
`blatt_kern_shared_blocks.py` (Nachbearbeitung geparster Blocklisten) und
`blatt_kern_shared_meta.py` (Meta-/Formatierungs-Helfer). Externer Code
importiert weiterhin unverändert aus `app.core.blatt_kern_shared`; dieser
Modulpfad ist ein reines internes Implementierungsdetail.
"""

from __future__ import annotations

from .blatt_kern_shared_blocks import (
    _alpha_label,
    _dedupe_preserve_order,
    _format_help_reference_text,
    _help_labels_for_tag,
    _normalize_help_tag,
    annotate_standalone_subtasks,
    annotate_task_help_references,
    assign_task_numbers,
    should_render_block,
)
from .blatt_kern_shared_data import (
    CONTROL_MARKERS,
    DOCUMENT_MODE_ALIASES,
    DOCUMENT_MODES,
    HELP_BLOCK_TYPES,
    JA_NEIN_BOOLEAN_TOKENS,
    MARKDOWN_EXTENSIONS,
    PRESENTATION_SECTION_MARK_PATTERN,
    PRESENTATION_SPACER_MARK_PATTERN,
    TASK_ACTION_MAP,
    TASK_HINT_MAP,
    WORK_MODE_MAP,
    ControlMarkerSpec,
)
from .blatt_kern_shared_meta import (
    _meta_bool_ja_nein,
    _normalize_keyword,
    _option_is_enabled,
    _resolve_help_level,
    _safe_int,
    format_meta_line,
    get_copyright_text,
    get_current_school_year_label,
    get_task_action_info,
    get_task_hint_info,
    get_work_info,
    is_hole_punch_layout_enabled,
    normalize_document_mode,
    split_sections,
)
from .blatt_kern_shared_parsing import (
    _new_markdown_converter,
    _parse_inline_control_marker,
    build_block_index_line_map,
    convert_markdown_with_math,
    normalize_markdown,
    parse_blocks,
    parse_options,
    split_front_matter,
)

__all__ = [
    "MARKDOWN_EXTENSIONS",
    "WORK_MODE_MAP",
    "TASK_ACTION_MAP",
    "TASK_HINT_MAP",
    "HELP_BLOCK_TYPES",
    "DOCUMENT_MODES",
    "DOCUMENT_MODE_ALIASES",
    "PRESENTATION_SECTION_MARK_PATTERN",
    "PRESENTATION_SPACER_MARK_PATTERN",
    "ControlMarkerSpec",
    "CONTROL_MARKERS",
    "JA_NEIN_BOOLEAN_TOKENS",
    "split_front_matter",
    "parse_options",
    "parse_blocks",
    "build_block_index_line_map",
    "normalize_markdown",
    "convert_markdown_with_math",
    "assign_task_numbers",
    "annotate_standalone_subtasks",
    "annotate_task_help_references",
    "should_render_block",
    "normalize_document_mode",
    "is_hole_punch_layout_enabled",
    "format_meta_line",
    "get_current_school_year_label",
    "get_copyright_text",
    "get_work_info",
    "get_task_action_info",
    "get_task_hint_info",
    "split_sections",
]
