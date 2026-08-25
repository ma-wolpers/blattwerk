from app.core.answer_special_wordsearch import render_wordsearch_answer

_CONTENT = "- HAUS\n- BAUM\n- ZUG\n"


def test_wordsearch_default_position_is_below_preserving_prior_behavior():
    html = render_wordsearch_answer({}, _CONTENT, include_solutions=False)
    assert "wordbank-position-below" in html
    assert "wordsearch-grid" in html
    assert "wordsearch-words" in html


def test_wordsearch_position_right_produces_right_wrapper_class():
    html = render_wordsearch_answer({"position": "right"}, _CONTENT, include_solutions=False)
    assert "wordbank-position-right" in html


def test_wordsearch_position_left_produces_left_wrapper_class():
    html = render_wordsearch_answer({"position": "links"}, _CONTENT, include_solutions=False)
    assert "wordbank-position-left" in html


def test_wordsearch_position_above_produces_above_wrapper_class():
    html = render_wordsearch_answer({"position": "above"}, _CONTENT, include_solutions=False)
    assert "wordbank-position-above" in html


def test_wordsearch_position_auto_resolves_to_a_concrete_position():
    html = render_wordsearch_answer(
        {"position": "auto", "_printable_width_cm": 18.0}, _CONTENT, include_solutions=False
    )
    assert "wordbank-position-right" in html or "wordbank-position-below" in html
    assert "wordbank-position-auto" not in html


def test_wordsearch_grid_and_words_are_both_present_regardless_of_position():
    for position in ("below", "above", "left", "right"):
        html = render_wordsearch_answer({"position": position}, _CONTENT, include_solutions=False)
        assert "wordsearch-grid" in html
        assert "<li" in html  # word list items still rendered
