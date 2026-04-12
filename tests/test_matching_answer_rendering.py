from app.core.blatt_kern_answer_table import _render_answer_block


def test_matching_shows_worksheet_example_pairs_only_in_worksheet_mode():
    options = {"type": "matching", "layout": "horizontal"}
    content = """
left:
  - Alpha
  - Beta
right:
  - Eins
  - Zwei
worksheet_matches:
  - "1-2"
matches:
  - "2-1"
"""

    worksheet_html = _render_answer_block(options, content, include_solutions=False)
    solution_html = _render_answer_block(options, content, include_solutions=True)

    assert "matching-line-worksheet" in worksheet_html
    assert "matching-line-worksheet" not in solution_html
    assert "class='matching-line'" in solution_html


def test_matching_defaults_to_center_and_no_guides():
    options = {"type": "matching", "layout": "horizontal"}
    content = """
left:
  - A
right:
  - B
"""

    html = _render_answer_block(options, content, include_solutions=False)

    assert "matching-no-guides" in html
    assert "matching-align-center" in html
    assert "matching-lane-align-center" in html
    assert "matching-empty" not in html


def test_matching_uniform_height_mode_sets_item_height_variable():
    options = {"type": "matching", "layout": "vertical", "height_mode": "uniform"}
    content = """
top:
  - Kurz
  - Ein deutlich laengerer Inhalt, der mehr Platz braucht
bottom:
  - X
  - Y
matches:
  - "1-1"
  - "2-2"
"""

    html = _render_answer_block(options, content, include_solutions=True)

    assert "matching-height-uniform" in html
    assert "--matching-item-height:" in html


def test_matching_distributes_two_items_over_five_slots():
    options = {"type": "matching", "layout": "horizontal", "show_guides": "false"}
    content = """
left:
  - L1
  - L2
  - L3
  - L4
  - L5
right:
  - R1
  - R2
matches:
  - "1-1"
  - "5-2"
"""

    html = _render_answer_block(options, content, include_solutions=True)

    assert "y1='10.00%'" in html
    assert "y2='30.00%'" in html
    assert "y1='90.00%'" in html
    assert "y2='70.00%'" in html


def test_matching_distributes_three_items_over_five_slots():
    options = {"type": "matching", "layout": "horizontal", "show_guides": "false"}
    content = """
left:
  - L1
  - L2
  - L3
  - L4
  - L5
right:
  - R1
  - R2
  - R3
matches:
  - "1-1"
  - "3-2"
  - "5-3"
"""

    html = _render_answer_block(options, content, include_solutions=True)

    assert "y2='10.00%'" in html
    assert "y2='50.00%'" in html
    assert "y2='90.00%'" in html
