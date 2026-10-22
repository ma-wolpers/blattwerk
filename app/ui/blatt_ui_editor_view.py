"""Schreibbereich: Gliederung, Ansichtsmodus, Fokus, Teilung und Tabellenumwandlung (BlattwerkApp-Mixin).

Aus ``blatt_ui_editor.py`` ausgelagert (300-Zeilen-Regel), Methoden unverändert."""

from __future__ import annotations

import re

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui

from .dialog_services import messagebox
from ..core.markdown_table_conversion import convert_markdown_tables_to_blocks
from .ui_constants import EDITOR_DOCUMENT_LOADED, EDITOR_VIEW_BOTH, EDITOR_VIEW_EDITOR_ONLY, EDITOR_VIEW_PREVIEW_ONLY


class BlattwerkAppEditorViewMixin:
    """Schreibbereich: Gliederung, Ansichtsmodus, Fokus, Teilung und Tabellenumwandlung (BlattwerkApp-Mixin)."""

    def _convert_markdown_tables_in_active_tab(self):
        """Extras-Menü-Aktion: wandelt alle GFM-Markdown-Tabellen im aktiven Tab in `:::table`-Blöcke um.

        Reine Funktionslogik lebt in `markdown_table_conversion.py`; diese
        Methode ist nur die Editor-Anbindung (Volltext lesen, Bulk-Ersetzung
        als ein einziger Undo-Schritt, Rückmeldung). Bei `converted_count == 0`
        wird der Editor nie angefasst -- auch nicht, wenn Tabellen gefunden,
        aber alle übersprungen wurden (dann zeigt eine Warnung die Gründe,
        statt den irreführenden Eindruck zu erwecken, es sei nichts gefunden
        worden).
        """
        if self.editor_widget is None:
            return

        original_text = self.editor_widget.get("1.0", "end-1c")
        result = convert_markdown_tables_to_blocks(original_text)

        if result.converted_count == 0:
            if result.skipped:
                skip_list = "\n".join(f"- {reason}" for reason in result.skipped)
                messagebox.showwarning(
                    "Markdown-Tabellen umwandeln",
                    f"Keine Tabelle umgewandelt. {len(result.skipped)} Tabelle(n) übersprungen:\n{skip_list}",
                )
            else:
                messagebox.showinfo("Markdown-Tabellen umwandeln", "Keine Markdown-Tabellen gefunden.")
            return

        scroll_fraction = self.editor_widget.yview()[0]
        self.editor_widget.configure(autoseparators=False)
        try:
            self.editor_widget.delete("1.0", "end")
            self.editor_widget.insert("1.0", result.new_text)
            self.editor_widget.edit_separator()
        finally:
            self.editor_widget.configure(autoseparators=True)
        self.editor_widget.yview_moveto(scroll_fraction)

        self.status_var.set(f"{result.converted_count} Markdown-Tabelle(n) umgewandelt.")
        if result.skipped:
            skip_list = "\n".join(f"- {reason}" for reason in result.skipped)
            messagebox.showwarning(
                "Markdown-Tabellen umwandeln",
                f"{result.converted_count} Tabelle(n) umgewandelt. "
                f"{len(result.skipped)} weitere Tabelle(n) übersprungen:\n{skip_list}",
            )

    def _queue_editor_outline(self, immediate: bool = False):
        """Schedules an outline refresh to keep section navigation current."""

        if self.editor_widget is None:
            return

        if self._editor_outline_after_id is not None:
            self.root.after_cancel(self._editor_outline_after_id)
            self._editor_outline_after_id = None

        if immediate:
            self._refresh_editor_outline()
            return

        self._editor_outline_after_id = self.root.after(
            self._editor_outline_delay_ms,
            self._refresh_editor_outline,
        )

    def _refresh_editor_outline(self):
        """Builds editor outline from frontmatter and Blattwerk block headers."""

        self._editor_outline_after_id = None
        if self.editor_widget is None:
            return

        line_count = int(self.editor_widget.index("end-1c").split(".")[0] or 1)
        # See `_refresh_editor_highlighting` for why splitting the bulk-fetched
        # text is equivalent to (and far cheaper than) a per-line widget `.get()`.
        text_lines = self.editor_widget.get("1.0", "end-1c").split("\n")
        items = []
        frontmatter_count = 0
        block_stack = []
        self_closing_pattern = re.compile(r"^:::(\w+)(.*?):::$")
        opening_pattern = re.compile(r"^:::(\w+)(.*)$")

        for line_no in range(1, max(1, line_count) + 1):
            line_text = text_lines[line_no - 1]
            stripped = line_text.strip()

            if stripped == "---":
                frontmatter_count += 1
                if frontmatter_count == 1:
                    items.append(
                        {
                            "line": line_no,
                            "label": f"{line_no:>4}  Frontmatter",
                        }
                    )
                continue

            if not stripped:
                continue

            if self_closing_pattern.match(stripped):
                continue

            opening_match = opening_pattern.match(stripped)
            if opening_match:
                block_type = opening_match.group(1)
                rest = (opening_match.group(2) or "").strip()
                indent = "  " * len(block_stack)
                suffix = f" {rest}" if rest else ""
                items.append(
                    {
                        "line": line_no,
                        "label": f"{line_no:>4}  {indent}{block_type}{suffix}",
                    }
                )
                block_stack.append(block_type.lower())
                continue

            if stripped.startswith(":::") and block_stack:
                block_stack.pop()
                continue

        self._set_editor_outline(items)

    def _set_editor_outline(self, items):
        """Renders outline items in structure list for quick line navigation."""

        self._editor_outline_items = list(items)
        if self.editor_outline_listbox is None:
            return

        self.editor_outline_listbox.delete(0, "end")
        if not self._editor_outline_items:
            self.editor_outline_listbox.insert("end", "Keine Struktur erkannt")
            return

        for item in self._editor_outline_items:
            self.editor_outline_listbox.insert("end", item["label"])

    def _on_editor_outline_selected(self, _event=None):
        """Jumps to selected structure entry in editor."""

        if self.editor_widget is None or self.editor_outline_listbox is None:
            return

        selection = self.editor_outline_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index >= len(self._editor_outline_items):
            return

        line = self._editor_outline_items[index]["line"]
        line_index = f"{max(1, int(line))}.0"
        self.editor_widget.mark_set("insert", line_index)
        self.editor_widget.see(line_index)
        self.editor_widget.focus_set()
        self._refresh_editor_block_pair_highlight()

    def _on_editor_outline_click(self, _event=None):
        """Ensures click on already selected outline entry still triggers jump."""

        if hasattr(self, "root"):
            self.root.after_idle(self._on_editor_outline_selected)

    def _set_editor_view_mode(self, mode: str):
        """Updates the selected editor/preview view mode and applies layout."""

        if mode != self.editor_view_mode_var.get():
            self.editor_view_mode_var.set(mode)
        self._apply_editor_view_mode()
        self._load_editor_for_current_input_if_needed()
        self._save_ui_settings()

    def _load_editor_for_current_input_if_needed(self):
        """Loads current input file into editor when editor pane is visible."""

        mode = self.editor_view_mode_var.get()
        if mode == EDITOR_VIEW_PREVIEW_ONLY:
            return

        input_path = self._get_input_path_if_exists()
        if input_path is None:
            return

        if self._editor_last_loaded_path == input_path:
            return

        self._load_editor_content(input_path)

    def _apply_editor_view_mode(self):
        """Shows preview area, editor area, or both depending on selected mode, and moves focus accordingly."""

        if self.editor_preview_paned is None or self.editor_container is None or self.preview_container is None:
            return

        mode = self.editor_view_mode_var.get()

        for pane in (self.editor_container, self.preview_container):
            try:
                self.editor_preview_paned.forget(pane)
            except Exception:
                pass

        if mode == EDITOR_VIEW_EDITOR_ONLY:
            self.editor_preview_paned.add(self.editor_container)
            self._focus_editor_widget_if_available()
        elif mode == EDITOR_VIEW_BOTH:
            self.editor_preview_paned.add(self.editor_container)
            self.editor_preview_paned.add(self.preview_container)
            self._schedule_equal_split()
            if hasattr(self, "_reflow_responsive_sections"):
                self.root.after_idle(self._reflow_responsive_sections)
            self._focus_editor_widget_if_available()
        else:
            self._close_editor_completion()
            if self._editor_search_visible:
                self._close_editor_search_bar()
            self.editor_preview_paned.add(self.preview_container)
            if hasattr(self, "_reflow_responsive_sections"):
                self.root.after_idle(self._reflow_responsive_sections)
            self._focus_preview_canvas_if_available()

    def _focus_editor_widget_if_available(self):
        """Moves keyboard focus into the editor text widget, if a document is loaded.

        Never focuses the editor while it is disabled (no document loaded, or
        still loading) -- doing so would make it the "text input focused"
        target for the global shortcut gating in shortcut_manager.py/
        keybinding.py, silently swallowing shortcuts like open-file ('o') and
        open-recent ('z') even though there is no text to protect from being
        overwritten. Falls back to the root window so those shortcuts keep
        firing right after a view switch.
        """

        if (
            self._editor_document_state == EDITOR_DOCUMENT_LOADED
            and self.editor_widget is not None
            and bool(self.editor_widget.winfo_exists())
        ):
            self.editor_widget.focus_set()
        elif self.root is not None:
            self.root.focus_set()

    def _focus_preview_canvas_if_available(self):
        """Moves keyboard focus onto the preview canvas so the editor text field no longer holds it."""

        preview_canvas = getattr(self, "preview_canvas", None)
        if preview_canvas is not None and bool(preview_canvas.winfo_exists()):
            preview_canvas.focus_set()
        elif self.root is not None:
            self.root.focus_set()

    def _schedule_equal_split(self):
        """Starts a guarded retry cycle to place the splitter in the middle."""

        self._equal_split_attempts = 0
        if bool(getattr(self, "_reduce_motion", False)):
            self._set_equal_split()
            return
        self.root.after_idle(self._set_equal_split)

    def _set_equal_split(self):
        """Sets a 50/50 split when both panes are visible."""

        if self.editor_preview_paned is None:
            return

        panes = self.editor_preview_paned.panes()
        if len(panes) != 2:
            return

        total_width = self.editor_preview_paned.winfo_width()
        if total_width <= 80:
            if bool(getattr(self, "_reduce_motion", False)):
                return
            if self._equal_split_attempts < 10:
                self._equal_split_attempts += 1
                self.root.after(30, self._set_equal_split)
            return

        try:
            preferences = getattr(self, "user_preferences", {})
            split_ratio = float(preferences.get("startup_split_ratio", 0.5) or 0.5)
            split_ratio = max(0.2, min(0.8, split_ratio))
            split_x = max(1, int(total_width * split_ratio))
            if hasattr(self.editor_preview_paned, "sashpos"):
                self.editor_preview_paned.sashpos(0, split_x)
            else:
                self.editor_preview_paned.sash_place(0, split_x, 1)
            self._equal_split_attempts = 0
        except ui.TclError:
            if bool(getattr(self, "_reduce_motion", False)):
                return
            if self._equal_split_attempts < 10:
                self._equal_split_attempts += 1
                self.root.after(30, self._set_equal_split)
