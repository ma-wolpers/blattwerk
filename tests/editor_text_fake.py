"""Gemeinsamer Lese-Fake für das Editor-`Text`-Widget in Completion-Tests (ohne Tk).

Vorher hatte jede Completion-Testdatei eine eigene Kopie, die nur einzelne
Zeilen lesen konnte. Liest der Code einen Bereich (z. B. den Dokumentanfang
für `scan_block_lines` oder das Frontmatter), musste jede Kopie einzeln
nachgezogen werden.
"""

from __future__ import annotations


class FakeEditorText:
    """Liest Zeilen und Zeilenbereiche wie Tk, mit fester Cursorposition.

    Args:
        text: Dokumenttext.
        cursor_line: Zeile von `insert` (1-basiert).
        cursor_col: Spalte von `insert`.
        total_line_count: Simulierte Dokumentlänge, auch weit über `text`
            hinaus. Zeilen hinter `text` liefern einen Fülltext, sodass ein
            Test prüfen kann, dass sie nie gelesen werden (`get_calls`).
    """

    FILLER_LINE = "Filler-Zeile ohne Frontmatter-Bezug"

    def __init__(self, text, cursor_line, cursor_col, total_line_count=None):
        self._lines = text.splitlines()
        self._cursor_line = cursor_line
        self._cursor_col = cursor_col
        self._total_line_count = total_line_count if total_line_count is not None else len(self._lines)
        self.get_calls = []

    def index(self, index):
        """`end-1c` ist der Anfang der letzten Zeile, alles andere die Cursorposition."""
        if index == "end-1c":
            return f"{self._total_line_count}.0"
        return f"{self._cursor_line}.{self._cursor_col}"

    def _line(self, line_no):
        if 0 < line_no <= len(self._lines):
            return self._lines[line_no - 1]
        if line_no <= self._total_line_count:
            return self.FILLER_LINE
        return ""

    def get(self, start, end):
        """Eine Zeile für `"n.0"`..`"n.end"`, ein Zeilenbereich (mit Zeilenumbrüchen) für `"a.0"`..`"b.0"`."""
        self.get_calls.append((start, end))
        first = int(start.split(".")[0])
        if end.endswith(".end"):
            return self._line(first)
        last = min(int(end.split(".")[0]) - 1, self._total_line_count)
        return "".join(self._line(n) + "\n" for n in range(first, last + 1))

    def compare(self, index1, op, index2):
        """Nur `>= "end-1c"` wird gebraucht: liegt `index1` hinter dem Dokumentende?"""
        assert op == ">="
        assert index2 == "end-1c"
        return int(index1.split(".")[0]) > self._total_line_count
