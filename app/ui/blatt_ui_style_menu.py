"""Menueleiste: Menuemodell (Datei, Extras, Ansicht, Shortcuts) fuer die bw-gui-Menueleiste.
"""

from __future__ import annotations

from .ui_constants import (
    EDITOR_VIEW_BOTH,
    EDITOR_VIEW_EDITOR_ONLY,
    EDITOR_VIEW_PREVIEW_ONLY,
    VIEW_FIT_PAGE,
    VIEW_FIT_WIDTH,
    VIEW_LAYOUT_SINGLE,
    VIEW_LAYOUT_STACK,
    VIEW_LAYOUT_STRIP,
)
from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()

from bw_gui.menu import MenuItem as SharedMenuItem


class BlattwerkAppStyleMenuMixin:
    """Baut das Menuemodell der Hauptfensters."""

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
                        description=item.get("description"),
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

    def _iter_shortcut_menu_labels(self):
            """Liefert deduplizierte Shortcut-Hinweise in definierter Reihenfolge."""

            preferences = getattr(self, "user_preferences", {})
            if not bool(preferences.get("shortcuts_menu_hints_visible", True)):
                return

            yield from self.shortcut_manager.iter_menu_labels(self.shortcut_bindings)
