"""GUI mixin module."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import BwBaseWindow, ui
from bw_gui.menu import section_spec
from bw_gui.runtime import AppShellConfig


from app.app_info import APP_INFO
from app.bootstrap.wiring import AppDependencies
from .blatt_shortcuts import build_preview_keybinding_registry, build_preview_shortcuts
from .shortcut_manager import ShortcutManager
from .ui_constants import EDITOR_DOCUMENT_NOT_LOADED, EDITOR_VIEW_PREVIEW_ONLY, VIEW_FIT_WIDTH, VIEW_LAYOUT_SINGLE
from bw_gui.contracts.hsm import build_ui_hsm_contract
from bw_gui.contracts.popup import POPUP_KIND_MODAL, POPUP_KIND_NON_MODAL, PopupPolicy, PopupPolicyRegistry
from .ui_theme import DEFAULT_THEME
from ..styles.blatt_styles import DEFAULT_FONT_PROFILE, DEFAULT_FONT_SIZE_PROFILE
from ..styles.worksheet_design import DEFAULT_COLOR_PROFILE
from .blatt_ui_shortcut_runtime import BlattwerkShortcutRuntimeMixin
from .blatt_ui_shortcut_debug import BlattwerkShortcutDebugMixin
from .blatt_ui_document_tabs import BlattwerkDocumentTabsMixin
from .blatt_ui_document_type import BlattwerkDocumentTypeMixin


class BlattwerkAppBase(
    BlattwerkDocumentTypeMixin,
    BlattwerkDocumentTabsMixin,
    BlattwerkShortcutDebugMixin,
    BlattwerkShortcutRuntimeMixin,
    BwBaseWindow,
):
    """Basisklasse für gemeinsamen GUI-Zustand und globale Shortcuts."""

    def __init__(self, deps: AppDependencies | None = None, startup_file: str | None = None):
        self.dependencies = deps
        self._startup_file = startup_file
        shell_config = (
            deps.shell_config
            if deps is not None
            else AppShellConfig(
                title=APP_INFO.window_title,
                geometry="980x860",
                min_width=760,
                min_height=640,
            )
        )
        super().__init__(
            title=shell_config.title,
            geometry=shell_config.geometry,
            min_width=shell_config.min_width,
            min_height=shell_config.min_height,
            theme_key=DEFAULT_THEME,
            on_close=self._on_shell_close,
            start_maximized=shell_config.start_maximized,
        )

    def build_menu(self) -> list:
        return [
            section_spec("file", lambda: self._to_shared_menu_items(self._menu_file_items()), label="Datei", alt="d"),
            section_spec("insert_block", lambda: self._to_shared_menu_items(self._menu_insert_block_items()), label="Einfügen", alt="i"),
            section_spec("view", lambda: self._to_shared_menu_items(self._menu_view_items()), label="Ansicht", alt="a"),
            section_spec("extras", lambda: self._to_shared_menu_items(self._menu_extras_items()), label="Extras", alt="e"),
            section_spec("shortcuts", lambda: self._to_shared_menu_items(self._menu_shortcuts_items()), label="Shortcuts", alt="s"),
        ]

    def build_content(self, frame) -> None:
        self.root = self  # backward-compat alias for all self.root.* calls
        from .window_identity import apply_window_icon
        apply_window_icon(self)

        try:
            self._default_tk_scaling = float(self.tk.call("tk", "scaling"))
        except Exception:
            self._default_tk_scaling = 1.0

        self.input_var = ui.StringVar()
        self.preview_mode_var = ui.StringVar(value="worksheet")
        self.preview_black_screen_var = ui.StringVar(value="none")
        self.preview_section_separator_var = ui.StringVar(value="dot")
        self.preview_hide_future_sections_var = ui.BooleanVar(value=False)
        self.preview_controls_collapsed_var = ui.BooleanVar(value=False)
        self.preview_page_format_var = ui.StringVar(value="a4_portrait")
        self.preview_contrast_var = ui.StringVar(value="standard")
        self.preview_fit_mode_var = ui.StringVar(value=VIEW_FIT_WIDTH)
        self.preview_layout_mode_var = ui.StringVar(value=VIEW_LAYOUT_SINGLE)
        self.editor_view_mode_var = ui.StringVar(value=EDITOR_VIEW_PREVIEW_ONLY)
        self.design_color_profile_var = ui.StringVar(value=DEFAULT_COLOR_PROFILE)
        self.design_font_profile_var = ui.StringVar(value=DEFAULT_FONT_PROFILE)
        self._font_profile_menu_var = ui.StringVar(value=DEFAULT_FONT_PROFILE)
        self.design_font_size_profile_var = ui.StringVar(value=DEFAULT_FONT_SIZE_PROFILE)
        self.theme_var = ui.StringVar(value=DEFAULT_THEME)

        self.status_var = ui.StringVar(value="Bereit")
        self.page_info_var = ui.StringVar(value="Seite 0/0")
        self.zoom_info_var = ui.StringVar(value="Zoom: 100%")

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
        self._preview_controls_frame = None
        self.preview_controls_toggle_btn = None
        self._preview_controls_after_anchor = None
        self._editor_loading_content = False
        self._editor_save_after_id = None
        self._editor_save_delay_ms = 800
        self._editor_highlighting_after_id = None
        self._editor_highlighting_delay_ms = 180
        self._editor_diagnostics_after_id = None
        self._editor_diagnostics_delay_ms = 350
        self._editor_diagnostics_items = []
        self._editor_diagnostics_by_row_id = {}
        self._editor_outline_after_id = None
        self._editor_outline_delay_ms = 220
        self._editor_outline_items = []
        self._editor_block_pair_after_id = None
        self._editor_block_pair_delay_ms = 120
        self._preview_auto_refresh_after_id = None
        self._preview_auto_refresh_on_edit_idle_enabled = False
        self._preview_auto_refresh_on_edit_idle_delay_ms = 1200
        self._editor_completion_popup = None
        self._editor_completion_listbox = None
        self._editor_completion_detail_frame = None
        self._editor_completion_detail_title_label = None
        self._editor_completion_detail_body_label = None
        self._editor_completion_items = []
        self._editor_completion_replace_start = None
        self._editor_completion_replace_end = None
        self._editor_completion_context_kind = None
        self._editor_completion_context_meta = {}
        self._editor_search_frame = None
        self._editor_search_replace_row = None
        self._editor_search_before_widget = None
        self._editor_search_query_entry = None
        self._editor_search_replace_entry = None
        self._editor_search_visible = False
        self._editor_search_replace_visible = False
        self._editor_search_matches = []
        self._editor_search_current_index = None
        self._editor_search_query_var = ui.StringVar(value="")
        self._editor_search_replace_var = ui.StringVar(value="")
        self._editor_search_case_sensitive_var = ui.BooleanVar(value=False)
        self._editor_search_match_count_var = ui.StringVar(value="0/0")
        self._editor_last_saved_block_type_counts = {}
        self._editor_last_loaded_path = None
        self._editor_document_state = EDITOR_DOCUMENT_NOT_LOADED
        self._editor_has_unsaved_changes = False
        self._editor_last_known_source_path = None
        self._editor_last_known_source_mtime_ns = None
        self._editor_source_sync_in_progress = False
        self._equal_split_attempts = 0
        self.recent_files = []
        self.recent_menu = None
        self.ui_settings = {}
        self.shortcut_manager = ShortcutManager(self.root)
        self.keybinding_registry = build_preview_keybinding_registry(self)
        self.hsm_contract = build_ui_hsm_contract(
            intents=[definition.intent for definition in self.keybinding_registry.all()]
        )
        self.shortcut_bindings = build_preview_shortcuts(self, registry=self.keybinding_registry)
        self.shortcut_debug_enabled_var = ui.BooleanVar(value=False)
        self.shortcut_debug_offline_var = ui.BooleanVar(value=False)
        self.shortcut_debug_context_var = ui.StringVar(value="")
        self.shortcut_debug_window = None
        self.shortcut_debug_table = None
        self.shortcut_debug_summary_var = ui.StringVar(value="")
        self._shortcut_debug_refresh_after_id = None
        self._laufkern_tracking_run_id = "runtime-shortcuts"
        self._laufkern_tracking_sequence = 0
        self._laufkern_tracking_step_ids: dict[str, str] = {}
        self._laufkern_tracking_artifacts = []
        self.popup_policy_registry = PopupPolicyRegistry()
        self.popup_policy_registry.register_policy(PopupPolicy(policy_id="dialog.modal", kind=POPUP_KIND_MODAL))
        self.popup_policy_registry.register_policy(
            PopupPolicy(
                policy_id="dialog.non_blocking",
                kind=POPUP_KIND_NON_MODAL,
                trap_focus=False,
                affects_mode=False,
            )
        )
        self._tracked_popup_ids: set[str] = set()
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

        self.help_docs_window = None
        self.help_docs_listbox = None
        self.help_docs_text = None
        self.help_docs_catalog = []

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
        self.help_page_info_var = ui.StringVar(value="Hilfe 0/0")
        self.help_zoom_info_var = ui.StringVar(value="Zoom: 100%")
        self._help_last_preview_input_path = None
        self._active_lernhilfen_available = False
        self.lernhilfen_action_btn = None
        self._last_diagnostics_signature = None
        self.preview_mode_btn_worksheet = None
        self.preview_mode_btn_solution = None
        self.preview_mode_static_label = None
        self.preview_phase_separator_btn_dot = None
        self.preview_phase_separator_btn_arrow = None
        self.preview_phase_hide_future_check = None
        self.preview_page_format_btn_a4 = None
        self.preview_page_format_btn_a5 = None
        self.preview_page_format_btn_16_9 = None
        self.preview_page_format_btn_16_10 = None
        self.preview_page_format_btn_4_3 = None
        self._current_preview_document_type = None
        self._preview_refresh_in_progress = False
        self._last_preview_page_format_by_mode = {
            "worksheet": "a4_portrait",
            "presentation": "presentation_16_9",
        }

        self._load_ui_settings()
        self._load_recent_files()
        # _load_ui_settings() already synced shell/menu/chrome and ttk styles via
        # _apply_user_preferences_live() -> BwBaseWindow.apply_theme(), so widgets
        # built below pick up the loaded theme's ttk styles from the start.
        self._build_ui(parent=frame)
        if hasattr(self, "_apply_user_preferences_live") and hasattr(self, "user_preferences"):
            self._apply_user_preferences_live(self.user_preferences)
        self._apply_theme(redraw_preview=False)
        self._refresh_zoom_label()
        self._bind_shortcuts()
        if hasattr(self, "_bind_window_geometry_tracking"):
            self._bind_window_geometry_tracking()
        if hasattr(self, "_maybe_apply_startup_file_preference"):
            self._maybe_apply_startup_file_preference()

    def open_settings(self) -> None:
        self._open_local_settings_dialog()

    def apply_theme(self, theme_key: str) -> None:
        """Called by BwBaseWindow View menu theme radios.

        Uses BwBaseWindow.apply_theme() (shell theme storage + menu-bar radio
        refresh + window chrome) instead of poking self._shell directly.
        _apply_user_preferences_live() (the other place theme_var can change)
        does the same via its own BwBaseWindow.apply_theme() call, so
        _apply_theme() no longer needs to redundantly re-apply root bg/chrome/
        ttk/menu itself — every caller has already synced the shell first.
        """
        BwBaseWindow.apply_theme(self, theme_key)
        if hasattr(self, "theme_var"):
            self.theme_var.set(theme_key)
            self._on_theme_changed()

    def _on_shell_close(self) -> bool:
        """Persist lightweight UI state before the root window closes."""

        try:
            if hasattr(self, "_cancel_editor_auto_preview_refresh"):
                self._cancel_editor_auto_preview_refresh()
        except Exception:
            pass

        try:
            if hasattr(self, "_close_help_preview_window"):
                self._close_help_preview_window()
        except Exception:
            pass

        try:
            if hasattr(self, "_set_shortcut_debug_overlay_visible"):
                self._set_shortcut_debug_overlay_visible(False)
        except Exception:
            pass

        try:
            if hasattr(self, "_save_ui_settings"):
                self._save_ui_settings()
        except Exception:
            pass

        return True

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


