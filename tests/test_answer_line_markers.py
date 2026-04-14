from app.core.answer_line_markers import (
    collect_answer_marker_conflict_lines,
    filter_answer_content_for_mode,
    is_effectively_empty_answer_content,
)


def test_filter_marker_visibility_for_modes():
    content = "§{Nur AB}\n%{Nur Loesung}\n&{Beides}"

    worksheet = filter_answer_content_for_mode(content, include_solutions=False)
    solution = filter_answer_content_for_mode(content, include_solutions=True)

    assert worksheet == "Nur AB\nBeides"
    assert solution == "Nur Loesung\nBeides"


def test_filter_legacy_line_markers_for_modes():
    content = "§ Nur AB\nNur Loesung %\n& Beides"

    worksheet = filter_answer_content_for_mode(content, include_solutions=False)
    solution = filter_answer_content_for_mode(content, include_solutions=True)

    assert worksheet == "Nur AB\nBeides"
    assert solution == "Nur Loesung\nBeides"


def test_math_dollar_is_not_a_marker_without_token_spacing():
    content = "$x^2 + 1$"

    worksheet = filter_answer_content_for_mode(content, include_solutions=False)
    solution = filter_answer_content_for_mode(content, include_solutions=True)

    assert worksheet == "$x^2 + 1$"
    assert solution == "$x^2 + 1$"


def test_invalid_unclosed_inline_marker_is_reported():
    content = "%{Startsatz\nNormale Zeile"
    conflicts = collect_answer_marker_conflict_lines(content)
    assert conflicts == [1]


def test_effective_empty_detects_marker_only_lines():
    content = "§{}\n   &{}   \n%{}"
    assert is_effectively_empty_answer_content(content)


def test_escaped_space_placeholders_are_kept_visible_in_filtered_text():
    content = "(\\ \\ \\ \\ )"

    worksheet = filter_answer_content_for_mode(content, include_solutions=False)
    solution = filter_answer_content_for_mode(content, include_solutions=True)

    assert worksheet == "(    )"
    assert solution == "(    )"
    assert not is_effectively_empty_answer_content(content)
