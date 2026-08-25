import re

from app.core.answer_special_categorize import (
    estimate_categorize_weight,
    parse_categorize_payload,
    render_categorize_answer,
)

_CONTENT = """
categories:
  - Tiere
  - Pflanzen
items:
  - word: Hund
    category: 1
  - word: Katze
    category: 1
  - word: Rose
    category: 2
  - word: Tulpe
    category: 2
  - word: Baum
    category: 2
"""


def test_parse_categorize_payload_reads_categories_and_items():
    categories, items = parse_categorize_payload(_CONTENT)
    assert categories == ["Tiere", "Pflanzen"]
    assert ("Hund", 1) in items
    assert ("Baum", 2) in items
    assert len(items) == 5


def test_parse_categorize_payload_accepts_german_key_aliases():
    content = "kategorien:\n  - A\nbegriffe:\n  - {wort: X, kategorie: 1}\n"
    categories, items = parse_categorize_payload(content)
    assert categories == ["A"]
    assert items == [("X", 1)]


def test_parse_categorize_payload_empty_for_missing_categories():
    assert parse_categorize_payload("items:\n  - word: X\n    category: 1\n") == ([], [])


def test_parse_categorize_payload_drops_out_of_range_category_index():
    content = "categories:\n  - A\nitems:\n  - word: X\n    category: 5\n"
    categories, items = parse_categorize_payload(content)
    assert categories == ["A"]
    assert items == []


def test_render_categorize_answer_empty_content_returns_empty_string():
    assert render_categorize_answer({}, "", include_solutions=False) == ""


def test_render_categorize_answer_worksheet_mode_has_empty_table_and_wordbank():
    html = render_categorize_answer({}, _CONTENT, include_solutions=False)
    assert "categorize-table" in html
    assert "categorize-wordbank" in html
    assert "Hund" not in re.sub(r"categorize-word'>Hund<", "", html) or "categorize-word'>Hund<" in html
    # Table cells must all be empty in worksheet mode.
    for cell in re.findall(r"<td>(.*?)</td>", html):
        assert cell == ""


def test_render_categorize_answer_solution_mode_places_words_in_correct_columns():
    html = render_categorize_answer({}, _CONTENT, include_solutions=True)
    assert "categorize-wordbank" not in html

    rows = re.findall(r"<tr>(.*?)</tr>", html)
    body_rows = rows[1:]  # skip header row
    animals = set()
    plants = set()
    for row in body_rows:
        cells = re.findall(r"<td>(.*?)</td>", row)
        assert len(cells) == 2
        if cells[0]:
            animals.add(cells[0])
        if cells[1]:
            plants.add(cells[1])

    assert animals == {"Hund", "Katze"}
    assert plants == {"Rose", "Tulpe", "Baum"}


def test_render_categorize_answer_wordbank_shuffle_can_be_disabled():
    html_shuffled = render_categorize_answer({}, _CONTENT, include_solutions=False)
    html_unshuffled = render_categorize_answer({"shuffle": "false"}, _CONTENT, include_solutions=False)

    def _words_in_order(html):
        return re.findall(r"categorize-word'>(.*?)<", html)

    assert _words_in_order(html_unshuffled) == ["Hund", "Katze", "Rose", "Tulpe", "Baum"]
    # Shuffled order is deterministic but (with 5 distinct items) essentially
    # never equals the identity order -- just assert both contain the same set.
    assert set(_words_in_order(html_shuffled)) == set(_words_in_order(html_unshuffled))


def test_render_categorize_answer_is_deterministic_across_calls():
    first = render_categorize_answer({}, _CONTENT, include_solutions=False)
    second = render_categorize_answer({}, _CONTENT, include_solutions=False)
    assert first == second


def test_render_categorize_answer_position_option_controls_wrapper_class():
    html = render_categorize_answer({"position": "right"}, _CONTENT, include_solutions=False)
    assert "wordbank-position-right" in html


def test_estimate_categorize_weight_zero_for_no_content():
    assert estimate_categorize_weight({}, "") == 0.0


def test_estimate_categorize_weight_positive_for_real_content():
    weight = estimate_categorize_weight({}, _CONTENT)
    assert 0.0 < weight <= 7.0
