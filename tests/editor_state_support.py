"""Shared fixtures and the real-Tk editor double for the editor document-state tests.

Split out of ``test_editor_document_state_load.py`` (300-Zeilen-Regel); used by it and
``test_editor_document_state_recovery.py``. Uses a genuine tkinter.Text widget (not a
fake stand-in) because the behavior under test is Tk-specific: Text.insert()/delete()
silently no-op while state="disabled", a class-level <Button-1> binding moves keyboard
focus regardless of -state, and root.focus_get()/focus_set() reflect real focus.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import pytest

from app.ui import dialog_services
from app.ui.blatt_ui_editor import BlattwerkAppEditorMixin
from app.ui.ui_constants import (
    EDITOR_DOCUMENT_LOADED,
    EDITOR_DOCUMENT_NOT_LOADED,
)
from app.ui.ui_theme import get_theme


@pytest.fixture
def tk_root():
    """A visible (not withdrawn) root -- these tests assert real keyboard
    focus (root.focus_get()/focus_set()), which Tk does not track correctly
    for a withdrawn/unmapped toplevel (focus stays pinned to the root itself
    regardless of focus_set() calls on child widgets, verified empirically).
    """

    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"no Tk display available: {error}")
    root.geometry("+0+0")
    # Only the first Tk toplevel a process creates gets real OS input focus
    # automatically (verified empirically); later ones stay unfocused unless
    # forced, which would make every focus assertion below meaningless.
    root.focus_force()
    root.update()
    yield root
    root.destroy()


@pytest.fixture(autouse=True)
def no_real_dialogs(monkeypatch):
    """Prevents a real modal error dialog from blocking the test process."""

    monkeypatch.setattr(dialog_services.messagebox, "showerror", lambda *a, **k: None)


class _RealEditor(BlattwerkAppEditorMixin):
    """Minimal app stand-in with a real Text widget wired the way blatt_ui_editor expects."""

    def __init__(self, root):
        self.root = root
        self.editor_widget = tk.Text(root, undo=True)
        self.editor_widget.pack()
        self.editor_widget.bind("<Button-1>", self._on_editor_mouse_click)
        self._editor_document_state = EDITOR_DOCUMENT_NOT_LOADED
        self._editor_loading_content = False
        self._editor_has_unsaved_changes = False
        self._editor_last_loaded_path = None
        self._editor_last_known_source_path = None
        self._editor_last_known_source_mtime_ns = None
        self._editor_last_saved_block_type_counts = {}
        self.theme_var = tk.StringVar(value="slate_indigo")
        self.status_var = tk.StringVar(value="")
        self.diagnostics_calls = 0
        self.outline_calls = 0
        self.highlighting_calls = 0
        self.editor_widget.configure(state="disabled", takefocus=0)

    def _collect_editor_block_type_counts(self, markdown_text):
        return {"info": markdown_text.count(":::info")}

    def _queue_editor_highlighting(self, immediate=False):
        self.highlighting_calls += 1

    def _queue_editor_diagnostics(self, immediate=False):
        self.diagnostics_calls += 1

    def _queue_editor_outline(self, immediate=False):
        self.outline_calls += 1

    def _apply_editor_widget_theme_colors(self):
        theme = get_theme(self.theme_var.get())
        interactive = self._editor_document_state == EDITOR_DOCUMENT_LOADED
        if interactive:
            self.editor_widget.configure(background=theme["bg_surface"], foreground=theme["fg_primary"])
        else:
            self.editor_widget.configure(background=theme["bg_main"], foreground=theme["fg_muted"])

    def _close_editor_completion(self):
        pass

    def _refresh_editor_block_pair_highlight(self):
        pass


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


