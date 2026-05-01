"""GUI mixin module."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from .blatt_shortcuts import build_preview_shortcuts
from .shortcut_manager import ShortcutManager
from .ui_constants import (
    EDITOR_VIEW_PREVIEW_ONLY,
    VIEW_FIT_WIDTH,
    VIEW_LAYOUT_SINGLE,
)
from .ui_theme import DEFAULT_THEME
from ..styles.blatt_styles import DEFAULT_FONT_PROFILE, DEFAULT_FONT_SIZE_PROFILE
from ..styles.worksheet_design import (
    CONTRAST_PROFILE_ORDER,
    DEFAULT_COLOR_PROFILE,
)

class BlattwerkAppBase:
    """Basisklasse für gemeinsamen GUI-Zustand und globale Shortcuts."""
    def __init__(self, root):
        """Init."""
        self.root = root
        self.root.title("Blattwerk")
        self.root.geometry("980x860")
        self.root.minsize(760, 640)
        try:
            self._default_tk_scaling = float(self.root.tk.call("tk", "scaling"))
        except Exception:
            self._default_tk_scaling = 1.0

        self.input_var = tk.StringVar()
        self.preview_mode_var = tk.StringVar(value="worksheet")
        self.preview_black_screen_var = tk.StringVar(value="none")
        self.preview_page_format_var = tk.StringVar(value="a4_portrait")
        self.preview_contrast_var = tk.StringVar(value="standard")
        self.preview_fit_mode_var = tk.StringVar(value=VIEW_FIT_WIDTH)
        self.preview_layout_mode_var = tk.StringVar(value=VIEW_LAYOUT_SINGLE)
        self.editor_view_mode_var = tk.StringVar(value=EDITOR_VIEW_PREVIEW_ONLY)
        self.design_color_profile_var = tk.StringVar(value=DEFAULT_COLOR_PROFILE)
        self.design_font_profile_var = tk.StringVar(value=DEFAULT_FONT_PROFILE)
        self.design_font_size_profile_var = tk.StringVar(value=DEFAULT_FONT_SIZE_PROFILE)
        self.theme_var = tk.StringVar(value=DEFAULT_THEME)

        self.status_var = tk.StringVar(value="Bereit")
        self.page_info_var = tk.StringVar(value="Seite 0/0")
        self.zoom_info_var = tk.StringVar(value="Zoom: 100%")

        self.preview_images = []
        self.current_page_index = 0
        self._tk_preview_images = []
        self.preview_image_items = []
        self._page_layout_boxes = []
        self._last_preview_input_path = None
        self.zoom_percent = 100
        self.editor_widget = None
        self.editor_vertical_scrollbar = None
        self.editor_diagnostics_listbox = None
        self.editor_outline_listbox = None
        self.editor_container = None
        self.preview_container = None
        self.editor_preview_paned = None
        self.preview_h_scroll = None
        self._editor_loading_content = False
        self._editor_save_after_id = None
        self._editor_save_delay_ms = 800
        self._editor_highlighting_after_id = None
        self._editor_highlighting_delay_ms = 180
        self._editor_diagnostics_after_id = None
        self._editor_diagnostics_delay_ms = 350
        self._editor_diagnostics_items = []
        self._editor_outline_after_id = None
        self._editor_outline_delay_ms = 220
        self._editor_outline_items = []
        self._editor_completion_popup = None
        self._editor_completion_listbox = None
        self._editor_completion_items = []
        self._editor_completion_replace_start = None
        self._editor_completion_replace_end = None
        self._editor_completion_context_kind = None
        self._editor_completion_context_meta = {}
        self._editor_last_saved_block_type_counts = {}
        self._editor_last_loaded_path = None
        self._editor_has_unsaved_changes = False
        self._editor_last_known_source_path = None
        self._editor_last_known_source_mtime_ns = None
        self._editor_source_sync_in_progress = False
        self._equal_split_attempts = 0
        self.recent_files = []
        self.recent_menu = None
        self.ui_settings = {}
        self.shortcut_manager = ShortcutManager(self.root)
        self.shortcut_bindings = build_preview_shortcuts(self)
        self._color_profile_swatches = {}
        self._hovered_color_profile = None
        self._swatch_tooltip = None
        self._responsive_controls_wrap_enabled = True
        self._reduce_motion = False
        self._ui_density = "comfort"
        self._window_geometry_after_id = None

        self.document_notebook = None
        self.document_tabs = {}
        self._document_tab_order = []
        self._active_document_tab_id = None
        self._document_tab_path_index = {}
        self._tab_switch_in_progress = False

        self.help_preview_window = None
        self.help_preview_canvas = None
        self.help_preview_text_item = None
        self.help_preview_images = []
        self.help_current_page_index = 0
        self.help_zoom_percent = 100
        self._help_tk_preview_images = []
        self._help_preview_image_items = []
        self._help_card_y_offsets = []
        self._help_stacked_image_size = (0, 0)
        self.help_page_info_var = tk.StringVar(value="Hilfe 0/0")
        self.help_zoom_info_var = tk.StringVar(value="Zoom: 100%")
        self._help_last_preview_input_path = None
        self._active_lernhilfen_available = False
        self.lernhilfen_action_btn = None
        self._last_diagnostics_signature = None
        self.preview_mode_btn_worksheet = None
        self.preview_mode_btn_solution = None
        self.preview_mode_static_label = None
        self.preview_page_format_btn_a4 = None
        self.preview_page_format_btn_a5 = None
        self.preview_page_format_btn_16_9 = None
        self.preview_page_format_btn_16_10 = None
        self.preview_page_format_btn_4_3 = None
        self._current_preview_document_mode = "worksheet"
        self._preview_refresh_in_progress = False
        self._last_preview_page_format_by_mode = {
            "worksheet": "a4_portrait",
            "presentation": "presentation_16_9",
        }

        self._load_ui_settings()
        self._load_recent_files()
        self._configure_styles()
        self._build_menu()
        self._build_ui()
        if hasattr(self, "_apply_user_preferences_live") and hasattr(self, "user_preferences"):
            self._apply_user_preferences_live(self.user_preferences)
        self._apply_theme(redraw_preview=False)
        self._refresh_zoom_label()
        self._bind_shortcuts()
        if hasattr(self, "_bind_window_geometry_tracking"):
            self._bind_window_geometry_tracking()
        if hasattr(self, "_maybe_apply_startup_file_preference"):
            self._maybe_apply_startup_file_preference()

        # Enforce startup behavior: always open with preview area only.
        self.editor_view_mode_var.set(EDITOR_VIEW_PREVIEW_ONLY)
        if hasattr(self, "_apply_editor_view_mode"):
            self._apply_editor_view_mode()

    @staticmethod
    def _clean_path_text(value):
        """Normalize path text read from entry fields."""

        return str(value or "").strip()

    def _bind_shortcuts(self):
        """Registriert globale Tastaturkürzel für Vorschau-Steuerung."""

        preferences = getattr(self, "user_preferences", {})
        if not bool(preferences.get("shortcuts_preview_group_enabled", True)):
            return

        self.shortcut_manager.bind_all(self.shortcut_bindings)

    def _set_page_format(self, page_format):
        """Set page format."""
        if self.preview_page_format_var.get() == page_format:
            return

        self.preview_page_format_var.set(page_format)
        self.refresh_preview()

    def _toggle_preview_mode(self):
        """Toggle preview mode."""
        if hasattr(self, "_read_document_mode"):
            input_text = self._clean_path_text(self.input_var.get())
            if input_text:
                path_obj = Path(input_text)
                if path_obj.exists():
                    document_mode = self._read_document_mode(path_obj)
                    if document_mode == "presentation":
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

    def _build_document_tab_state(self, input_path: Path) -> dict[str, str]:
        """Creates initial per-tab state for a document."""

        normalized_path = self._normalize_document_path(input_path)
        return {
            "path": normalized_path,
            "preview_mode": self.preview_mode_var.get(),
            "page_format": self.preview_page_format_var.get(),
            "contrast": self.preview_contrast_var.get(),
            "color_profile": self.design_color_profile_var.get(),
            "font_profile": self.design_font_profile_var.get(),
            "font_size_profile": self.design_font_size_profile_var.get(),
            "fit_mode": self.preview_fit_mode_var.get(),
            "layout_mode": self.preview_layout_mode_var.get(),
            "zoom_percent": int(round(self.zoom_percent)),
            "current_page_index": int(self.current_page_index),
            "x_view_start": 0.0,
            "y_view_start": 0.0,
            "preview_cache_key": None,
            "preview_images": [],
        }

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
                tab_state["path"] = self._normalize_document_path(Path(input_text))
            except Exception:
                pass
        tab_state["preview_mode"] = self.preview_mode_var.get()
        tab_state["page_format"] = self.preview_page_format_var.get()
        tab_state["contrast"] = self.preview_contrast_var.get()
        tab_state["color_profile"] = self.design_color_profile_var.get()
        tab_state["font_profile"] = self.design_font_profile_var.get()
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

        if not input_path.exists():
            self.status_var.set("Datei im Tab existiert nicht mehr")
            return

        self._tab_switch_in_progress = True
        try:
            self.input_var.set(str(input_path))
            self.preview_mode_var.set(tab_state.get("preview_mode", self.preview_mode_var.get()))
            self.preview_page_format_var.set(tab_state.get("page_format", self.preview_page_format_var.get()))
            self.preview_contrast_var.set(tab_state.get("contrast", self.preview_contrast_var.get()))
            self.design_color_profile_var.set(tab_state.get("color_profile", self.design_color_profile_var.get()))
            self.design_font_profile_var.set(tab_state.get("font_profile", self.design_font_profile_var.get()))
            self.design_font_size_profile_var.set(tab_state.get("font_size_profile", self.design_font_size_profile_var.get()))
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
    def _cycle_option(var: tk.StringVar, options: list[str], step: int = 1):
        """Cycle option."""
        current = var.get()
        try:
            current_index = options.index(current)
        except ValueError:
            current_index = 0
        next_index = (current_index + step) % len(options)
        var.set(options[next_index])
