"""GUI mixin module."""

from __future__ import annotations

from pathlib import Path
from .blatt_ui_dependencies import (
    COLOR_PROFILE_ORDER,
    DEFAULT_HISTORY_ROOT_NAME,
    DEFAULT_MAX_RECENT_FILES,
    LOCAL_CONFIG_PATH,
    MAX_MAX_RECENT_FILES,
    MIN_MAX_RECENT_FILES,
    add_recent_file,
    find_history_root,
    load_recent_files,
    load_system_settings,
    load_ui_settings,
    messagebox,
    migrate_legacy_config,
    normalize_color_profile,
    normalize_contrast_profile,
    normalize_font_profile,
    normalize_font_size_profile,
    normalize_recent_entries,
    normalize_theme_key,
    remove_recent_file,
    resolve_history_path,
    save_recent_files,
    save_system_settings,
    save_ui_settings,
    tk,
    to_history_relative_path,
    ttk,
)

class BlattwerkAppPersistenceMixin:
    """Verwaltet Persistenz für Verlauf, Dialogpfade und UI-Einstellungen."""

    def _open_local_settings_dialog(self):
            """Öffnet Dialog für lokale/systemnahe Blattwerk-Einstellungen."""
            dialog = tk.Toplevel(self.root)
            dialog.title("Einstellungen")
            dialog.transient(self.root)
            dialog.resizable(False, False)

            content = ttk.Frame(dialog, padding=12)
            content.pack(fill="both", expand=True)

            ttk.Label(content, text="Lokale Blattwerk-Konfiguration", font=("Segoe UI", 11, "bold")).grid(
                row=0, column=0, columnspan=2, sticky="w"
            )

            ttk.Label(content, text="Root-Anker (Verlauf):").grid(row=1, column=0, sticky="w", pady=(10, 4))
            root_name_var = tk.StringVar(value=str(getattr(self, "history_root_name", DEFAULT_HISTORY_ROOT_NAME)))
            ttk.Entry(content, textvariable=root_name_var, width=34).grid(row=1, column=1, sticky="ew", pady=(10, 4))

            ttk.Label(content, text="Max. zuletzt geöffnete Dateien:").grid(row=2, column=0, sticky="w", pady=4)
            max_recent_var = tk.StringVar(value=str(getattr(self, "max_recent_files", DEFAULT_MAX_RECENT_FILES)))
            ttk.Entry(content, textvariable=max_recent_var, width=10).grid(row=2, column=1, sticky="w", pady=4)

            ttk.Label(content, text="Config-Datei:").grid(row=3, column=0, sticky="w", pady=4)
            ttk.Label(content, text=str(LOCAL_CONFIG_PATH)).grid(row=3, column=1, sticky="w", pady=4)

            buttons = ttk.Frame(content)
            buttons.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
            buttons.columnconfigure(0, weight=1)

            def _reset_defaults():
                root_name_var.set(DEFAULT_HISTORY_ROOT_NAME)
                max_recent_var.set(str(DEFAULT_MAX_RECENT_FILES))

            def _save_and_close():
                history_root_name = str(root_name_var.get() or "").strip()
                if not history_root_name:
                    messagebox.showerror("Einstellungen", "Root-Anker darf nicht leer sein.", parent=dialog)
                    return

                try:
                    max_recent = int((max_recent_var.get() or "").strip())
                except Exception:
                    messagebox.showerror("Einstellungen", "Bitte eine ganze Zahl für das Dateilimit eingeben.", parent=dialog)
                    return

                if not (MIN_MAX_RECENT_FILES <= max_recent <= MAX_MAX_RECENT_FILES):
                    messagebox.showerror(
                        "Einstellungen",
                        (
                            "Ungültiges Dateilimit. Erlaubt sind "
                            f"{MIN_MAX_RECENT_FILES} bis {MAX_MAX_RECENT_FILES}."
                        ),
                        parent=dialog,
                    )
                    return

                self._apply_local_system_settings(history_root_name=history_root_name, max_recent_files=max_recent)
                dialog.destroy()

            ttk.Button(buttons, text="Standard", command=_reset_defaults).pack(side="left")
            ttk.Button(buttons, text="Abbrechen", command=dialog.destroy).pack(side="right")
            ttk.Button(buttons, text="Speichern", command=_save_and_close).pack(side="right", padx=(0, 8))

            content.columnconfigure(1, weight=1)
            dialog.grab_set()
            dialog.focus_set()

    def _apply_local_system_settings(self, *, history_root_name: str, max_recent_files: int):
            """Übernimmt neue lokale Systemsettings und persistiert sie konsistent."""
            old_history_root = getattr(self, "history_root", find_history_root(DEFAULT_HISTORY_ROOT_NAME))
            new_history_root = find_history_root(history_root_name)

            converted_recent = [
                to_history_relative_path(resolve_history_path(item, old_history_root), new_history_root)
                for item in list(getattr(self, "recent_files", []))
            ]
            normalized_recent = normalize_recent_entries(converted_recent, new_history_root, max_recent_files)

            self.history_root_name = history_root_name
            self.max_recent_files = max_recent_files
            self.history_root = new_history_root
            self.recent_files = normalized_recent
            self._save_recent_files()
            self._refresh_recent_menu()

            saved = save_system_settings(
                history_root_name=history_root_name,
                max_recent_files=max_recent_files,
            )
            self.system_settings = dict(saved.get("system", {}))

    def _load_recent_files(self):
            """Lädt die Liste zuletzt geöffneter Markdown-Dateien."""
            loaded_entries = load_recent_files()
            normalized_entries = normalize_recent_entries(loaded_entries, self.history_root, self.max_recent_files)
            self.recent_files = normalized_entries
            if normalized_entries != loaded_entries:
                self._save_recent_files()

    def _load_ui_settings(self):
            """Lädt persistierte UI-Einstellungen (z. B. Theme)."""

            migrate_legacy_config(delete_legacy_files=True)

            system_settings = load_system_settings()
            history_root_name = str(system_settings.get("history_root_name", DEFAULT_HISTORY_ROOT_NAME)).strip()
            if not history_root_name:
                history_root_name = DEFAULT_HISTORY_ROOT_NAME
            max_recent_files = int(system_settings.get("max_recent_files", DEFAULT_MAX_RECENT_FILES))
            if max_recent_files < MIN_MAX_RECENT_FILES:
                max_recent_files = MIN_MAX_RECENT_FILES
            if max_recent_files > MAX_MAX_RECENT_FILES:
                max_recent_files = MAX_MAX_RECENT_FILES

            self.system_settings = {
                "history_root_name": history_root_name,
                "max_recent_files": max_recent_files,
            }
            self.history_root_name = history_root_name
            self.max_recent_files = max_recent_files
            self.history_root = find_history_root(history_root_name)
            self.ui_settings = load_ui_settings()

            saved_theme = normalize_theme_key(self.ui_settings.get("theme"))
            self.theme_var.set(saved_theme)
            self.preview_contrast_var.set(normalize_contrast_profile(self.ui_settings.get("worksheet_contrast")))

            saved_color_profile = self.ui_settings.get("worksheet_color_profile")
            if not saved_color_profile:
                legacy_color_mode = (self.ui_settings.get("worksheet_color_mode") or "").strip().lower()
                legacy_accent = (self.ui_settings.get("worksheet_accent") or "").strip().lower()
                if legacy_color_mode == "bw":
                    saved_color_profile = "bw"
                elif legacy_accent in COLOR_PROFILE_ORDER:
                    saved_color_profile = legacy_accent

            self.design_color_profile_var.set(normalize_color_profile(saved_color_profile))

            saved_font_profile = self.ui_settings.get("worksheet_font_profile")
            self.design_font_profile_var.set(normalize_font_profile(saved_font_profile))
            saved_font_size_profile = self.ui_settings.get("worksheet_font_size_profile")
            self.design_font_size_profile_var.set(normalize_font_size_profile(saved_font_size_profile))

    def _save_ui_settings(self):
            """Speichert aktuelle UI-Einstellungen."""

            self.ui_settings["theme"] = normalize_theme_key(self.theme_var.get())
            self.ui_settings["worksheet_contrast"] = normalize_contrast_profile(self.preview_contrast_var.get())
            self.ui_settings["worksheet_color_profile"] = normalize_color_profile(self.design_color_profile_var.get())
            self.ui_settings["worksheet_font_profile"] = normalize_font_profile(self.design_font_profile_var.get())
            self.ui_settings["worksheet_font_size_profile"] = normalize_font_size_profile(self.design_font_size_profile_var.get())
            save_ui_settings(self.ui_settings)

    def _save_recent_files(self):
            """Speichert die Liste zuletzt geöffneter Dateien."""
            saved = save_recent_files(self.recent_files)
            self.recent_files = list(saved.get("recent_files", self.recent_files))

    def _refresh_recent_menu(self):
            """Aktualisiert Menüeinträge der zuletzt geöffneten Dateien."""

            if self.recent_menu is None:
                return

            self.recent_menu.delete(0, "end")
            self.recent_menu.add_command(
                label=f"Basis: {self.history_root_name} (relative Pfade)",
                state="disabled",
            )
            self.recent_menu.add_separator()

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
            history_entry = to_history_relative_path(path, self.history_root)
            self.recent_files = add_recent_file(self.recent_files, history_entry, self.max_recent_files)
            self._save_recent_files()
            self._refresh_recent_menu()

    def _remove_recent_file(self, path_text: str):
            """Entfernt eine Datei aus der Verlaufsliste."""
            self.recent_files = remove_recent_file(self.recent_files, path_text)
            self._save_recent_files()
            self._refresh_recent_menu()

    def _open_input_path(self, input_path: Path, add_recent=True):
            """Setzt Eingabedatei, lädt Vorschau und optional Verlaufseintrag."""

            self.input_var.set(str(input_path))
            self._warn_if_bw_mode_has_color_mentions()
            self.refresh_preview()
            if add_recent:
                self._add_recent_file(input_path)

    def _open_recent_file(self, path_text: str):
            """Öffnet eine Datei aus der Verlaufsliste oder entfernt ungültige Einträge."""

            file_path = resolve_history_path(path_text, self.history_root)
            if not file_path.exists():
                messagebox.showerror(
                    "Datei fehlt",
                    f"Die Datei existiert nicht mehr und wird aus der Liste entfernt:\n{file_path}",
                )
                self._remove_recent_file(path_text)
                return

            self._open_input_path(file_path, add_recent=True)

    def _get_initial_dialog_dir(self, purpose: str):
            """Get initial dialog dir."""
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
