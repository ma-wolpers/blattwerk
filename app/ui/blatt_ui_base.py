"""GUI mixin module."""

from __future__ import annotations

import tkinter as tk

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
        self.root.title("Blattwerk Vorschau")
        self.root.geometry("980x860")
        self.root.minsize(760, 640)
        try:
            self._default_tk_scaling = float(self.root.tk.call("tk", "scaling"))
        except Exception:
            self._default_tk_scaling = 1.0

        self.input_var = tk.StringVar()
        self.preview_mode_var = tk.StringVar(value="worksheet")
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

        self.help_preview_window = None
        self.help_preview_canvas = None
        self.help_preview_text_item = None
        self.help_preview_images = []
        self.help_current_page_index = 0
        self.help_zoom_percent = 100
        self._help_tk_preview_images = []
        self._help_preview_image_items = []
        self.help_page_info_var = tk.StringVar(value="Hilfe 0/0")
        self.help_zoom_info_var = tk.StringVar(value="Zoom: 100%")
        self._help_last_preview_input_path = None
        self._last_diagnostics_signature = None

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
        new_mode = "solution" if self.preview_mode_var.get() == "worksheet" else "worksheet"
        self.preview_mode_var.set(new_mode)
        self.refresh_preview()

    def _open_last_markdown(self):
        """Open last markdown."""
        if not self.recent_files:
            self.status_var.set("Kein zuletzt geladenes Markdown vorhanden")
            return

        self._open_recent_file(self.recent_files[0])

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
