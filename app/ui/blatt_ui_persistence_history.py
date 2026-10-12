"""Verlauf und Fensterzustand: zuletzt geoeffnete Dateien, letzte Dialogordner und
Fenstergeometrie.
"""

from __future__ import annotations

from pathlib import Path
from ..storage.local_config_store import (
    add_recent_file,
    load_recent_files,
    remove_recent_file,
    save_recent_files,
    save_ui_settings,
)
from ..storage.user_preferences_adapter import normalize_user_preferences
from ..storage.history_paths_adapter import (
    normalize_recent_entries,
    normalize_recent_path,
)


class BlattwerkAppPersistenceHistoryMixin:
    """Persistiert Verlauf, Dialogordner und Fenstergeometrie."""


    def _load_recent_files(self):
            """Lädt die Liste zuletzt geöffneter Markdown-Dateien."""
            loaded_entries = load_recent_files()
            normalized_entries = normalize_recent_entries(loaded_entries, self.max_recent_files)
            self.recent_files = normalized_entries
            if normalized_entries != loaded_entries:
                self._save_recent_files()


    def _save_recent_files(self):
            """Speichert die Liste zuletzt geöffneter Dateien."""
            saved = save_recent_files(self.recent_files)
            self.recent_files = list(saved.get("recent_files", self.recent_files))


    def _refresh_recent_menu(self):
            """Aktualisiert Menüeinträge der zuletzt geöffneten Dateien."""

            if hasattr(self, "_refresh_custom_menu_model"):
                self._refresh_custom_menu_model()

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
                # bw-gui opens main windows maximized; an explicit geometry only
                # wins over that if the maximized state is left first.
                self.root.state("normal")
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
