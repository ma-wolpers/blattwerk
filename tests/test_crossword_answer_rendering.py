import re

import app.core.answer_special_crossword as crossword_module
from app.core.answer_special_crossword import estimate_crossword_weight, render_crossword_answer
from app.core.block_computation_cache import BlockComputationCache
from app.core.crossword_numbering import assign_crossword_numbers
from app.core.crossword_placement import CrosswordLayout, CrosswordPlacement

_CONTENT = """
words:
  - word: SCHULE
    clue: Wo man lernt
  - word: LEHRER
    clue: Unterrichtet
  - word: KREIDE
    clue: Zum Schreiben an der Tafel
  - word: TAFEL
    clue: Haengt an der Wand
"""


def _cell_spans(html):
    """Extracts the raw '<span class=...>...</span>' cell markup as a list."""
    import re

    return re.findall(r"<span class='cw-cell[^>]*>.*?</span>", html)


def test_render_crossword_answer_returns_empty_string_for_no_entries():
    assert render_crossword_answer({"maxw": 10, "maxh": 10}, "", include_solutions=False) == ""
    assert render_crossword_answer({"maxw": 10, "maxh": 10}, "words: []", include_solutions=False) == ""


def test_render_crossword_answer_worksheet_mode_hides_letters():
    html = render_crossword_answer({"maxw": 15, "maxh": 15}, _CONTENT, include_solutions=False)

    assert "crossword-grid" in html
    spans = _cell_spans(html)
    occupied = [s for s in spans if "cw-cell-blocked" not in s]
    assert occupied
    # No bare uppercase letter should appear as cell text content in worksheet mode.
    for span in occupied:
        # Strip any nested cw-cell-number span, then check remaining text is empty.
        import re

        without_number = re.sub(r"<span class='cw-cell-number'>.*?</span>", "", span)
        text_only = re.sub(r"<[^>]+>", "", without_number)
        assert text_only == ""


def test_render_crossword_answer_solution_mode_shows_letters():
    html = render_crossword_answer({"maxw": 15, "maxh": 15}, _CONTENT, include_solutions=True)

    spans = _cell_spans(html)
    occupied = [s for s in spans if "cw-cell-blocked" not in s]
    assert occupied
    letters_found = 0
    for span in occupied:
        import re

        without_number = re.sub(r"<span class='cw-cell-number'>.*?</span>", "", span)
        text_only = re.sub(r"<[^>]+>", "", without_number)
        if text_only.strip():
            letters_found += 1
    assert letters_found > 0


def test_render_crossword_answer_has_numbered_cells_with_clue_list():
    html = render_crossword_answer({"maxw": 15, "maxh": 15}, _CONTENT, include_solutions=True)

    assert "cw-cell-number" in html
    assert "Waagerecht" in html
    assert "Senkrecht" in html
    assert "Wo man lernt" in html  # clue text rendered


def test_render_crossword_answer_keeps_distinct_clues_for_digit_differing_words():
    # End-to-end regression for the bundled Ctrl+B example (Wort1/Wort2/Wort3):
    # crossword normalization must not strip digits (that would collapse all
    # three onto "WORT" and silently drop two clues -- see
    # crossword_placement.py::_normalize_crossword_token).
    content = """
words:
  - word: Wort1
    clue: Erster Hinweis
  - word: Wort2
    clue: Zweiter Hinweis
  - word: Wort3
    clue: Dritter Hinweis
"""
    html = render_crossword_answer({"maxw": 15, "maxh": 15}, content, include_solutions=True)

    assert "Erster Hinweis" in html
    assert "Zweiter Hinweis" in html
    assert "Dritter Hinweis" in html


def test_render_crossword_answer_keeps_distinct_clues_for_genuine_word_collision():
    # Even a real collision (case-only difference, no digits) must not lose
    # a clue -- grouped_clues() reads the clue off each placement directly,
    # not via a word-text-keyed lookup that would overwrite on collision.
    content = """
words:
  - word: haus
    clue: Erste Nennung
  - word: HAUS
    clue: Zweite Nennung bleibt erhalten
"""
    html = render_crossword_answer({"maxw": 15, "maxh": 15}, content, include_solutions=True)

    assert "Erste Nennung" in html
    assert "Zweite Nennung bleibt erhalten" in html


