"""Block einfügen im echten Editor: Cursor, Markierung, ein Undo-Schritt, Fehler ohne Änderung.

Die Regeln selbst prüft `test_block_insert_transform.py`; hier nur die
Anbindung an das Tk-Textfeld (`_insert_block_from_menu`). Nur synthetische Inhalte.
"""

from __future__ import annotations

import pytest
from bw_gui.testing.tk_root import create_tk_root

from app.core.block_insert_snippets import BLOCK_INSERT_SNIPPETS
from app.ui.blatt_ui_editor_multicursor import MATH_CROSSING_MESSAGE
from editor_state_support import _RealEditor, _write, no_real_dialogs  # noqa: F401  (fixture)


@pytest.fixture(scope="module")
def tk_root():
    """Ein unsichtbarer Interpreter für die ganze Datei (viele `Tk()` hintereinander stolpern
    sporadisch über `init.tcl`; Fokus wird hier nicht geprüft)."""
    root = create_tk_root()
    root.withdraw()
    yield root
    root.destroy()


class _Editor(_RealEditor):
    def __init__(self, root):
        super().__init__(root)
        self.editor_multicursor = None


def _open(root, tmp_path, content):
    app = _Editor(root)
    app._load_editor_content(_write(tmp_path, "doc.abw", content))
    root.update()
    return app


def _value(app):
    return app.editor_widget.get("1.0", "end-1c")


def _select(app, first, last):
    app.editor_widget.tag_add("sel", first, last)


def test_cursor_insert_lands_in_the_content(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "vorher nachher\n")
    app.editor_widget.mark_set("insert", "1.6")
    before = (app.highlighting_calls, app.diagnostics_calls, app.outline_calls)

    app._insert_block_from_menu(BLOCK_INSERT_SNIPPETS["info"], "info")

    assert _value(app) == "vorher\n:::info type=note\nHinweis hier…\n:::\nnachher\n"
    assert app.editor_widget.index("insert") == "3.0"
    after = (app.highlighting_calls, app.diagnostics_calls, app.outline_calls)
    assert [b - a for a, b in zip(before, after)] == [1, 1, 1]


def test_selection_becomes_content_and_one_undo_restores_everything(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "Hallo Welt\n--\nZweiter Teil\n")
    _select(app, "1.0", "3.end")

    app._insert_block_from_menu(BLOCK_INSERT_SNIPPETS["solution"], "solution")

    assert _value(app) == ":::solution\nHallo Welt\n:::\n--\n:::solution\nZweiter Teil\n:::\n"
    assert not app.editor_widget.tag_ranges("sel")
    app.editor_widget.edit_undo()
    assert _value(app) == "Hallo Welt\n--\nZweiter Teil\n"


def test_header_swap_reports_dropped_options(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, ":::task points=2\nA\n:::\n")
    _select(app, "1.0", "3.end")

    app._insert_block_from_menu(BLOCK_INSERT_SNIPPETS["info"], "info")

    assert _value(app) == ":::info\nA\n:::\n"
    assert "points=2" in app.status_var.get()


def test_error_leaves_the_text_untouched_and_explains(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, ":::info\nA\n:::\n")
    app.editor_widget.mark_set("insert", "2.1")

    app._insert_block_from_menu(BLOCK_INSERT_SNIPPETS["task"], "task")

    assert _value(app) == ":::info\nA\n:::\n"
    assert "verschachteln" in app.status_var.get()


def test_selection_across_a_formula_is_refused_like_the_marker_keys(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "Text $a+b$ Ende\n")
    _select(app, "1.0", "1.7")

    app._insert_block_from_menu(BLOCK_INSERT_SNIPPETS["info"], "info")

    assert _value(app) == "Text $a+b$ Ende\n"
    assert app.status_var.get() == MATH_CROSSING_MESSAGE
