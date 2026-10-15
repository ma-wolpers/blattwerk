"""Schreibbereich: Tastenhandler, Completion-Abgleich beim Tippen, Marker-Tasten, Wortlöschen, Snippets (BlattwerkApp-Mixin).

Aus ``blatt_ui_editor.py`` ausgelagert (300-Zeilen-Regel), Methoden unverändert."""

from __future__ import annotations

from .editor_marker_shortcuts import apply_backtick_marker, apply_caret_marker, apply_dollar_marker, apply_highlight_marker, apply_pipe_marker, apply_star_marker, apply_tilde_marker, apply_underscore_marker, selection_crosses_math_boundary
from .ui_constants import EDITOR_DOCUMENT_LOADED


class BlattwerkAppEditorKeysMixin:
    """Schreibbereich: Tastenhandler, Completion-Abgleich beim Tippen, Marker-Tasten, Wortlöschen, Snippets (BlattwerkApp-Mixin)."""

    def _on_editor_key_release(self, event=None):
        """Keeps completion popup in sync while typing on matching contexts."""

        if self.editor_widget is None:
            return

        if event is None:
            return

        if event.keysym in {"Escape"}:
            return

        if event.keysym in {
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
            "Alt_L",
            "Alt_R",
            "Meta_L",
            "Meta_R",
            "ISO_Level3_Shift",
        }:
            return

        if event.keysym in {"period", "colon"} and self._is_editor_completion_visible():
            return

        if event.keysym in {"Up", "Down", "Left", "Right"}:
            self._queue_editor_block_pair_highlight()
            return

        preferences = getattr(self, "user_preferences", {})
        if not bool(preferences.get("completion_auto_enabled", True)):
            self._queue_editor_block_pair_highlight()
            return

        trigger_chars = {"_", " ", "!"}
        if bool(preferences.get("completion_trigger_colon", True)):
            trigger_chars.add(":")
        if bool(preferences.get("completion_trigger_equals", True)):
            trigger_chars.add("=")

        trigger_keys = {"BackSpace"}
        if bool(preferences.get("completion_trigger_enter", True)):
            trigger_keys.add("Return")

        should_trigger = (
            event.keysym in trigger_keys
            or bool(event.char and (event.char.isalnum() or event.char in trigger_chars))
        )

        if should_trigger:
            self._open_editor_completion(auto=True)
        else:
            self._close_editor_completion()

        self._queue_editor_block_pair_highlight()

    def _on_editor_insert_triple_pair(self, _event=None):
        """Inserts `::: :::` and opens completion at center cursor position."""

        if self.editor_widget is None:
            return "break"

        insert_index = self.editor_widget.index("insert")
        self.editor_widget.insert(insert_index, "::: :::")
        self.editor_widget.mark_set("insert", f"{insert_index}+3c")
        self.editor_widget.focus_set()
        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)
        self._open_editor_completion(auto=False)
        return "break"

    _MARKER_KEY_HANDLERS = {
        "*": apply_star_marker,
        "_": apply_underscore_marker,
        "=": apply_highlight_marker,
        "~": apply_tilde_marker,
        "^": apply_caret_marker,
        "|": apply_pipe_marker,
        "$": apply_dollar_marker,
    }
    """Marker-Tasten mit einheitlicher `(before, selected, after) -> MarkerEdit`-
    Signatur. `` ` `` fehlt hier absichtlich -- es braucht zusätzlich das
    `is_multiline`-Flag und wird in `_on_editor_backtick_key` separat
    behandelt (siehe dort)."""

    _MARKER_CONTEXT_CHARS = 40

    def _editor_marker_context(self):
        """Liefert `(before, selected, after)` um die aktuelle Selektion, plus die absoluten Zeichen-Offsets.

        Kontext ist auf `_MARKER_CONTEXT_CHARS` begrenzt -- für die
        Randlauf-Erkennung reicht ein kurzer Ausschnitt, das volle Dokument
        muss dafür nicht gelesen werden. Liefert `None`, wenn keine
        Selektion existiert.
        """
        if self.editor_widget is None:
            return None

        selection = self.editor_widget.tag_ranges("sel")
        if not selection:
            return None

        sel_first, sel_last = selection[0], selection[1]
        before = self.editor_widget.get(f"{sel_first} -{self._MARKER_CONTEXT_CHARS}c", sel_first)
        selected = self.editor_widget.get(sel_first, sel_last)
        after = self.editor_widget.get(sel_last, f"{sel_last} +{self._MARKER_CONTEXT_CHARS}c")
        return before, selected, after, sel_first, sel_last

    def _editor_selection_crosses_math(self, sel_first, sel_last) -> bool:
        """Prüft die Selektion gegen das GESAMTE Dokument auf eine Formelgrenzen-Überschneidung."""
        full_text = self.editor_widget.get("1.0", "end-1c")
        start_offset = len(self.editor_widget.get("1.0", sel_first))
        end_offset = len(self.editor_widget.get("1.0", sel_last))
        return selection_crosses_math_boundary(full_text, start_offset, end_offset)

    def _apply_editor_marker_edit(self, sel_first, sel_last, edit) -> None:
        """Wendet ein `MarkerEdit` an: Text ersetzen, neue (innere) Selektion setzen, Editor-Zustand aktualisieren.

        Reihenfolge ist hier bewusst wichtig (Tk löst einen relativen
        Indexausdruck wie `"1.7 -1c"` bei JEDEM Aufruf frisch gegen den
        AKTUELLEN Textinhalt auf, nicht gegen den Zustand zum Zeitpunkt der
        String-Erzeugung):
        1. `replace_start`/`replace_end` werden VOR jeder Mutation zu
           konkreten `"zeile.spalte"`-Strings aufgelöst -- sie beziehen
           sich auf die ALTE Selektion, deren Zeilenlänge sich durch das
           gleich folgende `delete()` ändert.
        2. `select_from`/`select_to` werden dagegen ERST NACH `insert()`
           aufgelöst -- sie beziehen sich auf `edit.replacement`, dessen
           Länge von der alten Selektion abweichen kann (z. B.
           `*Welt*` -> `**Welt**`); vor dem Einfügen existiert dieser
           Text an der Zielposition schlicht noch nicht.
        Beide Fehler (zu früh bzw. zu spät aufgelöst) wurden beim Testen
        mit einem echten Tk-`Text`-Widget als reale Bugs gefunden.
        """
        replace_start = self.editor_widget.index(
            f"{sel_first} -{edit.strip_left}c" if edit.strip_left else sel_first
        )
        replace_end = self.editor_widget.index(
            f"{sel_last} +{edit.strip_right}c" if edit.strip_right else sel_last
        )

        self.editor_widget.delete(replace_start, replace_end)
        self.editor_widget.insert(replace_start, edit.replacement)

        select_from = self.editor_widget.index(f"{replace_start} +{edit.select_start}c")
        select_to = self.editor_widget.index(f"{replace_start} +{edit.select_end}c")
        self.editor_widget.tag_remove("sel", "1.0", "end")
        self.editor_widget.tag_add("sel", select_from, select_to)
        self.editor_widget.mark_set("insert", select_to)

        self.editor_widget.focus_set()
        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)

    def _on_editor_marker_key(self, event, marker_char):
        """Dispatcht eine Marker-Tastendruck auf die aktuelle Editor-Selektion.

        Liefert `None` (fällt auf normales Zeichen-Einfügen zurück), wenn
        nichts selektiert ist -- so bleibt Tippen von `*`/`_`/`=`/`~`/`^`/
        `|`/`$` außerhalb des dokumentierten "Text markieren, Taste drücken"-
        Ablaufs unverändert normales Verhalten. Verweigert die Aktion
        (ohne Textänderung), wenn die Selektion eine `$...$`-Formelgrenze
        überschneidet -- die konkrete Umsetzung der geforderten Absicherung
        gegen Formatierungsfehler durch falsche Auswertungsreihenfolge.
        """
        context = self._editor_marker_context()
        if context is None:
            return None

        before, selected, after, sel_first, sel_last = context
        if self._editor_selection_crosses_math(sel_first, sel_last):
            self.status_var.set("Markierung überschneidet eine Formel ($...$) -- Aktion abgebrochen.")
            return "break"

        handler = self._MARKER_KEY_HANDLERS[marker_char]
        edit = handler(before, selected, after)
        self._apply_editor_marker_edit(sel_first, sel_last, edit)
        return "break"

    def _on_editor_backtick_key(self, _event=None):
        """Wie `_on_editor_marker_key`, aber für `` ` `` mit Einzeilig/Mehrzeilig-Verzweigung."""
        context = self._editor_marker_context()
        if context is None:
            return None

        before, selected, after, sel_first, sel_last = context
        if self._editor_selection_crosses_math(sel_first, sel_last):
            self.status_var.set("Markierung überschneidet eine Formel ($...$) -- Aktion abgebrochen.")
            return "break"

        is_multiline = str(sel_first).split(".")[0] != str(sel_last).split(".")[0]
        edit = apply_backtick_marker(before, selected, after, is_multiline=is_multiline)
        self._apply_editor_marker_edit(sel_first, sel_last, edit)
        return "break"

    def _on_editor_escape(self, _event=None):
        """Closes completion popup when escape is pressed in editor."""

        self._close_editor_completion()
        if self.root is not None and bool(self.root.winfo_exists()):
            self.root.focus_set()
        return "break"

    def _on_editor_tab(self, _event=None):
        """Applies selected completion on tab when popup is visible."""

        if self._editor_completion_items:
            return self._on_editor_completion_accept()
        return None

    def _on_editor_shift_tab(self, _event=None):
        """No-op for completion flow when no popup action applies."""

        return None

    def _on_editor_delete_word_before(self, _event=None):
        """Deletes the word (or whitespace token) before the cursor (Ctrl+Backspace)."""

        cursor_pos = self.editor_widget.index("insert")
        line, col = map(int, cursor_pos.split("."))

        if col == 0:
            if line > 1:
                self.editor_widget.delete("insert -1c", "insert")
            return "break"

        text_before = self.editor_widget.get(f"{line}.0", cursor_pos)
        pos = len(text_before)

        while pos > 0 and text_before[pos - 1] in " \t":
            pos -= 1
        if pos > 0:
            if text_before[pos - 1].isalnum() or text_before[pos - 1] == "_":
                while pos > 0 and (text_before[pos - 1].isalnum() or text_before[pos - 1] == "_"):
                    pos -= 1
            else:
                while pos > 0 and not text_before[pos - 1].isalnum() and text_before[pos - 1] not in " \t_":
                    pos -= 1

        chars_to_delete = len(text_before) - pos
        if chars_to_delete > 0:
            self.editor_widget.delete(f"insert -{chars_to_delete}c", "insert")
        return "break"

    def _on_editor_delete_word_after(self, _event=None):
        """Deletes the word (or whitespace token) after the cursor (Ctrl+Delete)."""

        cursor_pos = self.editor_widget.index("insert")
        line_end = self.editor_widget.index("insert lineend")

        if self.editor_widget.compare(cursor_pos, "==", line_end):
            self.editor_widget.delete("insert", "insert +1c")
            return "break"

        text_after = self.editor_widget.get(cursor_pos, line_end)
        pos = 0

        while pos < len(text_after) and text_after[pos] in " \t":
            pos += 1
        if pos < len(text_after):
            if text_after[pos].isalnum() or text_after[pos] == "_":
                while pos < len(text_after) and (text_after[pos].isalnum() or text_after[pos] == "_"):
                    pos += 1
            else:
                while pos < len(text_after) and not text_after[pos].isalnum() and text_after[pos] not in " \t_":
                    pos += 1

        if pos > 0:
            self.editor_widget.delete("insert", f"insert +{pos}c")
        return "break"

    def _insert_editor_snippet(self, template: str):
        """Inserts a block snippet at the cursor. \\x01 in template marks cursor landing position."""

        if self.editor_widget is None:
            return "break"

        cursor_mark = "\x01"
        cursor_offset = template.find(cursor_mark)
        clean_text = template.replace(cursor_mark, "")

        insert_pos = self.editor_widget.index("insert")
        line, col = map(int, insert_pos.split("."))

        prefix = "\n" if col > 0 else ""
        self.editor_widget.insert(insert_pos, prefix + clean_text)

        if cursor_offset >= 0:
            text_to_cursor = prefix + template[:cursor_offset]
            newline_count = text_to_cursor.count("\n")
            last_newline = text_to_cursor.rfind("\n")
            cursor_line = line + newline_count
            cursor_col = len(text_to_cursor) - last_newline - 1 if last_newline >= 0 else col + len(text_to_cursor)
            self.editor_widget.mark_set("insert", f"{cursor_line}.{cursor_col}")

        self.editor_widget.see("insert")
        self.editor_widget.focus_set()
        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)
        return "break"

    def _on_editor_mouse_click(self, _event=None):
        """Closes completion popup when user clicks in editor.

        Returns "break" while no document is loaded, which stops Tk's
        built-in Text class binding for <Button-1> from running -- that
        binding unconditionally moves keyboard focus into the widget
        regardless of its `-state` (verified empirically: state="disabled"
        and takefocus=0 alone do not prevent click-to-focus). Without this
        guard, clicking the disabled editor would still focus it and make
        it the "text input focused" target for the global shortcut gating
        in shortcut_manager.py/keybinding.py, silently blocking shortcuts
        like open-file ('o') and open-recent ('z').
        """

        if self._editor_document_state != EDITOR_DOCUMENT_LOADED:
            return "break"

        self._close_editor_completion()
        if hasattr(self, "root"):
            self.root.after_idle(self._refresh_editor_block_pair_highlight)
