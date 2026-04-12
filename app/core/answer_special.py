"""Spezielle Antworttypen für Blattwerk (Matching, Buchstabensalat)."""

from __future__ import annotations

from .answer_special_matching import (
    _normalize_matching_layout,
    _parse_matching_content,
    _parse_matching_pairs,
    _render_matching_horizontal_svg,
    _render_matching_item,
    _render_matching_vertical_svg,
    estimate_matching_weight,
    render_matching_answer,
)
from .answer_special_shared import (
    MARKDOWN_EXTENSIONS,
    _as_text_list,
    _new_markdown_converter,
    _normalize_keyword,
    _option_is_enabled,
    _parse_option_list,
    _safe_int,
    normalize_markdown,
)
from .answer_special_wordsearch import (
    _assign_wordsearch_directions,
    _build_wordsearch_grid,
    _normalize_wordsearch_token,
    _parse_min_wordsearch_size,
    _wordsearch_candidate_positions,
    _wordsearch_dimensions_feasible,
    _wordsearch_place_word,
    _wordsearch_unplace_word,
    estimate_wordsearch_weight,
    parse_wordsearch_words,
    render_wordsearch_answer,
)
