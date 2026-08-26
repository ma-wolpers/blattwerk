"""Crossword answer renderer -- HTML/CSS-Grid orchestration.

Parsing/placement live in `crossword_placement.py`, clue numbering in
`crossword_numbering.py`, code-word cell selection in `crossword_code.py`.
This module only turns those results into HTML, mirroring the shape of
`answer_special_wordsearch.py::render_wordsearch_answer`.
"""

from __future__ import annotations

import random
from html import escape

from .answer_grid_plot import _grid_cell_size_to_cm, _parse_grid_scale
from .answer_special_shared import _new_markdown_converter, _safe_int, convert_markdown_with_math
from .block_computation_cache import ComputationKey, get_or_compute
from .crossword_code import validate_crossword_code
from .crossword_numbering import assign_crossword_numbers, grouped_clues
from .crossword_placement import (
    _CROSSWORD_ALGORITHM_VERSION,
    _crossword_seed_payload,
    build_crossword_layout,
    parse_crossword_code_options,
    parse_crossword_entries,
    resolve_crossword_bounds,
)
from .wordbank_position import (
    normalize_wordbank_position,
    resolve_wordbank_auto_position,
    wrap_with_wordbank_position,
)

_CELL_SIZE_CM = 0.72
_DEFAULT_PRINTABLE_WIDTH_CM = 18.0
_ARROW_HORIZONTAL = "▶"  # ▶
_ARROW_VERTICAL = "▼"  # ▼


