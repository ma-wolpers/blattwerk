"""Façade for rendering functions split across focused render modules."""

from __future__ import annotations

from .blatt_kern_answer_choice import (
    _estimate_mc_inline_weights,
    _normalize_choice_values,
    _normalize_gap_mode,
    _normalize_word_position,
    _parse_mc_inline_weights,
    _parse_multiple_choice_content,
    _render_answer_solution_text,
    _render_cloze_answer,
    _render_multiple_choice_answer,
    _shuffle_word_bank,
)
from .blatt_kern_answer_table import (
    _parse_css_size,
    _parse_option_list,
    _parse_table_widths,
    _render_answer_block,
    _render_table_answer,
    _wrap_answer_with_solution,
)
from .blatt_kern_help_render import collect_help_blocks, render_help_cards_html
from .blatt_kern_layout_render import (
    auto_columns_template,
    estimate_block_weight,
    parse_columns_template,
    parse_height_cm,
    render_body_with_columns,
    render_columns_container,
    render_html,
)
from .blatt_kern_task_render import (
    _render_material_block,
    _render_subtask_block,
    _render_symbol_span,
    _render_task_block,
    _render_task_content,
    render_block,
)

__all__ = [
    "render_block",
    "collect_help_blocks",
    "render_help_cards_html",
    "parse_columns_template",
    "parse_height_cm",
    "estimate_block_weight",
    "auto_columns_template",
    "render_columns_container",
    "render_body_with_columns",
    "render_html",
]
