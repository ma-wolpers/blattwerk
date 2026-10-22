"""Schreibbereich: Tastenhandler, Completion-Abgleich beim Tippen, Marker-Tasten, Wortlöschen, Snippets (BlattwerkApp-Mixin).

Aus ``blatt_ui_editor.py`` ausgelagert (300-Zeilen-Regel); Tasten über den bw-gui-Keyboard-Contract."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.contracts import Key
from bw_gui.contracts.events import EventResult
from bw_gui.contracts.key_spec import KeySpec
from bw_gui.runtime import WidgetShortcutBinder

from .editor_marker_shortcuts import apply_backtick_marker, apply_caret_marker, apply_dollar_marker, apply_highlight_marker, apply_pipe_marker, apply_star_marker, apply_tilde_marker, apply_underscore_marker, selection_crosses_math_boundary
from .ui_constants import EDITOR_DOCUMENT_LOADED


class BlattwerkAppEditorKeysMixin:
    """Schreibbereich: Tastenhandler, Completion-Abgleich beim Tippen, Marker-Tasten, Wortlöschen, Snippets (BlattwerkApp-Mixin)."""

    def _bind_editor_keys(self):
        """Bind the editor shortcuts on a ``WidgetShortcutBinder`` of the editor (before Text class bindings).

        Every definition is active while the editor itself has text focus. A handler
        returning ``None`` lets the key reach the Text class binding (e.g. ↑ moves
        the cursor while no completion is open, a marker key without selection is
        typed). Modifiers are exact; Shift+Tab therefore no longer needs a no-op
        binding to keep Tab's completion accept from firing. Ctrl+Shift+Enter keeps
        rejecting the completion like Ctrl+Enter (formerly Tk picked either binding).
        """
        _k = KeySpec.parse
        rows = [
            (_k("Ctrl+Space"), "completion.trigger", self._on_editor_completion_trigger),
            # Ctrl+":" -- formerly <Control-colon> plus <Control-Shift-period>; on the German
            # and US layouts ":" *is* Shift+".", so one logical spec covers both.
            (_k("Ctrl+:"), "insert_triple_pair", self._on_editor_insert_triple_pair),
            (_k("Escape (tolerate: Shift)"), "escape", self._on_editor_escape),
            (_k("Tab"), "completion.tab", self._on_editor_tab),
            (_k("Up"), "completion.up", self._on_editor_completion_move_up),
            (_k("Down"), "completion.down", self._on_editor_completion_move_down),
            (_k("Enter"), "completion.enter", self._on_editor_completion_enter),
            ([_k("Ctrl+Enter (tolerate: Shift)"), _k("Shift+Enter")], "completion.reject_newline", self._on_editor_completion_reject_and_newline),
            (_k("Ctrl+Backspace (tolerate: Shift)"), "delete_word_before", self._on_editor_delete_word_before),
            (_k("Ctrl+Delete (tolerate: Shift)"), "delete_word_after", self._on_editor_delete_word_after),
            (_k("Ctrl+F"), "find", self._toggle_editor_find_bar),
            (_k("Ctrl+H"), "replace", self._toggle_editor_replace_bar),
            (KeySpec.char("`"), "marker.backtick", self._on_editor_backtick_key),
        ]
        rows += [
            (KeySpec.char(marker), f"marker.{name}", lambda event, m=marker: self._on_editor_marker_key(event, m))
            for name, marker in (("star", "*"), ("underscore", "_"), ("equal", "="), ("tilde", "~"),
                                 ("caret", "^"), ("bar", "|"), ("dollar", "$"))
        ]
        keys = WidgetShortcutBinder(self.editor_widget)
        for spec, binding_id, handler in rows:
            keys.bind(spec, handler, binding_id=f"editor.{binding_id}", intent=f"editor.{binding_id}", allow_when_text_input=True)
        self._editor_keys = keys

    _EDITOR_ARROWS = frozenset({Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT})

    def _on_editor_key_after(self, event=None):
        """Keeps the completion popup in sync after a key reached the editor (``on_key(phase="after")``).

        Runs after the Text class binding inserted or deleted text, and only for keys
        no editor shortcut consumed (formerly ``<KeyRelease>``, which also fired after
        consumed keys -- e.g. after accepting a suggestion with Enter it reopened the
        list beside the explicit chaining rule). Lock and modifier keys (``Key.OTHER``
        without text) are ignored, the typed character comes from ``KeyEvent.text``.
        """

        if self.editor_widget is None or event is None:
            return

        if event.key is Key.ESCAPE:
            return

        if event.key is Key.OTHER and event.text is None:
            return

        if event.text in {".", ":"} and self._is_editor_completion_visible():
            return

        if event.key in self._EDITOR_ARROWS:
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

        trigger_keys = {Key.BACKSPACE}
        if bool(preferences.get("completion_trigger_enter", True)):
            trigger_keys.add(Key.ENTER)

        should_trigger = event.key in trigger_keys or bool(
            event.text and (event.text.isalnum() or event.text in trigger_chars)
        )

        if should_trigger:
            self._open_editor_completion(auto=True)
        else:
            self._close_editor_completion()

        self._queue_editor_block_pair_highlight()

    def _on_editor_insert_triple_pair(self, _event=None):
        """Inserts `::: :::` and opens completion at center cursor position."""

        if self.editor_widget is None:
            return EventResult.HANDLED

        insert_index = self.editor_widget.index("insert")
        self.editor_widget.insert(insert_index, "::: :::")
        self.editor_widget.mark_set("insert", f"{insert_index}+3c")
        self.editor_widget.focus_set()
        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)
        self._open_editor_completion(auto=False)
        return EventResult.HANDLED

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
            return EventResult.HANDLED

        handler = self._MARKER_KEY_HANDLERS[marker_char]
        edit = handler(before, selected, after)
        self._apply_editor_marker_edit(sel_first, sel_last, edit)
        return EventResult.HANDLED

    def _on_editor_backtick_key(self, _event=None):
        """Wie `_on_editor_marker_key`, aber für `` ` `` mit Einzeilig/Mehrzeilig-Verzweigung."""
        context = self._editor_marker_context()
        if context is None:
            return None

        before, selected, after, sel_first, sel_last = context
        if self._editor_selection_crosses_math(sel_first, sel_last):
            self.status_var.set("Markierung überschneidet eine Formel ($...$) -- Aktion abgebrochen.")
            return EventResult.HANDLED

        is_multiline = str(sel_first).split(".")[0] != str(sel_last).split(".")[0]
        edit = apply_backtick_marker(before, selected, after, is_multiline=is_multiline)
        self._apply_editor_marker_edit(sel_first, sel_last, edit)
        return EventResult.HANDLED

    def _on_editor_escape(self, _event=None):
        """Closes completion popup when escape is pressed in editor."""

        self._close_editor_completion()
        if self.root is not None and bool(self.root.winfo_exists()):
            self.root.focus_set()
        return EventResult.HANDLED

    def _on_editor_tab(self, _event=None):
        """Applies selected completion on tab when popup is visible."""

        if self._editor_completion_items:
            return self._on_editor_completion_accept()
        return None

    def _on_editor_delete_word_before(self, _event=None):
        """Deletes the word (or whitespace token) before the cursor (Ctrl+Backspace)."""

        cursor_pos = self.editor_widget.index("insert")
        line, col = map(int, cursor_pos.split("."))

        if col == 0:
            if line > 1:
                self.editor_widget.delete("insert -1c", "insert")
            return EventResult.HANDLED

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
        return EventResult.HANDLED

    def _on_editor_delete_word_after(self, _event=None):
        """Deletes the word (or whitespace token) after the cursor (Ctrl+Delete)."""

        cursor_pos = self.editor_widget.index("insert")
        line_end = self.editor_widget.index("insert lineend")

        if self.editor_widget.compare(cursor_pos, "==", line_end):
            self.editor_widget.delete("insert", "insert +1c")
            return EventResult.HANDLED

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
        return EventResult.HANDLED

    def _insert_editor_snippet(self, template: str):
        """Inserts a block snippet at the cursor. \\x01 in template marks cursor landing position."""

        if self.editor_widget is None:
            return

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

    def _on_editor_mouse_click(self, _event=None):
        """Closes completion popup when user clicks in editor.

        Returns ``HANDLED`` while no document is loaded, which stops Tk's
        built-in Text class binding for <Button-1> from running -- that
        binding unconditionally moves keyboard focus into the widget
        regardless of its `-state` (verified empirically: state="disabled"
        and takefocus=0 alone do not prevent click-to-focus). Without this
        guard, clicking the disabled editor would still focus it and make
        it the "text input focused" target for the global shortcut gating
        of the window binder (bw-gui text-input contract), silently blocking shortcuts
        like open-file ('o') and open-recent ('z').
        """

        if self._editor_document_state != EDITOR_DOCUMENT_LOADED:
            return EventResult.HANDLED

        self._close_editor_completion()
        if hasattr(self, "root"):
            self.root.after_idle(self._refresh_editor_block_pair_highlight)