def test_render_crossword_answer_trims_to_occupied_bounding_box_not_full_search_space():
    # Regression test for the "huge empty space" bug: CrosswordLayout.rows/
    # .cols describe the full maxw x maxh search space, not the area the
    # placed words actually occupy. A hand-built layout whose occupied
    # cells sit away from (0, 0) and far short of the declared 15x15
    # search space catches a fix that still naively iterates
    # range(rows) x range(cols) from the origin -- that would either render
    # 225 cells (unfixed) or accidentally pass if the occupied area
    # happened to start at the origin.
    placements = (
        CrosswordPlacement(word="TEST", row=3, col=5, direction="H"),
        CrosswordPlacement(word="TANK", row=3, col=5, direction="V"),
    )
    layout = CrosswordLayout(rows=15, cols=15, placements=placements)
    numbering = assign_crossword_numbers(layout)
    cells = layout.cells()
    min_row, max_row, min_col, max_col = crossword_module._occupied_bounding_box(cells)

    assert (min_row, max_row, min_col, max_col) == (3, 6, 5, 8)

    direction_markers = crossword_module._cell_direction_markers(layout)
    cells_html = crossword_module._render_grid_cells(
        cells, min_row, max_row, min_col, max_col, direction_markers, numbering, True, set(), set()
    )
    spans = re.findall(r"<span class='cw-cell[^>]*>.*?</span>", cells_html)

    assert len(spans) == 16  # 4 rows x 4 cols, not the 15x15 = 225 search space
    grid_html = f"<div class='crossword-grid' style='--cw-cols:{max_col - min_col + 1}'>{cells_html}</div>"
    assert "--cw-cols:4" in grid_html


def test_render_crossword_answer_grid_trims_realistic_puzzle_well_below_search_space():
    html = render_crossword_answer({"maxw": 15, "maxh": 15}, _CONTENT, include_solutions=True)
    match = re.search(r"--cw-cols:(\d+)", html)
    assert match is not None
    assert int(match.group(1)) < 15


def test_render_crossword_answer_renders_all_cells_when_bounding_box_fills_the_full_grid():
    # A puzzle whose placed words happen to fill the entire declared search
    # space must still render every cell correctly (no off-by-one at the
    # edges from the trim).
    placements = (CrosswordPlacement(word="AB", row=0, col=0, direction="H"),)
    layout = CrosswordLayout(rows=1, cols=2, placements=placements)
    numbering = assign_crossword_numbers(layout)
    cells = layout.cells()
    min_row, max_row, min_col, max_col = crossword_module._occupied_bounding_box(cells)
    direction_markers = crossword_module._cell_direction_markers(layout)
    cells_html = crossword_module._render_grid_cells(
        cells, min_row, max_row, min_col, max_col, direction_markers, numbering, True, set(), set()
    )
    spans = re.findall(r"<span class='cw-cell[^>]*>.*?</span>", cells_html)

    assert len(spans) == 2
    assert all("cw-cell-blocked" not in span for span in spans)


def test_render_crossword_answer_prefill_reveals_letters_in_worksheet_mode():
    html_no_prefill = render_crossword_answer(
        {"maxw": 15, "maxh": 15, "prefill": 0}, _CONTENT, include_solutions=False
    )
    html_prefilled = render_crossword_answer(
        {"maxw": 15, "maxh": 15, "prefill": 5}, _CONTENT, include_solutions=False
    )

    def _visible_letter_count(html):
        import re

        count = 0
        for span in _cell_spans(html):
            if "cw-cell-blocked" in span:
                continue
            without_number = re.sub(r"<span class='cw-cell-number'>.*?</span>", "", span)
            text_only = re.sub(r"<[^>]+>", "", without_number)
            if text_only.strip():
                count += 1
        return count

    assert _visible_letter_count(html_no_prefill) == 0
    assert _visible_letter_count(html_prefilled) == 5


def test_render_crossword_answer_prefill_is_deterministic():
    options = {"maxw": 15, "maxh": 15, "prefill": 4}
    first = render_crossword_answer(options, _CONTENT, include_solutions=False)
    second = render_crossword_answer(options, _CONTENT, include_solutions=False)
    assert first == second


def test_render_crossword_answer_placement_failure_shows_visible_message_not_empty_string():
    # HAUS/BAUM/AUTO are a verified-infeasible combination (see
    # test_crossword_placement.py) -- confirms no silent empty output.
    content = "words:\n  - word: HAUS\n    clue: a\n  - word: BAUM\n    clue: b\n  - word: AUTO\n    clue: c\n"
    html = render_crossword_answer({"maxw": 12, "maxh": 12}, content, include_solutions=False)

    assert html != ""
    assert "crossword-answer-error" in html


