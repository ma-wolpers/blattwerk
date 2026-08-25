import re

from app.core.answer_special_ordering import (
    estimate_ordering_weight,
    parse_ordering_items,
    render_ordering_answer,
)

_CONTENT = (
    "- Zuerst das Ei kaufen\n"
    "- Dann den Teig anruehren\n"
    "- Dann backen\n"
    "- Zum Schluss servieren\n"
)


def _item_rows(html):
    return re.findall(r"<div class='ordering-item'>.*?</div>", html)


def test_parse_ordering_items_reads_bullet_list_in_order():
    items = parse_ordering_items(_CONTENT)
    assert items == [
        "Zuerst das Ei kaufen",
        "Dann den Teig anruehren",
        "Dann backen",
        "Zum Schluss servieren",
    ]


def test_parse_ordering_items_empty_for_blank_content():
    assert parse_ordering_items("") == []
    assert parse_ordering_items("   \n  ") == []


def test_render_ordering_answer_empty_content_returns_empty_string():
    assert render_ordering_answer({}, "", include_solutions=False) == ""


def test_render_ordering_answer_worksheet_mode_has_empty_rank_boxes():
    html = render_ordering_answer({}, _CONTENT, include_solutions=False)
    rows = _item_rows(html)
    assert len(rows) == 4
    for row in rows:
        assert "ordering-rank-filled" not in row
        assert "<span class='ordering-rank-box'></span>" in row


def test_render_ordering_answer_solution_mode_fills_correct_ranks():
    html = render_ordering_answer({}, _CONTENT, include_solutions=True)
    rows = _item_rows(html)
    assert len(rows) == 4

    rank_by_item = {}
    for row in rows:
        rank_match = re.search(r"ordering-rank-filled'>(\d+)<", row)
        label_match = re.search(r"<p>(.*?)</p>", row)
        assert rank_match and label_match
        rank_by_item[label_match.group(1)] = int(rank_match.group(1))

    assert rank_by_item["Zuerst das Ei kaufen"] == 1
    assert rank_by_item["Dann den Teig anruehren"] == 2
    assert rank_by_item["Dann backen"] == 3
    assert rank_by_item["Zum Schluss servieren"] == 4


def test_render_ordering_answer_worksheet_and_solution_share_the_same_shuffled_order():
    worksheet_html = render_ordering_answer({}, _CONTENT, include_solutions=False)
    solution_html = render_ordering_answer({}, _CONTENT, include_solutions=True)

    def _labels_in_order(html):
        return re.findall(r"<p>(.*?)</p>", html)

    assert _labels_in_order(worksheet_html) == _labels_in_order(solution_html)


def test_render_ordering_answer_is_deterministic_across_calls():
    first = render_ordering_answer({}, _CONTENT, include_solutions=False)
    second = render_ordering_answer({}, _CONTENT, include_solutions=False)
    assert first == second


def test_render_ordering_answer_numbering_letters_uses_alpha_labels():
    html = render_ordering_answer({"numbering": "letters"}, _CONTENT, include_solutions=True)
    rows = _item_rows(html)
    labels = set()
    for row in rows:
        match = re.search(r"ordering-rank-filled'>([A-Z]+)<", row)
        assert match
        labels.add(match.group(1))
    assert labels == {"A", "B", "C", "D"}


def test_render_ordering_answer_invalid_numbering_falls_back_to_numeric():
    html = render_ordering_answer({"numbering": "roman"}, _CONTENT, include_solutions=True)
    assert re.search(r"ordering-rank-filled'>\d+<", html)


def test_estimate_ordering_weight_zero_for_no_items():
    assert estimate_ordering_weight({}, "") == 0.0


def test_estimate_ordering_weight_positive_for_real_content():
    weight = estimate_ordering_weight({}, _CONTENT)
    assert 0.0 < weight <= 6.0
