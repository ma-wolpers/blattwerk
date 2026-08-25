from app.core.blatt_kern_answer_choice import _normalize_word_position, _render_cloze_answer
from app.core.blatt_kern_shared import _new_markdown_converter

_CONTENT = "Die {{Katze}} miaut, der {{Hund}} bellt."


def _render(options, include_solutions=False):
    md = _new_markdown_converter()
    return _render_cloze_answer(md, options, _CONTENT, include_solutions)


def test_normalize_word_position_defaults_to_none():
    assert _normalize_word_position(None) == "none"
    assert _normalize_word_position("") == "none"


def test_normalize_word_position_accepts_above_below_synonyms():
    assert _normalize_word_position("oben") == "above"
    assert _normalize_word_position("unten") == "below"


def test_normalize_word_position_accepts_left_right_new_values():
    assert _normalize_word_position("left") == "left"
    assert _normalize_word_position("links") == "left"
    assert _normalize_word_position("right") == "right"
    assert _normalize_word_position("rechts") == "right"


def test_normalize_word_position_auto_falls_back_to_below():
    assert _normalize_word_position("auto") == "below"


def test_render_cloze_answer_none_position_has_no_wordbank():
    html = _render({"words": "none"})
    assert "cloze-wordbank" not in html


def test_render_cloze_answer_default_has_no_wordbank():
    html = _render({})
    assert "cloze-wordbank" not in html


def test_render_cloze_answer_below_position_shows_wordbank_after_text():
    html = _render({"words": "below"})
    assert "cloze-wordbank" in html
    assert "wordbank-position-below" in html
    assert html.index("cloze-gap") < html.index("cloze-wordbank")


def test_render_cloze_answer_above_position_shows_wordbank_class():
    html = _render({"words": "above"})
    assert "wordbank-position-above" in html
    # DOM order is always main-content-then-bank (see wordbank_position.py);
    # "above" is achieved via CSS flex-direction, not DOM reordering.
    assert html.index("cloze-gap") < html.index("cloze-wordbank")


def test_render_cloze_answer_left_and_right_positions_are_new_capabilities():
    html_left = _render({"words": "left"})
    assert "wordbank-position-left" in html_left

    html_right = _render({"words": "rechts"})
    assert "wordbank-position-right" in html_right


def test_render_cloze_answer_solution_mode_never_shows_wordbank():
    html = _render({"words": "below"}, include_solutions=True)
    assert "cloze-wordbank" not in html
