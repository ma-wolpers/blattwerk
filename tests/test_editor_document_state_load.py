"""Real-Tk tests for the editor document-load state machine.

These use a genuine tkinter.Text widget (not a fake stand-in) because the
behavior under test is Tk-specific and cannot be reproduced by a mock:
Text.insert()/delete() silently no-op while state="disabled", a class-level
<Button-1> binding moves keyboard focus regardless of -state, and
root.focus_get()/focus_set() reflect real window-manager focus.
"""

from __future__ import annotations

import pytest

from app.ui.ui_constants import (
    EDITOR_DOCUMENT_LOADED,
    EDITOR_DOCUMENT_NOT_LOADED,
)
from editor_state_support import (  # noqa: F401  (fixtures are used by name)
    _RealEditor,
    _write,
    no_real_dialogs,
    tk_root,
)


# -- Befund 2: click on a disabled editor must not focus it -----------------


def test_click_on_disabled_editor_does_not_focus_it(tk_root):
    app = _RealEditor(tk_root)
    tk_root.update()

    app.editor_widget.event_generate("<Button-1>", x=5, y=5)
    tk_root.update()

    assert tk_root.focus_get() is not app.editor_widget


def test_click_on_loaded_editor_focuses_it(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    app._load_editor_content(_write(tmp_path, "a.md", "hello"))
    tk_root.update()

    app.editor_widget.event_generate("<Button-1>", x=5, y=5)
    tk_root.update()

    assert tk_root.focus_get() is app.editor_widget


# -- Befund 4: loading from NOT_LOADED must actually populate the widget ----


def test_load_from_not_loaded_fills_real_content_and_becomes_loaded(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    assert app.editor_widget.cget("state") == "disabled"

    path = _write(tmp_path, "doc.md", "hello from disk")
    app._load_editor_content(path)

    assert app._editor_document_state == EDITOR_DOCUMENT_LOADED
    assert app.editor_widget.get("1.0", "end-1c") == "hello from disk"
    assert app.editor_widget.cget("state") == "normal"
    assert app._editor_last_loaded_path == path


def test_editing_after_load_keeps_loaded_state(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    path = _write(tmp_path, "doc.md", "original")
    app._load_editor_content(path)

    app.editor_widget.insert("end", " plus unsaved typing")

    assert app._editor_document_state == EDITOR_DOCUMENT_LOADED
    assert str(app.editor_widget.cget("state")) == "normal"


# -- _editor_widget_unlocked_for_mutation: self-contained exception safety --


def test_unlocked_for_mutation_restores_state_and_loading_content_on_success(tk_root):
    app = _RealEditor(tk_root)
    app.editor_widget.configure(state="disabled")
    app._editor_loading_content = False

    with app._editor_widget_unlocked_for_mutation():
        assert str(app.editor_widget.cget("state")) == "normal"
        assert app._editor_loading_content is True

    assert str(app.editor_widget.cget("state")) == "disabled"
    assert app._editor_loading_content is False


def test_unlocked_for_mutation_restores_state_and_loading_content_on_exception(tk_root):
    app = _RealEditor(tk_root)
    app.editor_widget.configure(state="disabled")
    app._editor_loading_content = False

    with pytest.raises(RuntimeError):
        with app._editor_widget_unlocked_for_mutation():
            raise RuntimeError("boom")

    assert str(app.editor_widget.cget("state")) == "disabled"
    assert app._editor_loading_content is False


# -- Fix Teil 0: focus eviction only on the NOT_LOADED transition -----------


def test_not_loaded_transition_evicts_existing_focus(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    app._load_editor_content(_write(tmp_path, "a.md", "x"))
    app.editor_widget.focus_set()
    tk_root.update()
    assert tk_root.focus_get() is app.editor_widget

    app._reset_editor_widget_to_empty()
    tk_root.update()

    assert tk_root.focus_get() is not app.editor_widget
    assert app.editor_widget.get("1.0", "end-1c") == ""
    assert app._editor_document_state == EDITOR_DOCUMENT_NOT_LOADED


def test_different_document_load_failure_clears_editor_and_evicts_focus(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    app._load_editor_content(_write(tmp_path, "a.md", "A content"))
    app.editor_widget.focus_set()
    tk_root.update()

    missing = tmp_path / "does-not-exist.md"
    app._load_editor_content(missing)
    tk_root.update()

    assert app._editor_document_state == EDITOR_DOCUMENT_NOT_LOADED
    assert app.editor_widget.get("1.0", "end-1c") == ""
    assert app._editor_last_loaded_path is None
    assert tk_root.focus_get() is not app.editor_widget


def test_same_document_resync_success_keeps_focus(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    path = _write(tmp_path, "a.md", "A content")
    app._load_editor_content(path)
    app.editor_widget.focus_set()
    tk_root.update()

    app._load_editor_content(path)
    tk_root.update()

    assert app._editor_document_state == EDITOR_DOCUMENT_LOADED
    assert tk_root.focus_get() is app.editor_widget


def test_same_document_read_failure_keeps_focus_and_content(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    path = _write(tmp_path, "a.md", "A content")
    app._load_editor_content(path)
    app.editor_widget.focus_set()
    tk_root.update()

    path.unlink()
    app._load_editor_content(path)
    tk_root.update()

    assert app._editor_document_state == EDITOR_DOCUMENT_LOADED
    assert app.editor_widget.get("1.0", "end-1c") == "A content"
    assert tk_root.focus_get() is app.editor_widget


def test_same_document_phase_a_internal_failure_evicts_focus_and_clears(tmp_path, tk_root, monkeypatch):
    app = _RealEditor(tk_root)
    path = _write(tmp_path, "a.md", "A content")
    app._load_editor_content(path)
    app.editor_widget.focus_set()
    tk_root.update()

    def boom(_input_path):
        raise OSError("simulated stat failure after successful read")

    monkeypatch.setattr(app, "_get_editor_source_snapshot", boom)

    with pytest.raises(OSError):
        app._load_editor_content(path)
    tk_root.update()

    # Deliberately NOT a special case (see plan): a Phase-A-internal failure,
    # even for a same-document re-sync, resets exactly like an A-to-B failure.
    assert app._editor_document_state == EDITOR_DOCUMENT_NOT_LOADED
    assert app.editor_widget.get("1.0", "end-1c") == ""
    assert tk_root.focus_get() is not app.editor_widget


# -- Phase A exception (generic) ---------------------------------------------
