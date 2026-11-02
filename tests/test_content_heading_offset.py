"""Markdown-Überschriften im Inhalt liegen eine Ebene unter dem `<h1>`-Dokumenttitel.

Arbeitsblatt und Klausur setzen den `Titel` als `<h1>`; ein `#` im Inhalt darf nicht
genauso aussehen. Folien zeigen den Titel nur in der Kopfzeile und bleiben unverändert.
Nur synthetische Inhalte.
"""

from __future__ import annotations

from app.core.blatt_kern_task_render import render_block
from app.core.document_type_registry import (
    DOCUMENT_TYPE_EXAM,
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
    content_heading_offset,
)
from app.core.markdown_factory import new_markdown
from app.core.plain_markdown_render import render_plain_markdown_html


def _convert(text: str, offset: int) -> str:
    return new_markdown(inline_markup=False, heading_offset=offset).convert(text)


def test_offset_moves_every_level_down_and_stops_at_h6():
    html = _convert("# A\n\n## B\n\n##### E\n\n###### F", 1)
    assert "<h2>A</h2>" in html and "<h3>B</h3>" in html
    assert "<h6>E</h6>" in html and "<h6>F</h6>" in html
    assert "<h1>" not in html


def test_setext_headings_move_too():
    assert _convert("Titelzeile\n==========", 1) == "<h2>Titelzeile</h2>"


def test_zero_offset_keeps_headings():
    assert _convert("# A", 0) == "<h1>A</h1>"


def test_raw_html_heading_stays_as_written():
    assert "<h1>Roh</h1>" in _convert("<h1>Roh</h1>", 1)


def test_offset_follows_the_title_rule_of_each_document_type():
    assert content_heading_offset(DOCUMENT_TYPE_WORKSHEET) == 1
    assert content_heading_offset(DOCUMENT_TYPE_EXAM) == 1
    assert content_heading_offset(DOCUMENT_TYPE_PRESENTATION) == 0


def test_worksheet_text_and_block_bodies_start_at_h2():
    raw = render_block("raw", {}, "# Teil", document_type=DOCUMENT_TYPE_WORKSHEET)
    assert raw.startswith("<h2 ") and raw.endswith(">Teil</h2>")
    info = render_block("info", {}, "## Hinweis\n\nText", document_type=DOCUMENT_TYPE_WORKSHEET)
    assert "<h3>Hinweis</h3>" in info


def test_solution_content_moves_like_other_blocks():
    html = render_block("solution", {}, "# Weg\n\nText", include_solutions=True, document_type=DOCUMENT_TYPE_WORKSHEET)
    assert "<h2>Weg</h2>" in html


def test_presentation_headings_stay():
    raw = render_block("raw", {}, "# Folie", document_type=DOCUMENT_TYPE_PRESENTATION)
    assert raw.startswith("<h1 ") and raw.endswith(">Folie</h1>")


def test_plain_markdown_moves_headings_only_below_a_title():
    with_title = render_plain_markdown_html("---\nTitel: Notizen\n---\n# Abschnitt\n")
    assert with_title.count("<h1>") == 1 and "<h2>Abschnitt</h2>" in with_title
    without_title = render_plain_markdown_html("# Abschnitt\n")
    assert "<h1>Abschnitt</h1>" in without_title
