"""Categorize answer renderer -- sort a word bank into given category columns.

Genuinely new capability, not covered by existing blocks: `table` has no
word-bank concept, `matching` connects two lists with lines instead of
"put word under column", `cloze` has the chip word-bank rendering but no
column-sorting target.
"""

from __future__ import annotations

import random
from html import escape

import yaml

from .answer_special_shared import _new_markdown_converter, _option_is_enabled, normalize_markdown
from .wordbank_position import normalize_wordbank_position, resolve_wordbank_auto_position, wrap_with_wordbank_position

_DEFAULT_PRINTABLE_WIDTH_CM = 18.0
_ESTIMATED_COLUMN_WIDTH_CM = 3.0


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_categorize_payload(content):
    """Parses `categories:`/`items:` YAML into `(categories, items)`.

    `categories` is a list of header strings; `items` is a list of
    `(word, category_index)` pairs, `category_index` 1-based into
    `categories`. Returns `([], [])` for empty/unparsable content, mirroring
    `parse_crossword_entries`'s fail-quiet convention (the generic `AN003`/
    `AN004` diagnostics already cover malformed YAML at the validator level).
    """
    if not (content or "").strip():
        return [], []

    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError:
        return [], []

    if not isinstance(parsed, dict):
        return [], []

    categories_raw = parsed.get("categories") or parsed.get("kategorien") or []
    categories = (
        [str(category).strip() for category in categories_raw if str(category).strip()]
        if isinstance(categories_raw, list)
        else []
    )
    if not categories:
        return [], []

    items_raw = parsed.get("items") or parsed.get("begriffe") or []
    items = []
    if isinstance(items_raw, list):
        for entry in items_raw:
            if not isinstance(entry, dict):
                continue
            word = str(entry.get("word") or entry.get("wort") or "").strip()
            category_raw = entry.get("category") or entry.get("kategorie")
            try:
                category_index = int(category_raw)
            except (TypeError, ValueError):
                continue
            if word and 1 <= category_index <= len(categories):
                items.append((word, category_index))

    return categories, items


def _shuffle_categorize_words(words):
    """Deterministically shuffles the word bank, seeded from the words
    themselves, avoiding the identity permutation when possible -- mirrors
    `_shuffle_word_bank` (cloze) / `_shuffle_ranked_items` (ordering)."""
    if len(words) <= 1:
        return list(words)

    rng = random.Random("|".join(words))
    shuffled = list(words)
    original = list(words)
    for _ in range(8):
        rng.shuffle(shuffled)
        if shuffled != original:
            return shuffled
    return original[1:] + original[:1]


def render_categorize_answer(options, content, include_solutions):
    """Renders a `:::categorize` block: a column-per-category table, plus a
    word bank (worksheet mode) or the correctly sorted words (solution mode)."""
    options = options or {}
    categories, items = parse_categorize_payload(content)
    if not categories or not items:
        return ""

    by_category = {index: [] for index in range(1, len(categories) + 1)}
    for word, category_index in items:
        by_category[category_index].append(word)

    max_rows = max((len(words) for words in by_category.values()), default=0)
    if max_rows == 0:
        return ""

    md = _new_markdown_converter()
    header_html = "".join(
        f"<th>{md.convert(normalize_markdown(category)).strip()}</th>" for category in categories
    )

    body_rows = []
    for row_index in range(max_rows):
        cells = []
        for category_index in range(1, len(categories) + 1):
            words_in_category = by_category[category_index]
            cell_text = ""
            if include_solutions and row_index < len(words_in_category):
                cell_text = escape(words_in_category[row_index])
            cells.append(f"<td>{cell_text}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    table_html = (
        "<table class='categorize-table'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )

    word_bank_html = ""
    if not include_solutions:
        shuffle = _option_is_enabled(options.get("shuffle"), default=True)
        words = [word for word, _category_index in items]
        display_words = _shuffle_categorize_words(words) if shuffle else words
        chips = "".join(f"<span class='categorize-word'>{escape(word)}</span>" for word in display_words)
        word_bank_html = f"<div class='categorize-wordbank'>{chips}</div>"

    position = normalize_wordbank_position(options.get("position"), default="below")
    if position == "auto":
        printable_width_cm = _as_float(options.get("_printable_width_cm")) or _DEFAULT_PRINTABLE_WIDTH_CM
        main_content_width_cm = len(categories) * _ESTIMATED_COLUMN_WIDTH_CM
        position = resolve_wordbank_auto_position(main_content_width_cm, printable_width_cm)

    combined_html = wrap_with_wordbank_position(table_html, word_bank_html, position)
    return f"<div class='answer categorize-answer'>{combined_html}</div>"


def estimate_categorize_weight(options, content):
    """Estimates layout weight from category/item counts."""
    categories, items = parse_categorize_payload(content)
    if not categories or not items:
        return 0.0
    return max(1.5, min(7.0, 0.8 + len(categories) * 0.4 + len(items) * 0.25))
