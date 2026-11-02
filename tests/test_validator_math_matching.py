"""Validator: Zuordnung (MA001) und Formelschreibweise in Blöcken (MJ001).

Aus `test_blatt_validator.py` nach Themen aufgeteilt (300-Zeilen-Regel), Tests unverändert."""

from app.core.blatt_validator import inspect_markdown_text
from validator_doc_support import build_document


def test_matching_with_single_item_side_emits_ma001_warning():
    text = build_document(
        ":::matching\n"
        "left:\n"
        "  - Nur eins\n"
        "right:\n"
        "  - A\n"
        "  - B\n"
        "matches:\n"
        "  - '1-1'\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "MA001" in codes


def test_material_with_inline_math_syntax_emits_mj001_warning():
    text = build_document(":::material\nFormel: $x_i$\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "MJ001" in codes


def test_material_with_display_math_syntax_emits_mj001_warning():
    text = build_document(":::material\nFormel: $$\\frac{a}{b}$$\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "MJ001" in codes


def test_single_block_with_formula_emits_exactly_one_mj001():
    text = build_document(":::material\nFormel: $$\\frac{a}{b}$$\n:::")
    inspected = inspect_markdown_text(text)
    mj001_entries = [d for d in inspected.diagnostics if d.code == "MJ001"]
    assert len(mj001_entries) == 1
    assert "weitere Vorkommen" not in mj001_entries[0].message


def test_three_blocks_with_formula_collapse_to_one_mj001_with_count():
    text = build_document(
        ":::material\nFormel: $$a$$\n:::\n"
        ":::material\nFormel: $$b$$\n:::\n"
        ":::material\nFormel: $$c$$\n:::"
    )
    inspected = inspect_markdown_text(text)
    mj001_entries = [d for d in inspected.diagnostics if d.code == "MJ001"]
    assert len(mj001_entries) == 1
    assert "+2 weitere Vorkommen im Dokument" in mj001_entries[0].message
    assert mj001_entries[0].block_index == 0


def test_three_blocks_with_formula_and_another_diagnostic_leave_it_untouched():
    text = build_document(
        ":::material\nFormel: $$a$$\n:::\n"
        ":::material\nFormel: $$b$$\n:::\n"
        ":::material\nFormel: $$c$$\n:::\n"
        ":::keinbekannterblocktyp\nx\n:::"
    )
    inspected = inspect_markdown_text(text)
    codes = [d.code for d in inspected.diagnostics]
    assert codes.count("MJ001") == 1
    assert codes.count("BL001") == 1


def test_material_without_math_syntax_does_not_emit_mj001():
    text = build_document(":::material\nKein Formeltext hier.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "MJ001" not in codes


def test_material_with_currency_style_dollar_signs_does_not_emit_mj001():
    # The single unpaired "$" in a currency amount must not be
    # misrecognized as the start of a formula (see math_span_protection.py).
    text = build_document(":::material\nPreis: $5 und $10.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "MJ001" not in codes
