from app.core.answer_line_markers import (
    collect_answer_marker_conflict_lines,
    filter_answer_content_for_mode,
    is_effectively_empty_answer_content,
    parse_answer_line_visibility,
)


def test_filter_marker_visibility_for_modes():
    content = "§{Nur AB}\n%{Nur Loesung}\n&{Beides}"

    worksheet = filter_answer_content_for_mode(content, include_solutions=False)
    solution = filter_answer_content_for_mode(content, include_solutions=True)

    assert worksheet == "Nur AB\nBeides"
    assert solution == "Nur Loesung\nBeides"


def test_filter_legacy_line_markers_for_modes():
    content = "§ Nur AB\n% Nur Loesung\n& Beides"

    worksheet = filter_answer_content_for_mode(content, include_solutions=False)
    solution = filter_answer_content_for_mode(content, include_solutions=True)

    assert worksheet == "Nur AB\nBeides"
    assert solution == "Nur Loesung\nBeides"


def test_trailing_percent_stays_plain_text():
    content = "43 % Rabatt"

    worksheet = filter_answer_content_for_mode(content, include_solutions=False)
    solution = filter_answer_content_for_mode(content, include_solutions=True)

    assert worksheet == "43 % Rabatt"
    assert solution == "43 % Rabatt"


def test_inline_marker_in_line_middle_stays_supported():
    content = "zum %{Beispiel} so"

    worksheet = filter_answer_content_for_mode(content, include_solutions=False)
    solution = filter_answer_content_for_mode(content, include_solutions=True)

    assert worksheet == "zum  so"
    assert solution == "zum Beispiel so"


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


def test_backslash_commands_inside_formula_survive_marker_parsing():
    # Regression for the bug where `parse_answer_line_visibility`'s own
    # `\`-escape handling (meant for `\ `/marker braces) blindly ate every
    # backslash in the line, silently corrupting LaTeX commands like
    # `\frac`/`\mid` inside a `$...$` formula.
    raw_line = r"Text $\frac{a}{b} = \mid c \mid$ Ende"
    parsed = parse_answer_line_visibility(raw_line)

    assert parsed["text"] == raw_line
    assert [segment["text"] for segment in parsed["segments"]] == [raw_line]


def test_backslash_commands_inside_formula_survive_inside_solution_marker():
    raw_line = r"%{Antwort: $\frac{1}{2}$}"
    parsed = parse_answer_line_visibility(raw_line)

    assert len(parsed["segments"]) == 1
    assert parsed["segments"][0]["text"] == r"Antwort: $\frac{1}{2}$"
    assert parsed["segments"][0]["show"] == "solution"


def test_formula_fully_outside_marker_stays_untouched_by_marker_parsing():
    raw_line = r"$\alpha + \beta$ und %{nur Loesung}"
    parsed = parse_answer_line_visibility(raw_line)

    texts = [segment["text"] for segment in parsed["segments"]]
    assert texts[0] == r"$\alpha + \beta$ und "
    assert texts[1] == "nur Loesung"
    assert not parsed["has_conflict"]


def test_math_span_detection_wins_when_it_overlaps_a_marker_boundary():
    # Documents a deliberate priority, not just an accident: `protect_math_spans`
    # runs on the whole raw line before the marker loop knows anything about
    # `%{`/`}` boundaries. If a `$...$` candidate span happens to swallow what
    # would otherwise be a marker's closing `}`, the formula wins -- the `}`
    # becomes part of the protected placeholder, not a marker terminator, so
    # the marker is left unclosed (has_conflict=True). This pins today's
    # actual behavior for this inherently ambiguous overlap, rather than
    # leaving it to be discovered by surprise later.
    raw_line = r"%{$a} b$"
    parsed = parse_answer_line_visibility(raw_line)

    assert parsed["has_conflict"] is True
