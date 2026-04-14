"""GUI mixin module."""

from __future__ import annotations

from pathlib import Path
from tkinter import messagebox, ttk

from .ui_theme import normalize_theme_key
from ..storage.local_config_store import (
    add_recent_file,
    load_recent_files,
    remove_recent_file,
    load_system_settings,
    load_ui_settings,
    load_user_preferences,
    migrate_legacy_config,
    save_recent_files,
    save_system_settings,
    save_ui_settings,
    save_user_preferences,
)
from ..storage.system_settings_adapter import normalize_system_settings_payload
from ..storage.user_preferences_adapter import (
    normalize_user_preferences,
)
from ..storage.history_paths_adapter import (
    normalize_recent_entries,
    normalize_recent_path,
    resolve_recent_path,
)
from ..styles.ui_profile_adapter import (
    normalize_design_profiles_for_persistence,
    resolve_persisted_design_profiles,
)
from ..styles.worksheet_design import COLOR_PROFILE_ORDER
from .settings_dialog import SettingsDialog

class BlattwerkAppPersistenceMixin:
    """Verwaltet Persistenz für Verlauf, Dialogpfade und UI-Einstellungen."""

    @staticmethod
    def _format_document_tab_title(path_text: str) -> str:
            """Builds a compact tab title with inline close marker."""

            return f"{Path(path_text).name}  ×"

    def _on_document_notebook_click(self, event=None):
            """Handles close-clicks on tab title markers."""

            notebook = getattr(self, "document_notebook", None)
            if notebook is None or event is None:
                return None

            try:
                tab_index = notebook.index(f"@{event.x},{event.y}")
            except Exception:
                return None

            tabs = notebook.tabs()
            if tab_index < 0 or tab_index >= len(tabs):
                return None

            tab_id = tabs[tab_index]
            x_pos, _y_pos, width, _height = notebook.bbox(tab_index)
            close_hitbox_start = x_pos + max(0, width - 24)
            if event.x < close_hitbox_start:
                return None

            self._close_document_tab(tab_id)
            return "break"

    def _find_open_tab_id_for_path(self, input_path: Path):
            """Returns the notebook tab id for a currently open document path."""

            normalized_path = self._normalize_document_path(input_path)
            return self._document_tab_path_index.get(normalized_path)

    def _create_document_tab(self, input_path: Path):
            """Creates a new notebook tab and state entry for the provided file path."""

            if self.document_notebook is None:
                return None

            normalized_path = self._normalize_document_path(input_path)
            tab_title = self._format_document_tab_title(normalized_path)
            container = ttk.Frame(self.document_notebook)
            self.document_notebook.add(container, text=tab_title)
            tab_id = self.document_notebook.tabs()[-1]

            state = self._build_document_tab_state(Path(normalized_path))
            self.document_tabs[tab_id] = state
            self._document_tab_order.append(tab_id)
            self._document_tab_path_index[normalized_path] = tab_id
            return tab_id

    def _clear_active_document_view(self):
            """Resets editor and preview when no document tab remains open."""

            self.input_var.set("")
            self.preview_images = []
            self.current_page_index = 0
            self._clear_preview_image_items()
            self.preview_canvas.itemconfig(self.preview_text_item, text="Noch keine Vorschau geladen.")
            self.preview_canvas.coords(self.preview_text_item, 40, 40)
            self.preview_canvas.config(scrollregion=(0, 0, 600, 400))
            self.page_info_var.set("Seite 0/0")
            self.zoom_info_var.set("Zoom: 100%")
            self._update_nav_buttons()
            if self.editor_widget is not None:
                self._editor_loading_content = True
                try:
                    self.editor_widget.delete("1.0", "end")
                    self.editor_widget.edit_modified(False)
                finally:
                    self._editor_loading_content = False

    def _close_document_tab(self, tab_id: str):
            """Closes a specific document tab and restores another tab if available."""

            if self.document_notebook is None:
                return
            if not tab_id:
                return

            tab_state = self.document_tabs.pop(tab_id, None)
            if tab_state is not None:
                tab_path = tab_state.get("path")
                if isinstance(tab_path, str):
                    self._document_tab_path_index.pop(tab_path, None)
            self._document_tab_order = [item for item in self._document_tab_order if item != tab_id]

            self._tab_switch_in_progress = True
            try:
                self.document_notebook.forget(tab_id)
            finally:
                self._tab_switch_in_progress = False

            remaining_tabs = self.document_notebook.tabs()
            if not remaining_tabs:
                self._active_document_tab_id = None
                self._clear_active_document_view()
                self.status_var.set("Kein Dokument geöffnet")
                return

            next_tab_id = remaining_tabs[0]
            self._activate_document_tab(next_tab_id, apply_state=True)

    def close_active_document_tab(self):
            """Closes the currently selected document tab."""

            if self.document_notebook is None:
                return
            tab_id = self.document_notebook.select()
            self._close_document_tab(tab_id)

    def _open_most_recent_not_open_file(self) -> bool:
            """Opens the newest recent file that is not already opened in a tab."""

            stale_entries = []
            for path_text in list(getattr(self, "recent_files", [])):
                file_path = resolve_recent_path(path_text)
                if not file_path.exists():
                    stale_entries.append(path_text)
                    continue

                if self._find_open_tab_id_for_path(file_path) is not None:
                    continue

                self._open_input_path(file_path, add_recent=True, show_duplicate_message=False)
                if stale_entries:
                    for stale_entry in stale_entries:
                        self._remove_recent_file(stale_entry)
                return True

            if stale_entries:
                for stale_entry in stale_entries:
                    self._remove_recent_file(stale_entry)
            return False

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
            return normalize_user_preferences(payload)

    def _apply_user_preferences_live(self, preferences: dict[str, object]):
            normalized = normalize_user_preferences(preferences)
            self.user_preferences = dict(normalized)
            self.theme_var.set(normalized["default_theme_key"])
            self.design_color_profile_var.set(normalized["default_color_profile"])
            self.design_font_profile_var.set(normalized["default_font_profile"])
            self.design_font_size_profile_var.set(normalized["default_font_size_profile"])
            self.preview_contrast_var.set(normalized["default_contrast_profile"])
            self._responsive_controls_wrap_enabled = bool(normalized.get("responsive_controls_wrap", True))
            self._reduce_motion = bool(normalized.get("reduce_motion", False))
            self._ui_density = str(normalized.get("ui_density", "comfort") or "comfort")

            self._editor_diagnostics_delay_ms = int(str(normalized["diagnostics_debounce_ms"]))
            self._editor_outline_delay_ms = int(str(normalized["outline_debounce_ms"]))

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
                import tkinter.ttk as ttk

                style = ttk.Style(self.root)
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
                self._build_menu()

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
            """Öffnet optional zuletzt verwendete Datei beim Start."""
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

    def _load_recent_files(self):
            """Lädt die Liste zuletzt geöffneter Markdown-Dateien."""
            loaded_entries = load_recent_files()
            normalized_entries = normalize_recent_entries(loaded_entries, self.max_recent_files)
            self.recent_files = normalized_entries
            if normalized_entries != loaded_entries:
                self._save_recent_files()

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

    def _save_recent_files(self):
            """Speichert die Liste zuletzt geöffneter Dateien."""
            saved = save_recent_files(self.recent_files)
            self.recent_files = list(saved.get("recent_files", self.recent_files))

    def _refresh_recent_menu(self):
            """Aktualisiert Menüeinträge der zuletzt geöffneten Dateien."""

            if self.recent_menu is None:
                return

            self.recent_menu.delete(0, "end")

            if not self.recent_files:
                self.recent_menu.add_command(label="(leer)", state="disabled")
                return

            for file_path in self.recent_files:
                self.recent_menu.add_command(
                    label=file_path,
                    command=lambda p=file_path: self._open_recent_file(p),
                )

    def _add_recent_file(self, path: Path):
            """Fügt eine Datei zur Verlaufsliste hinzu (max. 5, ohne Duplikat)."""
            history_entry = normalize_recent_path(path)
            self.recent_files = add_recent_file(self.recent_files, history_entry, self.max_recent_files)
            self._save_recent_files()
            self._refresh_recent_menu()

    def _remove_recent_file(self, path_text: str):
            """Entfernt eine Datei aus der Verlaufsliste."""
            self.recent_files = remove_recent_file(self.recent_files, path_text)
            self._save_recent_files()
            self._refresh_recent_menu()

    def _open_input_path(self, input_path: Path, add_recent=True, show_duplicate_message=True):
            """Öffnet ein Markdown-Dokument in eigenem Tab oder fokussiert den vorhandenen Tab."""

            normalized_path = Path(self._normalize_document_path(input_path))
            existing_tab_id = self._find_open_tab_id_for_path(normalized_path)
            if existing_tab_id is not None:
                self._activate_document_tab(existing_tab_id, apply_state=True)
                if show_duplicate_message:
                    messagebox.showwarning(
                        "Bereits geöffnet",
                        f"Die Datei ist schon offen:\n{normalized_path}",
                    )
                self.status_var.set(f"Datei ist schon offen: {normalized_path.name}")
                return False

            self._persist_active_document_tab_state()

            tab_id = self._create_document_tab(normalized_path)
            if tab_id is None:
                self.status_var.set("Dokument-Tab konnte nicht erstellt werden")
                return False

            self._activate_document_tab(tab_id, apply_state=False)
            self._active_document_tab_id = tab_id
            self._apply_document_tab_state(tab_id)
            if add_recent:
                self._add_recent_file(normalized_path)
            return True

    def _open_recent_file(self, path_text: str):
            """Öffnet eine Datei aus der Verlaufsliste oder entfernt ungültige Einträge."""

            file_path = resolve_recent_path(path_text)
            if not file_path.exists():
                messagebox.showerror(
                    "Datei fehlt",
                    f"Die Datei existiert nicht mehr und wird aus der Liste entfernt:\n{file_path}",
                )
                self._remove_recent_file(path_text)
                return

            self._open_input_path(file_path, add_recent=True, show_duplicate_message=True)

    def _get_initial_dialog_dir(self, purpose: str):
            """Get initial dialog dir."""
            preferences = normalize_user_preferences(getattr(self, "user_preferences", {}))
            if purpose.startswith("export") and not bool(preferences.get("remember_export_dir", True)):
                return None
            if not bool(preferences.get("remember_dialog_dirs", True)):
                return None

            dialog_dirs = self.ui_settings.get("dialog_initial_dirs")
            if not isinstance(dialog_dirs, dict):
                return None

            saved = dialog_dirs.get(purpose)
            if not isinstance(saved, str) or not saved.strip():
                return None

            candidate = Path(saved).expanduser()
            if candidate.is_dir():
                return str(candidate)
            return None

    def _set_last_dialog_dir(self, purpose: str, selected_path):
            """Set last dialog dir."""
            preferences = normalize_user_preferences(getattr(self, "user_preferences", {}))
            if purpose.startswith("export") and not bool(preferences.get("remember_export_dir", True)):
                return
            if not bool(preferences.get("remember_dialog_dirs", True)):
                return

            try:
                candidate = Path(selected_path).expanduser()
            except Exception:
                return

            directory = candidate if candidate.is_dir() else candidate.parent
            if not directory.is_dir():
                return

            dialog_dirs = self.ui_settings.get("dialog_initial_dirs")
            if not isinstance(dialog_dirs, dict):
                dialog_dirs = {}

            dialog_dirs[purpose] = str(directory)
            self.ui_settings["dialog_initial_dirs"] = dialog_dirs
            self._save_ui_settings()

    def _restore_window_geometry_if_enabled(self, preferences: dict[str, object]):
            """Restore previously saved window geometry when enabled."""

            if not bool(preferences.get("remember_window_geometry", False)):
                return

            geometry_text = self.ui_settings.get("window_geometry")
            if not isinstance(geometry_text, str) or not geometry_text.strip():
                return

            try:
                self.root.geometry(geometry_text.strip())
            except Exception:
                return

    def _bind_window_geometry_tracking(self):
            """Track root geometry updates for optional persistence."""

            if getattr(self, "root", None) is None:
                return
            self.root.bind("<Configure>", self._on_root_configure_for_geometry, add="+")

    def _on_root_configure_for_geometry(self, _event=None):
            """Debounce geometry persistence writes while the window is resized/moved."""

            preferences = normalize_user_preferences(getattr(self, "user_preferences", {}))
            if not bool(preferences.get("remember_window_geometry", False)):
                return

            pending_id = getattr(self, "_window_geometry_after_id", None)
            if pending_id is not None:
                try:
                    self.root.after_cancel(pending_id)
                except Exception:
                    pass

            self._window_geometry_after_id = self.root.after(450, self._persist_window_geometry_now)

    def _persist_window_geometry_now(self):
            """Persist current root geometry if feature is enabled."""

            self._window_geometry_after_id = None
            preferences = normalize_user_preferences(getattr(self, "user_preferences", {}))
            if not bool(preferences.get("remember_window_geometry", False)):
                return

            try:
                geometry_text = str(self.root.geometry())
            except Exception:
                return

            if geometry_text and self.ui_settings.get("window_geometry") != geometry_text:
                self.ui_settings["window_geometry"] = geometry_text
                save_ui_settings(self.ui_settings)
