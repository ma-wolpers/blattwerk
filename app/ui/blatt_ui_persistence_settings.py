"""Einstellungen: Einstellungsdialog, Nutzerpraeferenzen live anwenden, UI-Einstellungen
laden und speichern, lokale Systemeinstellungen.
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()

from bw_gui.runtime import BwBaseWindow, widgets
from .blatt_ui_editor_panels import (
    EDITOR_PANELS_SETTINGS_KEY,
    normalize_editor_panels_collapsed,
)
from .ui_theme import normalize_theme_key
from ..storage.local_config_store import (
    load_system_settings,
    load_ui_settings,
    load_user_preferences,
    migrate_legacy_config,
    save_system_settings,
    save_ui_settings,
    save_user_preferences,
)
from ..storage.system_settings_adapter import normalize_system_settings_payload
from ..storage.user_preferences_adapter import normalize_user_preferences
from ..storage.history_paths_adapter import normalize_recent_entries
from ..styles.ui_profile_adapter import (
    normalize_design_profiles_for_persistence,
    resolve_persisted_design_profiles,
)
from ..styles.worksheet_design import COLOR_PROFILE_ORDER
from .settings_dialog import SettingsDialog


class BlattwerkAppPersistenceSettingsMixin:
    """Laedt, speichert und wendet Nutzer- und UI-Einstellungen an."""


    def _open_local_settings_dialog(self, initial_tab: str | None = None):
            """Öffnet den zentralen tab-basierten Einstellungsdialog."""
            current = self._build_current_user_preferences_payload()

            dialog = SettingsDialog(
                self.root,
                theme_key=self.theme_var.get(),
                preferences=current,
                initial_tab=initial_tab,
                on_live_apply=self._apply_user_preferences_live,
                on_commit=self._commit_user_preferences,
            )


    def _build_current_user_preferences_payload(self) -> dict[str, object]:
            payload = normalize_user_preferences(getattr(self, "user_preferences", {}))
            payload["max_recent_files"] = int(str(getattr(self, "max_recent_files", payload.get("max_recent_files", 5))))
            payload["default_theme_key"] = self.theme_var.get()
            payload["default_contrast_profile"] = self.preview_contrast_var.get()
            payload["default_color_profile"] = self.design_color_profile_var.get()
            payload["default_font_profile"] = self.design_font_profile_var.get()
            payload["default_font_size_profile"] = self.design_font_size_profile_var.get()
            payload["startup_fit_mode"] = self.preview_fit_mode_var.get()
            payload["startup_layout_mode"] = self.preview_layout_mode_var.get()
            payload["startup_editor_view_mode"] = self.editor_view_mode_var.get()
            payload["diagnostics_debounce_ms"] = int(str(getattr(self, "_editor_diagnostics_delay_ms", payload.get("diagnostics_debounce_ms", 350))))
            payload["outline_debounce_ms"] = int(str(getattr(self, "_editor_outline_delay_ms", payload.get("outline_debounce_ms", 220))))
            payload["preview_auto_refresh_on_edit_idle_enabled"] = bool(
                getattr(
                    self,
                    "_preview_auto_refresh_on_edit_idle_enabled",
                    payload.get("preview_auto_refresh_on_edit_idle_enabled", False),
                )
            )
            payload["preview_auto_refresh_on_edit_idle_delay_ms"] = int(
                str(
                    getattr(
                        self,
                        "_preview_auto_refresh_on_edit_idle_delay_ms",
                        payload.get("preview_auto_refresh_on_edit_idle_delay_ms", 1200),
                    )
                )
            )
            return normalize_user_preferences(payload)


    def _apply_user_preferences_live(self, preferences: dict[str, object]):
            normalized = normalize_user_preferences(preferences)
            self.user_preferences = dict(normalized)
            self.theme_var.set(normalized["default_theme_key"])
            # This path changes the theme independently of apply_theme(), so it must
            # sync the shell itself (shell theme storage + menu-bar radio refresh +
            # window chrome) — otherwise self.theme_key silently drifts from theme_var.
            BwBaseWindow.apply_theme(self, self.theme_var.get())
            self.design_color_profile_var.set(normalized["default_color_profile"])
            self.design_font_profile_var.set(normalized["default_font_profile"])
            self.design_font_size_profile_var.set(normalized["default_font_size_profile"])
            self.preview_contrast_var.set(normalized["default_contrast_profile"])
            self._responsive_controls_wrap_enabled = bool(normalized.get("responsive_controls_wrap", True))
            self._reduce_motion = bool(normalized.get("reduce_motion", False))
            self._ui_density = str(normalized.get("ui_density", "comfort") or "comfort")

            self._editor_diagnostics_delay_ms = int(str(normalized["diagnostics_debounce_ms"]))
            self._editor_outline_delay_ms = int(str(normalized["outline_debounce_ms"]))
            self._preview_auto_refresh_on_edit_idle_enabled = bool(
                normalized.get("preview_auto_refresh_on_edit_idle_enabled", False)
            )
            self._preview_auto_refresh_on_edit_idle_delay_ms = int(
                str(normalized.get("preview_auto_refresh_on_edit_idle_delay_ms", 1200))
            )
            if not self._preview_auto_refresh_on_edit_idle_enabled and hasattr(
                self, "_cancel_editor_auto_preview_refresh"
            ):
                self._cancel_editor_auto_preview_refresh()

            editor_mode = str(normalized["startup_editor_view_mode"])
            fit_mode = str(normalized["startup_fit_mode"])
            layout_mode = str(normalized["startup_layout_mode"])

            self.editor_view_mode_var.set(editor_mode)
            self.preview_fit_mode_var.set(fit_mode)
            self.preview_layout_mode_var.set(layout_mode)

            if getattr(self, "editor_preview_paned", None) is not None:
                self._set_editor_view_mode(editor_mode)
            if getattr(self, "preview_canvas", None) is not None:
                self.set_view_fit_mode(fit_mode)
                self.set_preview_layout_mode(layout_mode)

            ui_scale_percent = int(str(normalized.get("ui_scale_percent", 100)))
            try:
                base_scaling = float(getattr(self, "_default_tk_scaling", 1.0) or 1.0)
                self.root.tk.call(
                    "tk",
                    "scaling",
                    max(0.7, base_scaling * (ui_scale_percent / 100.0)),
                )
            except Exception:
                pass

            try:
                style = widgets.Style(self.root)
                compact = self._ui_density == "compact"
                button_padding = (8, 3) if compact else (12, 6)
                option_padding = (2, 1) if compact else (6, 2)
                style.configure("TButton", padding=button_padding)
                style.configure("TRadiobutton", padding=option_padding)
                style.configure("TCheckbutton", padding=option_padding)
            except Exception:
                pass

            self._sync_font_profile_combo()
            self._sync_font_size_profile_combo()
            self._apply_theme(redraw_preview=True)
            if hasattr(self, "_reflow_responsive_sections"):
                self.root.after_idle(self._reflow_responsive_sections)
            if hasattr(self, "_hide_swatch_tooltip") and not bool(normalized.get("tooltips_enabled", True)):
                self._hide_swatch_tooltip()
            if getattr(self, "root", None) is not None:
                self._refresh_custom_menu_model()


    def _commit_user_preferences(self, preferences: dict[str, object]):
            normalized = normalize_user_preferences(preferences)

            self._apply_local_system_settings(
                max_recent_files=int(str(normalized["max_recent_files"])),
            )
            self._apply_user_preferences_live(normalized)

            self.user_preferences = normalized
            save_user_preferences(self.user_preferences)
            self._save_ui_settings()


    def _maybe_apply_startup_file_preference(self):
            """Öffnet beim Start die übergebene Datei, sonst optional die zuletzt verwendete.

            Eine explizit übergebene Datei (Kommandozeile, "Öffnen mit") hat Vorrang vor
            ``start_with_last_file``: wer eine Datei öffnet, will genau diese sehen.
            """
            if getattr(self, "_startup_file", None):
                # Not opened here: opening renders a preview, and a start that is still inside
                # its constructor cannot yet accept files handed over by parallel starts
                # ("Öffnen mit" on several files at once). The first poll of
                # ``start_external_open_listener`` opens it once the event loop runs.
                return
            preferences = normalize_user_preferences(getattr(self, "user_preferences", {}))
            if not bool(preferences.get("start_with_last_file", False)):
                return
            if not getattr(self, "recent_files", []):
                return
            self._open_recent_file(self.recent_files[0])


    def _apply_local_system_settings(self, *, max_recent_files: int):
            """Übernimmt neue lokale Systemsettings und persistiert sie konsistent."""
            normalized_recent = normalize_recent_entries(
                list(getattr(self, "recent_files", [])),
                max_recent_files,
            )

            self.max_recent_files = max_recent_files
            self.recent_files = normalized_recent
            self._save_recent_files()
            self._refresh_recent_menu()

            saved = save_system_settings(
                max_recent_files=max_recent_files,
            )
            self.system_settings = dict(saved.get("system", {}))


    def _load_ui_settings(self):
            """Lädt persistierte UI-Einstellungen (z. B. Theme)."""

            migrate_legacy_config(delete_legacy_files=True)

            system_settings = normalize_system_settings_payload(load_system_settings())
            self.system_settings = system_settings
            self.max_recent_files = int(system_settings["max_recent_files"])
            self.ui_settings = load_ui_settings()

            saved_theme = normalize_theme_key(self.ui_settings.get("theme"))
            self.theme_var.set(saved_theme)
            resolved_profiles = resolve_persisted_design_profiles(
                self.ui_settings,
                color_profile_order=COLOR_PROFILE_ORDER,
            )
            self.preview_controls_collapsed_var.set(bool(self.ui_settings.get("preview_controls_collapsed", False)))
            self.preview_contrast_var.set(resolved_profiles["worksheet_contrast"])
            self.design_color_profile_var.set(resolved_profiles["worksheet_color_profile"])
            self.design_font_profile_var.set(resolved_profiles["worksheet_font_profile"])
            self.design_font_size_profile_var.set(resolved_profiles["worksheet_font_size_profile"])

            loaded_preferences = load_user_preferences()
            self.user_preferences = normalize_user_preferences(loaded_preferences)
            self._restore_window_geometry_if_enabled(self.user_preferences)
            self._apply_user_preferences_live(self.user_preferences)


    def _save_ui_settings(self):
            """Speichert aktuelle UI-Einstellungen."""

            self.ui_settings["theme"] = normalize_theme_key(self.theme_var.get())
            self.ui_settings["preview_controls_collapsed"] = bool(self.preview_controls_collapsed_var.get())
            # Kanonisches Schema auch für alte/kaputte Werte (siehe blatt_ui_editor_panels).
            self.ui_settings[EDITOR_PANELS_SETTINGS_KEY] = normalize_editor_panels_collapsed(
                self.ui_settings.get(EDITOR_PANELS_SETTINGS_KEY)
            )
            self.ui_settings.update(
                normalize_design_profiles_for_persistence(
                    worksheet_contrast=self.preview_contrast_var.get(),
                    worksheet_color_profile=self.design_color_profile_var.get(),
                    worksheet_font_profile=self.design_font_profile_var.get(),
                    worksheet_font_size_profile=self.design_font_size_profile_var.get(),
                )
            )

            preferences = normalize_user_preferences(getattr(self, "user_preferences", {}))
            if bool(preferences.get("remember_window_geometry", False)):
                try:
                    self.ui_settings["window_geometry"] = str(self.root.geometry())
                except Exception:
                    pass
            else:
                self.ui_settings.pop("window_geometry", None)

            save_ui_settings(self.ui_settings)

            merged_preferences = self._build_current_user_preferences_payload()
            self.user_preferences = normalize_user_preferences(
                {
                    **getattr(self, "user_preferences", {}),
                    **merged_preferences,
                }
            )
            save_user_preferences(self.user_preferences)
