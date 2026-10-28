"""`%`-Taste im Editor: Auswahl aus-/einkommentieren (`%%…%%`), mehrzeilig je Zeile.

Reine Logik über `apply_percent_marker`; das Erweitern auf ganze Zeilen und
das Anwenden im Widget mit einem echten (unsichtbaren) Tk-Textfeld.
"""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.blatt_ui_editor_keys import BlattwerkAppEditorKeysMixin
from app.ui.editor_marker_shortcuts import apply_percent_marker


def _apply(before, selected, after, is_multiline=False):
    edit = apply_percent_marker(before, selected, after, is_multiline)
    head = before[: len(before) - edit.strip_left] if edit.strip_left else before
    tail = after[edit.strip_right:]
    return head + edit.replacement + tail, edit.replacement[edit.select_start:edit.select_end]


def test_single_line_wraps_like_highlight():
    assert _apply("Text ", "Notiz", " weiter") == ("Text %%Notiz%% weiter", "Notiz")


def test_second_press_removes_the_comment_again():
    assert _apply("Text %%", "Notiz", "%% weiter") == ("Text Notiz weiter", "Notiz")


def test_multi_line_toggles_each_line_and_keeps_indent_and_blank_lines():
    text, selected = _apply("", "  a\n%%b%%\n\n   %%c%%  \nd", "", is_multiline=True)

    assert text == "  %%a%%\nb\n\n   c  \n%%d%%"
    assert selected == text


def test_multi_line_toggle_twice_restores_the_source():
    source = "  a\nb\n\nc"
    once, _ = _apply("", source, "", is_multiline=True)
    twice, _ = _apply("", once, "", is_multiline=True)

    assert twice == source


def test_line_with_two_comments_is_not_a_whole_line_comment():
    text, _ = _apply("", "%%a%% Text %%b%%\nx", "", is_multiline=True)

    assert text.split("\n")[0] == "%%%%a%% Text %%b%%%%"


@pytest.fixture(scope="module")
def tk_root():
    """Ein unsichtbares Tk-Fenster für das ganze Modul."""
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"no Tk display available: {error}")
    root.withdraw()
    yield root
    root.destroy()


class _Var:
    def __init__(self):
        self.value = ""

    def set(self, value):
        self.value = value


class _Editor(BlattwerkAppEditorKeysMixin):
    def __init__(self, root, text):
        self.editor_widget = tk.Text(root)
        self.editor_widget.insert("1.0", text)
        self.status_var = _Var()

    def _queue_editor_highlighting(self, immediate=False):
        pass

    _queue_editor_diagnostics = _queue_editor_highlighting
    _queue_editor_outline = _queue_editor_highlighting


def test_partial_multi_line_selection_comments_whole_lines(tk_root):
    editor = _Editor(tk_root, "erste Zeile\nzweite Zeile\ndritte Zeile")
    editor.editor_widget.tag_add("sel", "1.3", "2.4")

    editor._on_editor_percent_key()

    assert editor.editor_widget.get("1.0", "end-1c") == "%%erste Zeile%%\n%%zweite Zeile%%\ndritte Zeile"


def test_selection_ending_at_line_start_excludes_that_line(tk_root):
    editor = _Editor(tk_root, "a\nb\nc")
    editor.editor_widget.tag_add("sel", "1.0", "3.0")

    editor._on_editor_percent_key()

    assert editor.editor_widget.get("1.0", "end-1c") == "%%a%%\n%%b%%\nc"


def test_without_selection_percent_is_typed_normally(tk_root):
    editor = _Editor(tk_root, "a")

    assert editor._on_editor_percent_key() is None
