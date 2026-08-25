import app.core.answer_special_crossword as crossword_module
from app.core.answer_special_crossword import estimate_crossword_weight, render_crossword_answer
from app.core.block_computation_cache import BlockComputationCache

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


def test_render_crossword_answer_grid_cell_count_matches_maxw_times_maxh():
    html = render_crossword_answer({"maxw": 10, "maxh": 8}, _CONTENT, include_solutions=True)
    spans = _cell_spans(html)
    assert len(spans) == 10 * 8


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
