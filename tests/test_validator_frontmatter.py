"""Validator: Frontmatter-Felder (FM003 bis FM006, `mode`, `tag`).

Aus `test_blatt_validator.py` nach Themen aufgeteilt (300-Zeilen-Regel), Tests unverändert."""

import pytest

from app.core.blatt_validator import inspect_markdown_text
from validator_doc_support import build_document_with_mode


def test_frontmatter_mode_ws_and_test_are_accepted():
    ws_doc = build_document_with_mode("ws")
    test_doc = build_document_with_mode("test")
    worksheet_doc = build_document_with_mode("worksheet")
    solution_doc = build_document_with_mode("solution")
    presentation_doc = build_document_with_mode("presentation")

    ws_codes = {d.code for d in inspect_markdown_text(ws_doc).diagnostics}
    test_codes = {d.code for d in inspect_markdown_text(test_doc).diagnostics}
    worksheet_codes = {d.code for d in inspect_markdown_text(worksheet_doc).diagnostics}
    solution_codes = {d.code for d in inspect_markdown_text(solution_doc).diagnostics}
    presentation_codes = {d.code for d in inspect_markdown_text(presentation_doc).diagnostics}

    assert "FM002" not in ws_codes
    assert "FM002" not in test_codes
    assert "FM002" not in worksheet_codes
    assert "FM002" not in solution_codes
    assert "FM002" not in presentation_codes


def test_frontmatter_mode_is_no_longer_a_known_field():
    # `mode` existiert nicht mehr (I3): weder Wertepruefung (FM002) noch eine andere Diagnose.
    doc = build_document_with_mode("foobar")
    diagnostics = inspect_markdown_text(doc).diagnostics

    assert not [d for d in diagnostics if d.anchor == "mode" or d.code == "FM002"]


def test_frontmatter_invalid_presentation_layout_emits_fm004():
    doc = (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "mode: presentation\n"
        "presentation_layout: widescreen\n"
        "---\n"
        "Text\n"
    )
    diagnostics = inspect_markdown_text(doc).diagnostics

    fm004 = [d for d in diagnostics if d.code == "FM004"]
    assert fm004
    assert fm004[0].severity == "error"


def test_frontmatter_valid_presentation_layout_has_no_fm004():
    doc = (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "mode: presentation\n"
        "presentation_layout: presentation_16_9\n"
        "---\n"
        "Text\n"
    )
    codes = {d.code for d in inspect_markdown_text(doc).diagnostics}
    assert "FM004" not in codes


def test_frontmatter_invalid_presentation_bool_emits_fm005():
    doc = (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "mode: presentation\n"
        "presentation_show_mini_header: maybe\n"
        "---\n"
        "Text\n"
    )
    diagnostics = inspect_markdown_text(doc).diagnostics

    fm005 = [d for d in diagnostics if d.code == "FM005"]
    assert fm005
    assert fm005[0].severity == "error"


def _build_document_with_show_student_header(value):
    return (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        f"show_student_header: {value}\n"
        "---\n"
        "Text\n"
    )


@pytest.mark.parametrize("value", ["ja", "nein", "j", "n", "true", "false", "1", "0"])
def test_frontmatter_valid_show_student_header_has_no_fm006(value):
    doc = _build_document_with_show_student_header(value)
    codes = {d.code for d in inspect_markdown_text(doc).diagnostics}
    assert "FM006" not in codes


@pytest.mark.parametrize("value", ["wahr", "falsch", "maybe", "xyz"])
def test_frontmatter_invalid_show_student_header_emits_fm006(value):
    """`wahr`/`falsch` sind gueltig fuer FM005-Felder, aber NICHT fuer FM006

    (unterschiedliches Boolean-Vokabular: `_meta_bool_ja_nein` kennt kein
    `wahr`/`falsch`, dafuer `j`/`n` -- Regressionsschutz gegen versehentliches
    Verwenden von `TRUTHY_META_BOOLEAN_TOKENS` statt `JA_NEIN_BOOLEAN_TOKENS`).
    """
    doc = _build_document_with_show_student_header(value)
    diagnostics = inspect_markdown_text(doc).diagnostics
    fm006 = [d for d in diagnostics if d.code == "FM006"]
    assert fm006
    assert fm006[0].severity == "error"


def test_frontmatter_invalid_show_document_header_emits_fm006():
    doc = (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "show_document_header: wahr\n"
        "---\n"
        "Text\n"
    )
    codes = {d.code for d in inspect_markdown_text(doc).diagnostics}
    assert "FM006" in codes


def test_frontmatter_tag_accepts_simple_text_values():
    text = (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "tag: A1\n"
        "---\n"
        ":::help\nHinweis\n:::\n"
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "FM003" not in codes


def test_frontmatter_tag_rejects_empty_value_with_fm003():
    text = (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "tag: \"\"\n"
        "---\n"
        ":::help\nHinweis\n:::\n"
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "FM003" in codes


def test_frontmatter_tag_rejects_non_scalar_value_with_fm003():
    text = (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "tag:\n"
        "  nested: value\n"
        "---\n"
        ":::help\nHinweis\n:::\n"
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "FM003" in codes
