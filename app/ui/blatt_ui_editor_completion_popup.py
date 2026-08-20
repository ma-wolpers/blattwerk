"""Editor completion mixin: popup lifecycle (open/render/accept/close/navigate).

Ausgelagert aus `blatt_ui_editor.py` (300-Zeilen-Konvention, reiner
Struktur-Refactor ohne Verhaltensänderung), zweites von drei
Completion-Modulen. Kontext-Erkennung lebt in
`blatt_ui_editor_completion_context.py`, Nutzungsbasiertes Ranking in
`blatt_ui_editor_completion_ranking.py` -- dieses Modul ruft beide über
`self.` auf, ohne sie zu importieren (gemeinsame Mixin-Komposition in
`blatt_ui.py`).
"""

from __future__ import annotations

import re

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui


class BlattwerkAppEditorCompletionPopupMixin:
    """Verwaltet das Vorschlags-Popup: öffnen, navigieren, übernehmen, schließen."""

    def _on_editor_completion_trigger(self, _event=None):
        """Opens completion suggestions manually via Ctrl+Space."""

        self._open_editor_completion(auto=False)
        return "break"

    def _on_editor_completion_move_up(self, _event=None):
        """Moves completion selection up when popup is visible."""

        if not self._is_editor_completion_visible() or self._editor_completion_listbox is None:
            return None

        selection = self._editor_completion_listbox.curselection()
        current = selection[0] if selection else 0
        new_index = max(0, current - 1)
        self._editor_completion_listbox.selection_clear(0, "end")
        self._editor_completion_listbox.selection_set(new_index)
        self._editor_completion_listbox.activate(new_index)
        self._editor_completion_listbox.see(new_index)
        return "break"

    def _on_editor_completion_move_down(self, _event=None):
        """Moves completion selection down when popup is visible."""

        if not self._is_editor_completion_visible() or self._editor_completion_listbox is None:
            return None

        selection = self._editor_completion_listbox.curselection()
        current = selection[0] if selection else 0
        max_index = max(0, len(self._editor_completion_items) - 1)
        new_index = min(max_index, current + 1)
        self._editor_completion_listbox.selection_clear(0, "end")
        self._editor_completion_listbox.selection_set(new_index)
        self._editor_completion_listbox.activate(new_index)
        self._editor_completion_listbox.see(new_index)
        return "break"

    def _on_editor_completion_enter(self, _event=None):
        """Accepts completion on enter when popup is visible."""

        if self._editor_completion_items:
            return self._on_editor_completion_accept()
        return None

    def _on_editor_completion_reject_and_newline(self, _event=None):
        """Closes any open completion popup and inserts a plain newline (Ctrl+Enter / Shift+Enter).

        Both modifiers previously fell through to the unmodified `<Return>`
        binding (no more specific binding existed), so they accepted the
        open suggestion just like plain Enter -- exactly the opposite of
        "reject". Explicitly bound so the more specific pattern wins.
        """

        self._close_editor_completion()
        self.editor_widget.insert("insert", "\n")
        self.editor_widget.see("insert")
        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)
        return "break"

    def _open_editor_completion(self, auto: bool):
        """Collects completion suggestions and renders popup near caret."""

        if self.editor_widget is None:
            return

        context = self._collect_editor_completion_context(auto=auto)
        if context is None:
            self._close_editor_completion()
            return

        suggestions = context.get("suggestions") or []
        if not suggestions:
            self._close_editor_completion()
            return

        completion_kind = context.get("kind")
        raw_meta = context.get("meta")
        completion_meta = dict(raw_meta) if isinstance(raw_meta, dict) else {}
        if completion_kind == "block_type":
            suggestions = self._rank_block_type_suggestions(suggestions)
        if completion_kind == "option_value":
            suggestions = self._rank_option_value_suggestions(
                suggestions,
                block_type=str(completion_meta.get("block_type") or ""),
                option_key=str(completion_meta.get("option_key") or ""),
            )

        self._editor_completion_replace_start = context["replace_start"]
        self._editor_completion_replace_end = context["replace_end"]
        self._editor_completion_context_kind = completion_kind
        self._editor_completion_context_meta = completion_meta

        if self._editor_completion_popup is None or not self._editor_completion_popup.winfo_exists():
            popup = ui.Toplevel(self.root)
            popup.withdraw()
            popup.overrideredirect(True)
            popup.transient(self.root)

            listbox = ui.Listbox(
                popup,
                activestyle="none",
                height=min(8, len(suggestions)),
                width=72,
            )
            listbox.pack(fill="both", expand=True)
            listbox.bind("<Double-Button-1>", self._on_editor_completion_accept)
            listbox.bind("<Return>", self._on_editor_completion_accept)
            listbox.bind("<Escape>", lambda _event: self._close_editor_completion())

            self._editor_completion_popup = popup
            self._editor_completion_listbox = listbox

        if self._editor_completion_listbox is None:
            return

        self._editor_completion_items = list(suggestions)
        width_chars = max((len(item["label"]) for item in self._editor_completion_items), default=40)
        preferences = getattr(self, "user_preferences", {})
        popup_width_mode = str(preferences.get("completion_popup_width_mode", "wide") or "wide")
        if popup_width_mode == "compact":
            min_width = 32
            max_width = 72
        elif popup_width_mode == "normal":
            min_width = 40
            max_width = 90
        else:
            min_width = 46
            max_width = 110
        self._editor_completion_listbox.configure(width=min(max_width, max(min_width, width_chars + 2)))
        self._editor_completion_listbox.configure(height=min(8, len(self._editor_completion_items)))
        self._editor_completion_listbox.delete(0, "end")
        for item in self._editor_completion_items:
            self._editor_completion_listbox.insert("end", item["label"])

        self._editor_completion_listbox.selection_clear(0, "end")
        self._editor_completion_listbox.selection_set(0)
        self._editor_completion_listbox.activate(0)

        caret_box = self.editor_widget.bbox("insert")
        if caret_box is None:
            self._close_editor_completion()
            return

        x = self.editor_widget.winfo_rootx() + caret_box[0]
        y = self.editor_widget.winfo_rooty() + caret_box[1] + caret_box[3] + 2
        self._editor_completion_popup.geometry(f"+{x}+{y}")
        self._editor_completion_popup.deiconify()
        self._editor_completion_popup.lift()

    def _on_editor_completion_accept(self, _event=None):
        """Applies currently selected completion entry to the editor text."""

        if self.editor_widget is None or self._editor_completion_listbox is None:
            return "break"

        selection = self._editor_completion_listbox.curselection()
        if not selection:
            return "break"

        candidate = self._editor_completion_items[selection[0]]
        if not candidate:
            return "break"

        self._record_editor_completion_usage(candidate)

        insert_text, cursor_offset = self._resolve_completion_insert(candidate)
        if insert_text is None or cursor_offset is None:
            return "break"

        replace_start = self._editor_completion_replace_start or self.editor_widget.index("insert")
        replace_end = self._editor_completion_replace_end or self.editor_widget.index("insert")
        self.editor_widget.delete(replace_start, replace_end)
        self.editor_widget.insert(replace_start, insert_text)
        self.editor_widget.mark_set("insert", f"{replace_start}+{cursor_offset}c")
        self.editor_widget.focus_set()
        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)
        self._close_editor_completion()
        return "break"

    @staticmethod
    def _resolve_completion_insert(candidate):
        """Returns insert text plus target cursor offset after insertion."""

        if not isinstance(candidate, dict):
            return None, None

        raw_insert_text = candidate.get("insert_text")
        if raw_insert_text is None:
            return None, None

        placeholder_pattern = re.compile(r"\[\[(\d+):([^\]]*)\]\]")
        occurrences = []
        output_parts = []
        scan_index = 0

        for match in placeholder_pattern.finditer(raw_insert_text):
            output_parts.append(raw_insert_text[scan_index:match.start()])
            replacement_text = match.group(2)
            output_offset = len("".join(output_parts))
            output_parts.append(replacement_text)
            occurrences.append(
                {
                    "order": int(match.group(1)),
                    "start": output_offset,
                    "end": output_offset + len(replacement_text),
                }
            )
            scan_index = match.end()

        output_parts.append(raw_insert_text[scan_index:])
        parsed_insert_text = "".join(output_parts)

        if occurrences:
            ordered = sorted(occurrences, key=lambda item: (item["order"], item["start"]))
            return parsed_insert_text, ordered[0]["start"]

        cursor_marker = "[[CURSOR]]"
        marker_index = parsed_insert_text.find(cursor_marker)
        if marker_index >= 0:
            insert_text = parsed_insert_text.replace(cursor_marker, "", 1)
            return insert_text, marker_index

        return parsed_insert_text, len(parsed_insert_text)

    def _close_editor_completion(self):
        """Hides and clears completion popup state."""

        if self._editor_completion_popup is not None and self._editor_completion_popup.winfo_exists():
            self._editor_completion_popup.withdraw()

        self._editor_completion_items = []
        self._editor_completion_replace_start = None
        self._editor_completion_replace_end = None
        self._editor_completion_context_kind = None
        self._editor_completion_context_meta = {}

    def _is_editor_completion_visible(self) -> bool:
        """Returns true if completion popup exists and is currently visible."""

        if self._editor_completion_popup is None:
            return False
        if not self._editor_completion_popup.winfo_exists():
            return False
        return self._editor_completion_popup.state() != "withdrawn"
