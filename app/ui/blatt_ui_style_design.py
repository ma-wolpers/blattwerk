"""Gestaltung des Dokuments: Farb-, Schrift- und Groessenprofil, Farbfelder mit Tooltip und
der Hinweis auf Farbangaben im Schwarzweiss-Profil.
"""

from __future__ import annotations

from pathlib import Path
from .dialog_services import messagebox
from ..core.color_mentions import detect_bw_mode_color_warning_mentions
from ..core.build_requests import WorksheetDesignOptions
from ..styles.blatt_styles import (
    DEFAULT_FONT_SIZE_PROFILE,
    FONT_SIZE_PROFILE_LABELS,
    FONT_SIZE_PROFILE_ORDER,
    normalize_font_profile,
    normalize_font_size_profile,
)
from ..styles.worksheet_design import (
    COLOR_PROFILE_LABELS,
    COLOR_PROFILE_ORDER,
    get_color_profile_preview,
    normalize_color_profile,
)
from .ui_theme import get_theme
from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()

from bw_gui.contracts.screen_geometry import Rect, Side
from bw_gui.runtime.screen_placement import place_overlay_now
from bw_gui.runtime import ui, widgets
from bw_gui.runtime.overlay_stack import OverlayCategory, register_overlay

BW_COLOR_PROFILE_KEYS = {"bw"}


class BlattwerkAppStyleDesignMixin:
    """Verwaltet die Gestaltungsprofile der Vorschau."""

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

    def _sync_font_size_profile_combo(self):
            """Sync font size profile combo."""
            if not hasattr(self, "font_size_profile_combo"):
                return

            current_key = normalize_font_size_profile(self.design_font_size_profile_var.get())
            self.font_size_profile_combo.set(FONT_SIZE_PROFILE_LABELS.get(current_key, FONT_SIZE_PROFILE_LABELS[DEFAULT_FONT_SIZE_PROFILE]))

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
            # Tooltip: sperrt nie Kuerzel (der fruehere Scan zaehlte ihn zufaellig als Dialog).
            register_overlay(tooltip, OverlayCategory.TRANSIENT, toplevel=tooltip)
            tooltip.overrideredirect(True)

            label = widgets.Label(
                tooltip,
                text=COLOR_PROFILE_LABELS.get(profile_key, profile_key),
                style="Muted.TLabel",
                padding=(6, 3),
            )
            label.pack()
            tooltip.update_idletasks()

            # Below-right of the cursor, flipping above when it does not fit; clamped to
            # the work area of the cursor's monitor (bw-gui screen-placement contract).
            cursor_x = int(getattr(event, "x_root", self.root.winfo_rootx()))
            cursor_y = int(getattr(event, "y_root", self.root.winfo_rooty()))
            place_overlay_now(
                tooltip,
                anchor=Rect(cursor_x + 10, cursor_y, cursor_x + 11, cursor_y + 2),
                placement=(Side.BELOW, Side.ABOVE),
                tk_context=self.root,
                gap=10,
            )
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
