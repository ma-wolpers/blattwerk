"""Shared imports and constants for Blattwerk GUI mixins."""

from __future__ import annotations

from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import zipfile

import fitz
from PIL import Image, ImageTk

from ..core.blatt_kern import (
    build_help_cards,
    build_worksheet,
    inspect_markdown_document,
)
from ..core.color_mentions import find_color_mentions_in_file
from .blatt_shortcuts import build_preview_shortcuts
from .export_dialog import ExportDialog
from .preview_geometry import (
    clamp,
    find_active_page_index,
    get_centered_view_fractions,
    get_fit_scales,
    get_preview_frame_size,
    get_zoom_target_size,
    parse_scrollregion,
)
from ..storage.local_config_store import (
    DEFAULT_HISTORY_ROOT_NAME,
    DEFAULT_MAX_RECENT_FILES,
    LEGACY_RECENT_FILES_PATH,
    LEGACY_UI_SETTINGS_PATH,
    LOCAL_CONFIG_PATH,
    MAX_MAX_RECENT_FILES,
    MIN_MAX_RECENT_FILES,
    STORAGE_STATE_DIR,
    load_recent_files,
    load_system_settings,
    load_ui_settings,
    migrate_legacy_config,
    save_recent_files,
    save_system_settings,
    save_ui_settings,
)
from ..storage.recent_files_store import add_recent_file, remove_recent_file
from ..styles.worksheet_design import (
    COLOR_PROFILE_LABELS,
    COLOR_PROFILE_ORDER,
    CONTRAST_PROFILE_LABELS,
    CONTRAST_PROFILE_ORDER,
    DEFAULT_COLOR_PROFILE,
    get_color_profile_preview,
    normalize_contrast_profile,
    normalize_color_profile,
)
from ..styles.blatt_styles import invalidate_stylesheet_template_cache
from ..styles.blatt_styles import (
    DEFAULT_FONT_PROFILE,
    DEFAULT_FONT_SIZE_PROFILE,
    FONT_PROFILE_LABELS,
    FONT_PROFILE_ORDER,
    FONT_SIZE_PROFILE_LABELS,
    FONT_SIZE_PROFILE_ORDER,
    normalize_font_profile,
    normalize_font_size_profile,
)
from .ui_constants import (
    PREVIEW_CANVAS_PADDING_PX,
    PREVIEW_MIN_FRAME_PX,
    PREVIEW_PAGE_GAP_PX,
    PREVIEW_PAGE_MARGIN_PX,
    PREVIEW_SCALE_MAX,
    PREVIEW_SCALE_MIN,
    PREVIEW_ZOOM_MAX_PERCENT,
    PREVIEW_ZOOM_MIN_PERCENT,
    VIEW_FIT_PAGE,
    VIEW_FIT_WIDTH,
    VIEW_LAYOUT_SINGLE,
    VIEW_LAYOUT_STACK,
    VIEW_LAYOUT_STRIP,
    VIEW_MODE_LABELS,
)
from .ui_theme import (
    DEFAULT_THEME,
    apply_window_theme,
    configure_ttk_theme,
    get_theme,
    normalize_theme_key,
    populate_theme_menu,
    style_canvas,
    style_preview_placeholder,
)
from .shortcut_manager import ShortcutManager
from .history_paths import (
    HISTORY_ROOT_NAME,
    MAX_RECENT_FILES,
    find_history_root,
    normalize_recent_entries,
    resolve_history_path,
    to_history_relative_path,
)


CUSTOM_FIT_MODE = "__custom__"
BW_COLOR_PROFILE_KEYS = {"bw"}
