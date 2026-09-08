"""Editor mixin for acknowledging ("als gelesen markieren") diagnostics.

Split out of `blatt_ui_editor_diagnostics.py` to keep both files under the
project's ~300-line convention -- that file owns computing/rendering the
diagnostics list, this one owns the interactive "mark as read" actions on
top of it (checkbox click, context menu, clearing a document). Both are
part of the same Treeview built in `_build_editor_diagnostics_panel`
(`blatt_ui_editor_diagnostics.py`), which binds directly into methods here.
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui

from ..storage import acknowledged_warnings_store


class BlattwerkAppEditorDiagnosticsAckMixin:
    """Adds acknowledge/un-acknowledge interactions to the "Diagnostik" Treeview."""

    def _current_document_path_for_ack(self):
        """Raw path of the active document, or `None` for an unsaved tab (no acknowledgment persistence)."""

        if not hasattr(self, "_active_document_tab_state"):
            return None
        try:
            tab_state = self._active_document_tab_state()
        except Exception:
            return None
        if not isinstance(tab_state, dict):
            return None
        raw_path = str(tab_state.get("path", "") or "").strip()
        return raw_path or None

    def _on_editor_diagnostics_ack_column_click(self, event):
        """Toggles acknowledgment when the checkbox column is clicked.

        Returns `"break"` for such a click so the Treeview's own
        selection/navigation handling never runs for it -- ticking the box
        must not also jump the cursor to that line.
        """

        tree = self.editor_diagnostics_listbox
        if tree is None:
            return None

        row_id = tree.identify_row(event.y)
        if not row_id or tree.identify_column(event.x) != "#1":
            return None

        item = self._editor_diagnostics_by_row_id.get(row_id)
        if item is None or item["severity"] != "warning" or item.get("identity") is None:
            return "break"

        self._toggle_editor_diagnostic_acknowledged(row_id, item)
        return "break"

    def _toggle_editor_diagnostic_acknowledged(self, row_id, item):
        """Sets/unsets acknowledgment for one row -- shared by the checkbox click and the context menu."""

        tree = self.editor_diagnostics_listbox
        if tree is None:
            return

        document_path = self._current_document_path_for_ack()
        if not document_path:
            return

        currently_acked = "ack_done" in tree.item(row_id, "tags")
        new_state = not currently_acked
        try:
            acknowledged_warnings_store.set_acknowledged(document_path, item["identity"], new_state)
        except Exception:
            return

        values = list(tree.item(row_id, "values"))
        values[0] = "☑" if new_state else "☐"
        tree.item(row_id, values=values, tags=("ack_done",) if new_state else ())

    def _clear_editor_diagnostics_acknowledged(self):
        """Context-menu action: resets acknowledgments for the active document only."""

        document_path = self._current_document_path_for_ack()
        if not document_path:
            return
        try:
            acknowledged_warnings_store.clear_acknowledged(document_path)
        except Exception:
            return
        self._set_editor_diagnostics(self._editor_diagnostics_items)

    def _on_editor_diagnostics_context_menu(self, event):
        """Right-click menu: toggle the row under the cursor, or reset the whole document."""

        tree = self.editor_diagnostics_listbox
        if tree is None:
            return None

        row_id = tree.identify_row(event.y)
        menu = ui.Menu(tree, tearoff=0)

        if row_id:
            item = self._editor_diagnostics_by_row_id.get(row_id)
            if item is not None and item["severity"] == "warning" and item.get("identity") is not None:
                tree.selection_set(row_id)
                is_acked = "ack_done" in tree.item(row_id, "tags")
                label = "Wieder anzeigen" if is_acked else "Als gelesen markieren"
                menu.add_command(
                    label=label,
                    command=lambda: self._toggle_editor_diagnostic_acknowledged(row_id, item),
                )
                menu.add_separator()

        menu.add_command(
            label="Alle in diesem Dokument wieder anzeigen",
            command=self._clear_editor_diagnostics_acknowledged,
        )

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"
