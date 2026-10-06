"""Document tab state, preview mode and option cycling (BlattwerkAppBase mixin).

Split out of blatt_ui_base.py (file-size rule); method bodies unchanged."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui

from pathlib import Path

from .ui_constants import EDITOR_DOCUMENT_LOADED
from ..storage.user_preferences_adapter import normalize_user_preferences
from ..styles.worksheet_design import CONTRAST_PROFILE_ORDER


class BlattwerkDocumentTabsMixin:
    """Document tab state, preview mode and option cycling (BlattwerkAppBase mixin)."""

    def _set_page_format(self, page_format):
        """Set page format."""
        if self.preview_page_format_var.get() == page_format:
            return

        self.preview_page_format_var.set(page_format)
        self.refresh_preview()

    def _toggle_preview_mode(self):
        """Toggle preview mode."""
        input_text = self._clean_path_text(self.input_var.get())
        if input_text:
            spec = self._document_spec_for_path(Path(input_text))
            if spec is not None and not spec.solutions_renderable:
                return

        new_mode = "solution" if self.preview_mode_var.get() == "worksheet" else "worksheet"
        self.preview_mode_var.set(new_mode)
        self.refresh_preview()

    def _set_preview_black_screen_both(self):
        """Enable black-screen insertion before and after for preview/export parity."""
        if self.preview_black_screen_var.get() != "both":
            self.preview_black_screen_var.set("both")
        self.refresh_preview()

    def _open_last_markdown(self):
        """Open last markdown."""
        if not self.recent_files:
            self.status_var.set("Kein zuletzt geladenes Markdown vorhanden")
            return

        if hasattr(self, "_open_most_recent_not_open_file") and self._open_most_recent_not_open_file():
            return

        self.status_var.set("Alle zuletzt geladenen Markdown-Dateien sind bereits geöffnet")

    @staticmethod
    def _normalize_document_path(input_path: Path) -> str:
        """Builds a stable dictionary key for a document path."""

        return str(Path(input_path).expanduser().resolve())

    def _build_document_tab_state(self, input_path: Path) -> dict[str, object]:
        """Creates initial per-tab state for a document."""

        normalized_path = self._normalize_document_path(input_path)
        document_type = self._read_document_type(input_path)

        preview_mode = self.preview_mode_var.get()
        if not self._solutions_renderable_for_type(document_type):
            preview_mode = "worksheet"

        tab_state = {
            "path": normalized_path,
            "document_type": document_type,
            "preview_mode": preview_mode,
            "page_format": self.preview_page_format_var.get(),
            "section_separator": self.preview_section_separator_var.get(),
            "hide_future_sections": bool(self.preview_hide_future_sections_var.get()),
            "contrast": self.preview_contrast_var.get(),
            "color_profile": self.design_color_profile_var.get(),
            "font_profile": self.design_font_profile_var.get(),
            "fit_mode": self.preview_fit_mode_var.get(),
            "layout_mode": self.preview_layout_mode_var.get(),
            "zoom_percent": int(round(self.zoom_percent)),
            "current_page_index": int(self.current_page_index),
            "x_view_start": 0.0,
            "y_view_start": 0.0,
            "preview_cache_key": None,
            "preview_images": [],
        }
        if self._font_size_profile_is_per_tab():
            tab_state["font_size_profile"] = self.design_font_size_profile_var.get()
        return tab_state

    def _font_size_profile_is_per_tab(self) -> bool:
        """Whether font size should be saved/restored per document tab (togglable, see Einstellungen).

        Reverted once before (commit 6b0bd6c, "keep font-size class stable
        across tab switches") after the size selection flipped implicitly on
        tab switches -- kept as an opt-out preference this time instead of an
        unconditional re-introduction, so a recurrence has an immediate
        fallback without a code change.
        """
        preferences = normalize_user_preferences(getattr(self, "user_preferences", {}))
        return bool(preferences.get("font_size_profile_per_tab", True))

    def _persist_active_document_tab_state(self):
        """Writes current control values back into the active tab state."""

        tab_id = self._active_document_tab_id
        if tab_id is None:
            return

        tab_state = self.document_tabs.get(tab_id)
        if tab_state is None:
            return

        input_text = self._clean_path_text(self.input_var.get())
        if input_text:
            try:
                current_path = Path(input_text)
                tab_state["path"] = self._normalize_document_path(current_path)
                tab_state["document_type"] = self._read_document_type(current_path)
            except Exception:
                pass
        tab_state["preview_mode"] = self.preview_mode_var.get()
        tab_state["page_format"] = self.preview_page_format_var.get()
        tab_state["section_separator"] = self.preview_section_separator_var.get()
        tab_state["hide_future_sections"] = bool(self.preview_hide_future_sections_var.get())
        tab_state["contrast"] = self.preview_contrast_var.get()
        tab_state["color_profile"] = self.design_color_profile_var.get()
        tab_state["font_profile"] = self.design_font_profile_var.get()
        if self._font_size_profile_is_per_tab():
            tab_state["font_size_profile"] = self.design_font_size_profile_var.get()
        tab_state["fit_mode"] = self.preview_fit_mode_var.get()
        tab_state["layout_mode"] = self.preview_layout_mode_var.get()
        tab_state["zoom_percent"] = int(round(self.zoom_percent))
        tab_state["current_page_index"] = int(self.current_page_index)

        if hasattr(self, "preview_canvas") and self.preview_canvas is not None:
            try:
                tab_state["x_view_start"] = float(self.preview_canvas.xview()[0])
                tab_state["y_view_start"] = float(self.preview_canvas.yview()[0])
            except Exception:
                tab_state["x_view_start"] = float(tab_state.get("x_view_start", 0.0))
                tab_state["y_view_start"] = float(tab_state.get("y_view_start", 0.0))

    def _apply_document_tab_state(self, tab_id: str):
        """Loads per-tab control values and refreshes editor/preview for that tab."""

        tab_state = self.document_tabs.get(tab_id)
        if tab_state is None:
            return

        try:
            input_path = Path(tab_state["path"])
        except Exception:
            return

        # Der Pfad ist die Typquelle; der Tab-Cache wird bei jedem Anwenden neu gesetzt (I1).
        tab_state["document_type"] = self._read_document_type(input_path)

        self._tab_switch_in_progress = True
        try:
            separator_value = str(
                tab_state.get(
                    "section_separator",
                    self.preview_section_separator_var.get(),
                )
                or "dot"
            ).strip().lower()
            if separator_value not in {"dot", "arrow"}:
                separator_value = "dot"
            hide_future_value = tab_state.get(
                "hide_future_sections",
                self.preview_hide_future_sections_var.get(),
            )
            if isinstance(hide_future_value, str):
                hide_future_value = hide_future_value.strip().lower() in {
                    "1",
                    "true",
                    "yes",
                    "ja",
                    "on",
                }

            self.input_var.set(str(input_path))
            preview_mode = str(tab_state.get("preview_mode", self.preview_mode_var.get()) or self.preview_mode_var.get())
            if not self._solutions_renderable_for_type(tab_state.get("document_type")):
                preview_mode = "worksheet"
            self.preview_mode_var.set(preview_mode)
            self.preview_page_format_var.set(tab_state.get("page_format", self.preview_page_format_var.get()))
            self.preview_section_separator_var.set(separator_value)
            self.preview_hide_future_sections_var.set(bool(hide_future_value))
            self.preview_contrast_var.set(tab_state.get("contrast", self.preview_contrast_var.get()))
            self.design_color_profile_var.set(tab_state.get("color_profile", self.design_color_profile_var.get()))
            self.design_font_profile_var.set(tab_state.get("font_profile", self.design_font_profile_var.get()))
            if self._font_size_profile_is_per_tab():
                self.design_font_size_profile_var.set(
                    tab_state.get("font_size_profile", self.design_font_size_profile_var.get())
                )
            self.preview_fit_mode_var.set(tab_state.get("fit_mode", self.preview_fit_mode_var.get()))
            self.preview_layout_mode_var.set(tab_state.get("layout_mode", self.preview_layout_mode_var.get()))
            self.zoom_percent = int(str(tab_state.get("zoom_percent", int(round(self.zoom_percent))) or self.zoom_percent))
            self.current_page_index = int(str(tab_state.get("current_page_index", self.current_page_index) or self.current_page_index))
        finally:
            self._tab_switch_in_progress = False

        self._sync_font_profile_combo()
        self._sync_font_size_profile_combo()
        self._refresh_color_profile_swatches()
        self._load_editor_content(input_path)
        if self._editor_document_state != EDITOR_DOCUMENT_LOADED:
            # _load_editor_content() already reported the failure (e.g. file
            # missing/unreadable); avoid a second, duplicate error dialog
            # from refresh_preview()'s own _validate_input() check.
            return
        self._warn_if_bw_mode_has_color_mentions()
        if hasattr(self, "_refresh_preview_for_active_tab"):
            self._refresh_preview_for_active_tab()
        else:
            self.refresh_preview()

    def _activate_document_tab(self, tab_id: str, apply_state: bool = True):
        """Selects a tab in UI and optionally applies its state."""

        if self.document_notebook is not None:
            try:
                self.document_notebook.select(tab_id)
            except Exception:
                return

        self._active_document_tab_id = tab_id
        if apply_state:
            self._apply_document_tab_state(tab_id)

    def _on_document_tab_changed(self, _event=None):
        """Keeps tab state isolated when the selected notebook tab changes."""

        if self._tab_switch_in_progress or self.document_notebook is None:
            return

        selected_tab_id = self.document_notebook.select()
        if not selected_tab_id:
            return

        previous_tab_id = self._active_document_tab_id
        if previous_tab_id == selected_tab_id:
            return

        if hasattr(self, "_sync_editor_with_source"):
            self._sync_editor_with_source(trigger="tab-switch")

        self._persist_active_document_tab_state()
        self._active_document_tab_id = selected_tab_id
        self._apply_document_tab_state(selected_tab_id)

    def _scroll_preview_vertical(self, units: int):
        """Scroll preview vertical."""
        if not hasattr(self, "preview_canvas"):
            return

        self.preview_canvas.yview_scroll(units, "units")
        self._update_current_page_from_viewport_center()

    def _cycle_contrast(self, step: int):
        """Cycle contrast."""
        profiles = CONTRAST_PROFILE_ORDER
        current = self.preview_contrast_var.get()
        try:
            current_index = profiles.index(current)
        except ValueError:
            current_index = 0

        next_index = (current_index + step) % len(profiles)
        self.preview_contrast_var.set(profiles[next_index])
        self.refresh_preview()

    def _toggle_contrast(self):
        """Toggle contrast."""
        self._cycle_contrast(step=1)

    @staticmethod
    def _cycle_option(var: ui.StringVar, options: list[str], step: int = 1):
        """Cycle option."""
        current = var.get()
        try:
            current_index = options.index(current)
        except ValueError:
            current_index = 0
        next_index = (current_index + step) % len(options)
        var.set(options[next_index])
