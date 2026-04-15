from app.core.blatt_kern_answer_table import _render_answer_block


def test_lines_answer_shows_worksheet_marker_text_only_in_worksheet_mode():
    options = {"type": "lines", "rows": "2"}
    content = "§{Starthilfe}"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "Starthilfe" in worksheet_html
    assert solution_html == ""


def test_lines_answer_legacy_marker_stays_supported():
    options = {"type": "lines", "rows": "2"}
    content = "Starthilfe %"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "Starthilfe" not in worksheet_html
    assert "Starthilfe" in solution_html


def test_lines_answer_keeps_unmarked_text_solution_only():
    options = {"type": "lines", "rows": "2"}
    content = "Lsg-Impuls"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "Lsg-Impuls" in worksheet_html
    assert "Lsg-Impuls" in solution_html


def test_dots_answer_can_show_both_marker_text_in_worksheet():
    options = {"type": "dots", "height": "3cm"}
    content = "&{Leitfrage}"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "Leitfrage" in worksheet_html
    assert "Leitfrage" in solution_html


def test_lines_answer_worksheet_rows_use_max_of_rows_and_visible_lines():
    options = {"type": "lines", "rows": "2"}
    content = "&{Impuls 1}\n§{Impuls 2}\n%{Nur Loesung}"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)

    assert worksheet_html.count("<div class='line'></div>") == 2


def test_lines_answer_worksheet_uses_visible_lines_when_greater_than_rows():
    options = {"type": "lines", "rows": "1"}
    content = "&{Impuls 1}\n§{Impuls 2}\n&{Impuls 3}"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)

    assert worksheet_html.count("<div class='line'></div>") == 3


def test_lines_answer_solution_uses_visible_solution_line_count():
    options = {"type": "lines", "rows": "2"}
    content = "&{Impuls 1}\n%{Loesung 2}\n§{Nur AB}"

    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert solution_html.count("<div class='line'></div>") == 2


def test_lines_answer_solution_does_not_add_lines_for_wrapped_long_text():
    options = {"type": "lines", "rows": "1"}
    content = "% " + ("Sehr langer Loesungssatz " * 8).strip()

    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert solution_html.count("<div class='line'></div>") == 1


def test_lines_answer_creates_row_markup_per_visible_line():
    options = {"type": "lines", "rows": "1"}
    content = "A\nB\n%{C}"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert worksheet_html.count("<div class='answer-line-row'>") == 2
    assert solution_html.count("<div class='answer-line-row'>") == 3


def test_lines_answer_renders_inline_markdown_bold():
    options = {"type": "lines", "rows": "1"}
    content = "EVA steht fuer **E**ingabe"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "<strong>E</strong>" in worksheet_html
    assert "<strong>E</strong>" in solution_html


def test_lines_answer_preserves_escaped_spaces_as_visible_placeholders():
    options = {"type": "lines", "rows": "1"}
    content = "(\\ \\ \\ \\ )"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "(&nbsp;&nbsp;&nbsp;&nbsp;)" in worksheet_html
    assert "(&nbsp;&nbsp;&nbsp;&nbsp;)" in solution_html


def test_lines_height_option_sets_css_variable_on_wrapper():
    options = {"type": "lines", "rows": "2", "height": "2.1em"}
    content = "A"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)

    assert "--answer-line-pitch:2.1em" in worksheet_html


def test_lines_height_option_invalid_value_falls_back_to_default_pitch():
    options = {"type": "lines", "rows": "2", "height": "auto"}
    content = "A"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)

    assert "--answer-line-pitch:" not in worksheet_html


def test_lines_answer_solution_list_uses_valid_block_wrapper():
    options = {"type": "lines", "rows": "2"}
    content = "% - Punkt eins"

    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "<span class='table-solution-marker'><ul>" not in solution_html
    assert "<div class='table-solution-marker'><ul>" in solution_html


def test_table_cells_use_inline_visibility_tokens():
    options = {"type": "table", "rows": "1", "cols": "2"}
    content = (
        "cells:\n"
        "  - [\"§{Nur AB} %{Nur Loesung} Beides\", \"Text mit Escape \\\\%\\\\{ bleibt\"]"
    )

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "Nur AB" in worksheet_html
    assert "Nur Loesung" not in worksheet_html
    assert "Nur AB" not in solution_html
    assert "Nur Loesung" in solution_html
    assert "Text mit Escape %{ bleibt" in worksheet_html


def test_grid_yaml_uses_marker_visibility_symbols():
    options = {"type": "grid", "rows": "6", "cols": "6"}
    content = (
        "points:\n"
        "  - {col: 1, row: 1, label: 'W', show: '§'}\n"
        "  - {col: 2, row: 2, label: 'S', show: '%'}\n"
        "  - {col: 3, row: 3, label: 'B', show: '&'}\n"
    )

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "W" in worksheet_html
    assert "S" not in worksheet_html
    assert "B" in worksheet_html

    assert "W" not in solution_html
    assert "S" in solution_html
    assert "B" in solution_html


def test_grid_yaml_legacy_word_show_values_are_not_rendered():
    options = {"type": "grid", "rows": "4", "cols": "4"}
    content = "points:\n  - {col: 1, row: 1, label: 'ALT', show: 'both'}\n"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "ALT" not in worksheet_html
    assert "ALT" not in solution_html