def _as_float(value):
    """Converts to `float`, returning `None` instead of raising -- a local
    copy rather than a cross-module import, matching `answer_grid_plot.py`'s
    `_as_float` precedent (too small a helper to justify a dependency)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_cell_size_cm(options):
    """Resolves the `scale=` option to a cell size in cm.

    Reuses `answer_grid_plot.py`'s generic CSS-length parser/converter
    (already shared by `grid`/`geometry`'s own `scale=` option) instead of
    duplicating unit-conversion logic. Falls back to crossword's own
    default `_CELL_SIZE_CM` (0.72cm) -- not `answer_grid_plot.py`'s
    unrelated 0.5cm default -- both when `scale=` is absent and when it
    doesn't parse as a recognized CSS length, so existing crosswords (and
    ones with a typo'd `scale=`) render at exactly today's size.
    """
    raw_scale = str((options or {}).get("scale") or "").strip()
    if not raw_scale:
        return _CELL_SIZE_CM
    validated = _parse_grid_scale(raw_scale)
    if validated != raw_scale:
        return _CELL_SIZE_CM
    return _grid_cell_size_to_cm(validated)


def render_crossword_answer(options, content, include_solutions):
    """Renders a `:::crossword` block to HTML for worksheet or solution mode."""
    entries = parse_crossword_entries(content)
    if not entries:
        return ""

    options = options or {}
    cell_size_cm = _resolve_cell_size_cm(options)
    printable_width_cm = _as_float(options.get("_printable_width_cm"))
    printable_height_cm = _as_float(options.get("_printable_height_cm"))
    maxw, maxh = resolve_crossword_bounds(
        options,
        cell_size_cm=cell_size_cm,
        printable_width_cm=printable_width_cm,
        printable_height_cm=printable_height_cm,
    )
    code_word_raw, code_word, code_row = parse_crossword_code_options(options)
    cache = options.get("_computation_cache")

    layout_key = ComputationKey(
        block_type="crossword",
        version=_CROSSWORD_ALGORITHM_VERSION,
        payload=_crossword_seed_payload(entries, maxw, maxh, code_row, code_word),
    )
    layout = get_or_compute(
        cache,
        layout_key,
        lambda: build_crossword_layout(entries, maxw, maxh, code_row=code_row, code_word=code_word or None),
    )

    if layout is None:
        # Never a silent empty block -- the author needs to see that this
        # specific word list/grid size combination didn't work, even
        # outside the editor's live diagnostics (e.g. a direct HTML/PDF
        # export where diagnostics aren't shown inline).
        return (
            "<div class='answer crossword-answer crossword-answer-error'>"
            "Kreuzworträtsel konnte mit den gegebenen Wörtern nicht platziert werden. "
            "Bitte Rastergröße (<code>maxw=</code>/<code>maxh=</code>) vergrößern oder "
            "Wörter anpassen."
            "</div>"
        )

    numbering = assign_crossword_numbers(layout)
    prefill_count = max(0, _safe_int(options.get("prefill"), 0))
    prefill_cells = _resolve_prefill_cells(layout, layout_key, prefill_count) if not include_solutions else set()

    code_cell_positions = set()
    code_html = ""
    if code_word:
        code_key = ComputationKey(
            block_type="crossword_code_selection",
            version=_CROSSWORD_ALGORITHM_VERSION,
            payload={**layout_key.payload, "code_word": code_word},
        )
        selection = get_or_compute(cache, code_key, lambda: validate_crossword_code(layout, code_word))
        if selection is not None:
            code_cell_positions = {(entry.row, entry.col) for entry in selection.letters}
            if include_solutions:
                code_html = _render_code_solution(selection)

    cells = layout.cells()
    min_row, max_row, min_col, max_col = _occupied_bounding_box(cells)
    trimmed_cols = max_col - min_col + 1
    direction_markers = _cell_direction_markers(layout)

    cells_html = _render_grid_cells(
        cells,
        min_row,
        max_row,
        min_col,
        max_col,
        direction_markers,
        numbering,
        include_solutions,
        prefill_cells,
        code_cell_positions,
    )
    grid_html = (
        f"<div class='crossword-grid' style='--cw-cols:{trimmed_cols}; --cw-cell-size:{cell_size_cm}cm'>"
        f"{cells_html}</div>"
    )

    md = _new_markdown_converter()
    horizontal_clues, vertical_clues = grouped_clues(layout, numbering)
    clues_html = _render_clue_lists(horizontal_clues, vertical_clues, md)

    position = normalize_wordbank_position(options.get("position"), default="auto")
    if position == "auto":
        main_content_width_cm = trimmed_cols * cell_size_cm
        position = resolve_wordbank_auto_position(
            main_content_width_cm, printable_width_cm or _DEFAULT_PRINTABLE_WIDTH_CM
        )
    combined_html = wrap_with_wordbank_position(grid_html, clues_html, position, extra_classes=["crossword-layout"])

    return f"<div class='answer crossword-answer'>{combined_html}{code_html}</div>"


def _resolve_prefill_cells(layout, layout_key, prefill_count):
    """Deterministically picks `prefill_count` occupied cells to reveal in
    worksheet mode. Seeded from the same normalized inputs as the layout's
    cache key plus the prefill count itself, so the same document always
    prefills the same cells (see `block_computation_cache.py`'s determinism
    invariant -- prefill isn't itself cached, but must still be
    reproducible)."""
    if prefill_count <= 0:
        return set()

    positions = sorted(layout.cells().keys())
    if not positions:
        return set()

    seed = repr((sorted(layout_key.payload.items()), prefill_count))
    rng = random.Random(seed)
    rng.shuffle(positions)
    return set(positions[:prefill_count])


def _cell_direction_markers(layout):
    """`(row, col) -> set of "H"/"V"` for every non-code-row word start --
    used only to pick the arrow glyph(s) on numbered cells."""
    markers: dict[tuple[int, int], set] = {}
    for placement in layout.placements:
        if placement.is_code_row:
            continue
        markers.setdefault((placement.row, placement.col), set()).add(placement.direction)
    return markers


def _occupied_bounding_box(cells):
    """Returns `(min_row, max_row, min_col, max_col)` spanning every occupied
    cell in `cells` (a `{(row, col): CrosswordCell}` mapping, as returned by
    `CrosswordLayout.cells()`).

    `CrosswordLayout.rows`/`.cols` describe the *full search space*
    (`maxw`/`maxh`), not the area the placed words actually occupy -- a
    puzzle that only fills a small corner of a generously sized `maxw=15
    maxh=15` grid would otherwise render 200+ invisible `cw-cell-blocked`
    cells around it. `_render_grid_cells` uses this bounding box to trim the
    rendered/CSS-grid size to what's actually there; the layout's own
    coordinates and cache key are untouched (this is a rendering-only crop).
    Callers must not call this with an empty `cells` (a successfully built
    `CrosswordLayout` always has at least one placed word).
    """
    rows = [row for row, _col in cells]
    cols = [col for _row, col in cells]
    return min(rows), max(rows), min(cols), max(cols)


def _render_grid_cells(
    cells,
    min_row,
    max_row,
    min_col,
    max_col,
    direction_markers,
    numbering,
    include_solutions,
    prefill_cells,
    code_cell_positions,
):
    parts = []

    for row in range(min_row, max_row + 1):
        for col in range(min_col, max_col + 1):
            position = (row, col)
            cell = cells.get(position)
            if cell is None:
                parts.append("<span class='cw-cell cw-cell-blocked'></span>")
                continue

            css_classes = ["cw-cell"]
            if position in code_cell_positions:
                css_classes.append("cw-cell-code")

            number = numbering.numbers.get(position)
            number_html = ""
            if number is not None:
                directions = direction_markers.get(position, set())
                arrow = ""
                if "H" in directions:
                    arrow += _ARROW_HORIZONTAL
                if "V" in directions:
                    arrow += _ARROW_VERTICAL
                number_html = f"<span class='cw-cell-number'>{arrow}{number}</span>"

            show_letter = include_solutions or position in prefill_cells
            letter_html = escape(cell.letter) if show_letter else ""
            parts.append(f"<span class='{' '.join(css_classes)}'>{number_html}{letter_html}</span>")

    return "".join(parts)


def _render_clue_group(label, clues, md):
    if not clues:
        return ""
    items = "".join(
        f"<li value='{number}'>{convert_markdown_with_math(md, clue).strip()}</li>"
        for number, _word, clue in clues
    )
    return f"<div class='crossword-clue-group'><h4 class='crossword-clue-heading'>{escape(label)}</h4><ol class='crossword-clues'>{items}</ol></div>"


def _render_clue_lists(horizontal_clues, vertical_clues, md):
    groups = _render_clue_group("Waagerecht", horizontal_clues, md) + _render_clue_group(
        "Senkrecht", vertical_clues, md
    )
    if not groups:
        return ""
    return f"<div class='crossword-clues-wrap'>{groups}</div>"


def _render_code_solution(selection):
    if not selection.letters:
        return ""
    letters_html = "".join(
        f"<span class='crossword-code-letter'>{escape(entry.letter)}</span>" for entry in selection.letters
    )
    return (
        "<div class='crossword-code'>"
        "<span class='crossword-code-label'>Lösungscode:</span> "
        f"{letters_html}"
        "</div>"
    )


def estimate_crossword_weight(options, content):
    """Estimates layout weight for automatic column-width sizing, mirroring
    `estimate_wordsearch_weight`'s shape/clamping."""
    entries = parse_crossword_entries(content)
    if not entries:
        return 0.0
    options = options or {}
    maxw, maxh = resolve_crossword_bounds(options, cell_size_cm=_resolve_cell_size_cm(options))
    area_estimate = max(36, maxw * maxh)
    return max(2.0, min(7.8, area_estimate / 40.0))
