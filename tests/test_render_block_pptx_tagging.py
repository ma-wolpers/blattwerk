"""Tests for `render_block()`'s `data-block-type` tagging.

Added for the experimental editable-PPTX export
(`blatt_kern_pptx_export_editable.py`), which needs a way to find each
block's DOM root during Playwright-driven extraction. `render_block()`
tags whichever element it already emits as a block's root, rather than
introducing a new wrapping element -- these tests pin that contract (no
new element, attribute on the existing root, harmless for empty output).
"""

from app.core.blatt_kern_task_render import render_block


def test_info_block_root_gets_tagged_without_a_new_wrapper_element():
    html = render_block("info", {"type": "note"}, "Hinweis.")

    assert html.startswith('<div data-block-type="info" ')
    assert "class='info note'" in html
    # Exactly one root <div> for the block -- tagging must not add a
    # second, wrapping <div> around the existing one.
    assert html.count("<div") == 1


def test_qrcode_block_root_gets_tagged():
    html = render_block("qrcode", {"url": "https://example.org"}, "")

    assert 'data-block-type="qrcode"' in html
    # The attribute must land on the block's own first tag, not appended
    # as a fresh outer element.
    assert html.index('data-block-type="qrcode"') < 40


def test_task_block_root_gets_tagged():
    html = render_block("task", {}, "Rechne aus.")

    assert 'data-block-type="task"' in html


def test_table_block_root_gets_tagged():
    html = render_block("table", {}, "cells:\n  - [\"A\", \"B\"]")

    assert 'data-block-type="table"' in html


def test_raw_block_with_multiple_paragraphs_tags_only_the_first_root():
    # `raw` markdown can produce several sibling top-level elements --
    # `_tag_root_element_with_block_type` deliberately only tags the
    # first one (it only ever inserts into html's OWN first tag), it does
    # not walk/tag every sibling.
    html = render_block("raw", {}, "Absatz A\n\nAbsatz B")

    assert html.count('data-block-type="raw"') == 1
    assert html.startswith("<p data-block-type=\"raw\">")


def test_empty_block_output_is_not_mutated_by_tagging():
    # `pagebreak`/`framebreak` etc. either render nothing or a self-
    # contained marker div; blocks that render "" (e.g. framebreak) must
    # stay exactly "" -- no attribute gets attached to nothing.
    assert render_block("framebreak", {}, "") == ""
    assert render_block("sectionmark", {}, "") == ""


def test_pagebreak_marker_div_also_gets_tagged():
    html = render_block("pagebreak", {}, "")

    assert 'data-block-type="pagebreak"' in html


def test_block_that_should_not_render_stays_untagged_empty():
    # `mode=solution` on a block hides it in the worksheet view entirely --
    # should_render_block() returns "" before block-type dispatch even
    # runs, and tagging must not turn that into a stray tagged fragment.
    html = render_block("info", {"mode": "solution"}, "Nur Loesung.", include_solutions=False)

    assert html == ""
