"""Real-Tk tests for the editor document-load state machine: recovery, baselines, snapshots.

Split out of ``test_editor_document_state_load.py`` (300-Zeilen-Regel); fixtures and the
editor double live in ``editor_state_support.py``.
"""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.blatt_ui_persistence import BlattwerkAppPersistenceMixin
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


def test_phase_a_exception_recovers_to_not_loaded_and_propagates(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    path = _write(tmp_path, "b.md", "B content")

    original_delete = app.editor_widget.delete
    calls = {"n": 0}

    def flaky_delete(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated mutation failure")
        return original_delete(*args, **kwargs)

    app.editor_widget.delete = flaky_delete

    with pytest.raises(RuntimeError):
        app._load_editor_content(path)
    tk_root.update()

    assert app._editor_document_state == EDITOR_DOCUMENT_NOT_LOADED
    assert str(app.editor_widget.cget("state")) == "disabled"
    assert app._editor_last_loaded_path is None


# -- Fix Teil 2: baselines belong to the newly loaded document --------------


def test_successful_load_baselines_belong_to_new_document(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    app._load_editor_content(_write(tmp_path, "a.md", ":::info\nA\n:::"))
    a_snapshot_path = app._editor_last_known_source_path

    path_b = _write(tmp_path, "b.md", ":::info\nB\n:::\n:::info\nmore\n:::")
    app._load_editor_content(path_b)

    assert app._editor_document_state == EDITOR_DOCUMENT_LOADED
    assert app._editor_last_loaded_path == path_b
    assert app._editor_last_known_source_path == path_b
    assert app._editor_last_known_source_path != a_snapshot_path
    assert app._editor_last_known_source_mtime_ns is not None
    assert app._editor_last_saved_block_type_counts == {"info": 2}


def test_source_snapshot_failure_triggers_full_recovery_no_stale_snapshot(tmp_path, tk_root, monkeypatch):
    app = _RealEditor(tk_root)
    app._load_editor_content(_write(tmp_path, "a.md", "A content"))
    a_path = app._editor_last_loaded_path

    path_b = _write(tmp_path, "b.md", "B content")

    def boom(_input_path):
        raise OSError("simulated stat failure")

    monkeypatch.setattr(app, "_get_editor_source_snapshot", boom)

    with pytest.raises(OSError):
        app._load_editor_content(path_b)

    assert app._editor_document_state == EDITOR_DOCUMENT_NOT_LOADED
    assert app.editor_widget.get("1.0", "end-1c") == ""
    assert app._editor_last_loaded_path is None
    assert app._editor_last_known_source_path is None
    assert app._editor_last_known_source_mtime_ns is None
    assert app._editor_last_saved_block_type_counts == {}
    # No trace of A left behind mislabeled as a valid snapshot either.
    assert app._editor_last_known_source_path != a_path


def test_block_type_counts_failure_triggers_full_recovery(tmp_path, tk_root, monkeypatch):
    app = _RealEditor(tk_root)
    path_b = _write(tmp_path, "b.md", "B content")

    def boom(_markdown_text):
        raise ValueError("simulated parse failure")

    monkeypatch.setattr(app, "_collect_editor_block_type_counts", boom)

    with pytest.raises(ValueError):
        app._load_editor_content(path_b)

    assert app._editor_document_state == EDITOR_DOCUMENT_NOT_LOADED
    assert app._editor_last_loaded_path is None
    assert app._editor_last_saved_block_type_counts == {}


def test_no_premature_baseline_mutation_before_full_success(tmp_path, tk_root, monkeypatch):
    """A failure while preparing a new baseline must not have already
    overwritten the still-valid baseline of the previously loaded document,
    before the recovery reset runs."""

    app = _RealEditor(tk_root)
    path_a = _write(tmp_path, "a.md", "A content")
    app._load_editor_content(path_a)
    a_last_loaded_path = app._editor_last_loaded_path
    a_source_path = app._editor_last_known_source_path
    a_block_counts = dict(app._editor_last_saved_block_type_counts)

    path_b = _write(tmp_path, "b.md", "B content")
    observed = {}
    original_reset = app._reset_editor_widget_to_empty

    def spying_reset():
        observed["last_loaded_path"] = app._editor_last_loaded_path
        observed["source_path"] = app._editor_last_known_source_path
        observed["block_counts"] = dict(app._editor_last_saved_block_type_counts)
        return original_reset()

    monkeypatch.setattr(app, "_reset_editor_widget_to_empty", spying_reset)

    def boom(_markdown_text):
        raise ValueError("simulated parse failure")

    monkeypatch.setattr(app, "_collect_editor_block_type_counts", boom)

    with pytest.raises(ValueError):
        app._load_editor_content(path_b)

    # At the moment recovery started, A's baseline was still fully intact --
    # nothing from B had been committed yet.
    assert observed["last_loaded_path"] == a_last_loaded_path
    assert observed["source_path"] == a_source_path
    assert observed["block_counts"] == a_block_counts


# -- Fix Teil 2: Phase B failures never undo an already-successful Phase A --


def test_phase_b_exception_does_not_undo_phase_a_success(tmp_path, tk_root, monkeypatch):
    app = _RealEditor(tk_root)
    path = _write(tmp_path, "b.md", "B content")

    def boom(immediate=False):
        raise RuntimeError("simulated diagnostics failure")

    monkeypatch.setattr(app, "_queue_editor_diagnostics", boom)

    with pytest.raises(RuntimeError):
        app._load_editor_content(path)

    assert app._editor_document_state == EDITOR_DOCUMENT_LOADED
    assert app.editor_widget.get("1.0", "end-1c") == "B content"
    assert app._editor_last_loaded_path == path


# -- _get_editor_source_snapshot / _update_editor_source_snapshot -----------


def test_get_editor_source_snapshot_is_pure_and_raises_on_missing_file(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    path = _write(tmp_path, "x.md", "content")

    result_path, mtime_ns = app._get_editor_source_snapshot(path)
    assert result_path == path
    assert isinstance(mtime_ns, int)
    # Purely computational -- no state touched.
    assert app._editor_last_known_source_path is None

    path.unlink()
    with pytest.raises(Exception):
        app._get_editor_source_snapshot(path)


def test_update_editor_source_snapshot_tolerates_stat_failure(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    path = _write(tmp_path, "x.md", "content")
    app._update_editor_source_snapshot(path)
    assert app._editor_last_known_source_path == path
    previous_mtime = app._editor_last_known_source_mtime_ns

    missing = tmp_path / "gone.md"
    app._update_editor_source_snapshot(missing)

    # Tolerant: a stat() failure on the save path leaves the prior snapshot
    # untouched rather than raising or wiping it.
    assert app._editor_last_known_source_path == path
    assert app._editor_last_known_source_mtime_ns == previous_mtime


# -- A -> B tab-switch identity, and Befund 3 (diagnostics/outline reset) ---


def test_a_to_b_tab_switch_failure_leaves_editor_empty_not_a_content(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    app._load_editor_content(_write(tmp_path, "a.md", "A content"))

    missing = tmp_path / "missing.md"
    app._load_editor_content(missing)

    assert app.editor_widget.get("1.0", "end-1c") == ""
    assert app._editor_document_state == EDITOR_DOCUMENT_NOT_LOADED


def test_recovery_then_successful_reload_restores_interactivity(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    app._load_editor_content(tmp_path / "missing.md")
    assert app._editor_document_state == EDITOR_DOCUMENT_NOT_LOADED

    path = _write(tmp_path, "c.md", "C content")
    app._load_editor_content(path)

    assert app._editor_document_state == EDITOR_DOCUMENT_LOADED
    assert app.editor_widget.get("1.0", "end-1c") == "C content"


def test_reset_editor_widget_to_empty_refreshes_derived_ui(tmp_path, tk_root):
    app = _RealEditor(tk_root)
    app._load_editor_content(_write(tmp_path, "a.md", "A content"))
    highlighting_before = app.highlighting_calls
    diagnostics_before = app.diagnostics_calls
    outline_before = app.outline_calls

    app._reset_editor_widget_to_empty()

    assert app.highlighting_calls > highlighting_before
    assert app.diagnostics_calls > diagnostics_before
    assert app.outline_calls > outline_before


# -- Befund 3: _clear_active_document_view delegates to the shared reset ----


class _RealEditorWithClose(_RealEditor, BlattwerkAppPersistenceMixin):
    def __init__(self, root):
        super().__init__(root)
        self.input_var = tk.StringVar(value="")
        self.preview_images = []
        self.current_page_index = 0
        self.page_info_var = tk.StringVar(value="")
        self.zoom_info_var = tk.StringVar(value="")
        self.preview_canvas = tk.Canvas(root)
        self.preview_text_item = self.preview_canvas.create_text(0, 0, text="")

    def _clear_preview_image_items(self):
        pass

    def _update_nav_buttons(self):
        pass


def test_clear_active_document_view_delegates_to_reset_helper(tmp_path, tk_root, monkeypatch):
    app = _RealEditorWithClose(tk_root)
    app._load_editor_content(_write(tmp_path, "a.md", "A content"))

    calls = {"n": 0}
    original = app._reset_editor_widget_to_empty

    def spy():
        calls["n"] += 1
        return original()

    monkeypatch.setattr(app, "_reset_editor_widget_to_empty", spy)

    app._clear_active_document_view()

    assert calls["n"] == 1
    assert app._editor_document_state == EDITOR_DOCUMENT_NOT_LOADED
    assert app.editor_widget.get("1.0", "end-1c") == ""
