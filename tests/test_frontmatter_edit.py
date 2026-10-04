"""Tests für die gemeinsame Frontmatter-Edit-Engine (`app/core/frontmatter_edit.py`)."""

import pytest

from app.core.frontmatter import BOM
from app.core.frontmatter_edit import EditUnsafe, FrontmatterEditor


def _edit(text, *, remove=(), set_values=None):
    editor = FrontmatterEditor(text)
    for name in remove:
        editor.remove_key(name)
    for name, value in (set_values or {}).items():
        editor.set_scalar(name, value)
    return editor.result()


def test_set_existing_key_keeps_everything_else_byte_exact():
    text = "---\r\n# Kopf\r\nTitel: 'A'  # Kommentar\r\ndocument_type: slide_deck\r\nFach: M\r\n---\r\nBody\r\n"
    result = _edit(text, set_values={"document_type": "presentation"})
    assert result == text.replace("document_type: slide_deck", "document_type: presentation")


def test_insert_missing_key_as_first_line_with_open_line_ending():
    text = "---\r\nTitel: A\r\n---\r\nBody"
    assert _edit(text, set_values={"document_type": "exam"}) == "---\r\ndocument_type: exam\r\nTitel: A\r\n---\r\nBody"


def test_remove_key_with_inline_comment_and_quotes():
    text = '---\nTitel: A\nmode: "test" # alt\nFach: M\n---\nX'
    assert _edit(text, remove=["mode"]) == "---\nTitel: A\nFach: M\n---\nX"


def test_remove_key_respects_predicate():
    text = "---\nmode: worksheet\n---\n"
    editor = FrontmatterEditor(text)
    assert editor.remove_key("mode", when=lambda v: v in {"presentation", "test"}) is False
    assert editor.result() == text


def test_block_scalar_continuation_is_part_of_entry():
    text = "---\nmode: |\n  zeile1\n\n  zeile2\nFach: M\n---\nX"
    assert _edit(text, remove=["mode"]) == "---\nFach: M\n---\nX"


def test_body_mention_of_mode_stays_untouched():
    text = "---\nmode: test\n---\nmode: test im Text\n```\nmode: presentation\n```\n"
    result = _edit(text, remove=["mode"])
    assert result == "---\n---\nmode: test im Text\n```\nmode: presentation\n```\n"


def test_mode_inside_other_block_scalar_is_not_a_key():
    text = "---\nNotiz: |\n  mode: test\nFach: M\n---\n"
    editor = FrontmatterEditor(text)
    assert editor.remove_key("mode") is False
    assert editor.result() == text


def test_bom_and_missing_final_newline_preserved():
    text = BOM + "---\nTitel: A\n---\nOhne Schluss-Newline"
    result = _edit(text, set_values={"document_type": "worksheet"})
    assert result.startswith(BOM + "---\ndocument_type: worksheet\n")
    assert result.endswith("Ohne Schluss-Newline")


def test_mixed_line_endings_preserved_outside_edit():
    text = "---\nTitel: A\r\nmode: test\nFach: M\r\n---\r\nX\nY\r\n"
    assert _edit(text, remove=["mode"]) == "---\nTitel: A\r\nFach: M\r\n---\r\nX\nY\r\n"


@pytest.mark.parametrize(
    "text",
    [
        "---\na: 1\na: 2\n---\n",  # doppelter Schlüssel
        "---\na: 1\n# c\n\na: 2\n---\n",  # Duplikat hinter Kommentar/Leerzeile
        "---\n{a: 1, b: 2}\n---\n",  # Flow-Mapping
        "---\n- a\n- b\n---\n",  # Liste statt Mapping
        "---\n  eingerueckt: 1\n---\n",
        "---\nkaputt: [1\n---\n",  # YAML-Fehler
    ],
)
def test_unsafe_documents_raise(text):
    with pytest.raises(EditUnsafe):
        _edit(text, set_values={"document_type": "worksheet"})


def test_ensure_frontmatter_creates_block_before_content():
    editor = FrontmatterEditor("Text\r\nZeile\r\n")
    editor.ensure_frontmatter()
    editor.set_scalar("document_type", "kurzentwurf")
    assert editor.result() == "---\r\ndocument_type: kurzentwurf\r\n---\r\nText\r\nZeile\r\n"


def test_ensure_frontmatter_refuses_ambiguous_lenient_head():
    editor = FrontmatterEditor("\n---\nStundenthema: X\n---\n")
    with pytest.raises(EditUnsafe):
        editor.ensure_frontmatter()


def test_ensure_frontmatter_keeps_bom():
    editor = FrontmatterEditor(BOM + "Text")
    editor.ensure_frontmatter()
    editor.set_scalar("document_type", "kurzentwurf")
    assert editor.result() == BOM + "---\ndocument_type: kurzentwurf\n---\nText"


def test_set_scalar_rejects_values_needing_quotes():
    with pytest.raises(ValueError):
        FrontmatterEditor("---\n---\n").set_scalar("document_type", "a: b")


def test_unchanged_text_returns_original():
    text = "---\nA: 1\n---\n"
    assert FrontmatterEditor(text).result() == text


def test_set_then_remove_same_key():
    text = "---\nA: 1\n---\n"
    editor = FrontmatterEditor(text)
    editor.set_scalar("document_type", "exam")
    editor.remove_key("document_type")
    assert editor.result() == text
