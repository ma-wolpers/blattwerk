"""Layout-, Validator- und PDF-Prüf-Tests für Worterklärungen und Randspalten.

Sichert die Invarianten aus dem Planungs-Review ab:
- ohne Worterklärung keine rechte Randspalte (volle Textbreite),
- mit Worterklärung reserviert das Stylesheet die rechte Randspalte, und das
  wird aus der tatsächlich gerenderten Sammlung abgeleitet (nicht per
  Textsuche im HTML),
- Präsentation/Hilfekarten bekommen keine Randspalten,
- ein fehlerhaftes `??...??` blockiert den Build (`IM002`),
- Erklärungen, die nicht (vollständig) am Rand stehen, lösen `IM003` aus;
  passende Erklärungen nicht.
"""

import fitz
import pytest

from app.core.blatt_kern_io_build import build_worksheet
from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_validator import has_blocking_diagnostics, inspect_markdown_text
from app.core.inline_markup.word_notes import WordNoteOccurrence
from app.core.word_note_pdf_check import append_word_note_placement_warnings
from app.styles.blatt_styles import build_stylesheet

META = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "worksheet"}
FRONTMATTER = "---\nTitel: T\nFach: M\nThema: X\nStufe: 8\nmode: worksheet\n---\n\n"


def _html(content, word_notes_out=None):
    blocks = [("material", {}, content)]
    return render_html(META, blocks, include_solutions=False, word_notes_out=word_notes_out)


def test_document_without_word_note_has_no_right_gutter():
    collected = []
    html = _html("Ein normaler Absatz.", word_notes_out=collected)

    assert collected == []
    assert "--word-note-gutter" not in html
    assert "--task-margin-gutter" in html


def test_document_with_word_note_reserves_right_gutter_from_collected_notes():
    collected = []
    html = _html("Die ??Zelle|kleinste Einheit?? lebt.", word_notes_out=collected)

    assert [(n.term, n.explanation) for n in collected] == [("Zelle", "kleinste Einheit")]
    assert "--word-note-gutter" in html
    assert "padding-right: var(--word-note-gutter)" in html


def test_word_note_text_in_literal_word_does_not_reserve_gutter():
    """Regression gegen die String-Heuristik: das Wort im Text ist keine Worterklärung."""
    html = _html("Die CSS-Klasse word-note-text steht hier nur als Text.")

    assert "--word-note-gutter" not in html


def test_stylesheet_gutters_are_opt_in():
    default_css = build_stylesheet("a4_portrait", "standard")
    worksheet_css = build_stylesheet("a4_portrait", "standard", reserve_gutters=True)
    presentation_css = build_stylesheet(
        "presentation_16_9", "standard", document_mode="presentation"
    )

    assert "--task-margin-gutter" not in default_css
    assert "--task-margin-gutter" in worksheet_css
    assert "--task-margin-gutter" not in presentation_css


def test_word_note_text_is_hidden_by_default_and_in_unsupported_containers():
    css = build_stylesheet("a4_portrait", "standard", reserve_gutters=True, has_word_notes=True)

    assert ".word-note-text {\n    display: none;" in css
    assert "td .word-note-text" in css
    assert ".column:not(:last-child) .word-note-text" in css


def test_malformed_word_note_is_a_blocking_validator_error():
    inspected = inspect_markdown_text(FRONTMATTER + ":::material\nText ??kein Trenner?? hier\n:::\n")

    errors = [d for d in inspected.diagnostics if d.code == "IM002"]
    assert len(errors) == 1 and errors[0].severity == "error"
    assert has_blocking_diagnostics(inspected.diagnostics)


def test_valid_word_note_and_code_span_do_not_trigger_validator_error():
    inspected = inspect_markdown_text(
        FRONTMATTER + ":::material\nOk ??A|B?? und `??x??` als Code.\n:::\n"
    )

    assert not [d for d in inspected.diagnostics if d.code == "IM002"]


def test_build_worksheet_refuses_malformed_word_note(tmp_path):
    source = tmp_path / "doc.md"
    source.write_text(FRONTMATTER + ":::material\n??nur Begriff??\n:::\n", encoding="utf-8")

    with pytest.raises(ValueError, match="IM002"):
        build_worksheet(source, tmp_path / "out.html")


def test_build_worksheet_html_contains_word_note(tmp_path):
    source = tmp_path / "doc.md"
    source.write_text(FRONTMATTER + ":::material\nDie ??Zelle|Baustein?? lebt.\n:::\n", encoding="utf-8")

    out = build_worksheet(source, tmp_path / "out.html")

    assert 'class="word-note-text">Baustein<' in out.read_text(encoding="utf-8")


def _pdf_with_pages(tmp_path, pages):
    path = tmp_path / "check.pdf"
    doc = fitz.open()
    for words in pages:
        page = doc.new_page()
        for x, y, text in words:
            page.insert_text((x, y), text, fontsize=8)
    doc.save(path)
    doc.close()
    return path


def _check(tmp_path, pages, explanation):
    diagnostics = []
    append_word_note_placement_warnings(
        diagnostics_out=diagnostics,
        pdf_path=_pdf_with_pages(tmp_path, pages),
        word_notes=[WordNoteOccurrence(term="Zelle", explanation=explanation)],
        page_format="a4_portrait",
        hole_punch_enabled=False,
    )
    return diagnostics


GUTTER_X = 490
IN_TEXT_X = 100


def test_pdf_check_accepts_note_fully_in_gutter_on_one_page(tmp_path):
    pages = [[(IN_TEXT_X, 200, "Zelle"), (GUTTER_X, 200, "kleinste"), (GUTTER_X, 212, "Einheit")]]

    assert _check(tmp_path, pages, "kleinste Einheit") == []


def test_pdf_check_warns_when_note_continues_on_next_page(tmp_path):
    pages = [
        [(IN_TEXT_X, 700, "Zelle"), (GUTTER_X, 700, "kleinste")],
        [(GUTTER_X, 100, "Einheit")],
    ]

    diagnostics = _check(tmp_path, pages, "kleinste Einheit")

    assert [(d.code, d.severity) for d in diagnostics] == [("IM003", "warning")]
    assert "nächsten Seite" in diagnostics[0].message


def test_pdf_check_warns_when_note_is_not_in_gutter(tmp_path):
    pages = [[(IN_TEXT_X, 200, "Zelle"), (IN_TEXT_X, 300, "kleinste Einheit")]]

    diagnostics = _check(tmp_path, pages, "kleinste Einheit")

    assert [d.code for d in diagnostics] == ["IM003"]
    assert "nicht in der rechten Randspalte" in diagnostics[0].message


def test_pdf_check_ignores_running_header_and_footer_words(tmp_path):
    pages = [[(GUTTER_X, 30, "kleinste"), (GUTTER_X, 30, "Einheit")]]

    assert [d.code for d in _check(tmp_path, pages, "kleinste Einheit")] == ["IM003"]
