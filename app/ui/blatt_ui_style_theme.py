"""Theme der Oberflaeche: Editorfarben und Theme-Wechsel.
"""

from __future__ import annotations

from .ui_constants import EDITOR_DOCUMENT_LOADED
from .ui_theme import (
    apply_window_theme,
    configure_ttk_theme,
    get_theme,
    style_canvas,
    style_preview_placeholder,
)


class BlattwerkAppStyleThemeMixin:
    """Wendet das UI-Theme an."""

    def _editor_widget_colors(self, theme: dict, interactive: bool) -> dict:
            """Returns the Text-widget color kwargs for the editor, themed and state-aware.

            `interactive=True` reproduces the editor's normal, active look for
            the given theme. `interactive=False` reuses the same theme's own
            "muted" tokens (bg_main/fg_muted, already used elsewhere for
            de-emphasized UI such as TLabelframe.Label) instead of a hardcoded
            gray, so the disabled look stays correct across every theme.
            """
            if interactive:
                return dict(
                    background=theme["bg_surface"],
                    foreground=theme["fg_primary"],
                    insertbackground=theme["fg_primary"],
                    selectbackground=theme["accent_soft"],
                    selectforeground=theme["fg_primary"],
                )
            return dict(
                background=theme["bg_main"],
                foreground=theme["fg_muted"],
                insertbackground=theme["fg_muted"],
                selectbackground=theme["accent_soft"],
                selectforeground=theme["fg_muted"],
            )

    def _apply_editor_widget_theme_colors(self):
            """Applies theme- and document-state-aware colors to the editor widget.

            Called both on theme switches and on every editor document-state
            transition, so the two never fall out of sync -- a theme change
            while no document is loaded must not accidentally restore the
            "active" colors.
            """
            if getattr(self, "editor_widget", None) is None:
                return

            theme = get_theme(self.theme_var.get())
            interactive = getattr(self, "_editor_document_state", None) == EDITOR_DOCUMENT_LOADED
            self.editor_widget.configure(**self._editor_widget_colors(theme, interactive))

    def _apply_theme(self, redraw_preview=True):
            """Wendet das aktive Theme auf Canvas, Editor und Zusatzfenster an.

            Hauptfenster-Hintergrund/-Chrome und Menüband laufen inzwischen immer
            über BwBaseWindow.apply_theme() (aufgerufen von apply_theme() bzw.
            _apply_user_preferences_live(), beide vor jedem _apply_theme()-Aufruf) —
            hier daher nicht mehr redundant erneut angewendet.
            """

            theme_key = self.theme_var.get()

            if hasattr(self, "preview_canvas"):
                style_canvas(self.preview_canvas, theme_key)
                style_preview_placeholder(self.preview_canvas, self.preview_text_item, theme_key)

            if self.help_preview_canvas is not None:
                style_canvas(self.help_preview_canvas, theme_key)
                if self.help_preview_text_item is not None:
                    style_preview_placeholder(self.help_preview_canvas, self.help_preview_text_item, theme_key)

            if self.help_preview_window is not None and self.help_preview_window.winfo_exists():
                apply_window_theme(self.help_preview_window, theme_key)
                configure_ttk_theme(self.help_preview_window, theme_key)

            if getattr(self, "editor_widget", None) is not None:
                self._apply_editor_widget_theme_colors()
                if hasattr(self, "_configure_editor_diagnostic_tags"):
                    self._configure_editor_diagnostic_tags()
                if hasattr(self, "_configure_editor_syntax_tags"):
                    self._configure_editor_syntax_tags()
                if hasattr(self, "_apply_editor_theme_widgets"):
                    self._apply_editor_theme_widgets()

            if hasattr(self, "_apply_help_docs_theme"):
                self._apply_help_docs_theme()

            self._refresh_color_profile_swatches()

            if redraw_preview and self.preview_images:
                x_view_start = self.preview_canvas.xview()[0]
                y_view_start = self.preview_canvas.yview()[0]
                self._show_current_page(
                    reset_scroll=False,
                    x_view_start=x_view_start,
                    y_view_start=y_view_start,
                )

    def _cycle_theme(self, step: int = 1):
            """Cycle themes via BwBaseWindow apply_theme so the View menu stays in sync."""
            from bw_gui.theming import THEME_ORDER
            self._cycle_option(self.theme_var, THEME_ORDER, step=step)
            self.apply_theme(self.theme_var.get())

    def _on_theme_changed(self):
            """On theme changed."""
            self._save_ui_settings()
            self._apply_theme(redraw_preview=True)
