"""Validator: Spaltenstruktur `columns`/`nextcol`/`endcolumns` (BL007 bis BL011).

Aus `test_blatt_validator.py` nach Themen aufgeteilt (300-Zeilen-Regel), Tests unverändert."""

from app.core.blatt_validator import inspect_markdown_text
from validator_doc_support import build_document


def test_nextcol_outside_open_columns_emits_bl007_error():
    text = build_document(":::nextcol:::")
    inspected = inspect_markdown_text(text)
    bl007 = [d for d in inspected.diagnostics if d.code == "BL007"]

    assert bl007
    assert bl007[0].severity == "error"


def test_endcolumns_without_open_columns_emits_bl008_error():
    text = build_document(":::endcolumns:::")
    inspected = inspect_markdown_text(text)
    bl008 = [d for d in inspected.diagnostics if d.code == "BL008"]

    assert bl008
    assert bl008[0].severity == "error"


def test_unclosed_columns_block_emits_bl009_error():
    text = build_document(":::columns cols=2 :::\n:::raw\nA\n:::")
    inspected = inspect_markdown_text(text)
    bl009 = [d for d in inspected.diagnostics if d.code == "BL009"]

    assert bl009
    assert bl009[0].severity == "error"


def test_nested_columns_block_emits_exactly_one_bl010_and_nothing_else():
    text = build_document(
        ":::columns cols=2 :::\n:::columns cols=2 :::\n:::endcolumns:::\n:::endcolumns:::"
    )
    inspected = inspect_markdown_text(text)
    columns_codes = [
        d.code for d in inspected.diagnostics if d.code in {"BL007", "BL008", "BL009", "BL010", "BL011"}
    ]

    assert columns_codes == ["BL010"]


def test_columns_with_wrong_nextcol_count_emits_bl011_warning():
    text = build_document(":::columns cols=3 :::\n:::nextcol:::\n:::endcolumns:::")
    inspected = inspect_markdown_text(text)
    bl011 = [d for d in inspected.diagnostics if d.code == "BL011"]

    assert bl011
    assert bl011[0].severity == "warning"


def test_columns_with_correct_nextcol_count_has_no_bl0xx_diagnostics():
    text = build_document(
        ":::columns cols=2 widths='1 1' :::\n:::raw\nA\n:::\n"
        ":::nextcol:::\n:::raw\nB\n:::\n:::endcolumns:::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}

    assert not (codes & {"BL007", "BL008", "BL009", "BL010", "BL011"})


def test_columns_across_pagebreak_does_not_falsely_trigger_bl010():
    # Jede Folie hat ihren eigenen columns/endcolumns-Scope (siehe
    # _build_presentation_slides); ein pagebreak resettet den Scope, statt
    # eine fehlerhafte Verschachtelung mit der naechsten Folie zu erzeugen.
    text = build_document(
        ":::columns cols=2 :::\n:::pagebreak:::\n"
        ":::columns cols=2 :::\n:::nextcol:::\n:::endcolumns:::"
    )
    inspected = inspect_markdown_text(text)
    bl010 = [d for d in inspected.diagnostics if d.code == "BL010"]
    bl009 = [d for d in inspected.diagnostics if d.code == "BL009"]

    assert not bl010
    assert bl009  # die erste, nie geschlossene columns wird trotzdem gemeldet


def test_columns_recovery_nested_then_both_closed_emits_only_bl010():
    text = build_document(
        ":::columns:::\n:::columns:::\n:::endcolumns:::\n:::endcolumns:::"
    )
    inspected = inspect_markdown_text(text)
    columns_codes = [
        d.code for d in inspected.diagnostics if d.code in {"BL007", "BL008", "BL009", "BL010", "BL011"}
    ]

    assert columns_codes == ["BL010"]


def test_columns_recovery_nextcol_after_close_emits_bl011_and_bl007():
    text = build_document(
        ":::columns cols=3 :::\n:::nextcol:::\n:::endcolumns:::\n:::nextcol:::"
    )
    inspected = inspect_markdown_text(text)
    columns_codes = [
        d.code for d in inspected.diagnostics if d.code in {"BL007", "BL008", "BL009", "BL010", "BL011"}
    ]

    assert columns_codes == ["BL011", "BL007"]


def test_columns_recovery_pagebreak_then_orphan_endcolumns_emits_bl009_and_bl008():
    text = build_document(":::columns:::\n:::pagebreak:::\n:::endcolumns:::")
    inspected = inspect_markdown_text(text)
    columns_codes = [
        d.code for d in inspected.diagnostics if d.code in {"BL007", "BL008", "BL009", "BL010", "BL011"}
    ]

    assert columns_codes == ["BL009", "BL008"]
