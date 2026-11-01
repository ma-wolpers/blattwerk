"""Schreibbereich: Anbindung des bw-gui-Multi-Cursors (BlattwerkApp-Mixin).

Der Controller (`bw_gui.runtime.attach_multicursor`) kennt Gesten, Tippen, Bewegung
und Undo mit Cursorn. Hier steht nur, was Blattwerk dazugibt: Marker-Tasten und
Wortlöschen je Region (dieselben Regeln wie mit einem Cursor) sowie die Zustandsfragen
für Escape, Vervollständigung und Dokumentwechsel.
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.contracts.events import EventResult
from bw_gui.contracts.multicursor import Edit
from bw_gui.runtime import attach_multicursor

MATH_CROSSING_MESSAGE = "Markierung überschneidet eine Formel ($...$) -- Aktion abgebrochen."


class BlattwerkAppEditorMultiCursorMixin:
    """Schreibbereich: Anbindung des bw-gui-Multi-Cursors (BlattwerkApp-Mixin)."""

    editor_multicursor = None

    def _attach_editor_multicursor(self):
        """Hängt den Controller an; nach den Klick-Handlern, damit „kein Dokument“ auch Strg+Klick stoppt."""
        self.editor_multicursor = attach_multicursor(self.editor_widget)

    def _editor_multicursor_active(self) -> bool:
        """Ob gerade mehrere Cursor aktiv sind."""
        return self.editor_multicursor is not None and self.editor_multicursor.is_active()

    def _editor_multicursor_has_selection(self) -> bool:
        """Ob mindestens eine Region etwas ausgewählt hat (sonst sind Marker-Tasten normales Tippen)."""
        return any(not region.is_caret for region in self.editor_multicursor.regions)

    def _on_editor_add_cursor_above(self, _event=None):
        """Strg+Alt+↑: weiterer Cursor über dem obersten."""
        self._close_editor_completion()
        return self.editor_multicursor.add_cursor(-1)

    def _on_editor_add_cursor_below(self, _event=None):
        """Strg+Alt+↓: weiterer Cursor unter dem untersten."""
        self._close_editor_completion()
        return self.editor_multicursor.add_cursor(1)

    def _apply_marker_to_regions(self, marker_char, resolve_edit, resolve_range=None):
        """Marker-Taste bei mehreren Cursorn: jede Auswahl wird markiert, jeder Cursor tippt das Zeichen.

        Läuft nur mit mindestens einer Auswahl (`_editor_key_condition`). Schneidet eine
        Auswahl eine Formelgrenze, wird die ganze Aktion abgelehnt (wie mit einem Cursor).

        Args:
            marker_char: Getipptes Zeichen, auch für Cursor ohne Auswahl.
            resolve_edit: ``(before, selected, after, first, last) -> MarkerEdit``.
            resolve_range: Optional ``(first, last) -> (first, last)``, z. B. volle Zeilen.
        """
        controller = self.editor_multicursor
        surface = controller.surface
        ranges = {}
        for region in controller.regions:
            if region.is_caret:
                continue
            first, last = surface.index(region.start), surface.index(region.end)
            ranges[region.order] = resolve_range(first, last) if resolve_range else (first, last)
        if any(self._editor_selection_crosses_math(first, last) for first, last in ranges.values()):
            self.status_var.set(MATH_CROSSING_MESSAGE)
            return EventResult.HANDLED

        def plan(region):
            first, last = ranges[region.order]
            before, selected, after = self._editor_context_around(first, last)
            edit = resolve_edit(before, selected, after, first, last)
            return Edit(
                surface.offset(first) - edit.strip_left,
                surface.offset(last) + edit.strip_right,
                edit.replacement,
                select=(edit.select_start, edit.select_end),
            )

        controller.apply_per_region(plan, caret_text=marker_char)
        return EventResult.HANDLED

    def _delete_word_at_regions(self, word_length, *, forward):
        """Wortlöschen an jedem Cursor; eine Auswahl wird wie bei Entf/Rücktaste gelöscht."""
        surface = self.editor_multicursor.surface

        def plan(region):
            if not region.is_caret:
                return Edit(region.start, region.end, "")
            length = word_length(surface.index(region.head))
            if forward:
                return Edit(region.head, region.head + length, "")
            return Edit(region.head - length, region.head, "")

        self.editor_multicursor.run_on_regions(plan)
        return EventResult.HANDLED
