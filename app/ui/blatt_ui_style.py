"""GUI mixin module."""

from __future__ import annotations

from pathlib import Path
from PIL import Image
import tkinter as tk
from tkinter import messagebox, ttk

from bw_libs.shared_gui_core import ensure_bw_gui_on_path
from ..core.color_mentions import detect_bw_mode_color_warning_mentions
from ..core.build_requests import WorksheetDesignOptions
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
from ..styles.worksheet_design import (
    COLOR_PROFILE_LABELS,
    COLOR_PROFILE_ORDER,
    CONTRAST_PROFILE_ORDER,
    DEFAULT_COLOR_PROFILE,
    get_color_profile_preview,
    normalize_color_profile,
)
from .preview_geometry import clamp, get_fit_scales
from .ui_constants import (
    EDITOR_VIEW_BOTH,
    EDITOR_VIEW_EDITOR_ONLY,
    EDITOR_VIEW_PREVIEW_ONLY,
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
    THEMES,
    THEME_ORDER,
    apply_window_theme,
    configure_ttk_theme,
    get_theme,
    style_canvas,
    style_preview_placeholder,
)

ensure_bw_gui_on_path()
try:
    from bw_gui.menu import CustomMenuBar as SharedCustomMenuBar
    from bw_gui.menu import MenuDefinition as SharedMenuDefinition
    from bw_gui.menu import MenuItem as SharedMenuItem
except ModuleNotFoundError:
    SharedCustomMenuBar = None
    SharedMenuDefinition = None
    SharedMenuItem = None

BW_COLOR_PROFILE_KEYS = {"bw"}

