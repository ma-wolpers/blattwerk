"""GUI mixin module."""

from __future__ import annotations

from pathlib import Path
from PIL import Image

from bw_libs.shared_gui_core import ensure_bw_gui_on_path
from .dialog_services import messagebox
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
    apply_window_theme,
    configure_ttk_theme,
    get_theme,
    style_canvas,
    style_preview_placeholder,
)

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets
from bw_gui.menu import MenuItem as SharedMenuItem

BW_COLOR_PROFILE_KEYS = {"bw"}

class BlattwerkAppStyleMixin:
    """Kapselt Theme-, Menü- und Designprofil-Logik der GUI."""
    def _on_worksheet_design_changed(self):
            """On worksheet design changed."""
            self._refresh_color_profile_swatches()
            self._sync_font_profile_combo()
            self._sync_font_size_profile_combo()
            self._save_ui_settings()
            self.refresh_preview()

    def _cycle_design_color_profile(self, step: int = 1):
            """Cycle design color profile."""
            previous_profile = self.design_color_profile_var.get()
            self._cycle_option(self.design_color_profile_var, COLOR_PROFILE_ORDER, step=step)
            self._warn_if_bw_mode_has_color_mentions(previous_profile=previous_profile)
            self._on_worksheet_design_changed()

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
            """Reflects the current font profile onto the Schrift menu button/menu-radio state."""
            if not hasattr(self, "font_profile_menubutton"):
                return

            current_key = normalize_font_profile(self.design_font_profile_var.get())
            self._font_profile_menu_var.set(current_key)
            self.font_profile_menubutton.configure(
                text=FONT_PROFILE_LABELS.get(current_key, FONT_PROFILE_LABELS[DEFAULT_FONT_PROFILE])
            )

    def _sync_font_size_profile_combo(self):
            """Sync font size profile combo."""
            if not hasattr(self, "font_size_profile_combo"):
                return

            current_key = normalize_font_size_profile(self.design_font_size_profile_var.get())
            self.font_size_profile_combo.set(FONT_SIZE_PROFILE_LABELS.get(current_key, FONT_SIZE_PROFILE_LABELS[DEFAULT_FONT_SIZE_PROFILE]))

    def _apply_theme(self, redraw_preview=True):
            """Wendet das aktive Theme auf Canvas, Editor und Zusatzfenster an.

            Hauptfenster-Hintergrund/-Chrome und Menüband laufen inzwischen immer
            über BwBaseWindow.apply_theme() (aufgerufen von apply_theme() bzw.
            _apply_user_preferences_live(), beide vor jedem _apply_theme()-Aufruf) —
            hier daher nicht mehr redundant erneut angewendet.
            """

            theme_key = self.theme_var.get()
            theme = get_theme(theme_key)

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

            tooltip = ui.Toplevel(self.root)
            tooltip.overrideredirect(True)

            label = widgets.Label(
                tooltip,
                text=COLOR_PROFILE_LABELS.get(profile_key, profile_key),
                style="Muted.TLabel",
                padding=(6, 3),
            )
            label.pack()
            tooltip.update_idletasks()

            x_pos = int(getattr(event, "x_root", self.root.winfo_rootx()) + 10)
            y_pos = int(getattr(event, "y_root", self.root.winfo_rooty()) + 12)

            screen_width = max(1, int(self.root.winfo_screenwidth()))
            screen_height = max(1, int(self.root.winfo_screenheight()))
            tip_width = max(1, int(tooltip.winfo_reqwidth()))
            tip_height = max(1, int(tooltip.winfo_reqheight()))
            margin = 8

            if y_pos + tip_height + margin > screen_height:
                y_pos = int(getattr(event, "y_root", self.root.winfo_rooty()) - tip_height - 10)

            max_x = max(margin, screen_width - tip_width - margin)
            max_y = max(margin, screen_height - tip_height - margin)
            x_pos = max(margin, min(x_pos, max_x))
            y_pos = max(margin, min(y_pos, max_y))

            tooltip.geometry(f"+{x_pos}+{y_pos}")
            self._swatch_tooltip = tooltip

    def _hide_swatch_tooltip(self):
            """Hide swatch tooltip."""
            if self._swatch_tooltip is None:
                return

            try:
                self._swatch_tooltip.destroy()
            except ui.TclError:
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

    def _refresh_custom_menu_model(self):
            """Refresh hook used by persistence when recent files change."""

            menu_bar = getattr(self, "_menu_bar", None)
            if menu_bar is not None:
                menu_bar.build()

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
                {"type": "command", "label": "Dokumenttypen", "command": lambda: self._open_local_settings_dialog("document_types")},
                {"type": "command", "label": "Accessibility", "command": lambda: self._open_local_settings_dialog("accessibility")},
                {"type": "command", "label": "Backup", "command": lambda: self._open_local_settings_dialog("backup")},
            ]

            return [
                {"type": "command", "label": "Neues Dokument…", "command": self.create_new_markdown_file},
                {"type": "command", "label": "Markdown öffnen…", "command": self.pick_input},
                {"type": "command", "label": "Speichern unter…", "command": self.save_markdown_file_as},
                {"type": "submenu", "label": "Zuletzt geöffnet", "items": recent_items},
                {"type": "separator"},
                {"type": "submenu", "label": "Einstellungen", "items": settings_items},
                {"type": "separator"},
                {"type": "command", "label": "Beenden", "command": self.root.destroy},
            ]

    def _menu_extras_items(self):
            """Builds rows for top menu Extras."""

            return [
                {
                    "type": "command",
                    "label": "Markdown-Tabellen in Blattwerk-Tabellen umwandeln",
                    "command": self._convert_markdown_tables_in_active_tab,
                },
                {"type": "separator"},
                {
                    "type": "command",
                    "label": "Dokumentation…",
                    "command": self.open_help_docs_dialog,
                },
            ]

    def _menu_view_items(self):
            """Builds rows for top menu Ansicht including radio-like entries."""

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
            ]

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
