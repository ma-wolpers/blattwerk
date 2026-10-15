"""Editor mixin for loading and live-saving markdown text in the main window."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets

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
        self.editor_widget.bind("<<Modified>>", self._on_editor_modified)
        self.editor_widget.bind("<KeyRelease>", self._on_editor_key_release)
        self.editor_widget.bind("<Button-1>", self._on_editor_mouse_click)
        self.editor_widget.bind("<FocusIn>", self._on_editor_focus_in)

        self._build_editor_search_bar(parent, editor_body)

        preferences = getattr(self, "user_preferences", {})
        if bool(preferences.get("shortcuts_editor_group_enabled", True)):
            self.editor_widget.bind("<Control-space>", self._on_editor_completion_trigger)
            self.editor_widget.bind("<Control-Shift-period>", self._on_editor_insert_triple_pair)
            self.editor_widget.bind("<Control-colon>", self._on_editor_insert_triple_pair)
            self.editor_widget.bind("<Escape>", self._on_editor_escape)
            self.editor_widget.bind("<Tab>", self._on_editor_tab)
            self.editor_widget.bind("<Shift-Tab>", self._on_editor_shift_tab)
            self.editor_widget.bind("<ISO_Left_Tab>", self._on_editor_shift_tab)
            self.editor_widget.bind("<Up>", self._on_editor_completion_move_up)
            self.editor_widget.bind("<Down>", self._on_editor_completion_move_down)
            self.editor_widget.bind("<Return>", self._on_editor_completion_enter)
            self.editor_widget.bind("<Control-Return>", self._on_editor_completion_reject_and_newline)
            self.editor_widget.bind("<Shift-Return>", self._on_editor_completion_reject_and_newline)
            self.editor_widget.bind("<Control-BackSpace>", self._on_editor_delete_word_before)
            self.editor_widget.bind("<Control-Delete>", self._on_editor_delete_word_after)
            self.editor_widget.bind("<Control-f>", self._toggle_editor_find_bar)
            self.editor_widget.bind("<Control-h>", self._toggle_editor_replace_bar)
            self.editor_widget.bind("<KeyPress-asterisk>", lambda e: self._on_editor_marker_key(e, "*"))
            self.editor_widget.bind("<KeyPress-underscore>", lambda e: self._on_editor_marker_key(e, "_"))
            self.editor_widget.bind("<KeyPress-equal>", lambda e: self._on_editor_marker_key(e, "="))
            self.editor_widget.bind("<KeyPress-asciitilde>", lambda e: self._on_editor_marker_key(e, "~"))
            self.editor_widget.bind("<KeyPress-asciicircum>", lambda e: self._on_editor_marker_key(e, "^"))
            self.editor_widget.bind("<KeyPress-bar>", lambda e: self._on_editor_marker_key(e, "|"))
            self.editor_widget.bind("<KeyPress-dollar>", lambda e: self._on_editor_marker_key(e, "$"))
            self.editor_widget.bind("<KeyPress-grave>", self._on_editor_backtick_key)

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