def test_numberline_yaml_uses_marker_visibility_symbols():
    options = {"type": "numberline", "min": "-3", "max": "3"}
    content = (
        "labels:\n"
        "  - {value: -2, text: 'W', show: '§'}\n"
        "  - {value: 0, text: 'S', show: '%'}\n"
        "  - {value: 2, text: 'B', show: '&'}\n"
    )

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "W" in worksheet_html
    assert "S" not in worksheet_html
    assert "B" in worksheet_html

    assert "W" not in solution_html
    assert "S" in solution_html
    assert "B" in solution_html


def test_numberline_yaml_legacy_word_show_values_are_not_rendered():
    options = {"type": "numberline", "min": "-3", "max": "3"}
    content = "labels:\n  - {value: -1, text: 'ALT', show: 'both'}\n"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "ALT" not in worksheet_html
    assert "ALT" not in solution_html


def test_grid_fallback_solution_text_is_only_rendered_in_solution_mode():
    options = {"type": "grid", "rows": "4", "cols": "4"}
    content = "solution_text: 'Nur Loesungstext'\n"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "Nur Loesungstext" not in worksheet_html
    assert "Nur Loesungstext" in solution_html


def test_grid_plain_marker_text_renders_in_worksheet_mode():
    options = {"type": "grid", "rows": "4", "cols": "4"}
    content = "§ Starthilfe\n% Nur Loesung\n"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "Starthilfe" in worksheet_html
    assert "Nur Loesung" not in worksheet_html
    assert "Starthilfe" not in solution_html
    assert "Nur Loesung" in solution_html


def test_grid_plain_unmarked_text_renders_in_both_modes():
    options = {"type": "grid", "rows": "4", "cols": "4"}
    content = "Leitfrage"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "Leitfrage" in worksheet_html
    assert "Leitfrage" in solution_html


def test_numberline_fallback_solution_key_is_only_rendered_in_solution_mode():
    options = {"type": "numberline", "min": "0", "max": "5"}
    content = "solution: 'Skizze mit Begruendung'\n"

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "Skizze mit Begruendung" not in worksheet_html
    assert "Skizze mit Begruendung" in solution_html


def test_cloze_wordbank_shows_duplicate_words_by_default():
    options = {"type": "cloze", "words": "below"}
    content = "Die {{CPU}} arbeitet mit der {{CPU}}."

    worksheet_html = _render_answer_block(options, content, include_solutions=False)

    assert worksheet_html.count("<span class='cloze-word'>CPU</span>") == 2


def test_cloze_wordbank_can_hide_duplicate_words():
    options = {"type": "cloze", "words": "below", "words_multi": "false"}
    content = "Die {{CPU}} arbeitet mit der {{CPU}}."

    worksheet_html = _render_answer_block(options, content, include_solutions=False)

    assert worksheet_html.count("<span class='cloze-word'>CPU</span>") == 1


def test_table_alignment_center_sets_css_variable_on_wrapper():
    options = {"type": "table", "rows": "1", "cols": "2", "alignment": "center"}
    content = "cells:\n  - ['A', 'B']"

    html = _render_answer_block(options, content, include_solutions=False)

    assert "--table-text-align:center" in html


def test_table_alignment_invalid_value_falls_back_to_left():
    options = {"type": "table", "rows": "1", "cols": "2", "alignment": "diagonal"}
    content = "cells:\n  - ['A', 'B']"

    html = _render_answer_block(options, content, include_solutions=False)

    assert "--table-text-align:left" in html


def test_table_alignment_per_column_shorthand_is_applied():
    options = {
        "type": "table",
        "rows": "1",
        "cols": "4",
        "alignment": "l r c c",
        "headers": "A|B|C|D",
    }
    content = "cells:\n  - ['1', '2', '3', '4']"

    html = _render_answer_block(options, content, include_solutions=False)

    assert "<th style='text-align:left'>A</th>" in html
    assert "<th style='text-align:right'>B</th>" in html
    assert "<th style='text-align:center'>C</th>" in html
    assert "<th style='text-align:center'>D</th>" in html
    assert "<td style='text-align:left'>1</td>" in html
    assert "<td style='text-align:right'>2</td>" in html
    assert "<td style='text-align:center'>3</td>" in html
    assert "<td style='text-align:center'>4</td>" in html


def test_table_alignment_per_column_uses_long_aliases_too():
    options = {
        "type": "table",
        "rows": "1",
        "cols": "3",
        "alignment": "links rechts mitte",
    }
    content = "cells:\n  - ['A', 'B', 'C']"

    html = _render_answer_block(options, content, include_solutions=False)

    assert "<td style='text-align:left'>A</td>" in html
    assert "<td style='text-align:right'>B</td>" in html
    assert "<td style='text-align:center'>C</td>" in html


def test_table_header_columns_render_body_cells_as_row_headers():
    options = {
        "type": "table",
        "rows": "2",
        "cols": "3",
        "headers": "A|B|C",
        "header_columns": "1",
    }
    content = "cells:\n  - ['R1', '10', '20']\n  - ['R2', '30', '40']"

    html = _render_answer_block(options, content, include_solutions=False)

    assert "<th scope='row'>R1</th>" in html
    assert "<th scope='row'>R2</th>" in html
    assert "<td>10</td>" in html


def test_table_header_cols_alias_is_supported():
    options = {"type": "table", "rows": "1", "cols": "2", "header_cols": "1"}
    content = "cells:\n  - ['Name', 'Wert']"

    html = _render_answer_block(options, content, include_solutions=False)

    assert "<th scope='row'>Name</th>" in html
    assert "<td>Wert</td>" in html
