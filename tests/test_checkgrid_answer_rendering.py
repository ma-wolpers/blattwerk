import re

from app.core.answer_special_checkgrid import (
    estimate_checkgrid_weight,
    parse_checkgrid_payload,
    render_checkgrid_answer,
)

_CONTENT = """
columns:
  - richtig
  - falsch
rows:
  - text: Die Erde ist eine Scheibe.
    correct: 2
  - text: Wasser besteht aus H2O.
    correct: 1
"""


def test_parse_checkgrid_payload_reads_columns_and_rows():
    columns, rows = parse_checkgrid_payload(_CONTENT)
    assert columns == ["richtig", "falsch"]
    assert rows == [
        ("Die Erde ist eine Scheibe.", 2),
        ("Wasser besteht aus H2O.", 1),
    ]


def test_parse_checkgrid_payload_accepts_german_key_aliases():
    content = "spalten:\n  - A\nzeilen:\n  - {text: X, richtig: 1}\n"
    columns, rows = parse_checkgrid_payload(content)
    assert columns == ["A"]
    assert rows == [("X", 1)]


def test_parse_checkgrid_payload_handles_missing_correct_gracefully():
    content = "columns:\n  - A\n  - B\nrows:\n  - text: Ungewertet\n"
    columns, rows = parse_checkgrid_payload(content)
    assert columns == ["A", "B"]
    assert rows == [("Ungewertet", None)]


def test_parse_checkgrid_payload_empty_for_missing_columns():
    assert parse_checkgrid_payload("rows:\n  - text: X\n    correct: 1\n") == ([], [])


def test_render_checkgrid_answer_empty_content_returns_empty_string():
    assert render_checkgrid_answer({}, "", include_solutions=False) == ""


def test_render_checkgrid_answer_worksheet_mode_has_no_checked_boxes():
    html = render_checkgrid_answer({}, _CONTENT, include_solutions=False)
    assert "☑" not in html
    assert html.count("☐") == 4  # 2 rows x 2 columns


def test_render_checkgrid_answer_solution_mode_marks_correct_column_per_row():
    html = render_checkgrid_answer({}, _CONTENT, include_solutions=True)
    rows = re.findall(r"<tr>(.*?)</tr>", html)[1:]  # skip header
    assert len(rows) == 2

    # Row 1: "Die Erde ist eine Scheibe." -> correct column 2 (falsch).
    row1_cells = re.findall(r"<td[^>]*>(.*?)</td>", rows[0])
    assert row1_cells[1] == "☐"
    assert row1_cells[2] == "☑"

    # Row 2: "Wasser besteht aus H2O." -> correct column 1 (richtig).
    row2_cells = re.findall(r"<td[^>]*>(.*?)</td>", rows[1])
    assert row2_cells[1] == "☑"
    assert row2_cells[2] == "☐"


def test_render_checkgrid_answer_column_headers_appear_once_not_per_row():
    html = render_checkgrid_answer({}, _CONTENT, include_solutions=True)
    assert html.count("checkgrid-column") == 2  # once each for "richtig"/"falsch"


def test_render_checkgrid_answer_statement_text_is_markdown_rendered():
    content = "columns:\n  - A\nrows:\n  - text: '**Wichtig**'\n    correct: 1\n"
    html = render_checkgrid_answer({}, content, include_solutions=False)
    assert "<strong>Wichtig</strong>" in html


def test_estimate_checkgrid_weight_zero_for_no_content():
    assert estimate_checkgrid_weight({}, "") == 0.0


def test_estimate_checkgrid_weight_positive_for_real_content():
    weight = estimate_checkgrid_weight({}, _CONTENT)
    assert 0.0 < weight <= 7.0
