"""Validator: Blockoptionen: erlaubte Schlüssel (OP001), Werte (OP002), Veraltetes (OP003) und QR-Code (QR001/QR002).

Aus `test_blatt_validator.py` nach Themen aufgeteilt (300-Zeilen-Regel), Tests unverändert."""

import pytest

from app.core.blatt_validator import inspect_markdown_text
from validator_doc_support import build_document


def test_matching_new_options_are_allowed_without_op001():
    text = build_document(
        ":::matching height_mode=uniform align=center scale=0.4cm "
        "show_guides=false lane_align=center\n"
        "left:\n"
        "  - A\n"
        "right:\n"
        "  - B\n"
        "worksheet_matches:\n"
        "  - '1-1'\n"
        "matches:\n"
        "  - '1-1'\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_table_alignment_option_is_allowed_without_op001():
    text = build_document(
        ":::table rows=2 cols=2 alignment=center\n"
        "cells:\n"
        "  - ['A', 'B']\n"
        "  - ['C', 'D']\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_table_column_headers_option_is_allowed_without_op001():
    text = build_document(
        ':::table rows=2 cols=2 column_headers="A|B"\n'
        "cells:\n"
        "  - ['A', 'B']\n"
        "  - ['C', 'D']\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_table_row_headers_option_is_allowed_without_op001():
    text = build_document(
        ':::table rows=2 cols=2 row_headers="R1|R2"\n'
        "cells:\n"
        "  - ['A', 'B']\n"
        "  - ['C', 'D']\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_table_header_columns_option_now_triggers_op001():
    """Regression guard: `header_columns` wurde ersatzlos entfernt, kein Alias/Backcompat."""
    text = build_document(
        ":::table rows=2 cols=2 header_columns=1\n"
        "cells:\n"
        "  - ['A', 'B']\n"
        "  - ['C', 'D']\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" in codes


def test_lines_height_option_is_allowed_without_op001():
    text = build_document(":::lines rows=2 height=2.2em\nHinweis\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_qrcode_options_are_allowed_without_op001():
    text = build_document(":::qrcode url=https://example.org w=3cm h=2.5cm maxw=60%\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes
    assert "QR001" not in codes
    assert "QR002" not in codes


def test_qrcode_alignment_alias_is_allowed_without_op001():
    text = build_document(":::qrcode url=https://example.org alignment=center\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP001" not in codes
    assert "OP002" not in codes


def test_task_align_option_is_allowed_without_op001():
    text = build_document(":::task align=right\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP001" not in codes
    assert "OP002" not in codes


def test_columns_align_option_is_allowed_without_op001():
    text = build_document(
        ":::columns cols=2 widths='1 1' align=center\n:::raw\nA\n:::\n:::nextcol:::\n:::raw\nB\n:::\n:::endcolumns:::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP001" not in codes
    assert "OP002" not in codes


def test_qrcode_without_url_emits_qr001_error():
    text = build_document(":::qrcode w=3cm\n:::")
    inspected = inspect_markdown_text(text)
    qr001 = [d for d in inspected.diagnostics if d.code == "QR001"]

    assert qr001
    assert qr001[0].severity == "error"


def test_qrcode_with_invalid_url_emits_qr002_error():
    text = build_document(":::qrcode url=javascript:alert(1)\n:::")
    inspected = inspect_markdown_text(text)
    qr002 = [d for d in inspected.diagnostics if d.code == "QR002"]

    assert qr002
    assert qr002[0].severity == "error"


def test_qrcode_with_invalid_size_emits_op002():
    text = build_document(":::qrcode url=https://example.org w=riesig\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP002" in codes


def test_task_with_invalid_align_emits_op002():
    text = build_document(":::task align=diagonal\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP002" in codes


def test_columns_with_invalid_align_emits_op002():
    text = build_document(":::columns cols=2 widths='1 1' align=diagonal :::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP002" in codes


@pytest.mark.parametrize(
    "removed_value",
    ["einzelarbeit", "partnerarbeit", "gruppenarbeit"],
)
def test_removed_work_long_forms_emit_op002(removed_value):
    # Echte Syntaxaenderung (nicht nur Completion-Aenderung): diese
    # Data-noise-Langformen sind komplett aus KNOWN_WORK_VALUES entfernt.
    text = build_document(f":::task work={removed_value}\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP002" in codes


def test_removed_hint_long_form_emits_op002():
    text = build_document(":::task hint=expertenaufgabe\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP002" in codes


@pytest.mark.parametrize(
    "new_short_value",
    ["einzel", "partner", "gruppe"],
)
def test_new_work_short_forms_are_valid(new_short_value):
    text = build_document(f":::task work={new_short_value}\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP002" not in codes


def test_new_hint_short_form_experte_is_valid():
    text = build_document(":::task hint=experte\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP002" not in codes


@pytest.mark.parametrize(
    "option_key,abbreviation",
    [
        ("work", "sgl"),
        ("work", "grp"),
        ("action", "exc"),
        ("action", "calc"),
        ("hint", "tp"),
        ("hint", "eri"),
    ],
)
def test_newly_curated_abbreviations_are_valid(option_key, abbreviation):
    text = build_document(f":::task {option_key}={abbreviation}\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP002" not in codes


@pytest.mark.parametrize("align_abbreviation", ["l", "r", "c", "j", "m", "b"])
def test_newly_curated_align_abbreviations_are_valid(align_abbreviation):
    text = build_document(f":::task align={align_abbreviation}\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP002" not in codes


@pytest.mark.parametrize(
    "block_snippet",
    [
        ":::qrcode url=https://example.org width=3cm\n:::",
        ":::columns cols=2 ratio='1 1'\n:::raw\nA\n:::\n:::nextcol:::\n:::raw\nB\n:::\n:::endcolumns:::",
    ],
)
def test_key_aliases_remain_valid_syntax_without_op001(block_snippet):
    # Reine Completion-Aenderung: Alias-Schluessel bleiben gueltig, nur
    # nicht mehr vorgeschlagen (siehe test_completion_catalogs.py).
    text = build_document(block_snippet)
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP001" not in codes


def test_info_with_valid_type_is_allowed_without_op002():
    text = build_document(":::info type=warning\nAchtung.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP001" not in codes
    assert "OP002" not in codes


def test_info_with_invalid_type_emits_op002():
    text = build_document(":::info type=danger\nAchtung.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert "OP002" in codes


def test_task_title_option_is_allowed_without_op001():
    text = build_document(":::task title='Titel hier'\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_task_time_option_is_allowed_without_op001():
    text = build_document(":::task time=3\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_subtask_time_option_is_allowed_without_op001():
    text = build_document(
        ":::task\nOberaufgabe\n:::\n"
        ":::subtask time=2\nTeilaufgabe\n:::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_show_option_emits_deprecation_warning_op003():
    text = build_document(":::task show=worksheet\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP003" in codes
