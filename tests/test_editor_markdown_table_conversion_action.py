"""Editor-Aktion „Markdown-Tabellen umwandeln“ mit einem echten (unsichtbaren) Tk-Textfeld.

Geprüft wird das Verhalten, nicht die Aufrufe: unveränderter Text ohne Fund,
ein einziger Undo-Schritt bei Erfolg, unveränderter Text nach einem Fehler
mittendrin (die Undo-Klammer liefert `replace_editor_text` über bw-guis
`TextSurface.transact`).
"""

import tkinter as tk

import pytest
from bw_gui.testing.tk_root import create_tk_root

from app.ui.blatt_ui_editor import BlattwerkAppEditorMixin

_TABLE = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"


@pytest.fixture(scope="module")
def tk_root():
    root = create_tk_root()
    root.withdraw()
    yield root
    root.destroy()


class _StatusVar:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


class _Editor(BlattwerkAppEditorMixin):
    def __init__(self, root, text):
        self.editor_widget = tk.Text(root, undo=True)
        self.editor_widget.insert("1.0", text)
        self.editor_widget.edit_reset()
        self.status_var = _StatusVar()

    def text(self):
        return self.editor_widget.get("1.0", "end-1c")


@pytest.fixture
def dialogs(monkeypatch):
    calls = {"info": [], "warning": []}
    monkeypatch.setattr("app.ui.blatt_ui_editor_view.messagebox.showinfo", lambda title, message: calls["info"].append(message))
    monkeypatch.setattr("app.ui.blatt_ui_editor_view.messagebox.showwarning", lambda title, message: calls["warning"].append(message))
    return calls


def test_no_tables_leaves_document_untouched_and_shows_info(tk_root, dialogs):
    editor = _Editor(tk_root, "Nur Text, keine Tabelle.\n")
    editor._convert_markdown_tables_in_active_tab()

    assert editor.text() == "Nur Text, keine Tabelle.\n"
    assert len(dialogs["info"]) == 1 and dialogs["warning"] == []


def test_all_tables_skipped_leaves_document_untouched_and_shows_warning(tk_root, dialogs):
    # A header containing "," can never be safely represented in column_headers=,
    # so this table is a real find that gets skipped -- not "nothing found".
    text = "| A, B | C |\n| --- | --- |\n| x | y |\n"
    editor = _Editor(tk_root, text)
    editor._convert_markdown_tables_in_active_tab()

    assert editor.text() == text
    assert dialogs["info"] == [] and "übersprungen" in dialogs["warning"][0]


def test_successful_conversion_is_one_undo_step_and_updates_status(tk_root, dialogs):
    editor = _Editor(tk_root, "Vorher\n" + _TABLE)
    editor.editor_widget.insert("1.0", "getippt ")  # eigener Undo-Schritt davor

    editor._convert_markdown_tables_in_active_tab()

    assert ":::table" in editor.text()
    assert editor.status_var.value == "1 Markdown-Tabelle(n) umgewandelt."
    editor.editor_widget.edit_undo()
    assert editor.text() == "getippt Vorher\n" + _TABLE  # genau die Umwandlung, nicht das Getippte
    assert editor.editor_widget.cget("autoseparators") in (True, 1, "1")


def test_failure_midway_leaves_text_and_autoseparators_unchanged(tk_root, dialogs, monkeypatch):
    editor = _Editor(tk_root, _TABLE)

    def failing_insert(*_args):
        raise RuntimeError("boom")  # das delete davor ist schon gelaufen

    monkeypatch.setattr(editor.editor_widget, "insert", failing_insert)
    with pytest.raises(RuntimeError):
        editor._convert_markdown_tables_in_active_tab()

    assert editor.text() == _TABLE
    assert editor.editor_widget.cget("autoseparators") in (True, 1, "1")
