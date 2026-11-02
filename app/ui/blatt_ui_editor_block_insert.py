"""Block einfügen im Editor: wendet `plan_block_insert` auf Markierung bzw. Cursor an (BlattwerkApp-Mixin).

Die ganze Entscheidung, was eingefügt wird und wo es nicht geht, trifft der
Core (`app/core/block_insert_transform.py`). Hier passiert nur, was ein
Tk-Editor dafür braucht: Markierung und Cursor als Zeichen-Offsets lesen,
die Formelgrenzen-Prüfung der Marker-Tasten anwenden, die Änderung als
genau einen Undo-Schritt einsetzen (`replace_editor_range`) und Cursor,
Ansicht und Statusleiste nachziehen.

GRENZE: Mit mehreren Cursorn wird nichts eingefügt (Hinweis in der
Statusleiste); ein Block pro Cursor wäre ein eigenes Feature.
"""

from __future__ import annotations

from ..core.block_insert_transform import BlockInsertError, plan_block_insert
from .blatt_ui_editor_edits import editor_surface, replace_editor_range
from .blatt_ui_editor_multicursor import MATH_CROSSING_MESSAGE
from .ui_constants import EDITOR_DOCUMENT_LOADED

MULTICURSOR_INSERT_MESSAGE = "Block einfügen geht nur mit einem Cursor. Esc beendet die Mehrfach-Cursor."


class BlattwerkAppEditorBlockInsertMixin:
    """Fügt Blöcke aus dem Menü "Einfügen" an Cursor oder Markierung ein."""

    def _insert_block_from_menu(self, snippet: str, block_type: str | None) -> None:
        """Fügt `snippet` (Blocktyp `block_type`, `None` für das Bild) an Cursor oder Markierung ein.

        Fehler (Block im Block, Spalten in Spalten, Formel geschnitten …)
        stehen in der Statusleiste; der Text bleibt dann unverändert. Ein
        Hinweis des Cores (z. B. verworfene Optionen beim Kopftausch) steht
        nach dem Einfügen dort.
        """
        widget = self.editor_widget
        if widget is None or self._editor_document_state != EDITOR_DOCUMENT_LOADED:
            return
        if self._editor_multicursor_active():
            self.status_var.set(MULTICURSOR_INSERT_MESSAGE)
            return

        selection = widget.tag_ranges("sel")
        if selection and self._editor_selection_crosses_math(selection[0], selection[1]):
            self.status_var.set(MATH_CROSSING_MESSAGE)
            return
        surface = editor_surface(widget)
        start_index, end_index = (selection[0], selection[1]) if selection else ("insert", "insert")
        start, end = surface.offset(start_index), surface.offset(end_index)

        try:
            edit = plan_block_insert(surface.content(), start, end, snippet, block_type)
        except BlockInsertError as error:
            self.status_var.set(str(error))
            return

        replace_editor_range(widget, edit.start, edit.end, edit.text)
        widget.tag_remove("sel", "1.0", "end")
        widget.mark_set("insert", surface.index(edit.start + edit.cursor))
        widget.see("insert")
        widget.focus_set()
        if edit.note:
            self.status_var.set(edit.note)
        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)
