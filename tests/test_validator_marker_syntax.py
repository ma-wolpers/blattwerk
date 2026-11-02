"""Validator: `:::`-Markersyntax und Abschnittstrenner (BL002 bis BL006, BL017).

Aus `test_blatt_validator.py` nach Themen aufgeteilt (300-Zeilen-Regel), Tests unverändert."""

from app.core.blatt_validator import inspect_markdown_text
from validator_doc_support import build_document


def test_space_after_block_marker_emits_bl002_error():
    text = build_document("::: lines\nInhalt\n:::")
    inspected = inspect_markdown_text(text)
    bl002 = [d for d in inspected.diagnostics if d.code == "BL002"]
    assert bl002
    assert bl002[0].severity == "error"


def test_text_after_closing_marker_emits_one_bl002_error():
    # Früher meldete der Editor hier zusätzlich SY001; jetzt gibt es genau eine Diagnose.
    text = build_document(":::info\nInhalt\n::: Ende\n:::")
    codes = [d.code for d in inspect_markdown_text(text).diagnostics]
    assert codes.count("BL002") == 1
    assert "SY001" not in codes


def test_closing_marker_followed_by_symbol_emits_bl002_error():
    text = build_document(":::info\nInhalt\n:::-\n:::")
    assert "BL002" in {d.code for d in inspect_markdown_text(text).diagnostics}


def test_unclosed_block_emits_bl017_error_at_its_header():
    text = build_document("Text\n:::info type=note\nInhalt ohne Schluss")
    bl017 = [d for d in inspect_markdown_text(text).diagnostics if d.code == "BL017"]
    assert len(bl017) == 1
    assert bl017[0].severity == "error"
    assert bl017[0].line_number == 7
    assert "`:::info`" in bl017[0].message


def test_closed_blocks_emit_no_bl017():
    text = build_document(":::task\nA\n:::\n:::space:::")
    assert "BL017" not in {d.code for d in inspect_markdown_text(text).diagnostics}


def test_orphan_closing_marker_emits_bl003_error():
    text = build_document("Text vorab\n:::\nText danach")
    inspected = inspect_markdown_text(text)
    bl003 = [d for d in inspected.diagnostics if d.code == "BL003"]
    assert bl003
    assert bl003[0].severity == "error"


def test_regular_open_and_close_marker_do_not_emit_bl003():
    text = build_document(":::task\nInhalt\n:::")
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}
    assert "BL003" not in codes


def test_orphan_closing_marker_line_number_includes_frontmatter():
    text = build_document(":::\n")
    inspected = inspect_markdown_text(text)
    bl003 = [d for d in inspected.diagnostics if d.code == "BL003"]
    assert bl003
    assert bl003[0].line_number == 6
    assert "Zeile 6" in bl003[0].message


def test_nested_block_open_inside_open_block_emits_bl004_error():
    text = build_document(
        ":::material\n"
        "Einleitung\n"
        ":::table rows=2 cols=2\n"
        "cells:\n"
        "  - ['A', 'B']\n"
        "  - ['C', 'D']\n"
        ":::\n"
        ":::\n"
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    bl004 = [d for d in diagnostics if d.code == "BL004"]
    bl003 = [d for d in diagnostics if d.code == "BL003"]

    assert bl004
    assert bl004[0].severity == "error"
    assert bl003


def test_self_closing_block_inside_open_block_emits_bl004_error():
    text = build_document(":::task\n:::space:::\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl004 = [d for d in diagnostics if d.code == "BL004"]
    assert bl004
    assert bl004[0].severity == "error"


def test_subtask_after_unclosed_task_gets_follow_block_hint():
    text = build_document(":::task\nAufgabe\n:::subtask\nTeilaufgabe\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl004 = [d for d in diagnostics if d.code == "BL004"]

    assert bl004
    assert bl004[0].severity == "error"
    assert "Folgeblock" in bl004[0].message
    assert "zuerst `task` mit `:::` schließen" in bl004[0].message


def test_section_break_triple_dash_inside_open_block_is_allowed_as_markdown_hr():
    text = build_document(":::task\nInhalt\n---\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl005 = [d for d in diagnostics if d.code == "BL005"]

    assert not bl005


def test_section_break_double_dash_inside_open_block_emits_bl005_error():
    text = build_document(":::task\nInhalt\n--\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl005 = [d for d in diagnostics if d.code == "BL005"]

    assert bl005
    assert bl005[0].severity == "error"


def test_invalid_section_marker_without_title_emits_bl006_error():
    text = build_document("--#\n:::task\nInhalt\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl006 = [d for d in diagnostics if d.code == "BL006"]

    assert bl006
    assert bl006[0].severity == "error"


def test_invalid_vspacer_marker_without_unit_emits_bl006_error():
    text = build_document("-=2\n:::task\nInhalt\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl006 = [d for d in diagnostics if d.code == "BL006"]

    assert bl006
    assert bl006[0].severity == "error"


def test_slide_chrome_marker_inside_open_block_emits_bl005_error():
    text = build_document(":::task\nInhalt\n--hf\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl005 = [d for d in diagnostics if d.code == "BL005"]

    assert bl005
    assert bl005[0].severity == "error"


def test_invalid_slide_chrome_marker_variant_emits_bl006_error():
    text = build_document("--hf extra\n:::task\nInhalt\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl006 = [d for d in diagnostics if d.code == "BL006"]

    assert bl006
    assert bl006[0].severity == "error"
