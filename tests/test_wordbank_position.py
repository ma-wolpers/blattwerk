import pytest

from app.core.wordbank_position import (
    normalize_wordbank_position,
    resolve_wordbank_auto_position,
    wrap_with_wordbank_position,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("above", "above"),
        ("top", "above"),
        ("oben", "above"),
        ("ueber", "above"),
        ("über", "above"),
        ("below", "below"),
        ("bottom", "below"),
        ("under", "below"),
        ("unten", "below"),
        ("unter", "below"),
        ("left", "left"),
        ("links", "left"),
        ("right", "right"),
        ("rechts", "right"),
        ("auto", "auto"),
        ("AUTO", "auto"),
        ("  Right  ", "right"),
    ],
)
def test_normalize_wordbank_position_accepts_all_synonyms(value, expected):
    assert normalize_wordbank_position(value) == expected


def test_normalize_wordbank_position_falls_back_to_default_for_unknown_value():
    assert normalize_wordbank_position("diagonal") == "below"
    assert normalize_wordbank_position("diagonal", default="above") == "above"
    assert normalize_wordbank_position(None) == "below"
    assert normalize_wordbank_position("") == "below"


def test_resolve_wordbank_auto_position_prefers_right_when_space_remains():
    assert resolve_wordbank_auto_position(10.0, 18.0, min_side_width_cm=4.0) == "right"


def test_resolve_wordbank_auto_position_falls_back_to_below_when_tight():
    assert resolve_wordbank_auto_position(16.0, 18.0, min_side_width_cm=4.0) == "below"


def test_resolve_wordbank_auto_position_boundary_is_inclusive():
    assert resolve_wordbank_auto_position(14.0, 18.0, min_side_width_cm=4.0) == "right"


def test_wrap_with_wordbank_position_wraps_with_position_class():
    html = wrap_with_wordbank_position("<div>main</div>", "<ul>bank</ul>", "right")
    assert "wordbank-layout" in html
    assert "wordbank-position-right" in html
    # DOM order is always main then bank, regardless of visual position.
    assert html.index("<div>main</div>") < html.index("<ul>bank</ul>")


@pytest.mark.parametrize("position", ["above", "below", "left", "right"])
def test_wrap_with_wordbank_position_all_positions_produce_correct_class(position):
    html = wrap_with_wordbank_position("<div>main</div>", "<ul>bank</ul>", position)
    assert f"wordbank-position-{position}" in html


def test_wrap_with_wordbank_position_unknown_position_falls_back_to_below():
    html = wrap_with_wordbank_position("<div>main</div>", "<ul>bank</ul>", "diagonal")
    assert "wordbank-position-below" in html


def test_wrap_with_wordbank_position_returns_main_only_when_bank_empty():
    assert wrap_with_wordbank_position("<div>main</div>", "", "right") == "<div>main</div>"
    assert wrap_with_wordbank_position("<div>main</div>", None, "right") == "<div>main</div>"


def test_wrap_with_wordbank_position_returns_bank_only_when_main_empty():
    assert wrap_with_wordbank_position("", "<ul>bank</ul>", "right") == "<ul>bank</ul>"


def test_wrap_with_wordbank_position_supports_extra_classes():
    html = wrap_with_wordbank_position("<div>main</div>", "<ul>bank</ul>", "right", extra_classes=["crossword-layout"])
    assert "crossword-layout" in html
