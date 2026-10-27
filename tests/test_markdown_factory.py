"""Eine Markdown-Fabrik: geordnete Listen behalten ihre Startnummer.

Frueher begann jede nummerierte Liste in Blattwerk-Dokumenten bei 1
(python-markdown `LAZY_OL`): "3. drei" wurde "1. drei", "2025. Jahr" wurde "1. Jahr".
"""

from __future__ import annotations

from app.core.answer_line_markers import render_answer_content_html_for_mode
from app.core.blatt_kern_answer_choice import _render_choice_fragment
from app.core.blatt_kern_shared import _new_markdown_converter, convert_markdown_with_math, normalize_markdown
from app.core.markdown_factory import new_markdown


def test_block_converter_keeps_list_start_number():
    """Blockinhalt: `3.` startet die Liste bei 3."""
    html = convert_markdown_with_math(_new_markdown_converter(), normalize_markdown("Text\n\n3. drei\n4. vier"))
    assert '<ol start="3">' in html


def test_paragraph_starting_with_year_keeps_the_year():
    """"2025. Jahr" zeigt 2025, nicht 1."""
    assert '<ol start="2025">' in new_markdown(inline_markup=False).convert("2025. Jahr")


def test_list_starting_at_one_has_no_start_attribute():
    """Normalfall unveraendert: keine `start`-Angabe bei 1."""
    assert new_markdown(inline_markup=False).convert("1. a\n2. b").startswith("<ol>")


def test_lists_false_keeps_markers_literal():
    """Tabellenzellen-Modus: Listenmarker bleiben Text."""
    assert new_markdown(inline_markup=False, lists=False).convert("2. Frage") == "<p>2. Frage</p>"


def test_answer_lines_keep_start_number():
    """Antwortzeilen behalten ihre Listen, jetzt mit richtiger Nummer."""
    assert '<ol start="5">' in render_answer_content_html_for_mode("5. fuenf", include_solutions=False)


def test_multiple_choice_question_keeps_line_breaks():
    """MC nutzt den gemeinsamen Renderer mit Block-Konverter: Umbrueche bleiben."""
    assert _render_choice_fragment("Zeile 1\nZeile 2") == "Zeile 1<br />\nZeile 2"
    assert _render_choice_fragment("  **A**  ") == "<strong>A</strong>"
