"""GUI mixin module."""

from __future__ import annotations

from pathlib import Path
from PIL import Image
import tkinter as tk
from tkinter import messagebox, ttk

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
    THEME_ORDER,
    apply_window_theme,
    configure_ttk_theme,
    get_theme,
    populate_theme_menu,
    style_canvas,
    style_preview_placeholder,
)

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
                if hasattr(self, "_configure_editor_syntax_tags"):
                    self._configure_editor_syntax_tags()

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

    def _build_menu(self):
            """Erstellt Menüleiste inkl. zuletzt geöffneter Dateien."""

            menubar = tk.Menu(self.root)

            file_menu = tk.Menu(menubar, tearoff=False)
            file_menu.add_command(label="Neue Markdown-Datei…", command=self.create_new_markdown_file)
            file_menu.add_command(label="Markdown öffnen…", command=self.pick_input)

            self.recent_menu = tk.Menu(file_menu, tearoff=False)
            file_menu.add_cascade(label="Zuletzt geöffnet", menu=self.recent_menu)
            self._refresh_recent_menu()

            file_menu.add_separator()
            file_menu.add_command(label="Einstellungen…", command=self._open_local_settings_dialog)

            settings_tabs_menu = tk.Menu(file_menu, tearoff=False)
            settings_tabs_menu.add_command(label="Allgemein", command=lambda: self._open_local_settings_dialog("general"))
            settings_tabs_menu.add_command(label="Editor Vervollständigung", command=lambda: self._open_local_settings_dialog("editor_completion"))
            settings_tabs_menu.add_command(label="Editor Diagnostik", command=lambda: self._open_local_settings_dialog("editor_diagnostics"))
            settings_tabs_menu.add_command(label="Ansicht und Layout", command=lambda: self._open_local_settings_dialog("view_layout"))
            settings_tabs_menu.add_command(label="Design und Theme", command=lambda: self._open_local_settings_dialog("design_theme"))
            settings_tabs_menu.add_command(label="Export", command=lambda: self._open_local_settings_dialog("export"))
            settings_tabs_menu.add_command(label="Shortcuts", command=lambda: self._open_local_settings_dialog("shortcuts"))
            settings_tabs_menu.add_command(label="Identitaet und Copyright", command=lambda: self._open_local_settings_dialog("identity"))
            settings_tabs_menu.add_command(label="Dokument Defaults", command=lambda: self._open_local_settings_dialog("document_defaults"))
            settings_tabs_menu.add_command(label="Accessibility", command=lambda: self._open_local_settings_dialog("accessibility"))
            settings_tabs_menu.add_command(label="Backup", command=lambda: self._open_local_settings_dialog("backup"))
            file_menu.add_cascade(label="Einstellungen direkt", menu=settings_tabs_menu)

            file_menu.add_command(label="Beenden", command=self.root.destroy)

            menubar.add_cascade(label="Datei", menu=file_menu)

            view_menu = tk.Menu(menubar, tearoff=False)
            view_menu.add_radiobutton(
                label="Seitenbreite",
                value=VIEW_FIT_WIDTH,
                variable=self.preview_fit_mode_var,
                command=lambda: self.set_view_fit_mode(VIEW_FIT_WIDTH),
            )
            view_menu.add_radiobutton(
                label="Ganze Seite",
                value=VIEW_FIT_PAGE,
                variable=self.preview_fit_mode_var,
                command=lambda: self.set_view_fit_mode(VIEW_FIT_PAGE),
            )
            view_menu.add_separator()
            view_menu.add_radiobutton(
                label="Einzelseite",
                value=VIEW_LAYOUT_SINGLE,
                variable=self.preview_layout_mode_var,
                command=lambda: self.set_preview_layout_mode(VIEW_LAYOUT_SINGLE),
            )
            view_menu.add_radiobutton(
                label="Seiten nebeneinander",
                value=VIEW_LAYOUT_STRIP,
                variable=self.preview_layout_mode_var,
                command=lambda: self.set_preview_layout_mode(VIEW_LAYOUT_STRIP),
            )
            view_menu.add_radiobutton(
                label="Seiten untereinander",
                value=VIEW_LAYOUT_STACK,
                variable=self.preview_layout_mode_var,
                command=lambda: self.set_preview_layout_mode(VIEW_LAYOUT_STACK),
            )
            view_menu.add_separator()
            view_menu.add_radiobutton(
                label="Nur Vorschau",
                value=EDITOR_VIEW_PREVIEW_ONLY,
                variable=self.editor_view_mode_var,
                command=lambda: self._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY),
            )
            view_menu.add_radiobutton(
                label="Vorschau und Schreibbereich",
                value=EDITOR_VIEW_BOTH,
                variable=self.editor_view_mode_var,
                command=lambda: self._set_editor_view_mode(EDITOR_VIEW_BOTH),
            )
            view_menu.add_radiobutton(
                label="Nur Schreibbereich",
                value=EDITOR_VIEW_EDITOR_ONLY,
                variable=self.editor_view_mode_var,
                command=lambda: self._set_editor_view_mode(EDITOR_VIEW_EDITOR_ONLY),
            )
            view_menu.add_separator()

            theme_menu = tk.Menu(view_menu, tearoff=False)
            populate_theme_menu(theme_menu, self.theme_var, self._on_theme_changed)
            view_menu.add_cascade(label="Theme", menu=theme_menu)
            menubar.add_cascade(label="Ansicht", menu=view_menu)

            shortcuts_menu = tk.Menu(menubar, tearoff=False)
            for menu_label in self._iter_shortcut_menu_labels():
                shortcuts_menu.add_command(label=menu_label, state="disabled")
            menubar.add_cascade(label="Shortcuts", menu=shortcuts_menu)

            self.root.config(menu=menubar)

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

    def set_preview_layout_mode(self, layout_mode):
            """Schaltet zwischen Einzelseite und Seitenband um."""

            if layout_mode not in {VIEW_LAYOUT_SINGLE, VIEW_LAYOUT_STRIP, VIEW_LAYOUT_STACK}:
                return

            self.preview_layout_mode_var.set(layout_mode)
            if self.preview_images:
                self._show_current_page(reset_scroll=True)
