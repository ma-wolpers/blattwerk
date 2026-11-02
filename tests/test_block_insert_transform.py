"""`plan_block_insert`: Block am Cursor, um eine Markierung, als Spalten (nur synthetische Texte).

Jedes erfolgreiche Ergebnis läuft zusätzlich durch den echten Validator: Die
Umwandlung darf keine Strukturfehler (`BL*`) erzeugen.
"""

from __future__ import annotations

import pytest

from app.core.blatt_validator import inspect_markdown_text
from app.core.block_insert_snippets import BLOCK_INSERT_SNIPPETS, IMAGE_INSERT_SNIPPET
from app.core.block_insert_transform import BlockInsertError, plan_block_insert

_FRONTMATTER = "---\nTitel: T\nFach: M\nThema: X\n---\n"


def _run(document, selection, block_type):
    """Wendet das Einfügen an. `selection` ist `(start, end)` oder ein markierter Teiltext (erstes Vorkommen)."""
    if isinstance(selection, str):
        start = document.index(selection)
        selection = (start, start + len(selection))
    snippet = IMAGE_INSERT_SNIPPET if block_type is None else BLOCK_INSERT_SNIPPETS[block_type]
    edit = plan_block_insert(document, *selection, snippet, block_type)
    result = document[: edit.start] + edit.text + document[edit.end :]
    return result, edit.start + edit.cursor, edit.note


def _structure_errors(document):
    codes = {d.code for d in inspect_markdown_text(_FRONTMATTER + document).diagnostics if d.severity == "error"}
    return {code for code in codes if code.startswith("BL")}


# -- ohne Markierung ---------------------------------------------------------------

def test_cursor_in_empty_document_puts_cursor_into_the_content():
    result, cursor, _note = _run("", (0, 0), "task")
    assert result == BLOCK_INSERT_SNIPPETS["task"].replace("[[CURSOR]]", "").rstrip("\n")
    assert result[cursor:].startswith("Aufgabentext")


def test_cursor_in_the_middle_of_a_line_splits_it():
    result, _cursor, _note = _run("vorher nachher", (6, 6), "info")
    assert result == "vorher\n:::info type=note\nHinweis hier…\n:::\nnachher"
    assert not _structure_errors(result)


def test_cursor_at_start_of_a_header_and_after_a_closing_line_is_allowed():
    document = ":::info\nA\n:::"
    before, _c, _n = _run(document, (0, 0), "task")
    after, _c, _n = _run(document, (len(document), len(document)), "task")
    assert before.endswith("\n:::info\nA\n:::") and after.startswith(":::info\nA\n:::\n:::task")


@pytest.mark.parametrize("document, offset, message", [
    (":::info\nA\n:::", 9, "im Block `:::info`"),
    (":::info\nA", 9, "nicht geschlossen"),
    ("---\nTitel: T\n---\nText", 6, "Frontmatter"),
])
def test_cursor_where_no_block_may_start(document, offset, message):
    with pytest.raises(BlockInsertError, match=message):
        _run(document, (offset, offset), "task")


# -- mit Markierung ------------------------------------------------------------------

def test_selection_becomes_the_content_and_cursor_lands_in_it():
    result, cursor, _note = _run("Hallo Welt\n", "Hallo Welt", "info")
    assert result == ":::info type=note\nHallo Welt\n:::\n"
    assert result[cursor:].startswith("Hallo Welt")


def test_word_in_the_middle_of_a_line_gets_its_own_block():
    result, _cursor, _note = _run("a Wort b", "Wort", "solution")
    assert result == "a\n:::solution\nWort\n:::\nb"


def test_selection_is_split_at_separators_which_stay_outside():
    document = "A\n--\nB\n--!\nC"
    result, _cursor, _note = _run(document, (0, len(document)), "material")
    header = BLOCK_INSERT_SNIPPETS["material"].split("\n")[0]
    assert result == f"{header}\nA\n:::\n--\n{header}\nB\n:::\n--!\n{header}\nC\n:::"
    assert not _structure_errors(result)


def test_selected_blocks_only_get_a_new_header_with_valid_options():
    document = ":::task points=2 title=X\nEins\n:::\n\n:::task points=1\nZwei\n:::"
    result, cursor, note = _run(document, (0, len(document)), "info")
    assert result == ":::info\nEins\n:::\n\n:::info\nZwei\n:::"
    assert result[cursor:].startswith("Eins")
    assert "points=2" in note and "title=X" in note and "`:::info`" in note


def test_text_and_blocks_mixed():
    document = "Einleitung\n:::info\nA\n:::"
    result, _cursor, _note = _run(document, (0, len(document)), "solution")
    assert result == ":::solution\nEinleitung\n:::\n:::solution\nA\n:::"


def test_selection_up_to_the_next_line_start_ends_at_the_line_end():
    result, _cursor, _note = _run("Zeile\nRest", (0, 6), "info")
    assert result == ":::info type=note\nZeile\n:::\nRest"


@pytest.mark.parametrize("document, selection, block_type, message", [
    (":::info\nAbc\n:::", "Abc", "task", "im Block"),
    ("Text\n:::info\nAbc\n:::", "Text\n:::info\nA", "task", "schneidet"),
    ("Text", "Text", "evaluation", "keinen Inhalt"),
    ("Text", "Text", None, "Bild"),
    ("---\nTitel: T\n---\nText", "T\n---\nText", "task", "Frontmatter"),
])
def test_selection_errors(document, selection, block_type, message):
    with pytest.raises(BlockInsertError, match=message):
        _run(document, selection, block_type)


# -- Spalten -------------------------------------------------------------------------

def test_one_part_goes_into_the_first_of_two_columns():
    result, cursor, _note = _run("Text", "Text", "columns")
    assert result == ':::columns cols=2 widths="1 1" :::\nText\n:::nextcol :::\n\n:::endcolumns :::'
    assert result[cursor:].startswith("Text")
    assert not _structure_errors(result)


def test_double_dash_parts_become_columns_and_unfitting_widths_are_dropped():
    document = "A\n--\n:::info\nB\n:::\n--\nC"
    result, _cursor, _note = _run(document, (0, len(document)), "columns")
    assert result == ":::columns cols=3 :::\nA\n:::nextcol :::\n:::info\nB\n:::\n:::nextcol :::\nC\n:::endcolumns :::"
    assert not _structure_errors(result)


@pytest.mark.parametrize("document, selection, message", [
    ("\n--\n".join("ABCDEFG"), None, "höchstens 6"),
    ("A\n--!\nB", None, "--!"),
    (":::columns :::\nA\n:::nextcol :::\nB\n:::endcolumns :::", "A", "Spaltenbereich"),
])
def test_columns_errors(document, selection, message):
    with pytest.raises(BlockInsertError, match=message):
        _run(document, selection or (0, len(document)), "columns")


def test_cursor_inside_columns_cannot_open_columns_but_other_blocks_can():
    document = ":::columns :::\nA\n:::nextcol :::\nB\n:::endcolumns :::"
    offset = document.index("A")
    with pytest.raises(BlockInsertError, match="Spaltenbereich"):
        _run(document, (offset, offset), "columns")
    result, _cursor, _note = _run(document, (offset, offset), "task")
    assert not _structure_errors(result)