class BlattwerkAppStyleMixin:
    """Kapselt Theme-, Menü- und Designprofil-Logik der GUI."""
    def _on_worksheet_design_changed(self):
            """On worksheet design changed."""
            self._refresh_color_profile_swatches()
            self._save_ui_settings()
            self.refresh_preview()

    def _cycle_design_color_profile(self, step: int = 1):
            """Cycle design color profile."""
            previous_profile = self.design_color_profile_var.get()
            self._cycle_option(self.design_color_profile_var, COLOR_PROFILE_ORDER, step=step)
            self._warn_if_bw_mode_has_color_mentions(previous_profile=previous_profile)
            self._on_worksheet_design_changed()

    def _cycle_theme(self, step: int = 1):
            """Cycle through available themes and apply immediately."""
            self._cycle_option(self.theme_var, THEME_ORDER, step=step)
            self._on_theme_changed()

    def _cycle_font_profile(self, step: int = 1):
            """Cycle through available worksheet font profiles."""
            self._cycle_option(self.design_font_profile_var, FONT_PROFILE_ORDER, step=step)
            self._on_worksheet_design_changed()

    def _worksheet_design_kwargs(self):
            """Worksheet design kwargs."""
            return self._worksheet_design_options().as_kwargs()

    def _worksheet_design_options(self):
            """Worksheet design options."""
            return WorksheetDesignOptions(
                color_profile=normalize_color_profile(self.design_color_profile_var.get()),
                font_profile=normalize_font_profile(self.design_font_profile_var.get()),
                font_size_profile=normalize_font_size_profile(self.design_font_size_profile_var.get()),
            )

    def _set_font_profile(self, profile_key: str):
            """Set font profile."""
            normalized_key = normalize_font_profile(profile_key)
            if self.design_font_profile_var.get() == normalized_key:
                return

            self.design_font_profile_var.set(normalized_key)
            self._on_worksheet_design_changed()

    def _on_font_profile_selected(self, _event=None):
            """On font profile selected."""
            if not hasattr(self, "font_profile_combo"):
                return

            selected_label = (self.font_profile_combo.get() or "").strip()
            selected_key = None
            for profile_key in FONT_PROFILE_ORDER:
                if FONT_PROFILE_LABELS.get(profile_key) == selected_label:
                    selected_key = profile_key
                    break

            if selected_key is None:
                selected_key = DEFAULT_FONT_PROFILE

            self._set_font_profile(selected_key)

    def _set_font_size_profile(self, profile_key: str):
            """Set font size profile."""
            normalized_key = normalize_font_size_profile(profile_key)
            if self.design_font_size_profile_var.get() == normalized_key:
                return

            self.design_font_size_profile_var.set(normalized_key)
            self._on_worksheet_design_changed()

    def _on_font_size_profile_selected(self, _event=None):
            """On font size profile selected."""
            if not hasattr(self, "font_size_profile_combo"):
                return

            selected_label = (self.font_size_profile_combo.get() or "").strip()
            selected_key = None
            for profile_key in FONT_SIZE_PROFILE_ORDER:
                if FONT_SIZE_PROFILE_LABELS.get(profile_key) == selected_label:
                    selected_key = profile_key
                    break

            if selected_key is None:
                selected_key = DEFAULT_FONT_SIZE_PROFILE

            self._set_font_size_profile(selected_key)

    def _sync_font_profile_combo(self):
            """Sync font profile combo."""
            if not hasattr(self, "font_profile_combo"):
                return

            current_key = normalize_font_profile(self.design_font_profile_var.get())
            self.font_profile_combo.set(FONT_PROFILE_LABELS.get(current_key, FONT_PROFILE_LABELS[DEFAULT_FONT_PROFILE]))

    def _sync_font_size_profile_combo(self):
            """Sync font size profile combo."""
            if not hasattr(self, "font_size_profile_combo"):
                return

            current_key = normalize_font_size_profile(self.design_font_size_profile_var.get())
            self.font_size_profile_combo.set(FONT_SIZE_PROFILE_LABELS.get(current_key, FONT_SIZE_PROFILE_LABELS[DEFAULT_FONT_SIZE_PROFILE]))

    def _configure_styles(self):
            """Konfiguriert zentrale UI-Stile auf Basis des aktiven Themes."""

            apply_window_theme(self.root, self.theme_var.get())
            configure_ttk_theme(self.root, self.theme_var.get())

    def _apply_theme(self, redraw_preview=True):
            """Wendet das aktive Theme auf Fenster, ttk-Styles und Canvas an."""

            theme_key = self.theme_var.get()
            theme = get_theme(theme_key)
            apply_window_theme(self.root, theme_key)
            configure_ttk_theme(self.root, theme_key)

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
                self.editor_widget.configure(
                    background=theme["bg_surface"],
                    foreground=theme["fg_primary"],
                    insertbackground=theme["fg_primary"],
                    selectbackground=theme["accent_soft"],
                    selectforeground=theme["fg_primary"],
                )
                if hasattr(self, "_configure_editor_diagnostic_tags"):
                    self._configure_editor_diagnostic_tags()
                if hasattr(self, "_configure_editor_syntax_tags"):
                    self._configure_editor_syntax_tags()
                if hasattr(self, "_apply_editor_theme_widgets"):
                    self._apply_editor_theme_widgets()

            self._refresh_custom_menu_theme()

            self._refresh_color_profile_swatches()

            if redraw_preview and self.preview_images:
                x_view_start = self.preview_canvas.xview()[0]
                y_view_start = self.preview_canvas.yview()[0]
                self._show_current_page(
                    reset_scroll=False,
                    x_view_start=x_view_start,
                    y_view_start=y_view_start,
                )

    def _on_theme_changed(self):
            """On theme changed."""
            self._save_ui_settings()
            self._apply_theme(redraw_preview=True)

    def _set_color_profile(self, profile_key: str):
            """Set color profile."""
            if self.design_color_profile_var.get() == profile_key:
                return

            previous_profile = self.design_color_profile_var.get()
            self.design_color_profile_var.set(profile_key)
            self._warn_if_bw_mode_has_color_mentions(previous_profile=previous_profile)
            self._hide_swatch_tooltip()
            self._on_worksheet_design_changed()

    def _on_color_profile_swatch_enter(self, event, profile_key: str):
            """On color profile swatch enter."""
            self._hovered_color_profile = profile_key
            self._refresh_color_profile_swatches()
            self._show_swatch_tooltip(event, profile_key)

    def _on_color_profile_swatch_leave(self, _event):
            """On color profile swatch leave."""
            self._hovered_color_profile = None
            self._refresh_color_profile_swatches()
            self._hide_swatch_tooltip()

    def _show_swatch_tooltip(self, event, profile_key: str):
            """Show swatch tooltip."""
            self._hide_swatch_tooltip()

            preferences = getattr(self, "user_preferences", {})
            if not bool(preferences.get("tooltips_enabled", True)):
                return

            tooltip = tk.Toplevel(self.root)
            tooltip.overrideredirect(True)
            tooltip.attributes("-topmost", True)

            label = ttk.Label(
                tooltip,
                text=COLOR_PROFILE_LABELS.get(profile_key, profile_key),
                style="Muted.TLabel",
                padding=(6, 3),
            )
            label.pack()

            x_pos = int(getattr(event, "x_root", self.root.winfo_rootx()) + 10)
            y_pos = int(getattr(event, "y_root", self.root.winfo_rooty()) + 12)
            tooltip.geometry(f"+{x_pos}+{y_pos}")
            self._swatch_tooltip = tooltip

    def _hide_swatch_tooltip(self):
            """Hide swatch tooltip."""
            if self._swatch_tooltip is None:
                return

            try:
                self._swatch_tooltip.destroy()
            except tk.TclError:
                pass
            self._swatch_tooltip = None

    def _refresh_color_profile_swatches(self):
            """Refresh color profile swatches."""
            if not self._color_profile_swatches:
                return

            active_profile = self.design_color_profile_var.get()
            theme = get_theme(self.theme_var.get())

            for profile_key, canvas in self._color_profile_swatches.items():
                colors = get_color_profile_preview(profile_key)
                selected = profile_key == active_profile
                hovered = profile_key == self._hovered_color_profile
                frame_fill = colors["secondary_bg"] if hovered else colors["info_bg"]
                outer_outline = theme["accent"] if selected else colors["secondary_border"]
                inner_outline = theme["accent_hover"] if selected or hovered else theme["border"]

                canvas.delete("all")
                canvas.create_rectangle(
                    1,
                    1,
                    27,
                    19,
                    outline=outer_outline,
                    width=2 if (selected or hovered) else 1,
                    fill=frame_fill,
                )
                canvas.create_rectangle(
                    3,
                    3,
                    25,
                    17,
                    outline=inner_outline,
                    width=1,
                    fill=colors["info_bg"],
                )
                canvas.create_rectangle(
                    5,
                    5,
                    23,
                    10,
                    outline=colors["info_border"],
                    width=1,
                    fill=colors["info_border"],
                )
                canvas.create_rectangle(
                    5,
                    11,
                    23,
                    16,
                    outline=colors["secondary_border"],
                    width=1,
                    fill=colors["secondary_border"],
                )

    def _to_shared_menu_items(self, items: list[dict]):
            """Convert local dict-based menu rows into shared menu item objects."""

            if SharedMenuItem is None:
                return tuple()

            converted = []
            for item in items:
                item_type = str(item.get("type", "command"))
                sub_items = tuple()
                if item_type == "submenu":
                    sub_items = self._to_shared_menu_items(list(item.get("items", [])))

                converted.append(
                    SharedMenuItem(
                        type=item_type,
                        label=str(item.get("label", "")),
                        command=item.get("command"),
                        checked=bool(item.get("checked", False)),
                        items=sub_items,
                    )
                )

            return tuple(converted)

    def _refresh_custom_menu_theme(self):
            """Applies current theme colors to custom top menu strip and open popups."""

            shared_menu_bar = getattr(self, "_shared_menu_bar", None)
            if shared_menu_bar is not None:
                shared_menu_bar.refresh_theme(self.theme_var.get())
                self._custom_menu_strip = shared_menu_bar.strip
                self._menu_popup_stack = list(getattr(shared_menu_bar, "_popup_stack", []))
                self._active_menu_key = getattr(shared_menu_bar, "_active_key", None)
                return

            menu_strip = getattr(self, "_custom_menu_strip", None)
            if menu_strip is None or not menu_strip.winfo_exists():
                return

            theme = get_theme(self.theme_var.get())
            strip_bg = theme["bg_surface"]
            border = theme["border"]
            muted = theme["fg_muted"]

            menu_strip.configure(bg=strip_bg, highlightthickness=1, highlightbackground=border, bd=0)

            active_key = getattr(self, "_active_menu_key", None)
            for key, button in getattr(self, "_menu_top_buttons", {}).items():
                if button is None or not button.winfo_exists():
                    continue
                is_active = key == active_key and bool(getattr(self, "_menu_popup_stack", []))
                button.configure(
                    bg=theme["accent_soft"] if is_active else strip_bg,
                    fg=theme["fg_primary"],
                    activebackground=theme["accent_soft"],
                    activeforeground=theme["fg_primary"],
                    highlightbackground=border,
                    highlightcolor=theme["accent"],
                    disabledforeground=muted,
                )

            for popup in list(getattr(self, "_menu_popup_stack", [])):
                if popup is None or not popup.winfo_exists():
                    continue
                popup.configure(bg=border)
                body = getattr(popup, "_menu_body", None)
                if body is not None and body.winfo_exists():
                    body.configure(bg=strip_bg)

    def _close_all_menu_popups(self):
            """Closes all open custom menu popups and resets active menu state."""

            shared_menu_bar = getattr(self, "_shared_menu_bar", None)
            if shared_menu_bar is not None:
                shared_menu_bar.close_all_popups()
                self._menu_popup_stack = list(getattr(shared_menu_bar, "_popup_stack", []))
                self._active_menu_key = getattr(shared_menu_bar, "_active_key", None)
                self._refresh_custom_menu_theme()
                return

            focus_guard_id = getattr(self, "_menu_focus_guard_after_id", None)
            if focus_guard_id is not None:
                try:
                    self.root.after_cancel(focus_guard_id)
                except Exception:
                    pass
                self._menu_focus_guard_after_id = None

            for popup in reversed(list(getattr(self, "_menu_popup_stack", []))):
                try:
                    if popup is not None and popup.winfo_exists():
                        popup.destroy()
                except tk.TclError:
                    pass

            self._menu_popup_stack = []
            self._active_menu_key = None
            self._refresh_custom_menu_theme()

    def _close_menu_popups_from_level(self, level: int):
            """Closes submenu popups deeper than the requested level."""

            stack = list(getattr(self, "_menu_popup_stack", []))
            while len(stack) > level:
                popup = stack.pop()
                try:
                    if popup is not None and popup.winfo_exists():
                        popup.destroy()
                except tk.TclError:
                    pass
            self._menu_popup_stack = stack

    def _menu_widget_is_managed(self, widget) -> bool:
            """Returns whether widget belongs to custom menu strip or one of its popups."""

            if widget is None:
                return False

            managed_roots = []
            strip = getattr(self, "_custom_menu_strip", None)
            if strip is not None and strip.winfo_exists():
                managed_roots.append(strip)
            for popup in getattr(self, "_menu_popup_stack", []):
                if popup is not None and popup.winfo_exists():
                    managed_roots.append(popup)

            current = widget
            while current is not None:
                for root_widget in managed_roots:
                    if current == root_widget:
                        return True
                parent_name = current.winfo_parent()
                if not parent_name:
                    break
                try:
                    current = current._nametowidget(parent_name)
                except Exception:
                    break
            return False

    def _on_global_menu_click(self, event):
            """Closes menu popups when user clicks outside menu strip or popup windows."""

            if not getattr(self, "_menu_popup_stack", []):
                return
            if self._menu_widget_is_managed(getattr(event, "widget", None)):
                return
            self._close_all_menu_popups()

    def _on_root_deactivate_for_menu(self, _event=None):
            """Closes open menus on app deactivation (including Alt+Tab focus loss)."""

            if not getattr(self, "_menu_popup_stack", []):
                return

            def _maybe_close():
                focus_widget = None
                try:
                    focus_widget = self.root.focus_displayof()
                except Exception:
                    focus_widget = None

                # Focuswechsel innerhalb der eigenen Custom-Menüs darf nicht schließen.
                if self._menu_widget_is_managed(focus_widget):
                    return

                self._close_all_menu_popups()

            self.root.after(0, _maybe_close)

    def _schedule_menu_focus_guard(self):
            """Continuously checks focus while menus are open and closes on real app focus loss."""

            current_id = getattr(self, "_menu_focus_guard_after_id", None)
            if current_id is not None:
                try:
                    self.root.after_cancel(current_id)
                except Exception:
                    pass
                self._menu_focus_guard_after_id = None

            if not getattr(self, "_menu_popup_stack", []):
                return

            def _check_focus():
                self._menu_focus_guard_after_id = None
                if not getattr(self, "_menu_popup_stack", []):
                    return

                focus_widget = None
                try:
                    focus_widget = self.root.focus_displayof()
                except Exception:
                    focus_widget = None

                if focus_widget is None:
                    self._close_all_menu_popups()
                    return

                if self._menu_widget_is_managed(focus_widget):
                    self._menu_focus_guard_after_id = self.root.after(120, _check_focus)
                    return

                self._menu_focus_guard_after_id = self.root.after(120, _check_focus)

            self._menu_focus_guard_after_id = self.root.after(160, _check_focus)

    def _on_menu_mnemonic(self, menu_key: str):
            """Opens top-level menu by mnemonic key and consumes the Alt event."""

            self._open_top_menu_by_key(menu_key)
            return "break"

    def _bind_custom_menu_global_handlers(self):
            """Installs global handlers for outside click and deactivation close behavior."""

            if getattr(self, "_custom_menu_global_handlers_bound", False):
                return

            self.root.bind_all("<Button-1>", self._on_global_menu_click, add="+")
            self.root.bind("<Unmap>", self._on_root_deactivate_for_menu, add="+")
            self.root.bind("<Deactivate>", self._on_root_deactivate_for_menu, add="+")
            self.root.bind_all("<Alt-d>", lambda _event: self._on_menu_mnemonic("datei"), add="+")
            self.root.bind_all("<Alt-D>", lambda _event: self._on_menu_mnemonic("datei"), add="+")
            self.root.bind_all("<Alt-a>", lambda _event: self._on_menu_mnemonic("ansicht"), add="+")
            self.root.bind_all("<Alt-A>", lambda _event: self._on_menu_mnemonic("ansicht"), add="+")
            self.root.bind_all("<Alt-s>", lambda _event: self._on_menu_mnemonic("shortcuts"), add="+")
            self.root.bind_all("<Alt-S>", lambda _event: self._on_menu_mnemonic("shortcuts"), add="+")
            self._custom_menu_global_handlers_bound = True

    def _menu_popup_style(self):
            """Returns consolidated colors for custom menu popups."""

            theme = get_theme(self.theme_var.get())
            return {
                "popup_bg": theme["bg_surface"],
                "popup_fg": theme["fg_primary"],
                "popup_border": theme["border"],
                "hover_bg": theme["accent_soft"],
                "hover_fg": theme["fg_primary"],
                "muted_fg": theme["fg_muted"],
                "separator": theme["border"],
            }

    def _menu_shortcuts_items(self):
            """Builds menu rows for shortcut hints."""

            labels = list(self._iter_shortcut_menu_labels() or [])
            if not labels:
                return [{"type": "disabled", "label": "(leer)"}]
            return [{"type": "disabled", "label": label} for label in labels]

    def _menu_file_items(self):
            """Builds rows for top menu Datei."""

            recent_items = [
                {
                    "type": "command",
                    "label": file_path,
                    "command": (lambda p=file_path: self._open_recent_file(p)),
                }
                for file_path in self.recent_files
            ]
            if not recent_items:
                recent_items = [{"type": "disabled", "label": "(leer)"}]

            settings_items = [
                {"type": "command", "label": "Allgemein", "command": lambda: self._open_local_settings_dialog("general")},
                {"type": "command", "label": "Editor Vervollständigung", "command": lambda: self._open_local_settings_dialog("editor_completion")},
                {"type": "command", "label": "Editor Diagnostik", "command": lambda: self._open_local_settings_dialog("editor_diagnostics")},
                {"type": "command", "label": "Ansicht und Layout", "command": lambda: self._open_local_settings_dialog("view_layout")},
                {"type": "command", "label": "Design und Theme", "command": lambda: self._open_local_settings_dialog("design_theme")},
                {"type": "command", "label": "Export", "command": lambda: self._open_local_settings_dialog("export")},
                {"type": "command", "label": "Shortcuts", "command": lambda: self._open_local_settings_dialog("shortcuts")},
                {"type": "command", "label": "Shortcut-Runtime-Debug", "command": self._toggle_shortcut_debug_overlay},
                {"type": "command", "label": "Identitaet und Copyright", "command": lambda: self._open_local_settings_dialog("identity")},
                {"type": "command", "label": "Dokument Defaults", "command": lambda: self._open_local_settings_dialog("document_defaults")},
                {"type": "command", "label": "Accessibility", "command": lambda: self._open_local_settings_dialog("accessibility")},
                {"type": "command", "label": "Backup", "command": lambda: self._open_local_settings_dialog("backup")},
            ]

            return [
                {"type": "command", "label": "Neue Markdown-Datei…", "command": self.create_new_markdown_file},
                {"type": "command", "label": "Markdown öffnen…", "command": self.pick_input},
                {"type": "command", "label": "Speichern unter…", "command": self.save_markdown_file_as},
                {"type": "submenu", "label": "Zuletzt geöffnet", "items": recent_items},
                {"type": "separator"},
                {"type": "command", "label": "Einstellungen…", "command": self._open_local_settings_dialog},
                {"type": "submenu", "label": "Einstellungen direkt", "items": settings_items},
                {"type": "separator"},
                {"type": "command", "label": "Beenden", "command": self.root.destroy},
            ]

    def _menu_view_items(self):
            """Builds rows for top menu Ansicht including radio-like entries."""

            theme_items = []
            for theme_key in THEME_ORDER:
                label = THEMES.get(theme_key, {}).get("label", theme_key)
                theme_items.append(
                    {
                        "type": "radio",
                        "label": label,
                        "checked": self.theme_var.get() == theme_key,
                        "command": (lambda key=theme_key: (self.theme_var.set(key), self._on_theme_changed())),
                    }
                )

            return [
                {
                    "type": "radio",
                    "label": "Seitenbreite",
                    "checked": self.preview_fit_mode_var.get() == VIEW_FIT_WIDTH,
                    "command": lambda: self.set_view_fit_mode(VIEW_FIT_WIDTH),
                },
                {
                    "type": "radio",
                    "label": "Ganze Seite",
                    "checked": self.preview_fit_mode_var.get() == VIEW_FIT_PAGE,
                    "command": lambda: self.set_view_fit_mode(VIEW_FIT_PAGE),
                },
                {"type": "separator"},
                {
                    "type": "radio",
                    "label": "Einzelseite",
                    "checked": self.preview_layout_mode_var.get() == VIEW_LAYOUT_SINGLE,
                    "command": lambda: self.set_preview_layout_mode(VIEW_LAYOUT_SINGLE),
                },
                {
                    "type": "radio",
                    "label": "Seiten nebeneinander",
                    "checked": self.preview_layout_mode_var.get() == VIEW_LAYOUT_STRIP,
                    "command": lambda: self.set_preview_layout_mode(VIEW_LAYOUT_STRIP),
                },
                {
                    "type": "radio",
                    "label": "Seiten untereinander",
                    "checked": self.preview_layout_mode_var.get() == VIEW_LAYOUT_STACK,
                    "command": lambda: self.set_preview_layout_mode(VIEW_LAYOUT_STACK),
                },
                {"type": "separator"},
                {
                    "type": "radio",
                    "label": "Nur Vorschau",
                    "checked": self.editor_view_mode_var.get() == EDITOR_VIEW_PREVIEW_ONLY,
                    "command": lambda: self._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY),
                },
                {
                    "type": "radio",
                    "label": "Vorschau und Schreibbereich",
                    "checked": self.editor_view_mode_var.get() == EDITOR_VIEW_BOTH,
                    "command": lambda: self._set_editor_view_mode(EDITOR_VIEW_BOTH),
                },
                {
                    "type": "radio",
                    "label": "Nur Schreibbereich",
                    "checked": self.editor_view_mode_var.get() == EDITOR_VIEW_EDITOR_ONLY,
                    "command": lambda: self._set_editor_view_mode(EDITOR_VIEW_EDITOR_ONLY),
                },
                {"type": "separator"},
                {
                    "type": "command",
                    "label": "Lernhilfenansicht",
                    "command": self.open_help_preview_window,
                },
                {"type": "separator"},
                {"type": "submenu", "label": "Theme", "items": theme_items},
            ]

    def _menu_top_definitions(self):
            """Defines top-level menus with mnemonic keys and row builders."""

            return [
                {"key": "datei", "label": "Datei", "underline": 0, "alt": "d", "items_fn": self._menu_file_items},
                {"key": "ansicht", "label": "Ansicht", "underline": 0, "alt": "a", "items_fn": self._menu_view_items},
                {"key": "shortcuts", "label": "Shortcuts", "underline": 0, "alt": "s", "items_fn": self._menu_shortcuts_items},
            ]

    def _menu_execute_command(self, command):
            """Runs menu command and closes all popups afterwards."""

            self._close_all_menu_popups()
            if callable(command):
                command()

    def _open_menu_popup(self, anchor_widget, items: list[dict], level: int, top_key: str):
            """Creates one popup window for a menu level and renders row widgets."""

            existing_stack = list(getattr(self, "_menu_popup_stack", []))
            if level < len(existing_stack):
                existing_popup = existing_stack[level]
                if existing_popup is not None and existing_popup.winfo_exists():
                    if getattr(existing_popup, "_menu_anchor_widget", None) == anchor_widget:
                        return

            self._close_menu_popups_from_level(level)

            style = self._menu_popup_style()
            popup = tk.Toplevel(self.root)
            popup.overrideredirect(True)
            popup.transient(self.root)
            popup.attributes("-topmost", True)
            popup.configure(bg=style["popup_border"], bd=1, highlightthickness=0)

            body = tk.Frame(popup, bg=style["popup_bg"], bd=0, highlightthickness=0)
            body.pack(fill="both", expand=True, padx=1, pady=1)
            popup._menu_body = body
            popup._menu_anchor_widget = anchor_widget

            if level == 0:
                x_pos = anchor_widget.winfo_rootx()
                y_pos = anchor_widget.winfo_rooty() + anchor_widget.winfo_height()
            else:
                x_pos = anchor_widget.winfo_rootx() + anchor_widget.winfo_width() - 1
                y_pos = anchor_widget.winfo_rooty()

            popup.geometry(f"+{int(x_pos)}+{int(y_pos)}")
            popup.lift()
            popup.update_idletasks()

            default_bg = style["popup_bg"]
            default_fg = style["popup_fg"]
            hover_bg = style["hover_bg"]
            hover_fg = style["hover_fg"]

            for row_index, item in enumerate(items):
                row_type = item.get("type", "command")
                if row_type == "separator":
                    separator = tk.Frame(body, height=1, bg=style["separator"], bd=0, highlightthickness=0)
                    separator.pack(fill="x", padx=8, pady=4)
                    continue

                text = item.get("label", "")
                prefix = ""
                suffix = ""
                fg = default_fg

                if row_type == "radio":
                    prefix = "● " if bool(item.get("checked", False)) else "○ "
                if row_type == "submenu":
                    suffix = "   ▸"
                if row_type == "disabled":
                    fg = style["muted_fg"]

                row = tk.Label(
                    body,
                    text=f"{prefix}{text}{suffix}",
                    anchor="w",
                    justify="left",
                    bg=default_bg,
                    fg=fg,
                    padx=10,
                    pady=6,
                    font=("Segoe UI", 9),
                )
                row.pack(fill="x")

                if row_type == "disabled":
                    continue

                def _set_row_hover(widget=row, active=True):
                    try:
                        if widget.winfo_exists():
                            widget.configure(bg=hover_bg if active else default_bg, fg=hover_fg if active else fg)
                    except tk.TclError:
                        pass

                if row_type == "submenu":
                    submenu_items = list(item.get("items", []))

                    def _open_submenu(_event=None, parent_row=row, sub_items=submenu_items, next_level=level + 1):
                        self._open_menu_popup(parent_row, sub_items, next_level, top_key=top_key)

                    row.bind("<Enter>", lambda _event, widget=row: _set_row_hover(widget, True))
                    row.bind("<Leave>", lambda _event, widget=row: _set_row_hover(widget, False))
                    row.bind("<Button-1>", _open_submenu)
                    continue

                command = item.get("command")
                row.bind("<Enter>", lambda _event, widget=row: _set_row_hover(widget, True))
                row.bind("<Leave>", lambda _event, widget=row: _set_row_hover(widget, False))
                row.bind("<Button-1>", lambda _event, cmd=command: self._menu_execute_command(cmd))

            self._menu_popup_stack.append(popup)
            self._active_menu_key = top_key
            self._refresh_custom_menu_theme()
            self._schedule_menu_focus_guard()

    def _open_top_menu(self, menu_definition: dict):
            """Opens one top-level menu popup below its strip button."""

            shared_menu_bar = getattr(self, "_shared_menu_bar", None)
            if shared_menu_bar is not None:
                target_key = menu_definition.get("key")
                for shared_definition in getattr(shared_menu_bar, "definitions", ()): 
                    if getattr(shared_definition, "key", None) == target_key:
                        shared_menu_bar.open_top_menu(shared_definition)
                        self._refresh_custom_menu_theme()
                        return

            key = menu_definition.get("key")
            button = getattr(self, "_menu_top_buttons", {}).get(key)
            if button is None or not button.winfo_exists():
                return

            if key == getattr(self, "_active_menu_key", None) and getattr(self, "_menu_popup_stack", []):
                self._close_all_menu_popups()
                return

            items = list(menu_definition.get("items_fn", lambda: [])())
            self._open_menu_popup(button, items, level=0, top_key=key)

    def _open_top_menu_by_key(self, key: str):
            """Opens top-level menu by mnemonic key."""

            shared_menu_bar = getattr(self, "_shared_menu_bar", None)
            if shared_menu_bar is not None:
                for shared_definition in getattr(shared_menu_bar, "definitions", ()): 
                    if getattr(shared_definition, "key", None) == key:
                        shared_menu_bar.open_top_menu(shared_definition)
                        self._refresh_custom_menu_theme()
                        return

            for definition in getattr(self, "_menu_top_definitions_cache", []):
                if definition.get("key") == key:
                    self._open_top_menu(definition)
                    return

    def _build_custom_menu_strip(self):
            """Builds themed custom menu strip with top-level buttons and mnemonics."""

            if SharedCustomMenuBar is not None and SharedMenuDefinition is not None:
                old_shared = getattr(self, "_shared_menu_bar", None)
                if old_shared is not None:
                    old_shared.destroy()

                definitions = self._menu_top_definitions()
                self._menu_top_definitions_cache = definitions

                shared_definitions = []
                for definition in definitions:
                    items_fn = definition.get("items_fn", lambda: [])

                    def _provider(func=items_fn):
                        return self._to_shared_menu_items(list(func()))

                    shared_definitions.append(
                        SharedMenuDefinition(
                            key=str(definition.get("key", "")),
                            label=str(definition.get("label", "")),
                            alt=str(definition.get("alt", "")),
                            items_provider=_provider,
                        )
                    )

                self._shared_menu_bar = SharedCustomMenuBar(
                    self.root,
                    shared_definitions,
                    theme_key=self.theme_var.get(),
                )
                self._shared_menu_bar.build()
                self._custom_menu_strip = self._shared_menu_bar.strip
                self._menu_top_buttons = {}
                self._menu_popup_stack = list(getattr(self._shared_menu_bar, "_popup_stack", []))
                self._active_menu_key = getattr(self._shared_menu_bar, "_active_key", None)
                return

            old_strip = getattr(self, "_custom_menu_strip", None)
            if old_strip is not None and old_strip.winfo_exists():
                try:
                    old_strip.destroy()
                except tk.TclError:
                    pass

            self._close_all_menu_popups()
            self._menu_top_buttons = {}

            theme = get_theme(self.theme_var.get())
            strip = tk.Frame(self.root, bg=theme["bg_surface"], highlightthickness=1, highlightbackground=theme["border"], bd=0)
            root_children = [child for child in self.root.winfo_children() if child is not strip]
            if root_children:
                strip.pack(fill="x", side="top", before=root_children[0])
            else:
                strip.pack(fill="x", side="top")
            self._custom_menu_strip = strip

            definitions = self._menu_top_definitions()
            self._menu_top_definitions_cache = definitions

            for definition in definitions:
                key = definition["key"]
                button = tk.Button(
                    strip,
                    text=definition["label"],
                    underline=int(definition.get("underline", 0)),
                    relief="flat",
                    bd=0,
                    padx=10,
                    pady=5,
                    bg=theme["bg_surface"],
                    fg=theme["fg_primary"],
                    activebackground=theme["accent_soft"],
                    activeforeground=theme["fg_primary"],
                    highlightthickness=0,
                    command=lambda d=definition: self._open_top_menu(d),
                )
                button.pack(side="left", padx=(0, 2))
                self._menu_top_buttons[key] = button

            self._bind_custom_menu_global_handlers()

    def _refresh_custom_menu_model(self):
            """Refresh hook used by persistence when recent files change."""

            shared_menu_bar = getattr(self, "_shared_menu_bar", None)
            if shared_menu_bar is not None:
                shared_menu_bar.build()
                self._custom_menu_strip = shared_menu_bar.strip
                self._menu_popup_stack = list(getattr(shared_menu_bar, "_popup_stack", []))
                self._active_menu_key = getattr(shared_menu_bar, "_active_key", None)
                return

            active_key = getattr(self, "_active_menu_key", None)
            has_open_popups = bool(getattr(self, "_menu_popup_stack", []))
            if has_open_popups:
                self._close_all_menu_popups()
                if active_key is not None:
                    self._open_top_menu_by_key(active_key)

    def _build_menu(self):
            """Builds a themed custom menu strip replacing native Tk menubar."""

            self.root.config(menu="")
            self.recent_menu = None
            self._build_custom_menu_strip()

    def _get_input_path_if_exists(self):
            """Get input path if exists."""
            input_text = self._clean_path_text(self.input_var.get())
            if not input_text:
                return None

            path = Path(input_text)
            return path if path.exists() else None

    def _warn_if_bw_mode_has_color_mentions(self, previous_profile: str | None = None):
            """Warn if bw mode has color mentions."""
            current_profile = normalize_color_profile(self.design_color_profile_var.get())
            input_path = self._get_input_path_if_exists()
            mentions = detect_bw_mode_color_warning_mentions(
                input_path=input_path,
                current_profile=current_profile,
                previous_profile=previous_profile,
                bw_profiles=BW_COLOR_PROFILE_KEYS,
            )
            if not mentions:
                return

            mentions_text = ", ".join(mentions)
            profile_label = COLOR_PROFILE_LABELS.get(current_profile, current_profile)
            messagebox.showwarning(
                "Farbhinweis im S/W-Modus",
                "Im Aufgabenblatt wurden Farbbegriffe erkannt "
                f"({mentions_text}).\n\n"
                f"Aktives Profil: {profile_label}. Bitte prüfen, ob die Aufgabenstellung auch in Schwarz-Weiß eindeutig ist.",
            )

    def _iter_shortcut_menu_labels(self):
            """Liefert deduplizierte Shortcut-Hinweise in definierter Reihenfolge."""

            preferences = getattr(self, "user_preferences", {})
            if not bool(preferences.get("shortcuts_menu_hints_visible", True)):
                return

            yield from self.shortcut_manager.iter_menu_labels(self.shortcut_bindings)

    def _refresh_zoom_label(self):
            """Aktualisiert den Zoomtext (immer seitenbreitenbezogene Prozent)."""

            display_zoom_percent = self._get_display_zoom_percent()
            self.zoom_info_var.set(f"Zoom: {display_zoom_percent}%")

    def _get_fit_scales(self, image: Image.Image):
            """Berechnet Skalierung für Seitenbreite und ganze Seite."""

            frame_width, frame_height = self._get_preview_frame_size()
            source_w, source_h = image.size
            return get_fit_scales(frame_width, frame_height, source_w, source_h)

    def _get_display_zoom_percent(self):
            """Liefert Zoomanzeige immer relativ zur Seitenbreite."""

            return int(round(self.zoom_percent))

    def set_view_fit_mode(self, fit_mode):
            """Setzt Ansichts-Preset als seitenbreitenbezogenen Zoomwert."""

            if fit_mode not in VIEW_MODE_LABELS:
                return

            self.preview_fit_mode_var.set(fit_mode)

            if self.preview_images:
                page = self.preview_images[self.current_page_index]
                width_fit_scale, page_fit_scale = self._get_fit_scales(page)

                if fit_mode == VIEW_FIT_WIDTH:
                    target_zoom_percent = 100.0
                else:
                    ratio = (page_fit_scale / width_fit_scale) if width_fit_scale > 0 else 1.0
                    target_zoom_percent = 100.0 * ratio

                self.zoom_percent = clamp(target_zoom_percent, PREVIEW_ZOOM_MIN_PERCENT, PREVIEW_ZOOM_MAX_PERCENT)

            self._refresh_zoom_label()
            if self.preview_images:
                x_view_start = self.preview_canvas.xview()[0]
                y_view_start = self.preview_canvas.yview()[0]
                self._show_current_page(
                    reset_scroll=False,
                    x_view_start=x_view_start,
                    y_view_start=y_view_start,
                )
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()

    def set_preview_layout_mode(self, layout_mode):
            """Schaltet zwischen Einzelseite und Seitenband um."""

            if layout_mode not in {VIEW_LAYOUT_SINGLE, VIEW_LAYOUT_STRIP, VIEW_LAYOUT_STACK}:
                return

            self.preview_layout_mode_var.set(layout_mode)
            if self.preview_images:
                self._show_current_page(reset_scroll=True)
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()
