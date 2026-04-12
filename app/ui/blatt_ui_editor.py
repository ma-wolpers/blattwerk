"""Editor mixin for loading and live-saving markdown text in the main window."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from .ui_constants import (
    EDITOR_VIEW_BOTH,
    EDITOR_VIEW_EDITOR_ONLY,
    EDITOR_VIEW_PREVIEW_ONLY,
)


class BlattwerkAppEditorMixin:
    """Adds a basic markdown editor area with debounced live save."""

    def _build_editor_panel(self, parent):
        """Creates the editor widget and wires change events for live save."""

        editor_toolbar = ttk.Frame(parent)
        editor_toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(editor_toolbar, text="Schreibbereich").pack(side="left")

        editor_body = ttk.Frame(parent)
        editor_body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.editor_widget = tk.Text(
            editor_body,
            wrap="word",
            undo=True,
            borderwidth=0,
            highlightthickness=0,
        )
        self.editor_widget.pack(side="left", fill="both", expand=True)

        self.editor_vertical_scrollbar = ttk.Scrollbar(
            editor_body,
            orient="vertical",
            command=self.editor_widget.yview,
        )
        self.editor_vertical_scrollbar.pack(side="right", fill="y")
        self.editor_widget.configure(yscrollcommand=self.editor_vertical_scrollbar.set)
        self.editor_widget.bind("<<Modified>>", self._on_editor_modified)

    def _load_editor_content(self, input_path: Path):
        """Loads the selected markdown file into the editor widget."""

        if self.editor_widget is None:
            return

        try:
            content = input_path.read_text(encoding="utf-8")
        except Exception as error:
            messagebox.showerror("Datei konnte nicht gelesen werden", str(error))
            self.status_var.set("Datei konnte nicht gelesen werden")
            return

        self._editor_loading_content = True
        try:
            self.editor_widget.delete("1.0", "end")
            self.editor_widget.insert("1.0", content)
            self.editor_widget.edit_modified(False)
            self._editor_last_loaded_path = input_path
        finally:
            self._editor_loading_content = False

    def _on_editor_modified(self, _event=None):
        """Schedules a debounced save after user edits."""

        if self.editor_widget is None:
            return

        if self._editor_loading_content:
            self.editor_widget.edit_modified(False)
            return

        if not self.editor_widget.edit_modified():
            return

        self.editor_widget.edit_modified(False)
        self.status_var.set("Ungespeichert")

        if self._editor_save_after_id is not None:
            self.root.after_cancel(self._editor_save_after_id)

        self._editor_save_after_id = self.root.after(self._editor_save_delay_ms, self._save_editor_content)
        self.status_var.set("Speichert…")

    def _save_editor_content(self):
        """Writes the current editor content back to the selected markdown file."""

        self._editor_save_after_id = None

        if self.editor_widget is None:
            return

        input_path = self._validate_input()
        if input_path is None:
            return

        content = self.editor_widget.get("1.0", "end-1c")
        try:
            self.status_var.set("Speichert…")
            input_path.write_text(content, encoding="utf-8")
            self.status_var.set("Gespeichert")
        except Exception as error:
            self.status_var.set("Speichern fehlgeschlagen")
            messagebox.showerror("Speichern fehlgeschlagen", str(error))

    def _set_editor_view_mode(self, mode: str):
        """Updates the selected editor/preview view mode and applies layout."""

        if mode == self.editor_view_mode_var.get():
            return

        self.editor_view_mode_var.set(mode)
        self._apply_editor_view_mode()
        self._load_editor_for_current_input_if_needed()
        self._save_ui_settings()

    def _load_editor_for_current_input_if_needed(self):
        """Loads current input file into editor when editor pane is visible."""

        mode = self.editor_view_mode_var.get()
        if mode == EDITOR_VIEW_PREVIEW_ONLY:
            return

        input_path = self._get_input_path_if_exists()
        if input_path is None:
            return

        if self._editor_last_loaded_path == input_path:
            return

        self._load_editor_content(input_path)

    def _apply_editor_view_mode(self):
        """Shows preview area, editor area, or both depending on selected mode."""

        if self.editor_preview_paned is None or self.editor_container is None or self.preview_container is None:
            return

        mode = self.editor_view_mode_var.get()

        for pane in (self.editor_container, self.preview_container):
            try:
                self.editor_preview_paned.forget(pane)
            except Exception:
                pass

        if mode == EDITOR_VIEW_EDITOR_ONLY:
            self.editor_preview_paned.add(self.editor_container, weight=1)
            if self.preview_h_scroll is not None:
                self.preview_h_scroll.pack_forget()
        elif mode == EDITOR_VIEW_BOTH:
            self.editor_preview_paned.add(self.editor_container, weight=1)
            self.editor_preview_paned.add(self.preview_container, weight=1)
            self.root.after_idle(self._set_equal_split)
            if self.preview_h_scroll is not None:
                self.preview_h_scroll.pack(fill="x", padx=12, pady=(0, 8), after=self.editor_preview_paned)
        else:
            self.editor_preview_paned.add(self.preview_container, weight=1)
            if self.preview_h_scroll is not None:
                self.preview_h_scroll.pack(fill="x", padx=12, pady=(0, 8), after=self.editor_preview_paned)

    def _set_equal_split(self):
        """Sets a 50/50 split when both panes are visible."""

        if self.editor_preview_paned is None:
            return

        panes = self.editor_preview_paned.panes()
        if len(panes) != 2:
            return

        total_width = self.editor_preview_paned.winfo_width()
        if total_width <= 2:
            return

        self.editor_preview_paned.sashpos(0, max(1, total_width // 2))