def test_render_crossword_answer_shows_code_solution_only_in_solution_mode():
    options = {"maxw": 15, "maxh": 15, "code": "HERR"}
    worksheet_html = render_crossword_answer(options, _CONTENT, include_solutions=False)
    solution_html = render_crossword_answer(options, _CONTENT, include_solutions=True)

    assert "crossword-code" not in worksheet_html
    assert "crossword-code" in solution_html
    assert "cw-cell-code" in solution_html


def test_render_crossword_answer_position_option_controls_wrapper_class():
    options_right = {"maxw": 15, "maxh": 15, "position": "right"}
    html_right = render_crossword_answer(options_right, _CONTENT, include_solutions=True)
    assert "wordbank-position-right" in html_right

    options_below = {"maxw": 15, "maxh": 15, "position": "below"}
    html_below = render_crossword_answer(options_below, _CONTENT, include_solutions=True)
    assert "wordbank-position-below" in html_below


def test_render_crossword_answer_rendering_reuses_a_cached_layout_without_recomputing(monkeypatch):
    calls = []
    original = crossword_module.build_crossword_layout

    def counting(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(crossword_module, "build_crossword_layout", counting)

    cache = BlockComputationCache()
    options = {"maxw": 15, "maxh": 15, "_computation_cache": cache}

    render_crossword_answer(options, _CONTENT, include_solutions=False)
    assert len(calls) == 1

    # Rendering the SAME content again (e.g. solution mode) with the same
    # cache instance must hit the cache, not recompute the placement --
    # this is the "validate once, render twice" scenario Slice 1 exists for.
    render_crossword_answer(options, _CONTENT, include_solutions=True)
    assert len(calls) == 1


def test_estimate_crossword_weight_returns_zero_for_no_entries():
    assert estimate_crossword_weight({}, "") == 0.0


def test_estimate_crossword_weight_is_positive_and_bounded_for_real_content():
    weight = estimate_crossword_weight({"maxw": 15, "maxh": 15}, _CONTENT)
    assert 0.0 < weight <= 7.8


def test_render_crossword_answer_scale_option_sets_cw_cell_size():
    html = render_crossword_answer({"maxw": 15, "maxh": 15, "scale": "1.2cm"}, _CONTENT, include_solutions=True)
    assert "--cw-cell-size:1.2cm" in html


def test_render_crossword_answer_without_scale_keeps_default_cell_size():
    # Regression: the new `scale=` option must not change anything for
    # documents that don't set it.
    html = render_crossword_answer({"maxw": 15, "maxh": 15}, _CONTENT, include_solutions=True)
    assert "--cw-cell-size:0.72cm" in html


def test_render_crossword_answer_invalid_scale_falls_back_to_crossword_default():
    # Must fall back to crossword's own 0.72cm default, not
    # answer_grid_plot.py's unrelated 0.5cm default for other blocks.
    html = render_crossword_answer({"maxw": 15, "maxh": 15, "scale": "banana"}, _CONTENT, include_solutions=True)
    assert "--cw-cell-size:0.72cm" in html


def test_estimate_crossword_weight_ignores_scale_with_explicit_bounds():
    # estimate_crossword_weight is based on maxw*maxh; with maxw/maxh
    # given explicitly, cell_size_cm never enters that computation.
    without_scale = estimate_crossword_weight({"maxw": 10, "maxh": 10}, _CONTENT)
    with_scale = estimate_crossword_weight({"maxw": 10, "maxh": 10, "scale": "2cm"}, _CONTENT)
    assert without_scale == with_scale


def test_estimate_crossword_weight_ignores_scale_without_explicit_bounds():
    # estimate_crossword_weight is only ever called (via auto_columns_template)
    # with raw author options, before _printable_width_cm/_printable_height_cm
    # get injected -- so even without explicit maxw/maxh, resolve_crossword_bounds
    # always falls back to the fixed _DEFAULT_CROSSWORD_MAXW/MAXH here,
    # independent of cell_size_cm. Pinning this so a future change to that
    # call chain is noticed rather than silently assumed.
    without_scale = estimate_crossword_weight({}, _CONTENT)
    with_scale = estimate_crossword_weight({"scale": "2cm"}, _CONTENT)
    assert without_scale == with_scale
