"""Wordsearch answer renderer -- word parsing and HTML orchestration.

Grid-placement algorithm lives in `wordsearch_placement.py` (split out to
keep both files under the project's ~300-line convention).
"""

from __future__ import annotations

import re
from html import escape

from .answer_special_shared import _as_text_list
from .block_computation_cache import ComputationKey, get_or_compute
from .wordbank_position import normalize_wordbank_position, resolve_wordbank_auto_position, wrap_with_wordbank_position
from .wordsearch_placement import (
    _WORDSEARCH_ALGORITHM_VERSION,
    _build_wordsearch_grid,
    _normalize_wordsearch_token,
    _wordsearch_seed_payload,
)


_WORDSEARCH_CELL_SIZE_CM = 0.68
"""Matches `.wordsearch-grid`'s `--cell-size` CSS default (`assets/worksheet.css`)
-- only used to estimate the grid's rendered width for `position=auto`."""


def _as_float(value):
    """Converts to `float`, returning `None` instead of raising."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_wordsearch_words(options, content):
    """Sammelt und dedupliziert Wortlisten aus Blockinhalt und Optionen."""
    words = []

    for raw_line in (content or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        bullet_match = re.match(r"^[-*+]\s+(.*)$", stripped)
        candidate = bullet_match.group(1).strip() if bullet_match else stripped

        for part in re.split(r"[,;|]", candidate):
            normalized = _normalize_wordsearch_token(part)
            if normalized:
                words.append(normalized)

    option_words = _as_text_list(options.get("words") or options.get("word_list"))
    for part in option_words:
        normalized = _normalize_wordsearch_token(part)
        if normalized:
            words.append(normalized)

    unique_words = []
    seen = set()
    for word in words:
        if word in seen:
            continue
        seen.add(word)
        unique_words.append(word)

    return unique_words


def render_wordsearch_answer(options, content, include_solutions):
    """Generiert die HTML-Darstellung der Wortsuche mit Lösungen."""
    words = parse_wordsearch_words(options, content)
    if not words:
        return ""

    cache = options.get("_computation_cache")
    layout_key = ComputationKey(
        block_type="wordsearch",
        version=_WORDSEARCH_ALGORITHM_VERSION,
        payload=_wordsearch_seed_payload(words, options),
    )
    generated = get_or_compute(cache, layout_key, lambda: _build_wordsearch_grid(words, options))
    if not generated:
        return ""

    rows = generated["rows"]
    cols = generated["cols"]
    grid = generated["grid"]
    placements = generated["placements"]
    ordered_words = generated["words"]

    solution_map = {}
    if include_solutions:
        for word_index, word in enumerate(ordered_words):
            placement = placements.get(word)
            if placement is None:
                continue
            start_row, start_col, d_row, d_col = placement
            for letter_index in range(len(word)):
                row = start_row + d_row * letter_index
                col = start_col + d_col * letter_index
                solution_map.setdefault((row, col), []).append(word_index)

    cells_html = []
    for row in range(rows):
        for col in range(cols):
            css_classes = ["ws-cell"]
            if include_solutions and (row, col) in solution_map:
                color_index = solution_map[(row, col)][0] % 8
                css_classes.append("ws-solved")
                css_classes.append(f"ws-hit-{color_index}")
            cells_html.append(
                f"<span class='{' '.join(css_classes)}'>{escape(grid[row][col])}</span>"
            )

    word_items = []
    for word_index, word in enumerate(ordered_words):
        css_classes = ["ws-word"]
        if include_solutions:
            css_classes.append(f"ws-hit-{word_index % 8}")
        word_items.append(f"<li class='{' '.join(css_classes)}'>{escape(word)}</li>")

    grid_html = f"<div class='wordsearch-grid' style='--ws-cols:{cols}'>{''.join(cells_html)}</div>"
    words_html = f"<ul class='wordsearch-words'>{''.join(word_items)}</ul>"

    position = normalize_wordbank_position(options.get("position"), default="below")
    if position == "auto":
        printable_width_cm = _as_float(options.get("_printable_width_cm")) or 18.0
        position = resolve_wordbank_auto_position(cols * _WORDSEARCH_CELL_SIZE_CM, printable_width_cm)

    combined_html = wrap_with_wordbank_position(grid_html, words_html, position)

    return f"<div class='answer wordsearch-answer'>{combined_html}</div>"


def estimate_wordsearch_weight(options, content):
    """Schätzt das Gewicht der Wortsuche basierend auf den Wörtern."""
    words = parse_wordsearch_words(options, content)
    if not words:
        return 0.0
    area_estimate = max(36, sum(len(word) for word in words) * 1.4)
    return max(2.0, min(7.8, area_estimate / 18.0))
