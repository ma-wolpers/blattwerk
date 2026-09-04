"""Tests für die reine Editor-Marker-Logik (kein Tkinter nötig)."""

from app.ui.editor_marker_shortcuts import (
    apply_backtick_marker,
    apply_caret_marker,
    apply_highlight_marker,
    apply_pipe_marker,
    apply_star_marker,
    apply_tilde_marker,
    apply_underscore_marker,
    selection_crosses_math_boundary,
)


def _apply(edit, before, selected, after):
    left = before[: len(before) - edit.strip_left] if edit.strip_left else before
    right = after[edit.strip_right :] if edit.strip_right else after
    return left + edit.replacement + right


class TestStarMarker:
    def test_fresh_selection_becomes_italic(self):
        edit = apply_star_marker("", "text", "")
        assert edit.replacement == "*text*"
        assert _apply(edit, "", "text", "") == "*text*"

    def test_italic_escalates_to_bold(self):
        edit = apply_star_marker("*", "text", "*")
        assert edit.replacement == "**text**"
        assert _apply(edit, "*", "text", "*") == "**text**"

    def test_bold_escalates_to_bold_italic(self):
        edit = apply_star_marker("**", "text", "**")
        assert edit.replacement == "***text***"

    def test_bold_italic_removes_everything(self):
        edit = apply_star_marker("***", "text", "***")
        assert edit.replacement == "text"
        assert edit.strip_left == 3
        assert edit.strip_right == 3

    def test_asymmetric_run_is_not_guessed(self):
        # Only one star on the right -> level = min(2, 1) = 1, not 2.
        edit = apply_star_marker("**", "text", "*")
        assert edit.strip_left == 1
        assert edit.strip_right == 1
        assert edit.replacement == "**text**"


class TestUnderscoreMarker:
    def test_fresh_selection_becomes_italic(self):
        edit = apply_underscore_marker("", "text", "")
        assert edit.replacement == "_text_"

    def test_italic_escalates_to_underline_not_bold(self):
        edit = apply_underscore_marker("_", "text", "_")
        assert edit.replacement == "__text__"

    def test_underline_removes_everything(self):
        edit = apply_underscore_marker("__", "text", "__")
        assert edit.replacement == "text"
        assert edit.strip_left == 2
        assert edit.strip_right == 2


class TestHighlightMarker:
    def test_first_press_inserts_double_equals_directly(self):
        edit = apply_highlight_marker("", "text", "")
        assert edit.replacement == "==text=="

    def test_second_press_toggles_off(self):
        edit = apply_highlight_marker("==", "text", "==")
        assert edit.replacement == "text"


class TestPipeMarker:
    def test_first_press_inserts_double_pipe_directly(self):
        edit = apply_pipe_marker("", "text", "")
        assert edit.replacement == "||text||"

    def test_second_press_toggles_off(self):
        edit = apply_pipe_marker("||", "text", "||")
        assert edit.replacement == "text"


class TestTildeMarker:
    def test_single_char_fresh_uses_bare_prefix(self):
        edit = apply_tilde_marker("", "2", "")
        assert edit.replacement == "~2"

    def test_multi_char_fresh_uses_braces(self):
        edit = apply_tilde_marker("", "abc", "")
        assert edit.replacement == "~{abc}"

    def test_bare_prefix_escalates_to_strikethrough(self):
        edit = apply_tilde_marker("~", "2", "")
        assert edit.replacement == "~~2~~"
        assert edit.strip_left == 1
        assert edit.strip_right == 0

    def test_braced_prefix_escalates_to_strikethrough(self):
        edit = apply_tilde_marker("~{", "abc", "}")
        assert edit.replacement == "~~abc~~"
        assert edit.strip_left == 2
        assert edit.strip_right == 1

    def test_strikethrough_removes_everything(self):
        edit = apply_tilde_marker("~~", "text", "~~")
        assert edit.replacement == "text"
        assert edit.strip_left == 2
        assert edit.strip_right == 2


class TestCaretMarker:
    def test_single_char_fresh_uses_bare_prefix(self):
        edit = apply_caret_marker("", "2", "")
        assert edit.replacement == "^2"

    def test_multi_char_fresh_uses_braces(self):
        edit = apply_caret_marker("", "abc", "")
        assert edit.replacement == "^{abc}"

    def test_pressing_again_removes_bare_prefix(self):
        edit = apply_caret_marker("^", "2", "")
        assert edit.replacement == "2"
        assert edit.strip_left == 1

    def test_pressing_again_removes_braced_prefix(self):
        edit = apply_caret_marker("^{", "abc", "}")
        assert edit.replacement == "abc"
        assert edit.strip_left == 2
        assert edit.strip_right == 1


class TestMathBoundary:
    def test_selection_fully_outside_math_is_allowed(self):
        text = "vor $x^2$ nach"
        assert selection_crosses_math_boundary(text, 0, 3) is False

    def test_selection_fully_inside_math_is_allowed(self):
        text = "vor $x^2$ nach"
        # indices 5..8 are inside the "x^2" interior of the $...$ span
        assert selection_crosses_math_boundary(text, 5, 8) is False

    def test_selection_straddling_math_start_is_refused(self):
        text = "vor $x^2$ nach"
        assert selection_crosses_math_boundary(text, 3, 6) is True

    def test_selection_straddling_math_end_is_refused(self):
        text = "vor $x^2$ nach"
        assert selection_crosses_math_boundary(text, 6, 11) is True


class TestBacktickMarker:
    def test_single_line_fresh_wraps_inline_code(self):
        edit = apply_backtick_marker("", "code", "", is_multiline=False)
        assert edit.replacement == "`code`"

    def test_single_line_wrapped_toggles_off(self):
        edit = apply_backtick_marker("`", "code", "`", is_multiline=False)
        assert edit.replacement == "code"
        assert edit.strip_left == 1
        assert edit.strip_right == 1

    def test_multiline_inserts_fenced_block(self):
        edit = apply_backtick_marker("", "line1\nline2", "", is_multiline=True)
        assert edit.replacement == "```\nline1\nline2\n```"
