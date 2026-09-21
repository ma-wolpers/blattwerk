"""Tests für die Worterklärung `??Begriff|Erklärung??` (`inline_markup/word_notes.py`).

Deckt die strenge Grammatik ab (genau ein `|`, Escapes, leere Felder =
`IM002`-Fehler), dass innerhalb einer Worterklärung kein Markup ausgewertet
wird, die `is_plain`-Regression (eine Worterklärung darf nie roh im
Markdown-Quelltext verbleiben) und die Anbindung an die python-markdown-
Brücke inklusive Sammelmechanismus.
"""

import markdown

from app.core.inline_markup import parse_inline_markup, render_inline_markup
from app.core.inline_markup.markdown_bridge import register_inline_markup_bridge
from app.core.inline_markup.word_notes import collect_word_notes
from app.core.math_span_protection import convert_markdown_with_math


def _annotated(text):
    runs, diagnostics = parse_inline_markup(text)
    return [r for r in runs if r.annotation is not None], runs, diagnostics


def test_valid_word_note_becomes_annotated_run():
    notes, runs, diagnostics = _annotated("Die ??Mitochondrien|Kraftwerke der Zelle?? arbeiten.")

    assert diagnostics == []
    assert len(notes) == 1
    assert notes[0].text == "Mitochondrien"
    assert notes[0].annotation == "Kraftwerke der Zelle"
    assert "".join(r.text for r in runs if r.annotation is None) == "Die  arbeiten."


def test_annotated_run_is_never_plain():
    """Regression: ein flagloser Worterklärungs-Run darf nicht als plain gelten, sonst geht die Erklärung verloren."""
    notes, _runs, _diagnostics = _annotated("??Begriff|Erklärung??")

    assert notes[0].bold is False and notes[0].italic is False
    assert notes[0].is_plain is False


def test_escaped_pipe_and_escaped_question_marks_are_literal_inside_note():
    notes, _runs, diagnostics = _annotated(r"??a\|b|c\??d??")

    assert diagnostics == []
    assert notes[0].text == "a|b"
    assert notes[0].annotation == "c??d"


def test_escaped_question_marks_outside_note_become_literal():
    _notes, runs, diagnostics = _annotated(r"Wirklich \?? ja")

    assert diagnostics == []
    assert "".join(r.text for r in runs) == "Wirklich ?? ja"


def test_missing_pipe_is_an_error_and_text_stays_literal():
    notes, runs, diagnostics = _annotated("Ein ??kein Trenner?? Text")

    assert notes == []
    assert [(d.code, d.severity) for d in diagnostics] == [("IM002", "error")]
    assert "??kein Trenner??" in "".join(r.text for r in runs)


def test_two_unescaped_pipes_is_an_error():
    notes, _runs, diagnostics = _annotated("??a|b|c??")

    assert notes == []
    assert [d.code for d in diagnostics] == ["IM002"]


def test_empty_term_or_empty_explanation_is_an_error():
    for text in ("??|nur Erklärung??", "??nur Begriff|??", "??  |  ??"):
        notes, _runs, diagnostics = _annotated(text)
        assert notes == [], text
        assert [d.code for d in diagnostics] == ["IM002"], text


def test_no_nested_markup_is_interpreted_inside_a_word_note():
    notes, _runs, diagnostics = _annotated("??T|nutze *stern* und ==gleich== und `code`??")

    assert diagnostics == []
    assert notes[0].annotation == "nutze *stern* und ==gleich== und `code`"
    assert notes[0].italic is False and notes[0].highlight is False


def test_question_marks_inside_inline_code_are_not_a_word_note():
    notes, runs, diagnostics = _annotated("`??x|y??` bleibt Code")

    assert notes == []
    assert diagnostics == []
    assert runs[0].kind == "code"


def test_term_keeps_surrounding_bold_style():
    notes, _runs, _diagnostics = _annotated("**fett ??Wort|Erklärung?? fett**")

    assert notes[0].bold is True


def test_render_inline_markup_html_structure_and_escaping():
    html = render_inline_markup("??<b>|a & b??")

    assert html == (
        '<span class="word-note"><span class="word-note-term">&lt;b&gt;</span>'
        '<span class="word-note-text">a &amp; b</span></span>'
    )


def test_bridge_renders_word_note_and_collects_occurrences():
    md = markdown.Markdown()
    register_inline_markup_bridge(md)

    with collect_word_notes() as occurrences:
        html = convert_markdown_with_math(
            md, "Ein ??Enzym|Biokatalysator?? im Absatz.", lambda text: text
        )

    assert 'class="word-note-text">Biokatalysator<' in html
    assert [(o.term, o.explanation) for o in occurrences] == [("Enzym", "Biokatalysator")]


def test_collector_is_a_noop_without_active_context():
    md = markdown.Markdown()
    register_inline_markup_bridge(md)

    html = convert_markdown_with_math(md, "??A|B??", lambda text: text)

    assert "word-note-text" in html
