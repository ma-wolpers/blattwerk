"""Editor mixin: inline Suchen/Ersetzen-Leiste im Schreibbereich (Strg+F / Strg+H).

Orientiert sich an klassischen Texteditor-Suchfunktionen: standardmäßig
Groß-/Kleinschreibung ignorierend, literale (nicht regex-basierte) Suche,
zyklische Navigation, Start ab aktuellem Cursor bzw. aktuellem Treffer.
Die eigentliche Matching-/Navigationslogik lebt in reinen, Tk-unabhängigen
Funktionen auf Modulebene (`_find_all_matches`, `_resolve_next_match_index`,
`_resolve_initial_match_index`) und ist direkt per `pytest` testbar; die
Mixin-Methoden orchestrieren nur noch Anzeige, Tags, Cursor und Ersetzen.

Kein neues Widget-Klassen-Typ (Strict-bw-gui-Policy): die Suchleiste ist
ein normales `widgets.Frame`, das inline oberhalb des Editor-Textfelds
ein-/ausgeblendet wird -- kein Toplevel-Popup.
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets


def _find_all_matches(text: str, query: str, case_sensitive: bool = False) -> list[tuple[int, int]]:
    """Returns all (start, end) character-offset spans of `query` in `text`.

    Literale Suche (kein Regex). Leere `query` liefert `[]` -- keine
    Treffer, kein Fehler.
    """
    if not query:
        return []

    haystack = text if case_sensitive else text.lower()
    needle = query if case_sensitive else query.lower()

    matches: list[tuple[int, int]] = []
    start = 0
    needle_length = len(needle)
    while True:
        found = haystack.find(needle, start)
        if found == -1:
            break
        matches.append((found, found + needle_length))
        start = found + needle_length if needle_length > 0 else found + 1

    return matches


def _resolve_next_match_index(match_count: int, current_index: int | None, direction: int) -> int | None:
    """Returns the next match index (cyclic) given the current index and a step direction.

    `direction` is `+1` (weiter) oder `-1` (zurück). Ohne aktuellen Treffer
    (`current_index=None`) wird der erste bzw. letzte Treffer je nach
    Richtung gewählt. Bei `match_count == 0` liefert die Funktion `None`.
    """
    if match_count <= 0:
        return None
    if current_index is None:
        return 0 if direction >= 0 else match_count - 1
    return (current_index + direction) % match_count


def _resolve_initial_match_index(matches: list[tuple[int, int]], cursor_offset: int) -> int | None:
    """Returns the index of the first match at or after `cursor_offset` (wraps to the first match).

    Bildet "Suche startet vom aktuellen Cursor aus" ab: wird für eine
    frische Suche (Öffnen der Leiste, geänderte Suchanfrage, nach einem
    Ersetzen-Vorgang) verwendet, nicht für Weiter/Zurück-Navigation
    zwischen bereits bekannten Treffern.
    """
    if not matches:
        return None
    for index, (start, _end) in enumerate(matches):
        if start >= cursor_offset:
            return index
    return 0


class BlattwerkAppEditorSearchMixin:
    """Verwaltet die inline Suchen/Ersetzen-Leiste oberhalb des Editor-Textfelds."""

    def _build_editor_search_bar(self, parent, before_widget):
        """Creates the (initially hidden) inline find/replace bar above the editor text widget."""

        self._editor_search_before_widget = before_widget
        self._editor_search_frame = widgets.Frame(parent)

        find_row = widgets.Frame(self._editor_search_frame)
        find_row.pack(fill="x")

        widgets.Label(find_row, text="Suchen:").pack(side="left")
        self._editor_search_query_entry = widgets.Entry(
            find_row, textvariable=self._editor_search_query_var, width=28
        )
        self._editor_search_query_entry.pack(side="left", padx=(4, 4))
        self._editor_search_query_entry.bind("<Return>", lambda _event: self._run_editor_search(direction=1))
        self._editor_search_query_entry.bind(
            "<Shift-Return>", lambda _event: self._run_editor_search(direction=-1)
        )
        self._editor_search_query_entry.bind("<Escape>", self._close_editor_search_bar)
        self._editor_search_query_var.trace_add("write", self._on_editor_search_query_changed)

        widgets.Label(find_row, textvariable=self._editor_search_match_count_var, width=8).pack(
            side="left", padx=(0, 8)
        )
        widgets.Button(
            find_row, text="▲", width=3, command=lambda: self._run_editor_search(direction=-1)
        ).pack(side="left")
        widgets.Button(
            find_row, text="▼", width=3, command=lambda: self._run_editor_search(direction=1)
        ).pack(side="left", padx=(4, 8))
        widgets.Checkbutton(
            find_row,
            text="Groß-/Kleinschreibung",
            variable=self._editor_search_case_sensitive_var,
            command=self._toggle_editor_search_case_sensitive,
        ).pack(side="left")
        widgets.Button(find_row, text="×", width=3, command=self._close_editor_search_bar).pack(
            side="right"
        )

        self._editor_search_replace_row = widgets.Frame(self._editor_search_frame)
        widgets.Label(self._editor_search_replace_row, text="Ersetzen:").pack(side="left")
        self._editor_search_replace_entry = widgets.Entry(
            self._editor_search_replace_row, textvariable=self._editor_search_replace_var, width=28
        )
        self._editor_search_replace_entry.pack(side="left", padx=(4, 4))
        self._editor_search_replace_entry.bind(
            "<Return>", lambda _event: self._replace_current_editor_match()
        )
        self._editor_search_replace_entry.bind("<Escape>", self._close_editor_search_bar)
        widgets.Button(
            self._editor_search_replace_row, text="Ersetzen", command=self._replace_current_editor_match
        ).pack(side="left", padx=(0, 4))
        widgets.Button(
            self._editor_search_replace_row, text="Alle ersetzen", command=self._replace_all_editor_matches
        ).pack(side="left")

    def _toggle_editor_find_bar(self, _event=None):
        """Opens the find bar in find-only mode (Ctrl+F) or refocuses it if already open."""

        self._open_editor_search_bar(show_replace=False)
        return "break"

    def _toggle_editor_replace_bar(self, _event=None):
        """Opens the find bar with the replace row visible (Ctrl+H) or reveals it if already open."""

        self._open_editor_search_bar(show_replace=True)
        return "break"

    def _open_editor_search_bar(self, show_replace: bool):
        """Shows the search bar (prefilled from selection if any), reveals the replace row if requested."""

        if self.editor_widget is None or self._editor_search_frame is None:
            return

        if not self._editor_search_visible:
            self._editor_search_frame.pack(
                fill="x", padx=8, pady=(0, 4), before=self._editor_search_before_widget
            )
            self._editor_search_visible = True
            selection_ranges = self.editor_widget.tag_ranges("sel")
            if selection_ranges:
                selected_text = self.editor_widget.get(selection_ranges[0], selection_ranges[1])
                self._editor_search_query_var.set(selected_text)
            else:
                self._editor_search_query_var.set("")

        if show_replace:
            if not self._editor_search_replace_visible:
                self._editor_search_replace_row.pack(fill="x", pady=(4, 0))
                self._editor_search_replace_visible = True
        elif self._editor_search_replace_visible:
            self._editor_search_replace_row.pack_forget()
            self._editor_search_replace_visible = False

        self._run_editor_search(direction=0)
        self._editor_search_query_entry.focus_set()
        self._editor_search_query_entry.select_range(0, "end")
        self._editor_search_query_entry.icursor("end")

    def _close_editor_search_bar(self, _event=None):
        """Hides the find/replace bar, clears match highlighting, and returns focus to the editor."""

        if self._editor_search_frame is not None:
            self._editor_search_frame.pack_forget()
        if self._editor_search_replace_row is not None:
            self._editor_search_replace_row.pack_forget()
        self._editor_search_visible = False
        self._editor_search_replace_visible = False
        self._editor_search_matches = []
        self._editor_search_current_index = None

        if self.editor_widget is not None:
            self.editor_widget.tag_remove("search_match", "1.0", "end")
            self.editor_widget.tag_remove("search_match_current", "1.0", "end")
            self.editor_widget.focus_set()

        return "break"

    def _current_editor_cursor_char_offset(self) -> int:
        """Returns the current cursor position as a character offset from the start of the buffer."""

        if self.editor_widget is None:
            return 0
        raw_count = self.editor_widget.count("1.0", "insert", "chars")
        if isinstance(raw_count, (tuple, list)):
            return int(raw_count[0]) if raw_count else 0
        return int(raw_count or 0)

    def _on_editor_search_query_changed(self, *_args):
        """Reruns the search live as the query text changes."""

        if not self._editor_search_visible:
            return
        self._run_editor_search(direction=0)

    def _toggle_editor_search_case_sensitive(self):
        """Reruns the search immediately when the case-sensitivity toggle changes."""

        self._run_editor_search(direction=0)

    def _run_editor_search(self, direction: int = 1):
        """Recomputes matches for the current query and moves to the next/previous match."""

        if self.editor_widget is None:
            return

        query = self._editor_search_query_var.get()
        case_sensitive = bool(self._editor_search_case_sensitive_var.get())
        text = self.editor_widget.get("1.0", "end-1c")
        matches = _find_all_matches(text, query, case_sensitive=case_sensitive)
        self._editor_search_matches = matches

        if not matches:
            self._editor_search_current_index = None
        elif direction == 0:
            cursor_offset = self._current_editor_cursor_char_offset()
            self._editor_search_current_index = _resolve_initial_match_index(matches, cursor_offset)
        else:
            self._editor_search_current_index = _resolve_next_match_index(
                len(matches), self._editor_search_current_index, direction
            )

        self._update_editor_search_match_display()

    def _update_editor_search_match_display(self):
        """Refreshes match tags, current-match highlight, cursor position, and the match counter."""

        if self.editor_widget is None:
            return

        self.editor_widget.tag_remove("search_match", "1.0", "end")
        self.editor_widget.tag_remove("search_match_current", "1.0", "end")

        matches = self._editor_search_matches
        for index, (start, end) in enumerate(matches):
            tag = "search_match_current" if index == self._editor_search_current_index else "search_match"
            self.editor_widget.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")

        if self._editor_search_current_index is not None:
            current_start, _current_end = matches[self._editor_search_current_index]
            self.editor_widget.mark_set("insert", f"1.0+{current_start}c")
            self.editor_widget.see(f"1.0+{current_start}c")
            self._editor_search_match_count_var.set(
                f"{self._editor_search_current_index + 1}/{len(matches)}"
            )
        else:
            self._editor_search_match_count_var.set("0/0")

    def _replace_current_editor_match(self, _event=None):
        """Replaces the currently highlighted match and advances to the next one."""

        query = self._editor_search_query_var.get()
        if not query or self.editor_widget is None:
            return "break"
        if self._editor_search_current_index is None or not self._editor_search_matches:
            return "break"

        replacement = self._editor_search_replace_var.get()
        start, end = self._editor_search_matches[self._editor_search_current_index]
        self.editor_widget.delete(f"1.0+{start}c", f"1.0+{end}c")
        self.editor_widget.insert(f"1.0+{start}c", replacement)
        self.editor_widget.mark_set("insert", f"1.0+{start + len(replacement)}c")

        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)
        self._run_editor_search(direction=0)
        return "break"

    def _replace_all_editor_matches(self, _event=None):
        """Replaces every current match in the editor buffer and recomputes the match display."""

        query = self._editor_search_query_var.get()
        if not query or self.editor_widget is None:
            return "break"

        case_sensitive = bool(self._editor_search_case_sensitive_var.get())
        text = self.editor_widget.get("1.0", "end-1c")
        matches = _find_all_matches(text, query, case_sensitive=case_sensitive)
        if not matches:
            self._editor_search_matches = []
            self._editor_search_current_index = None
            self._update_editor_search_match_display()
            return "break"

        replacement = self._editor_search_replace_var.get()
        # Rueckwaerts ersetzen, damit bereits verarbeitete Offsets die noch
        # ausstehenden (davorliegenden) Treffer nicht verschieben.
        for start, end in reversed(matches):
            self.editor_widget.delete(f"1.0+{start}c", f"1.0+{end}c")
            self.editor_widget.insert(f"1.0+{start}c", replacement)

        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)
        if hasattr(self, "status_var"):
            self.status_var.set(f"{len(matches)} Ersetzung(en) durchgeführt.")

        self._editor_search_current_index = None
        self._run_editor_search(direction=0)
        return "break"
