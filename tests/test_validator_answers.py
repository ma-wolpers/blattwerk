"""Validator: Antwortblöcke (AN005/AN006/AN008/AN010), Optionsverbote auf Antwortblöcken und Bildpfade (PT001).

Aus `test_blatt_validator.py` nach Themen aufgeteilt (300-Zeilen-Regel), Tests unverändert."""

from app.core.blatt_validator import inspect_markdown_text
from validator_doc_support import build_document


def test_empty_answer_block_emits_an005_warning():
    text = build_document(":::lines\n\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN005" in codes


def test_conflicting_line_markers_emit_an006_warning():
    text = build_document(":::lines\n%{Start\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN006" in codes


def test_trailing_legacy_marker_does_not_emit_an006_warning():
    text = build_document(":::lines\nText %\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN006" not in codes


def test_non_empty_answer_without_marker_conflict_has_no_new_warnings():
    text = build_document(":::lines\n&{Impuls}\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN005" not in codes
    assert "AN006" not in codes


def test_task_with_worksheet_marker_without_solution_emits_an010_warning():
    text = build_document(":::task\n§ Nur Arbeitsblatt\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN010" in codes


def test_task_with_matching_solution_marker_has_no_an010_warning():
    text = build_document(":::task\n§ Nur Arbeitsblatt\n% Musterloesung\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN010" not in codes


def test_answer_block_with_worksheet_marker_without_solution_emits_an010_warning():
    text = build_document(":::lines\n§ Nur Arbeitsblatt\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN010" in codes


def test_answer_block_with_matching_solution_marker_has_no_an010_warning():
    text = build_document(":::lines\n§ Nur Arbeitsblatt\n% Musterloesung\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN010" not in codes


def test_absolute_markdown_image_path_emits_pt001():
    text = build_document(
        ":::task\n"
        "![Abb](A:/7thCloud/7thVault/ZZ Assets/plot.png)\n"
        ":::"
    )
    diagnostics = inspect_markdown_text(text).diagnostics

    pt001 = [d for d in diagnostics if d.code == "PT001"]
    assert pt001


def test_relative_markdown_image_path_has_no_pt001():
    text = build_document(
        ":::task\n"
        "![Abb](ZZ Assets/plot.png)\n"
        ":::"
    )
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}
    assert "PT001" not in codes


def test_legacy_answer_block_emits_an008_error():
    text = build_document(":::answer type=lines\nText\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}
    assert "AN008" in codes


def test_type_option_is_forbidden_on_dedicated_answer_blocks():
    text = build_document(":::grid type=grid rows=3 cols=3\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}
    assert "AN009" in codes


def test_help_key_option_is_now_rejected_with_op001():
    text = build_document(":::help key=A1\nHinweis\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "OP001" in codes


def test_help_tag_option_is_allowed_without_op001():
    text = build_document(":::help tag=LOKAL\nHinweis\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "OP001" not in codes
