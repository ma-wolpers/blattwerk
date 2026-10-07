"""Schülerkopfzeile: Vorbefüllung von Lerngruppe/Datum aus dem Frontmatter (FM011)."""

from datetime import date

import pytest

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks
from app.core.blatt_validator import inspect_markdown_text
from app.core.document_type_registry import DOCUMENT_TYPE_EXAM
from app.core.document_type_templates import build_new_document_content
from app.core.exam_expectation_horizon import build_expectation_horizon_html
from app.core.student_header import render_student_header

HEAD = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\nshow_student_header: ja\n"


def _filled(html):
    return [part.split("</span>", 1)[0] for part in html.split("student-line-filled\">")[1:]]


def test_header_hidden_without_option():
    assert render_student_header({"Lerngruppe": "11.6"}) == ""


def test_string_values_are_prefilled():
    html = render_student_header({"show_student_header": "ja", "Lerngruppe": "11.6", "Datum": "25.09.26"})
    assert _filled(html) == ["11.6", "25.09.26"]
    assert html.count("class=\"student-line\"") == 1  # Name bleibt leer


def test_iso_date_object_is_formatted_german():
    html = render_student_header({"show_student_header": "ja", "Datum": date(2026, 9, 25)})
    assert _filled(html) == ["25.09.2026"]


@pytest.mark.parametrize("value", [None, "", "  ", "Lerngruppe eintragen"])
def test_empty_and_placeholder_learner_group_stay_empty(value):
    html = render_student_header({"show_student_header": "ja", "Lerngruppe": value, "Datum": "Datum eintragen"})
    assert _filled(html) == []


def test_values_are_escaped():
    html = render_student_header({"show_student_header": "ja", "Lerngruppe": "<b>11a</b>"})
    assert _filled(html) == ["&lt;b&gt;11a&lt;/b&gt;"]


def test_numeric_learner_group_is_not_prefilled_and_warns_fm011():
    text = HEAD + "Lerngruppe: 11.6\n---\n:::task\nA\n:::\n"
    diagnostics = inspect_markdown_text(text, document_type="exam").diagnostics
    fm011 = [d for d in diagnostics if d.code == "FM011"]
    assert len(fm011) == 1 and fm011[0].severity == "warning" and "Lerngruppe" in fm011[0].message
    assert _filled(render_student_header({"show_student_header": "ja", "Lerngruppe": 11.6})) == []


def test_string_learner_group_and_iso_date_have_no_fm011():
    text = HEAD + "Lerngruppe: \"11.6\"\nDatum: 2026-09-25\n---\n:::task\nA\n:::\n"
    codes = [d.code for d in inspect_markdown_text(text, document_type="exam").diagnostics]
    assert "FM011" not in codes


def test_full_render_contains_prefilled_header():
    html = render_html({"Titel": "T", "show_student_header": "ja", "Lerngruppe": "11.6"}, parse_blocks(":::task\nA\n:::\n"), document_type="exam")
    assert "student-line-filled\">11.6<" in html


def test_exam_template_has_placeholders_that_count_as_empty():
    template = build_new_document_content(DOCUMENT_TYPE_EXAM, {})
    assert "Lerngruppe: Lerngruppe eintragen" in template and "Datum: Datum eintragen" in template
    codes = [d.code for d in inspect_markdown_text(template, document_type="exam").diagnostics]
    assert "FM011" not in codes


def test_expectation_horizon_formats_date_and_skips_placeholder():
    body = ":::task points=1 afb=1\nA\n:::\n:::solution\n1. x (1P)\n:::\n"
    iso, _ = build_expectation_horizon_html("---\ndocument_type: exam\nTitel: K\nFach: M\nDatum: 2026-09-25\n---\n" + body)
    placeholder, _ = build_expectation_horizon_html("---\ndocument_type: exam\nTitel: K\nFach: M\nDatum: Datum eintragen\n---\n" + body)
    assert "25.09.2026" in iso and "2026-09-25" not in iso
    assert "Datum eintragen" not in placeholder
