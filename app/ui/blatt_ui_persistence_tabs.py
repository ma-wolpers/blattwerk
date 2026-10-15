"""Dokument-Tabs: Tabs anlegen, schliessen, wechseln und Dateien (auch aus dem Verlauf) oeffnen.
"""

from __future__ import annotations

from pathlib import Path
from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()

from bw_gui.runtime import widgets
from .dialog_services import messagebox
from ..storage.history_paths_adapter import resolve_recent_path


class BlattwerkAppPersistenceTabsMixin:
    """Verwaltet die Dokument-Tabs und das Oeffnen von Dateien."""


    @staticmethod
    def _format_document_tab_title(path_text: str) -> str:
            """Builds a compact tab title without inline close markers."""

            return Path(path_text).name


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
            container = widgets.Frame(self.document_notebook)
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
                self._reset_editor_widget_to_empty()


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


    def _open_input_path(self, input_path: Path, add_recent=True, show_duplicate_message=True):
            """Öffnet ein Markdown-Dokument in eigenem Tab oder fokussiert den vorhandenen Tab."""

            normalized_path = Path(self._normalize_document_path(input_path))
            if not self._confirm_open_unknown_extension(normalized_path):
                # Unbekannte Endung und keine Markdown-Interpretation: nie still Markdown annehmen (I1).
                self.status_var.set(f"Nicht geöffnet (unbekannte Endung): {normalized_path.name}")
                return False
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
