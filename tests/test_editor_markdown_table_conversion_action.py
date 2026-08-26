import pytest

from app.ui.blatt_ui_editor import BlattwerkAppEditorMixin


class _FakeStatusVar:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


class _FakeTextWidget:
    def __init__(self, text, raise_on_insert=False):
        self._text = text
        self._raise_on_insert = raise_on_insert
        self.delete_calls = []
        self.insert_calls = []
        self.configure_calls = []
        self.edit_separator_calls = 0
        self.yview_moveto_calls = []

    def get(self, start, end):
        assert (start, end) == ("1.0", "end-1c")
        return self._text

    def delete(self, start, end):
        self.delete_calls.append((start, end))
        self._text = ""

    def insert(self, pos, text):
        self.insert_calls.append((pos, text))
        if self._raise_on_insert:
            raise RuntimeError("boom")
        self._text = text

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)

    def edit_separator(self):
        self.edit_separator_calls += 1

    def yview(self):
        return (0.5, 1.0)

    def yview_moveto(self, fraction):
        self.yview_moveto_calls.append(fraction)


class _DummyEditor(BlattwerkAppEditorMixin):
    def __init__(self, text, raise_on_insert=False):
        self.editor_widget = _FakeTextWidget(text, raise_on_insert=raise_on_insert)
        self.status_var = _FakeStatusVar()


def test_no_tables_leaves_document_untouched_and_shows_info(monkeypatch):
    info_calls = []
    monkeypatch.setattr(
        "app.ui.blatt_ui_editor.messagebox.showinfo",
        lambda title, message: info_calls.append((title, message)),
    )
    warning_calls = []
    monkeypatch.setattr(
        "app.ui.blatt_ui_editor.messagebox.showwarning",
        lambda title, message: warning_calls.append((title, message)),
    )

    editor = _DummyEditor("Nur Text, keine Tabelle.\n")
    editor._convert_markdown_tables_in_active_tab()

    assert editor.editor_widget.delete_calls == []
    assert editor.editor_widget.insert_calls == []
    assert len(info_calls) == 1
    assert warning_calls == []


def test_all_tables_skipped_leaves_document_untouched_and_shows_warning(monkeypatch):
    info_calls = []
    monkeypatch.setattr(
        "app.ui.blatt_ui_editor.messagebox.showinfo",
        lambda title, message: info_calls.append((title, message)),
    )
    warning_calls = []
    monkeypatch.setattr(
        "app.ui.blatt_ui_editor.messagebox.showwarning",
        lambda title, message: warning_calls.append((title, message)),
    )

    # A header containing "," can never be safely represented in headers=,
    # so this table is a real find that gets skipped -- not "nothing found".
    text = "| A, B | C |\n| --- | --- |\n| x | y |\n"
    editor = _DummyEditor(text)
    editor._convert_markdown_tables_in_active_tab()

    assert editor.editor_widget.delete_calls == []
    assert editor.editor_widget.insert_calls == []
    assert info_calls == []
    assert len(warning_calls) == 1
    assert "übersprungen" in warning_calls[0][1]


def test_successful_conversion_is_a_single_undo_group_and_updates_status(monkeypatch):
    monkeypatch.setattr("app.ui.blatt_ui_editor.messagebox.showinfo", lambda *a, **k: None)
    monkeypatch.setattr("app.ui.blatt_ui_editor.messagebox.showwarning", lambda *a, **k: None)

    text = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    editor = _DummyEditor(text)
    editor._convert_markdown_tables_in_active_tab()

    widget = editor.editor_widget
    assert len(widget.delete_calls) == 1
    assert len(widget.insert_calls) == 1
    assert widget.configure_calls == [{"autoseparators": False}, {"autoseparators": True}]
    assert widget.edit_separator_calls == 1
    assert ":::table" in widget.insert_calls[0][1]
    assert editor.status_var.value == "1 Markdown-Tabelle(n) umgewandelt."
    assert widget.yview_moveto_calls == [0.5]


def test_autoseparators_restored_even_if_insert_raises(monkeypatch):
    monkeypatch.setattr("app.ui.blatt_ui_editor.messagebox.showinfo", lambda *a, **k: None)
    monkeypatch.setattr("app.ui.blatt_ui_editor.messagebox.showwarning", lambda *a, **k: None)

    text = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    editor = _DummyEditor(text, raise_on_insert=True)

    with pytest.raises(RuntimeError):
        editor._convert_markdown_tables_in_active_tab()

    assert editor.editor_widget.configure_calls == [{"autoseparators": False}, {"autoseparators": True}]
