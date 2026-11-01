"""Multi-Cursor im Blattwerk-Editor: Tasten, Marker je Region, Änderungs-Pipeline (echtes Tk).

Die Gesten und Regeln selbst testet bw-gui (`tests/test_multicursor.py`); hier steht, was
Blattwerk dazugibt. Nur synthetische Dokumente.
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import on_text_modified
from bw_gui.testing.keys import press_key

from app.ui.blatt_ui_editor_completion_popup import BlattwerkAppEditorCompletionPopupMixin
from editor_state_support import _RealEditor, _write, no_real_dialogs, tk_root  # noqa: F401  (fixtures)

CTRL, ALT = 0x4, 0x20000
BUTTON1 = 0x100


class _Editor(_RealEditor, BlattwerkAppEditorCompletionPopupMixin):
    """Stand-in mit echtem Controller, echten Editor-Tasten und echter Vervollständigung."""

    def __init__(self, root):
        super().__init__(root)
        self._attach_editor_multicursor()
        self._editor_completion_items = []
        self._editor_save_after_id = None
        self._editor_save_delay_ms = 600000
        self._bind_editor_keys()

    def _toggle_editor_find_bar(self, _event=None):
        pass

    def _toggle_editor_replace_bar(self, _event=None):
        pass

    def _queue_editor_auto_preview_refresh(self):
        pass

    def _save_editor_content(self):
        pass


def _open(root, tmp_path, content):
    app = _Editor(root)
    app._load_editor_content(_write(tmp_path, "doc.abw", content))
    root.update()
    return app


def _value(app):
    return app.editor_widget.get("1.0", "end-1c")


def _click(app, index, state=CTRL):
    text = app.editor_widget
    x, y, _w, height = text.bbox(index)
    text.event_generate("<ButtonPress-1>", x=x + 1, y=y + height // 2, state=state)
    text.event_generate("<ButtonRelease-1>", x=x + 1, y=y + height // 2, state=state | BUTTON1)
    text.update()


def _select_two(app):
    """Zwei Auswahlen: `foo` in Zeile 1 und `bar` in Zeile 2."""
    text = app.editor_widget
    text.tag_add("sel", "1.0", "1.3")
    text.mark_set("insert", "1.3")
    x1, y1, _w, h = text.bbox("2.0")
    x2, y2, _w, h = text.bbox("2.3")
    text.event_generate("<ButtonPress-1>", x=x1 + 1, y=y1 + h // 2, state=CTRL)
    text.event_generate("<B1-Motion>", x=x2 + 1, y=y2 + h // 2, state=CTRL | BUTTON1)
    text.event_generate("<ButtonRelease-1>", x=x2 + 1, y=y2 + h // 2, state=CTRL | BUTTON1)
    text.update()


def test_ctrl_click_works_only_with_a_loaded_document(tmp_path, tk_root):
    app = _Editor(tk_root)
    tk_root.update()
    app.editor_widget.event_generate("<ButtonPress-1>", x=5, y=5, state=CTRL)
    app.editor_widget.event_generate("<ButtonRelease-1>", x=5, y=5, state=CTRL | BUTTON1)
    assert not app._editor_multicursor_active()
    app._load_editor_content(_write(tmp_path, "doc.abw", "aaa\nbbb\n"))
    tk_root.update()
    app.editor_widget.mark_set("insert", "1.0")
    _click(app, "2.0")
    assert app._editor_multicursor_active()


def test_ctrl_alt_arrows_add_cursors_from_the_key_registry(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "abc\nabc\nabc\n")
    app.editor_widget.mark_set("insert", "2.1")
    assert press_key(app.editor_widget, "Down", state=CTRL | ALT) is True
    assert press_key(app.editor_widget, "Up", state=CTRL | ALT) is True
    press_key(app.editor_widget, "x", char="x")
    assert _value(app) == "axbc\naxbc\naxbc\n"


def test_escape_ends_the_mode_before_it_leaves_the_editor(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "aaa\nbbb\n")
    app.editor_widget.mark_set("insert", "1.0")
    _click(app, "2.0")
    app.editor_widget.focus_force()
    tk_root.update()
    assert press_key(app.editor_widget, "Escape") is True
    assert not app._editor_multicursor_active()
    assert tk_root.focus_get() is app.editor_widget
    press_key(app.editor_widget, "Escape")
    assert tk_root.focus_get() is not app.editor_widget


def test_completion_stays_closed_in_the_mode(tmp_path, tk_root, monkeypatch):
    app = _open(tk_root, tmp_path, "aaa\nbbb\n")
    app.editor_widget.mark_set("insert", "1.0")
    _click(app, "2.0")
    calls = []
    monkeypatch.setattr(app, "_collect_expectation_kind_completion_context", lambda *a, **k: calls.append(1), raising=False)
    press_key(app.editor_widget, "space", state=CTRL)
    app._open_editor_completion(auto=False)
    assert calls == []


def test_marker_key_marks_every_selection_as_one_undo_step(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "foo eins\nbar zwei\n")
    _select_two(app)
    assert press_key(app.editor_widget, "asterisk", char="*") is True
    assert _value(app) == "*foo* eins\n*bar* zwei\n"
    assert [(r.start, r.end) for r in app.editor_multicursor.regions] == [(1, 4), (12, 15)]
    press_key(app.editor_widget, "z", state=CTRL)
    assert _value(app) == "foo eins\nbar zwei\n" and app._editor_multicursor_active()


def test_marker_key_mixed_marks_selections_and_types_at_carets(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "foo eins\nbar zwei\n")
    app.editor_widget.tag_add("sel", "1.0", "1.3")
    app.editor_widget.mark_set("insert", "1.3")
    _click(app, "2.3")
    press_key(app.editor_widget, "underscore", char="_")
    assert _value(app) == "_foo_ eins\nbar_ zwei\n"


def test_marker_key_at_carets_only_is_plain_typing(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "aaa\nbbb\n")
    app.editor_widget.mark_set("insert", "1.0")
    _click(app, "2.0")
    press_key(app.editor_widget, "asterisk", char="*")
    assert _value(app) == "*aaa\n*bbb\n"


def test_marker_crossing_a_formula_refuses_the_whole_action(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "a $x$ b\nbar zwei\n")
    app.editor_widget.tag_add("sel", "1.0", "1.3")
    app.editor_widget.mark_set("insert", "1.3")
    _click(app, "2.0")
    press_key(app.editor_widget, "asterisk", char="*")
    assert _value(app) == "a $x$ b\nbar zwei\n"
    assert "Formel" in app.status_var.get()


def test_percent_comments_full_lines_per_selection(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "foo eins\nbar zwei\n")
    _select_two(app)
    press_key(app.editor_widget, "percent", char="%")
    assert _value(app) == "%%foo%% eins\n%%bar%% zwei\n"


def test_word_deletion_works_at_every_cursor(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "foo eins\nbar zwei\n")
    app.editor_widget.mark_set("insert", "1.8")
    _click(app, "2.8")
    press_key(app.editor_widget, "BackSpace", state=CTRL)
    assert _value(app) == "foo \nbar \n"
    press_key(app.editor_widget, "BackSpace", state=CTRL)
    assert _value(app) == "\n\n"


def test_word_deletion_forward_at_every_cursor(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "foo eins\nbar zwei\n")
    app.editor_widget.mark_set("insert", "1.0")
    _click(app, "2.0")
    press_key(app.editor_widget, "Delete", state=CTRL)
    assert _value(app) == " eins\n zwei\n"


def test_word_deletion_with_one_cursor_is_unchanged(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "foo eins\n\nzwei")
    text = app.editor_widget
    text.mark_set("insert", "1.8")
    press_key(text, "BackSpace", state=CTRL)
    assert _value(app) == "foo \n\nzwei"
    text.mark_set("insert", "3.0")
    press_key(text, "BackSpace", state=CTRL)
    assert _value(app) == "foo \nzwei"
    text.mark_set("insert", "1.4")
    press_key(text, "Delete", state=CTRL)
    assert _value(app) == "foo zwei"
    text.mark_set("insert", "1.0")
    press_key(text, "BackSpace", state=CTRL)
    assert _value(app) == "foo zwei"


def test_one_transaction_runs_the_change_pipeline_once_with_the_final_text(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "aaa\nbbb\nccc\n")
    seen = []
    app.editor_widget.mark_set("insert", "1.0")
    _click(app, "2.0")
    _click(app, "3.0")
    on_text_modified(app.editor_widget, lambda _w: (seen.append(_value(app)), app._on_editor_modified()))
    tk_root.update()
    app.highlighting_calls = app.diagnostics_calls = app.outline_calls = 0
    press_key(app.editor_widget, "x", char="x")
    tk_root.update()
    assert seen == ["xaaa\nxbbb\nxccc\n"]
    assert (app.highlighting_calls, app.diagnostics_calls, app.outline_calls) == (1, 1, 1)
    assert app._editor_has_unsaved_changes


def test_foreign_change_through_the_pipeline_ends_the_mode(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "aaa\nbbb\n")
    on_text_modified(app.editor_widget, lambda _w: app._on_editor_modified())
    app.editor_widget.mark_set("insert", "1.0")
    _click(app, "2.0")
    app._insert_editor_snippet("X")
    tk_root.update()
    assert not app._editor_multicursor_active()


def test_shift_enter_writes_at_every_cursor(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "ab\ncd\n")
    app.editor_widget.mark_set("insert", "1.1")
    _click(app, "2.1")
    press_key(app.editor_widget, "Return", state=0x1)
    assert _value(app) == "a\nb\nc\nd\n"


def test_loading_another_document_ends_the_mode_and_clears_cursor_history(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "aaa\nbbb\n")
    app.editor_widget.mark_set("insert", "1.0")
    _click(app, "2.0")
    press_key(app.editor_widget, "x", char="x")
    app._load_editor_content(_write(tmp_path, "other.abw", "anderer Text"))
    assert not app._editor_multicursor_active()
    press_key(app.editor_widget, "z", state=CTRL)
    assert _value(app) == "anderer Text" and not app._editor_multicursor_active()


def test_shared_keys_reach_the_controller_in_the_mode(tmp_path, tk_root):
    app = _open(tk_root, tmp_path, "abc\nabc\nabc\n")
    text = app.editor_widget
    text.mark_set("insert", "1.1")
    _click(app, "2.1")
    assert press_key(text, "Down") is True
    assert [text.index(f"1.0 + {r.head} chars") for r in app.editor_multicursor.regions] == ["2.1", "3.1"]
    assert press_key(text, "Up") is True
    press_key(text, "Tab")
    press_key(text, "Return")
    assert _value(app) == "a\t\nbc\na\t\nbc\nabc\n"
