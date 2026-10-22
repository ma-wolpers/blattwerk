"""Editor mixin for loading and live-saving markdown text in the main window."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import bind_click, on_focus_change, on_key, on_text_modified, ui, widgets

from .ui_constants import EDITOR_DOCUMENT_NOT_LOADED
from .blatt_ui_editor_source import BlattwerkAppEditorSourceMixin
from .blatt_ui_editor_highlight import BlattwerkAppEditorHighlightMixin
from .blatt_ui_editor_keys import BlattwerkAppEditorKeysMixin
from .blatt_ui_editor_view import BlattwerkAppEditorViewMixin


class BlattwerkAppEditorMixin(BlattwerkAppEditorViewMixin, BlattwerkAppEditorKeysMixin, BlattwerkAppEditorHighlightMixin, BlattwerkAppEditorSourceMixin):
    """Adds a basic markdown editor area with debounced live save."""

    def _build_editor_panel(self, parent):
        """Creates the editor widget and wires change events for live save."""

        editor_toolbar = widgets.Frame(parent)
        editor_toolbar.pack(fill="x", padx=8, pady=(8, 4))
        widgets.Label(editor_toolbar, text="Schreibbereich").pack(side="left")

        editor_body = widgets.Frame(parent)
        editor_body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.editor_widget = ui.Text(
            editor_body,
            wrap="word",
            undo=True,
            borderwidth=0,
            highlightthickness=0,
        )
        self.editor_widget.pack(side="left", fill="both", expand=True)

        self.editor_vertical_scrollbar = widgets.Scrollbar(
            editor_body,
            orient="vertical",
            command=self.editor_widget.yview,
        )
        self.editor_vertical_scrollbar.pack(side="right", fill="y")
        self.editor_widget.configure(yscrollcommand=self.editor_vertical_scrollbar.set)
        on_text_modified(self.editor_widget, self._on_editor_modified)
        on_key(self.editor_widget, self._on_editor_key_after, phase="after")
        bind_click(self.editor_widget, self._on_editor_mouse_click)
        on_focus_change(self.editor_widget, on_gained=self._on_editor_focus_in)

        self._build_editor_search_bar(parent, editor_body)

        preferences = getattr(self, "user_preferences", {})
        if bool(preferences.get("shortcuts_editor_group_enabled", True)):
            self._bind_editor_keys()

        self._build_editor_diagnostics_panel(parent)
        if hasattr(self, "_build_exam_overview_panel"):
            self._build_exam_overview_panel(parent)

        self._build_editor_outline_panel(parent, preferences)

        self._configure_editor_diagnostic_tags()
        self._configure_editor_syntax_tags()
        self.editor_widget.tag_raise("sel")
        self._set_editor_document_state(EDITOR_DOCUMENT_NOT_LOADED)

    def _on_editor_focus_in(self, _event=None):
        """Synchronizes the editor with external file changes when focus enters."""

        self._sync_editor_with_source(trigger="focus")
